"""Pilot driver for the frozen pre-registration (docs/prereg-gdpevo-pilot.md, issue #27).

``optimise`` runs one group campaign per process; ``final`` runs that group's
comparison in a separate process once its campaign is closed, then feeds the
schedule-ordered records to ``loop.accept``. The final phase is trimmed to the
upstream-style comparison (docs/prereg-s4-addendum.md, issue #36); ``rebind``
records a pre-measurement identity change. Kernel modules are reused unchanged.
Hosts, keys and the champion skills come from a run-time JSON config, never code.

    python -m rsi_kernel.adapters.gdpevo.pilot optimise --config C --group G
    python -m rsi_kernel.adapters.gdpevo.pilot final --config C --group G
    python -m rsi_kernel.adapters.gdpevo.pilot rebind --config C --group G --addendum PATH
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import secrets
import shutil
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable, Mapping

from ...archive import Archive
from ...candidate import Candidate, content_id
from ...compare import _valid_score
from ...decision.backends import DeterministicBackend, JevBackend
from ...decision.envelope import EnvelopeBuilder
from ...decision.log import Decider
from ...loop import AcceptResult, ApprovalRecord, accept, run_campaign
from ...splits import load_splits
from .adapter import GDPevoAdapter, _verify_task, validate_skill
from .proposer import propose
from .tasks import FrozenTask, carve_splits

# Prereg "Objective and diagnostic scope" and "Carving map".
GROUPS = ("task_group_001", "task_group_002", "task_group_003")
DEV_IDS = ("001", "002", "003")
ADJ_IDS = ("004", "005")
TRAIN_IDS = DEV_IDS + ADJ_IDS
TEST_IDS = ("001", "002", "003", "004", "005")
# Prereg "Frozen inputs": revision, caps, timeouts; "Metric and repetitions": runs.
UPSTREAM_COMMIT = "5082a777379156a048881e94940d640702e5e09a"
RUNS = 3
MAX_ATTEMPTS = 3
EVAL_CAP = 36
SPEND_CAP = 42
TIMEOUT = 3600  # solver wall time and evaluator timeout, both 3600 s
# Prereg "Schedule" arm order; the control and the dev re-run are dropped by the S4
# addendum (#36): upstream compares conditions with acc@3 on test only.
ARMS = ("champion", "candidate")
# Prereg "Calibration (reproduced)": feasibility attempt 8, the first dev task.
CALIBRATION_TASK = (GROUPS[0], "train", DEV_IDS[0])
CALIBRATION_ANSWER_SHA256 = "5eb5cc630e4f69d1892b2fe721a593b8eb83513c96b723ff4c0f756e518ae96b"
CALIBRATION_OUTPUT_SHA256 = "12308ca22e257b47c05099acec8679a9a06f2205c99870578885098adbf6205e"
# Lead decision on #27: the proposer reaches the model only through the solver's
# per-run forwarder (alias model-fwd, listen 8080, base /v1 as in SOLVER_COMMAND).
PROPOSER_URL = "http://model-fwd:8080/v1/responses"


class PilotStop(RuntimeError):
    """Pre-run or phase-order STOP; nothing was solved after it."""


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")


def _git_head(root: Path) -> str:
    return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True,
                          capture_output=True).stdout.decode().strip()


def frozen_tasks(root: Path, group: str) -> list[FrozenTask]:
    """Hash every task-relative file (prereg "Freeze manifests"); contents stay unread."""
    tasks = []
    for subset, ids in (("train", TRAIN_IDS), ("test", TEST_IDS)):
        for task_id in ids:
            directory = Path(root) / "data/task_groups" / group / f"{subset}_tasks" / task_id
            tasks.append(FrozenTask(group, subset, task_id, {
                p.relative_to(directory).as_posix(): _sha(p) for p in sorted(directory.rglob("*")) if p.is_file()}))
    return tasks


def _evaluator_hash(tasks) -> str:
    # Approval binds input/evaluator hashes, code and revision (prereg "Approver").
    code = {p.name: _sha(p) for p in sorted(Path(__file__).parent.iterdir()) if p.suffix in (".py", "") and p.is_file()}
    return content_id({"tasks": json.dumps({t.item_id: dict(t.hashes) for t in tasks}, sort_keys=True),
                       "code": json.dumps(code, sort_keys=True), "upstream": UPSTREAM_COMMIT})


# Code identity: every file under src/rsi_kernel/ plus uv.lock (prereg "Freeze manifests").
PACKAGE_DIR = Path(__file__).resolve().parents[2]
LOCK_FILE = PACKAGE_DIR.parents[1] / "uv.lock"


def _code_hash(package: Path | None = None, lock: Path | None = None, exclude: tuple[str, ...] = ()) -> str:
    """sha256 over sorted (path relative to ``src/``, sha256) pairs plus uv.lock.

    ``exclude`` skips top-level package directories. The S5 addendum §8 records the
    kernel-only identity as ``_code_hash(exclude=("adapters",))``: same formula, so
    the two identities are comparable rather than derived two different ways.
    """
    package, lock = package or PACKAGE_DIR, lock or LOCK_FILE
    # __pycache__ is interpreter output written at import time, not frozen source.
    files = [(p.relative_to(package.parent).as_posix(), _sha(p)) for p in sorted(package.rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts
             and not any(part in exclude for part in p.relative_to(package).parts)]
    return hashlib.sha256(json.dumps([*files, ("uv.lock", _sha(lock))]).encode()).hexdigest()


def _identity(champion: Candidate, tasks) -> dict:
    return {"champion_id": champion.id, "evaluator_hash": _evaluator_hash(tasks), "code_hash": _code_hash()}


def _prerun(root, run_dir, groups, calibration_answer, calibration_replay) -> dict:
    """Prereg "Pre-run STOPs": source pin, manifest drift, calibration replay."""
    if _git_head(root) != UPSTREAM_COMMIT:
        raise PilotStop("source pin drift")
    tasks = {}
    for group in groups:
        tasks[group] = frozen_tasks(root, group)
        manifest = {t.item_id: dict(t.hashes) for t in tasks[group]}
        path = run_dir / group / "manifest.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            _json(path, manifest)
        elif json.loads(path.read_text()) != manifest:
            raise PilotStop("frozen task manifest drift")
    if _sha(calibration_answer) != CALIBRATION_ANSWER_SHA256:
        raise PilotStop("calibration answer drift")
    if hashlib.sha256(calibration_replay(Path(calibration_answer))).hexdigest() != CALIBRATION_OUTPUT_SHA256:
        raise PilotStop("calibration replay mismatch")
    return tasks


def _champion(config: Mapping) -> Candidate:
    if _sha(config["path"]) != config["sha256"]:
        raise PilotStop("champion hash mismatch")
    return Candidate({"SKILL.md": Path(config["path"]).read_text(encoding="utf-8")}, "text/plain")


def _adapter(root, group_dir, tasks, champion, solver, work, adapter_class=GDPevoAdapter):
    archive = Archive(group_dir / "public", group_dir / "private")
    splits = carve_splits(tasks, {tasks[0].group: list(DEV_IDS)})
    return adapter_class(root=root, champion=champion, tasks=tasks, splits=splits, solver=solver,
                         evaluator_timeout=TIMEOUT, work_dir=group_dir / work, archive=archive)


@dataclasses.dataclass(frozen=True)
class Hooks:
    """Artifact-specific pilot hooks (issue #35); ``SKILL`` is the frozen prereg default.

    Only these differ between the S4 skill artifact and the S5 library (addendum
    "JSON library artifact"): how the champion is loaded, the adapter class, the
    text the proposer container sees, that container's entrypoint and payload
    field, host admission, and the spend cap. ``container`` runs in the container
    on the rendered text; ``admit`` turns its payload into a candidate on the
    host, inside the logical PROPOSE and before evaluation.
    """

    load_champion: Callable[[Mapping], Candidate]
    adapter_class: type
    render: Callable[[Candidate], Candidate]  # host artifact -> text the container sees
    module: str  # container entrypoint, run as ``python -m <module> propose-in-container``
    result_key: str  # result.json field carrying the container's payload
    container: Callable[..., object]  # (text champion, records, splits, model) -> payload
    admit: Callable[..., Candidate | None]  # (champion, payload, decider, dev_results)
    spend_cap: int


def _skill_container(champion, records, splits, model):
    candidate = propose(champion, records, splits, model)
    return None if candidate is None else candidate.components["SKILL.md"]


def _admit_skill(champion, payload, decider, dev_results):
    # The skill artifact has no D4: the container's text is the candidate itself (#27).
    if payload is None:
        return None
    candidate = Candidate({"SKILL.md": payload}, "text/plain", parent_ids=(champion.id,))
    validate_skill(candidate)
    return candidate


SKILL = Hooks(load_champion=_champion, adapter_class=GDPevoAdapter, render=lambda champion: champion,
              module="rsi_kernel.adapters.gdpevo.pilot", result_key="skill",
              container=_skill_container, admit=_admit_skill, spend_cap=SPEND_CAP)


class _Calls:
    """Campaign spend meter: one line per model call, failed calls included (prereg "Caps")."""

    def __init__(self, path: Path):
        self.path, self.count = path, 0

    def log(self, kind, token_usage=None):
        self.count += 1
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"kind": kind, "token_usage": token_usage}) + "\n")


def _token_usage(result):
    # DockerSolver writes measurement.json; proposer/Jev tokens are not reported here.
    try:
        return json.loads((Path(result["evidence_dir"]) / "measurement.json").read_text())["token_usage"]
    except (TypeError, KeyError, OSError, ValueError):
        return None


def _metered_solver(solver, calls):
    def run(*args):
        result = None
        try:
            result = solver(*args)
            return result
        finally:
            calls.log("solver", _token_usage(result))
    return run


class _MeteredBackend:
    def __init__(self, backend, calls):
        self.backend, self.calls = backend, calls
        self.name, self.model = backend.name, backend.model

    def decide(self, envelope):
        self.calls.log("jev")
        return self.backend.decide(envelope)


def in_process_proposer(model, hooks=SKILL):
    """Host-process proposer for the wiring tests: fake model, no network."""
    def run(champion, records, splits, calls, *, decider=None, dev_results=()):
        def metered(prompt):
            calls.log("proposer")
            return model(prompt)
        return hooks.admit(champion, hooks.container(hooks.render(champion), records, splits, metered),
                           decider, dev_results)
    return run


def _proposer(adapter, run_proposer, calls, hooks=SKILL, decider=None):
    def run(champion, component, dev_results):
        # Prereg "Isolation": only dev input/output text and projected {score, correct}.
        records = []
        for row in dev_results:
            if not isinstance(row, dict) or row.get("failure") or "evidence_dir" not in row:
                continue
            task = adapter.tasks[row["item_id"]]
            records.append({"item_id": row["item_id"], "feedback": row["feedback"],
                            "input": (task.directory(adapter.root) / "input/prompt.txt").read_text(encoding="utf-8"),
                            "output": (Path(row["evidence_dir"]) / "work/answer.json").read_text(encoding="utf-8")})
        # Admission completes inside the logical PROPOSE, before evaluation (#35 addendum).
        return run_proposer(champion, records, adapter.splits, calls,
                            decider=decider, dev_results=dev_results)
    return run


def _zero_margin(comparison) -> bool:
    # Prereg "Retention rule": per-group candidate mean >= champion mean, ties pass.
    # Equal runs per task make the pair mean the group-mean difference.
    return comparison.mean_delta >= 0


def optimise_group(*, root: Path, run_dir: Path, group: str, champion: Mapping, solver, proposer,
                   jev, calibration_answer: Path, calibration_replay, hooks=SKILL):
    """``proposer(champion, records, splits, calls)``: in_process_proposer or ContainerProposer."""
    root, run_dir = Path(root), Path(run_dir)
    if group not in GROUPS or not run_dir.is_absolute():
        raise PilotStop("unknown group or relative run directory")
    group_dir = run_dir / group
    if (group_dir / "campaign.json").exists():
        raise PilotStop("campaign already run")
    tasks = _prerun(root, run_dir, [group], calibration_answer, calibration_replay)[group]
    calls = _Calls(group_dir / "calls.jsonl")
    champion = hooks.load_champion(champion)
    identity = _identity(champion, tasks)  # frozen before any solve; final rechecks it
    adapter = _adapter(root, group_dir, tasks, champion, _metered_solver(solver, calls), "stages",
                       adapter_class=hooks.adapter_class)
    _json(group_dir / "campaign.json", {"status": "open"})
    with (group_dir / "decisions.jsonl").open("a+", encoding="utf-8") as log, \
            (group_dir / "outcomes.jsonl").open("a+", encoding="utf-8") as outcomes:
        decider = Decider(_MeteredBackend(jev, calls), log, fallback=DeterministicBackend())
        result = run_campaign(
            adapter=adapter, proposer=_proposer(adapter, proposer, calls, hooks, decider), decider=decider,
            envelope_builder=EnvelopeBuilder(component_ids=("c1",)),
            dev_item_ids=sorted(adapter.splits.dev_item_ids()), evaluator_hash=_evaluator_hash(tasks),
            archive=adapter.archive, outcome_log=outcomes, non_regression=_zero_margin,
            spend=lambda: calls.count, max_attempts=MAX_ATTEMPTS, spend_cap=hooks.spend_cap,
            eval_cap=EVAL_CAP, runs=RUNS)
    selected = result.selected
    _json(group_dir / "campaign.json", {
        "status": "closed", **identity, "outcome": result.outcome, "stop_reason": result.stop_reason,
        "attempts": result.attempts, "evaluator_items_used": result.evaluator_items_used,
        "selected": None if selected is None else {"id": selected.id, "components": dict(selected.components),
                                                   "media_type": selected.media_type,
                                                   "parent_ids": list(selected.parent_ids)}})
    return result


class _Replay:
    """Schedule-ordered records handed to ``accept``; each (arm, item_id, run) once."""

    def __init__(self, rows, champion_id, candidate_id):
        self.ids = {champion_id: "champion", candidate_id: "candidate"}
        self.rows, self.runs = {}, {}
        for row in rows:
            key = (row["arm"], row["item_id"], row["run"])
            if key in self.rows:
                raise ValueError("duplicate scheduled record")
            self.rows[key] = row

    def evaluate(self, candidate, item_ids):
        # loop._evaluate_runs calls once per run, in run order, per arm.
        arm = self.ids[candidate.id]
        run = self.runs.get((arm, tuple(item_ids)), 0)
        self.runs[(arm, tuple(item_ids))] = run + 1
        return [self.rows.pop((arm, item, run)) for item in item_ids]

    def check_consumed(self):
        if self.rows:
            raise PilotStop("scheduled records not consumed by accept")


def _file_approval(group_dir, wait):
    def approval(request):
        path = group_dir / "approval-request.json"
        _json(path, request.__dict__)
        wait(path)
        try:
            return ApprovalRecord(**json.loads((group_dir / "approval.json").read_text()))
        except (OSError, ValueError, TypeError):
            return None  # missing or malformed: accept() records not_updated
    return approval


def _wait_for_owner(path: Path) -> None:
    # Same local-state poll as the runner's health wait; no timeout (lead stops it).
    while not path.with_name("approval.json").exists():
        time.sleep(1)


def _selected(group_dir) -> Candidate | None:
    state = json.loads((group_dir / "campaign.json").read_text())
    if state["selected"] is None:
        return None
    s = state["selected"]
    candidate = Candidate(s["components"], s["media_type"], tuple(s["parent_ids"]))
    if candidate.id != s["id"]:
        raise PilotStop("selected candidate hash mismatch")
    return candidate


def _scheduled_valid(rows, item_ids) -> bool:
    """Complete schedule: exactly every (arm, item, run) once, valid score, no failure.

    Prereg "Retention": operational or data failures block acceptance, so any invalid
    row fails the gate. The S4 addendum (#36) schedules adjudication and holdout only,
    with the champion and candidate arms.
    """
    expected = {(arm, item, run) for arm in ARMS for item in item_ids for run in range(RUNS)}
    keys = [(r.get("arm"), r.get("item_id"), r.get("run")) for r in rows]
    return (len(keys) == len(expected) and set(keys) == expected
            and all(_valid_score(r.get("score")) and "failure" not in r for r in rows))


def _identity_ok(frozen, current, champion_id, record) -> bool:
    """S4 addendum (#36): the frozen identity holds, or one reviewed rebind does.

    A rebind is accepted only if ``from`` is exactly the campaign's frozen identity,
    ``to`` is exactly the current one, the champion is unchanged and the recorded
    addendum sha256 matches the addendum file itself.
    """
    if record is None:  # no rebind: the frozen identity must hold exactly
        return current == frozen
    if not isinstance(record, dict):
        return False
    # An existing rebind is always validated in full, and the champion must equal the
    # frozen, current and recorded one: only code/evaluator hashes may move.
    addendum = record.get("addendum")
    return (record.get("from") == frozen and record.get("to") == current
            and record.get("champion_id") == champion_id == frozen.get("champion_id")
            == current.get("champion_id")
            and isinstance(addendum, str) and Path(addendum).is_file()
            and record.get("addendum_sha256") == _sha(Path(addendum)))


def _rebind_record(run_dir: Path, group: str) -> dict | None:
    path = run_dir / group / "rebind.json"
    if not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        raise PilotStop(f"malformed rebind record in {group}")
    if not isinstance(record, dict):  # a present file is never treated as absent
        raise PilotStop(f"malformed rebind record in {group}")
    return record


def rebind(*, root: Path, run_dir: Path, group: str, champion: Mapping, addendum: Path,
           load_champion: Callable[[Mapping], Candidate] = _champion) -> dict:
    """Record a pre-measurement change of code/evaluator identity (S4 addendum, #36).

    ``from`` is the campaign's frozen identity, so it must equal campaign.json;
    ``to`` is the identity of the code and inputs that will actually run the final.
    """
    root, run_dir, addendum = Path(root), Path(run_dir), Path(addendum)
    if group not in GROUPS or not run_dir.is_absolute():
        raise PilotStop("unknown group or relative run directory")
    group_dir = run_dir / group
    state = json.loads((group_dir / "campaign.json").read_text())
    if state.get("status") != "closed":
        raise PilotStop(f"campaign {group} is open or missing")
    frozen = {k: state.get(k) for k in ("champion_id", "evaluator_hash", "code_hash")}
    current = _identity(load_champion(champion), frozen_tasks(root, group))
    if (group_dir / "rebind.json").exists():
        raise PilotStop(f"rebind already recorded for {group}")
    if current["champion_id"] != frozen["champion_id"]:
        raise PilotStop(f"champion changed in {group}")
    record = {"from": frozen, "to": current, "champion_id": current["champion_id"],
              "addendum": str(addendum), "addendum_sha256": _sha(addendum),
              "reason": "docs/prereg-s4-addendum.md"}
    _json(group_dir / "rebind.json", record)
    return record


def final_phase(*, root: Path, run_dir: Path, group: str, champions: Mapping, solver,
                calibration_answer: Path, calibration_replay,
                wait: Callable[[Path], None] = _wait_for_owner,
                hooks: Hooks = SKILL) -> AcceptResult:
    """One group's frozen comparison (S4 addendum, #36): adjudication and holdout only."""
    root, run_dir = Path(root), Path(run_dir)
    if group not in GROUPS or not run_dir.is_absolute():
        raise PilotStop("unknown group or relative run directory")
    group_dir = run_dir / group
    state_path = group_dir / "campaign.json"
    if not state_path.exists() or json.loads(state_path.read_text()).get("status") != "closed":
        raise PilotStop(f"campaign {group} is open or missing")
    final_dir = run_dir / "final" / group
    if (final_dir / "observations.jsonl").exists():
        raise PilotStop(f"final phase already ran for {group}")  # holdout is reported once
    # Prereg "Frozen inputs": drift is a STOP before any solver invocation; a recorded
    # rebind (S4 addendum) is the only way a pre-measurement change may proceed.
    state = json.loads(state_path.read_text())
    frozen = {k: state.get(k) for k in ("champion_id", "evaluator_hash", "code_hash")}
    champion = hooks.load_champion(champions[group])
    tasks = frozen_tasks(root, group)
    rebind = _rebind_record(run_dir, group)
    if not _identity_ok(frozen, _identity(champion, tasks), champion.id, rebind):
        raise PilotStop(f"frozen identity drift in {group}")
    # Issue #42: approval binds the validated code identity (frozen, or the rebind's ``to``).
    code_hash = (rebind["to"] if rebind is not None else frozen)["code_hash"]
    tasks = _prerun(root, run_dir, [group], calibration_answer, calibration_replay)[group]
    final_dir.mkdir(parents=True, exist_ok=True)
    entropy = run_dir / "entropy.json"
    try:  # prereg "Estimator": entropy recorded once, before any execution
        with entropy.open("x", encoding="utf-8") as stream:
            import numpy as np
            stream.write(json.dumps({"entropy": np.random.SeedSequence().entropy}) + "\n")
    except FileExistsError:
        pass
    adapter = _adapter(root, group_dir, tasks, champion, solver, "final-stages",
                       adapter_class=hooks.adapter_class)
    candidate = _selected(group_dir)
    # Addendum "Items": adjudication and holdout only; dev is never re-run.
    adj = sorted(adapter.splits.item_ids("adjudication"))
    hold = sorted(adapter.splits.item_ids("holdout"))
    scheduled = sorted([*adj, *hold])  # task id order, as in the prereg schedule
    records = []
    with (final_dir / "observations.jsonl").open("a", encoding="utf-8") as observations:
        if candidate is not None:  # no frozen candidate: no solves, accept() returns no_improvement
            arms = {"champion": champion, "candidate": candidate}
            # adapter.evaluate admits dev only; reuse its per-item staging/verification.
            adapter.work_dir.mkdir(parents=True, exist_ok=True)
            for run in range(RUNS):  # addendum schedule: run -> task id -> arm
                for item in scheduled:
                    directory = _verify_task(root, adapter.tasks[item])
                    for arm in ARMS:
                        # evaluate()'s dev-only guard protects the optimisation loop; the
                        # final phase bypasses it deliberately, after _verify_task above.
                        # The adapter renders its own host artifact (library -> SKILL.md).
                        row = {**adapter._evaluate_one(arms[arm], item, directory),
                               "group": group, "run": run, "arm": arm}
                        row["token_usage"] = _token_usage(row)
                        observations.write(json.dumps(row, sort_keys=True) + "\n")
                        observations.flush()
                        records.append(row)
    valid = _scheduled_valid(records, scheduled)
    replay = _Replay(records, champion.id, candidate.id if candidate else None)
    result = accept(
        campaign_id=group, candidate=candidate, champion=champion, adjudicate=replay.evaluate,
        adjudication_item_ids=adj, evaluator_hash=_evaluator_hash(tasks), code_hash=code_hash,
        retain=lambda comparison: valid and _zero_margin(comparison),
        approval=_file_approval(group_dir, wait), adapter=adapter, archive=adapter.archive,
        runs=RUNS, holdout=replay.evaluate, holdout_item_ids=hold)
    if candidate is not None:
        replay.check_consumed()
    _json(group_dir / "acceptance.json", {"outcome": result.outcome})
    return result


def _dev_rows(group_dir: Path) -> list[dict]:
    """Champion dev rows and the selected candidate's dev rows, from the optimise archive.

    The final phase no longer re-runs dev (S4 addendum, #36): these are the same
    campaign results, and the campaign already wrote them to the public store.
    """
    state = json.loads((group_dir / "campaign.json").read_text())
    selected = None if state["selected"] is None else state["selected"]["id"]
    results = [json.loads(line) for line in (group_dir / "public/results.jsonl").read_text().splitlines()]
    rows = []
    for row in results:
        arm = {state["champion_id"]: "champion", selected: "candidate"}.get(row["candidate_id"])
        if arm is not None:
            rows.append({**row, "arm": arm, "group": row["item_id"].split("/")[0]})
    return rows


def _run_spread(rows) -> float | None:
    """Champion run-to-run spread: mean population std over runs per task (upstream std@3)."""
    by_item: dict[str, list[float]] = {}
    for row in rows:
        by_item.setdefault(row["item_id"], []).append(float(row["score"]))
    spreads = [statistics.pstdev(scores) for scores in by_item.values() if len(scores) > 1]
    return sum(spreads) / len(spreads) if spreads else None


def report(run_dir: Path, root: Path, outcome: str) -> list[dict]:
    """Report inputs (S4 addendum, #36): dev from the optimise archive, then adjudication
    and holdout; noise is the champion's run-to-run spread on dev, not a control arm."""
    from ...analysis import report_table
    run_dir, root = Path(run_dir), Path(root)
    dev = [row for group in GROUPS for row in _dev_rows(run_dir / group)]
    # Paired tables cover only groups with a selected candidate; a no-candidate group
    # has no pairs and is reported as such, never as fabricated candidate rows.
    paired = [g for g in GROUPS if json.loads((run_dir / g / "campaign.json").read_text())["selected"]]
    unpaired = [g for g in GROUPS if g not in paired]
    noise = _run_spread([r for r in dev if r["arm"] == "champion"])
    if len(paired) < 2:
        # The paired group bootstrap needs at least two groups (SciPy rejects samples
        # of fewer than two); say so instead of substituting another estimator.
        return [{"split": split, "outcome": outcome, "comparison": "unavailable",
                 "reason": "fewer than two groups with a selected candidate",
                 "champion_run_spread": noise, "paired_groups": paired, "no_candidate_groups": unpaired}
                for split in ("dev", "adjudication", "holdout")]
    dev = [r for r in dev if r["group"] in paired]
    final = [json.loads(line) for group in paired
             for line in (run_dir / "final" / group / "observations.jsonl").read_text().splitlines()]
    purpose_of = {}
    for group in GROUPS:
        splits = carve_splits(frozen_tasks(root, group), {group: list(DEV_IDS)})
        purpose_of.update({item: purpose for purpose in ("adjudication", "holdout")
                           for item in splits.item_ids(purpose)})

    def arm(source, name, items):
        return [r for r in source if r["arm"] == name and r["item_id"] in items]
    tables = {}
    for purpose, source in (("dev", dev), ("adjudication", final), ("holdout", final)):
        group_of = {r["item_id"]: r["group"] for r in source
                    if purpose == "dev" or purpose_of.get(r["item_id"]) == purpose}
        tables[purpose] = {"outcome": outcome, "group_of": group_of,
                           "champion": arm(source, "champion", group_of),
                           "candidate": arm(source, "candidate", group_of)}
    entropy = json.loads((run_dir / "entropy.json").read_text())["entropy"]
    return [{**row, "champion_run_spread": noise, "paired_groups": paired, "no_candidate_groups": unpaired}
            for row in report_table(tables, list(range(RUNS)), entropy)]


def _docker_replay(solver) -> Callable[[Path], bytes]:
    """Calibration replay through DockerSolver's own trusted, --network none grader."""
    from . import solver_docker as sd
    group, subset, task_id = CALIBRATION_TASK
    task = next(t for t in frozen_tasks(solver.root, group) if (t.subset, t.task_id) == (subset, task_id))

    def replay(answer: Path) -> bytes:
        scope = "gdp-" + secrets.token_hex(4)
        out = solver.evidence_dir / scope
        out.mkdir(parents=True, mode=0o700)
        token = sd._DOCKER_ENV.set(None)
        try:
            skill = Candidate({"SKILL.md": "calibration\n"}, "text/plain")
            _, _, group_dir, task_path = solver._stage(skill, task, task.directory(solver.root) / "input", out, scope)
            solver._docker_environment(out)
            image, _ = solver._images(out, group_dir, scope)
            shutil.copyfile(answer, out / "calibration-answer.json")
            solver._grade(out, task_path, image, out / "calibration-answer.json", scope + "-calibration",
                          "calibration-score.json")
            output = (out / "calibration-score.json").read_bytes()
            solver._run(["docker", "rm", "-f", scope + "-calibration"])
            solver._run(["docker", "image", "rm", scope + "-solver", scope + "-task"])
            return output
        finally:
            sd._DOCKER_ENV.reset(token)
    return replay


def http_model(calls_log: Path, url: str = PROPOSER_URL, timeout: float = TIMEOUT):
    """In-container model: stdlib POST, no credentials; the forwarder routes it."""
    from .solver_docker import EFFORT, MODEL

    def model(prompt: str) -> str:
        with calls_log.open("a", encoding="utf-8") as stream:  # logged before the call: failures count
            stream.write(json.dumps({"call": "started"}) + "\n")
        # Responses API input as a message list (the local route rejects the string form).
        # https://platform.openai.com/docs/api-reference/responses/create
        message = [{"role": "user", "content": [{"type": "input_text", "text": prompt}]}]
        request = urllib.request.Request(url, data=json.dumps({"model": MODEL, "input": message,
                                                          "reasoning": {"effort": EFFORT}}).encode(),
                                         headers={"Content-Type": "application/json"})
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(request, timeout=timeout) as response:
            body = json.loads(response.read())
        with calls_log.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"call": "usage", "token_usage": body.get("usage")}) + "\n")
        # Responses API: output[] message items carry output_text content parts.
        return "".join(part["text"] for item in body["output"] if item.get("type") == "message"
                       for part in item["content"] if part.get("type") == "output_text")
    return model


def _propose_in_container(dev: Path, out: Path, model, hooks=SKILL) -> None:
    request = json.loads((dev / "request.json").read_text(encoding="utf-8"))
    # The container only ever sees the rendered text artifact, whichever host artifact it came from.
    champion = Candidate(request["champion"], "text/plain")
    splits = load_splits({"splits": [{"name": "dev", "purpose": "dev", "selection_eligible": True,
                                      "item_ids": request["dev_item_ids"]}]})
    payload = hooks.container(champion, request["records"], splits, model)
    _json(out / "result.json", {hooks.result_key: payload})


class ContainerProposer:
    """Live proposer via GDPevoProposerRuntime on a per-call --internal network whose
    only egress is the solver's forwarder (DockerSolver._forwarder, lead decision #27)."""

    def __init__(self, adapter, solver, work: Path, image: str, hooks=SKILL):
        self.adapter, self.solver, self.work, self.image = adapter, solver, Path(work), image
        self.hooks = hooks

    def __call__(self, champion, records, splits, calls, *, decider=None, dev_results=()):
        from . import solver_docker as sd
        import gepa
        scope = "gdp-" + secrets.token_hex(4)
        out = self.work / scope
        dev, output = out / "dev", out / "out"
        output.mkdir(parents=True)
        # Container precedent (tests/adapters/test_gdpevo_container.py): stage the kernel and GEPA.
        shutil.copytree(Path(__file__).parents[2], dev / "lib/rsi_kernel", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(Path(gepa.__file__).parent, dev / "lib/gepa", ignore=shutil.ignore_patterns("__pycache__"))
        _json(dev / "request.json", {"champion": dict(self.hooks.render(champion).components),
                                     "records": list(records),
                                     "dev_item_ids": sorted(splits.dev_item_ids())})
        network, name = scope + "-pnet", scope + "-proposer"
        runtime = self.adapter.proposer_runtime(self.image, dev, output)
        runtime = dataclasses.replace(runtime, network=network, name=name)
        token = sd._DOCKER_ENV.set(None)
        try:
            self.solver._docker_environment(out)
            self.solver._run(["docker", "network", "create", "--internal", network], out / "network-id.txt")
            self.solver._forwarder(out, scope, network)
            try:
                completed = self.solver._run(runtime.docker_argv(
                    ["python", "-m", self.hooks.module, "propose-in-container"],
                    {"PYTHONPATH": "/data/dev/lib"}), out / "proposer.log", check=False)
            except subprocess.TimeoutExpired:
                # Runner's documented kill + verify; forwarder/networks stay as evidence.
                self.solver._stop_timed_out(out, name)
                raise
            if completed.returncode != 0:
                raise RuntimeError("proposer container failed")  # resources retained as evidence
            # Same per-run Docker environment: its config dir is created once per attempt.
            self.solver._run(["docker", "rm", "-f", name, scope + "-fwd"])
            self.solver._run(["docker", "network", "rm", network, scope + "-egress"])
        finally:
            sd._DOCKER_ENV.reset(token)
            self._meter(output / "calls.jsonl", calls)
        return self.hooks.admit(champion, json.loads((output / "result.json").read_text())[self.hooks.result_key],
                                decider, dev_results)

    @staticmethod
    def _meter(path: Path, calls) -> None:
        rows = [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []
        for i, row in enumerate(rows):
            if row["call"] == "started":
                after = rows[i + 1] if i + 1 < len(rows) else {}
                calls.log("proposer", after.get("token_usage") if after.get("call") == "usage" else None)


def main(argv=None, hooks=SKILL) -> int:
    from .solver_docker import DockerSolver
    parser = argparse.ArgumentParser(prog="python -m rsi_kernel.adapters.gdpevo.pilot")
    if (argv if argv is not None else sys.argv[1:]) == ["propose-in-container"]:
        from ...isolation import DEV_TARGET, OUT_TARGET
        out = Path(OUT_TARGET)
        _propose_in_container(Path(DEV_TARGET), out, http_model(out / "calls.jsonl"), hooks)
        return 0
    parser.add_argument("phase", choices=("optimise", "final", "rebind"))
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--group", choices=GROUPS)
    parser.add_argument("--addendum", type=Path)
    args = parser.parse_args(argv)
    if args.phase != "optimise" and args.group is None:
        parser.error(f"{args.phase} needs --group")
    # Config: root, run_dir, champions {group: {path, sha256}}, calibration_answer, jev_url.
    config = json.loads(args.config.read_text())
    root, run_dir = Path(config["root"]), Path(config["run_dir"])
    if args.phase == "rebind":
        if args.addendum is None:
            parser.error("rebind needs --addendum")
        record = rebind(root=root, run_dir=run_dir, group=args.group, champion=config["champions"][args.group],
                        addendum=args.addendum, load_champion=hooks.load_champion)
        print(json.dumps({"group": args.group, "addendum_sha256": record["addendum_sha256"]}))
        return 0
    if args.phase == "final":
        # Acceptance stage admits test tasks; one group per process (host cap 4).
        tasks = frozen_tasks(root, args.group)
        solver = DockerSolver(root=root, tasks=tasks, evidence_dir=run_dir / f"final/{args.group}/evidence",
                              timeout=TIMEOUT, stage="acceptance")
        result = final_phase(root=root, run_dir=run_dir, group=args.group, champions=config["champions"],
                             solver=solver, calibration_answer=Path(config["calibration_answer"]),
                             calibration_replay=_docker_replay(solver), hooks=hooks)
        print(json.dumps({args.group: result.outcome}))
        return 0
    from .solver_docker import PYTHON_IMAGE
    tasks = frozen_tasks(root, args.group)
    dev = [t for t in tasks if t.subset == "train" and t.task_id in DEV_IDS]
    group_dir = run_dir / args.group
    solver = DockerSolver(root=root, tasks=dev, evidence_dir=group_dir / "evidence", timeout=TIMEOUT)
    # Adapter used only for proposer_runtime deny paths (source root, private store).
    adapter = _adapter(root, group_dir, tasks, hooks.load_champion(config["champions"][args.group]), solver,
                       "stages", adapter_class=hooks.adapter_class)
    result = optimise_group(
        root=root, run_dir=run_dir, group=args.group, champion=config["champions"][args.group], solver=solver,
        proposer=ContainerProposer(adapter, solver, group_dir / "proposer", PYTHON_IMAGE, hooks),
        jev=JevBackend(config["jev_url"], "jev-latest"),
        calibration_answer=Path(config["calibration_answer"]), calibration_replay=_docker_replay(solver),
        hooks=hooks)
    print(json.dumps({"outcome": result.outcome, "stop_reason": result.stop_reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
