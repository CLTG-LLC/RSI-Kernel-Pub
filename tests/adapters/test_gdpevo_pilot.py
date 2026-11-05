"""Pilot driver wiring (issue #27) on a synthetic GDPevo-shaped tree.

Fakes only: no Docker, network, live model or GDPevo data. Group/task ids
mirror the prereg carving map; the toy wrapper is the existing fixture.
"""

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from rsi_kernel.adapters.gdpevo import pilot
from rsi_kernel.adapters.gdpevo.solver_docker import DockerSolver
from rsi_kernel.candidate import Candidate

TOY = Path(__file__).parent / "fixtures" / "toy"


@pytest.fixture
def tree(tmp_path, monkeypatch):
    root = tmp_path / "gdpevo"
    for group in pilot.GROUPS:
        for subset, ids in (("train", pilot.TRAIN_IDS), ("test", pilot.TEST_IDS)):
            for task_id in ids:
                shutil.copytree(TOY, root / "data/task_groups" / group / f"{subset}_tasks" / task_id)
    champions = {}
    for group in pilot.GROUPS:
        path = tmp_path / f"{group}-SKILL.md"
        path.write_text(f"# {group} skill\n")
        champions[group] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    answer = tmp_path / "calibration-answer.json"
    answer.write_bytes(b"recorded")
    monkeypatch.setattr(pilot, "CALIBRATION_ANSWER_SHA256", hashlib.sha256(b"recorded").hexdigest())
    monkeypatch.setattr(pilot, "CALIBRATION_OUTPUT_SHA256", hashlib.sha256(b"graded").hexdigest())
    monkeypatch.setattr(pilot, "_git_head", lambda root: pilot.UPSTREAM_COMMIT)
    return root, tmp_path / "run", champions, answer


class Fakes:
    """Solver, proposer model and Jev with a shared call log."""

    def __init__(self, candidate_score=1.0, champion_score=1.0):
        self.solver_calls, self.model_calls, self.jev_calls = [], [], []
        self.scores = {"champion": champion_score, "candidate": candidate_score}
        self.replays = []
        self.overrides = {}  # 1-based solver call index -> replacement result

    def solver(self, candidate, item_id, input_dir, prediction, env):
        self.solver_calls.append((candidate.id, item_id))
        if len(self.solver_calls) in self.overrides:
            return {"item_id": item_id, **self.overrides[len(self.solver_calls)]}
        out = prediction.parent.parent / f"evidence-{len(self.solver_calls)}"
        (out / "work").mkdir(parents=True)
        (out / "work/answer.json").write_text('{"answer": "x"}')
        (out / "measurement.json").write_text(json.dumps({"token_usage": {"total_tokens": 3}}))
        arm = "candidate" if "Improved" in candidate.components["SKILL.md"] else "champion"
        return {"item_id": item_id, "score": self.scores[arm], "evidence_dir": str(out)}

    def model(self, prompt):
        self.model_calls.append(prompt)
        return f"```markdown\n# Improved skill {len(self.model_calls)}\n```"

    def replay(self, answer):
        self.replays.append(answer)
        return b"graded"

    @property
    def jev(self):
        fakes = self

        class Jev:
            name, model = "jev", "jev-latest"

            def decide(self, envelope):
                fakes.jev_calls.append(envelope)
                return {"D2": "c1"}
        return Jev()


def optimise(tree, fakes, group):
    root, run_dir, champions, answer = tree
    return pilot.optimise_group(root=root, run_dir=run_dir, group=group, champion=champions[group],
                                solver=fakes.solver, proposer=pilot.in_process_proposer(fakes.model), jev=fakes.jev,
                                calibration_answer=answer, calibration_replay=fakes.replay)


def approve_matching(path):
    request = json.loads(path.read_text())
    (path.parent / "approval.json").write_text(json.dumps({
        "candidate_hash": request["candidate_hash"], "evaluator_hash": request["evaluator_hash"],
        "data_hash": request["data_hash"], "approver": "Billy"}))


def final(tree, fakes, group, wait=approve_matching):
    root, run_dir, champions, answer = tree
    return pilot.final_phase(root=root, run_dir=run_dir, group=group, champions=champions,
                             solver=fakes.solver, calibration_answer=answer,
                             calibration_replay=fakes.replay, wait=wait)


def final_all(tree, fakes, wait=approve_matching):
    return {group: final(tree, fakes, group, wait) for group in pilot.GROUPS}


def drift_package(tmp_path, monkeypatch):
    """Copy the package and lock so a test can change the code hash after optimisation."""
    package, lock = tmp_path / "src/rsi_kernel", tmp_path / "uv.lock"
    shutil.copytree(pilot.PACKAGE_DIR, package, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(pilot.LOCK_FILE, lock)
    monkeypatch.setattr(pilot, "PACKAGE_DIR", package)
    monkeypatch.setattr(pilot, "LOCK_FILE", lock)
    return package


def addendum(tmp_path):
    path = tmp_path / "prereg-s4-addendum.md"
    path.write_text("# Trim the pilot final phase\n")
    return path


def rebind(tree, group, path):
    root, run_dir, champions, _ = tree
    return pilot.rebind(root=root, run_dir=run_dir, group=group, champion=champions[group], addendum=path)


def test_optimise_caps_per_group_and_wiring(tree):
    fakes = Fakes()
    result = optimise(tree, fakes, "task_group_001")
    assert result.evaluator_items_used <= pilot.EVAL_CAP == 36
    calls = [json.loads(line) for line in (tree[1] / "task_group_001/calls.jsonl").read_text().splitlines()]
    assert len(calls) <= pilot.SPEND_CAP == 42
    assert len(calls) == len(fakes.solver_calls) + len(fakes.model_calls) + len(fakes.jev_calls)
    assert {c["kind"] for c in calls} == {"solver", "proposer", "jev"}
    assert all(c["token_usage"] == {"total_tokens": 3} for c in calls if c["kind"] == "solver")
    assert {item for _, item in fakes.solver_calls} == {f"task_group_001/train/{i}" for i in pilot.DEV_IDS}
    assert result.selected is not None and result.attempts == pilot.MAX_ATTEMPTS
    decisions = [json.loads(line) for line in (tree[1] / "task_group_001/decisions.jsonl").read_text().splitlines()]
    assert decisions and all("baseline_answer" in d and d["backend"] == "jev" for d in decisions)
    state = json.loads((tree[1] / "task_group_001/campaign.json").read_text())
    assert state["status"] == "closed" and state["selected"]["components"] == dict(result.selected.components)


def test_optimise_spend_cap_counts_failed_calls(tree):
    fakes = Fakes()
    def failing(prompt):
        fakes.model_calls.append(prompt)
        raise RuntimeError("model down")
    root, run_dir, champions, answer = tree
    with pytest.raises(RuntimeError):
        pilot.optimise_group(root=root, run_dir=run_dir, group="task_group_001", champion=champions["task_group_001"],
                             solver=fakes.solver, proposer=pilot.in_process_proposer(failing), jev=fakes.jev,
                             calibration_answer=answer, calibration_replay=fakes.replay)
    kinds = [json.loads(line)["kind"] for line in (run_dir / "task_group_001/calls.jsonl").read_text().splitlines()]
    assert kinds.count("proposer") == 1


def group_items(group):
    """Adjudication + holdout item ids of one group (prereg carving map)."""
    return sorted([f"{group}/test/{i}" for i in pilot.TEST_IDS] + [f"{group}/train/{i}" for i in pilot.ADJ_IDS])


def test_group_with_candidate_has_42_final_observations(tree):
    """Issue #36 bullet 1: run -> task id -> arm, no dev or control rows."""
    fakes = Fakes()
    group = "task_group_001"
    optimise(tree, fakes, group)
    fakes.solver_calls.clear()
    result = final(tree, fakes, group)
    rows = [json.loads(line) for line in
            (tree[1] / f"final/{group}/observations.jsonl").read_text().splitlines()]
    expected = [(run, item, arm) for run in range(pilot.RUNS) for item in group_items(group) for arm in pilot.ARMS]
    assert len(rows) == len(fakes.solver_calls) == 42
    assert [(r["run"], r["item_id"], r["arm"]) for r in rows] == expected
    assert {r["arm"] for r in rows} == {"champion", "candidate"}
    dev = {f"{group}/train/{i}" for i in pilot.DEV_IDS}
    assert not dev & {r["item_id"] for r in rows}
    assert result.outcome == "updated"


def test_group_without_candidate_gets_no_solves_and_no_improvement(tree):
    """Issue #36 bullet 1: an unselected campaign solves nothing and is not an update."""
    fakes = Fakes(candidate_score=0.0)  # dev regression every attempt: nothing selected
    group = "task_group_001"
    optimise(tree, fakes, group)
    assert json.loads((tree[1] / group / "campaign.json").read_text())["selected"] is None
    fakes.solver_calls.clear()
    result = final(tree, fakes, group)
    assert result.outcome == "no_improvement"
    assert not fakes.solver_calls
    assert (tree[1] / f"final/{group}/observations.jsonl").read_text() == ""
    assert json.loads((tree[1] / group / "acceptance.json").read_text()) == {"outcome": "no_improvement"}


def test_final_runs_one_group_and_a_second_run_of_it_stops(tree):
    """Issue #36 bullet 2: one group per process; the holdout is reported once."""
    fakes = Fakes()
    optimise_all(tree, fakes)
    assert final(tree, fakes, "task_group_001").outcome == "updated"
    assert not (tree[1] / "final/task_group_002").exists()
    entropy = (tree[1] / "entropy.json").read_text()
    calls = len(fakes.solver_calls)
    with pytest.raises(pilot.PilotStop, match="already ran"):
        final(tree, fakes, "task_group_001")
    assert len(fakes.solver_calls) == calls  # the STOP is before any solve
    assert final(tree, fakes, "task_group_002").outcome == "updated"
    assert (tree[1] / "entropy.json").read_text() == entropy  # created exclusively once


def test_accept_consumes_each_record_exactly_once(tree):
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    champ = Candidate({"SKILL.md": "c"}, "text/plain")
    row = {"arm": "champion", "item_id": "a", "run": 0, "score": 1.0}
    with pytest.raises(ValueError, match="duplicate"):
        pilot._Replay([row, row], champ.id, None)
    replay = pilot._Replay([row], champ.id, None)
    assert replay.evaluate(champ, ["a"]) == [row]
    with pytest.raises(KeyError):  # a second request for the same key is never served
        replay.evaluate(champ, ["a"])
    replay.check_consumed()
    with pytest.raises(pilot.PilotStop):
        pilot._Replay([row], champ.id, None).check_consumed()
    results = final_all(tree, fakes)
    for group in pilot.GROUPS:
        private = [json.loads(line) for line in (tree[1] / group / "private/results.jsonl").read_text().splitlines()]
        keys = [(r["candidate_id"], r["item_id"], r["run"]) for r in private]
        assert len(keys) == len(set(keys)) == 2 * 7 * pilot.RUNS
        assert results[group].holdout_results is not None


def test_final_refuses_while_a_campaign_is_open(tree):
    fakes = Fakes()
    optimise(tree, fakes, "task_group_001")
    optimise(tree, fakes, "task_group_002")
    (tree[1] / "task_group_003").mkdir(parents=True)
    (tree[1] / "task_group_003/campaign.json").write_text(json.dumps({"status": "open"}))
    fakes.solver_calls.clear()
    with pytest.raises(pilot.PilotStop, match="open"):
        final(tree, fakes, "task_group_003")
    assert not fakes.solver_calls


def test_optimise_solver_still_rejects_test_tasks_acceptance_admits_them(tree):
    root = tree[0]
    tasks = pilot.frozen_tasks(root, "task_group_001")
    test_task = next(t for t in tasks if t.subset == "test")
    with pytest.raises(ValueError, match="dev train"):
        DockerSolver(root=root, tasks=[test_task], evidence_dir=tree[1] / "e", timeout=1)
    assert DockerSolver(root=root, tasks=tasks, evidence_dir=tree[1] / "e", timeout=1, stage="acceptance").tasks
    with pytest.raises(ValueError):
        DockerSolver(root=root, tasks=tasks, evidence_dir=tree[1] / "e", timeout=1, stage="other")


@pytest.mark.parametrize("approval", [None, "mismatch", "malformed"])
def test_missing_or_mismatched_approval_is_not_updated(tree, approval):
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)

    def wait(path):
        assert json.loads(path.read_text())["candidate_hash"]
        if approval == "mismatch":
            approve_matching(path)
            record = json.loads((path.parent / "approval.json").read_text())
            (path.parent / "approval.json").write_text(json.dumps({**record, "data_hash": "other"}))
        elif approval == "malformed":
            (path.parent / "approval.json").write_text("{")
    results = final_all(tree, fakes, wait)
    assert {r.outcome for r in results.values()} == {"not_updated"}
    decisions = [json.loads(line) for line in (tree[1] / "task_group_001/private/decisions.jsonl").read_text().splitlines()]
    assert not any(d.get("mode") == "record-only" for d in decisions)


def test_matching_approval_is_updated_record_only(tree):
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    group = "task_group_001"
    results = {group: final(tree, fakes, group)}
    assert results[group].outcome == "updated"
    decisions = [json.loads(line) for line in (tree[1] / group / "private/decisions.jsonl").read_text().splitlines()]
    assert {"candidate_id": results[group].request.candidate_hash, "mode": "record-only"} in decisions
    champion = Path(tree[2][group]["path"]).read_text()
    assert champion == f"# {group} skill\n"


@pytest.mark.parametrize("drift", ["replay", "answer", "pin"])
def test_prerun_drift_stops_before_any_solver_call(tree, monkeypatch, drift):
    fakes = Fakes()
    if drift == "replay":
        fakes.replay = lambda answer: b"different"
    elif drift == "answer":
        tree[3].write_bytes(b"changed")
    else:
        monkeypatch.setattr(pilot, "_git_head", lambda root: "0" * 40)
    with pytest.raises(pilot.PilotStop):
        optimise(tree, fakes, "task_group_001")
    assert not fakes.solver_calls and not fakes.model_calls and not fakes.jev_calls
    assert not (tree[1] / "task_group_001/campaign.json").exists()


def test_report_inputs_use_analysis(tree):
    """Issue #36: dev from the optimise archive, then adjudication and holdout."""
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    final_all(tree, fakes)
    rows = pilot.report(tree[1], tree[0], "updated")
    assert [r["split"] for r in rows] == ["dev", "adjudication", "holdout"]
    assert all(r["retention_passed"] for r in rows)
    # Noise is the champion's dev run-to-run spread; the fake scores never vary.
    assert {r["champion_run_spread"] for r in rows} == {0.0}
    assert pilot._run_spread([{"item_id": "a", "score": s} for s in (0.0, 1.0)]) == 0.5


def test_proposer_runtime_network_defaults_to_none(tmp_path):
    from rsi_kernel.adapters.gdpevo.runtime import GDPevoProposerRuntime
    (tmp_path / "dev").mkdir()
    (tmp_path / "out").mkdir()
    default = GDPevoProposerRuntime("img", tmp_path / "dev", tmp_path / "out").docker_argv(["true"])
    assert default[default.index("--network") + 1] == "none"
    live = GDPevoProposerRuntime("img", tmp_path / "dev", tmp_path / "out", network="gdp-x-pnet").docker_argv(["true"])
    assert live[live.index("--network") + 1] == "gdp-x-pnet" and live.count("--network") == 1


def test_http_model_posts_without_credentials_and_records_usage(tmp_path, monkeypatch):
    sent = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"usage": {"total_tokens": 9}, "output": [
                {"type": "reasoning"},
                {"type": "message", "content": [{"type": "output_text", "text": "```\n# New\n```"}]}]}).encode()

    class Opener:
        def open(self, request, timeout):
            sent.append((request, timeout))
            return Response()
    monkeypatch.setattr(pilot.urllib.request, "build_opener", lambda *handlers: Opener())
    log = tmp_path / "calls.jsonl"
    assert pilot.http_model(log)("prompt") == "```\n# New\n```"
    request, timeout = sent[0]
    assert request.full_url == "http://model-fwd:8080/v1/responses" and timeout == pilot.TIMEOUT
    assert {k.lower() for k in request.headers} == {"content-type"}
    body = json.loads(request.data)
    assert body["model"] == "gpt-6.1-sol" and body["input"] == [{"role": "user", "content": [{"type": "input_text", "text": "prompt"}]}]
    calls = pilot._Calls(tmp_path / "metered.jsonl")
    pilot.ContainerProposer._meter(log, calls)
    assert calls.count == 1
    assert json.loads((tmp_path / "metered.jsonl").read_text()) == {"kind": "proposer", "token_usage": {"total_tokens": 9}}


def test_failed_http_call_is_still_metered(tmp_path, monkeypatch):
    class Opener:
        def open(self, request, timeout):
            raise OSError("down")
    monkeypatch.setattr(pilot.urllib.request, "build_opener", lambda *handlers: Opener())
    log = tmp_path / "calls.jsonl"
    with pytest.raises(OSError):
        pilot.http_model(log)("prompt")
    calls = pilot._Calls(tmp_path / "metered.jsonl")
    pilot.ContainerProposer._meter(log, calls)
    assert calls.count == 1


def test_container_proposer_uses_internal_network_and_shared_forwarder(tree, monkeypatch):
    from rsi_kernel.adapters.gdpevo import solver_docker
    root, run_dir, champions, _ = tree
    tasks = pilot.frozen_tasks(root, "task_group_001")
    solver = DockerSolver(root=root, tasks=[t for t in tasks if t.subset == "train"],
                          evidence_dir=run_dir / "evidence", timeout=1)
    adapter = pilot._adapter(root, run_dir / "task_group_001", tasks, pilot._champion(champions["task_group_001"]),
                             solver, "stages")
    argvs = []

    def fake_run(argv, output=None, *, check=True):
        argvs.append(list(argv))
        if "propose-in-container" in argv:
            out = Path(argv[argv.index("--mount") + 3].split(",")[1].split("=", 1)[1])
            (out / "calls.jsonl").write_text('{"call": "started"}\n{"call": "usage", "token_usage": null}\n')
            (out / "result.json").write_text(json.dumps({"skill": "# Proposed\n"}))
        import subprocess
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    monkeypatch.setattr(solver, "_run", fake_run)
    envs = []
    def environment(out):  # the real one creates out/docker-config, so twice per attempt fails
        envs.append(out)
        solver_docker._DOCKER_ENV.set({"PATH": ""})
    monkeypatch.setattr(solver, "_docker_environment", environment)
    calls = pilot._Calls(run_dir / "calls.jsonl")
    proposer = pilot.ContainerProposer(adapter, solver, run_dir / "proposer", "img")
    champion = adapter.get_artifact()
    candidate = proposer(champion, [], adapter.splits, calls)
    assert candidate.components == {"SKILL.md": "# Proposed\n"} and candidate.parent_ids == (champion.id,)
    assert calls.count == 1
    internal = next(a for a in argvs if a[:4] == ["docker", "network", "create", "--internal"])[-1]
    run = next(a for a in argvs if "propose-in-container" in a)
    assert run[run.index("--network") + 1] == internal and "-e" in run
    assert not any("KEY" in arg or "TOKEN" in arg for arg in run)
    assert ["docker", "network", "connect", "--alias", "model-fwd", internal] == next(
        a for a in argvs if a[:3] == ["docker", "network", "connect"])[:6]
    assert any(solver_docker.NGINX_IMAGE in a for a in argvs)
    assert len(envs) == 1
    removed = next(a for a in argvs if a[:3] == ["docker", "rm", "-f"])
    assert {name.rsplit("-", 1)[1] for name in removed[3:]} == {"proposer", "fwd"}
    assert "--rm" not in run and run[run.index("--name") + 1].endswith("-proposer")


@pytest.mark.parametrize("phase", ["final", "rebind"])
def test_final_and_rebind_require_a_group(tmp_path, phase):
    """Issue #36: the final phase is a per-group process (the launcher parallelises groups)."""
    config = tmp_path / "config.json"
    config.write_text("{}")
    with pytest.raises(SystemExit):
        pilot.main([phase, "--config", str(config)])


def test_owner_wait_polls_until_approval_file(tmp_path, monkeypatch):
    request = tmp_path / "approval-request.json"
    sleeps = []
    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            (tmp_path / "approval.json").write_text("{}")
    monkeypatch.setattr(pilot.time, "sleep", sleep)
    pilot._wait_for_owner(request)
    assert sleeps == [1, 1]


def optimise_all(tree, fakes):
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    fakes.solver_calls.clear()
    fakes.replays.clear()


def test_champion_change_between_phases_stops_before_solver(tree):
    fakes = Fakes()
    optimise_all(tree, fakes)
    config = tree[2]["task_group_002"]
    Path(config["path"]).write_text("# swapped champion\n")
    config["sha256"] = hashlib.sha256(Path(config["path"]).read_bytes()).hexdigest()
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, "task_group_002")
    assert not fakes.solver_calls and not fakes.replays


def test_code_change_between_phases_stops_then_a_valid_rebind_proceeds(tree, tmp_path, monkeypatch):
    """Issue #36 bullet 3: code drift STOPs; one recorded rebind lets the final run."""
    package = drift_package(tmp_path, monkeypatch)
    fakes = Fakes()
    optimise_all(tree, fakes)
    (package / "loop.py").write_text((package / "loop.py").read_text() + "# drift\n")
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, "task_group_001")
    assert not fakes.solver_calls and not fakes.replays
    path = addendum(tmp_path)
    record = rebind(tree, "task_group_001", path)
    state = json.loads((tree[1] / "task_group_001/campaign.json").read_text())
    assert record["from"] == {k: state[k] for k in ("champion_id", "evaluator_hash", "code_hash")}
    assert record["to"] != record["from"] and record["champion_id"] == state["champion_id"]
    assert record["addendum"] == str(path)
    assert record["addendum_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    stored = json.loads((tree[1] / "task_group_001/rebind.json").read_text())
    assert stored == record
    assert final(tree, fakes, "task_group_001").outcome == "updated"


def test_rebind_with_wrong_from_or_changed_champion_stops_before_solver(tree, tmp_path, monkeypatch):
    """Issue #36 bullet 3: from must equal campaign.json; the champion may not change."""
    package = drift_package(tmp_path, monkeypatch)
    fakes = Fakes()
    optimise_all(tree, fakes)
    (package / "loop.py").write_text((package / "loop.py").read_text() + "# drift\n")
    path = addendum(tmp_path)
    group = "task_group_001"
    rebind(tree, group, path)
    record = json.loads((tree[1] / group / "rebind.json").read_text())
    for broken in ({**record, "from": {**record["from"], "code_hash": "0" * 64}},
                   {**record, "to": {**record["to"], "code_hash": "0" * 64}},
                   {**record, "champion_id": "0" * 64}):
        (tree[1] / group / "rebind.json").write_text(json.dumps(broken))
        with pytest.raises(pilot.PilotStop, match="identity drift"):
            final(tree, fakes, group)
    assert not fakes.solver_calls and not fakes.replays
    # A rebind is only accepted while its recorded addendum still hashes to itself.
    (tree[1] / group / "rebind.json").write_text(json.dumps(record))
    path.write_text("# rewritten\n")
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, group)
    with pytest.raises(pilot.PilotStop, match="malformed rebind"):
        (tree[1] / group / "rebind.json").write_text("{")
        final(tree, fakes, group)
    assert not fakes.solver_calls and not fakes.replays


def test_rebind_refuses_open_campaign_and_a_second_rebind(tree, tmp_path):
    fakes = Fakes()
    optimise(tree, fakes, "task_group_001")
    path = addendum(tmp_path)
    assert rebind(tree, "task_group_001", path)
    with pytest.raises(pilot.PilotStop, match="already recorded"):
        rebind(tree, "task_group_001", path)
    (tree[1] / "task_group_002").mkdir(parents=True, exist_ok=True)
    (tree[1] / "task_group_002/campaign.json").write_text(json.dumps({"status": "open"}))
    with pytest.raises(pilot.PilotStop, match="open or missing"):
        rebind(tree, "task_group_002", path)


def test_code_hash_covers_package_and_lock(tmp_path):
    package, lock = tmp_path / "src/rsi_kernel", tmp_path / "uv.lock"
    package.mkdir(parents=True)
    (package / "a.py").write_text("a")
    lock.write_text("lock")
    before = pilot._code_hash(package, lock)
    (package / "__pycache__").mkdir()
    (package / "__pycache__/a.pyc").write_bytes(b"cache")
    assert pilot._code_hash(package, lock) == before
    lock.write_text("lock2")
    assert pilot._code_hash(package, lock) != before


# Schedule order per group (addendum #36): run -> adjudication + holdout task id -> champion,
# candidate. Call 2 is the first champion row of run 0 (test/001), call 1 its candidate row.
FAILED = {"score": None, "failure": {"status": "STOP", "reason": "solver"}}


@pytest.mark.parametrize("call,where", [(1, "champion on holdout"), (2, "candidate on holdout")])
def test_invalid_final_row_fails_gate_without_approval(tree, call, where):
    """Issue #36 bullet 4: a failed final row still blocks acceptance (existing behaviour)."""
    fakes = Fakes()
    optimise_all(tree, fakes)
    fakes.overrides = {call: FAILED}
    approvals = []
    results = final_all(tree, fakes, lambda path: approvals.append(path))
    group = "task_group_001"
    assert results[group].outcome == "failed_gate"
    assert not (tree[1] / group / "approval-request.json").exists()
    assert all(p.parent.name != group for p in approvals)
    assert len(approvals) == 2  # the other, valid groups still reach approval
    decisions = [json.loads(line) for line in (tree[1] / group / "private/decisions.jsonl").read_text().splitlines()]
    assert not any(d.get("mode") == "record-only" for d in decisions)


def test_scheduled_valid_requires_exactly_the_trimmed_schedule(tree):
    """Issue #36 bullet 1: 7 items x 3 runs x 2 arms; a dev or control row is invalid."""
    item_ids = ["a", "b"]
    rows = [{"arm": arm, "item_id": item, "run": run, "score": 1.0}
            for run in range(pilot.RUNS) for item in item_ids for arm in pilot.ARMS]
    assert len(rows) == 2 * pilot.RUNS * 2
    assert pilot._scheduled_valid(rows, item_ids)
    assert not pilot._scheduled_valid(rows + [{"arm": "control", "item_id": "a", "run": 0, "score": 1.0}], item_ids)
    assert not pilot._scheduled_valid(rows + [{"arm": "champion", "item_id": "c", "run": 0, "score": 1.0}], item_ids)
    assert not pilot._scheduled_valid(rows[:-1], item_ids)


def test_proposer_timeout_kills_and_verifies_named_container(tree, monkeypatch):
    import subprocess
    from rsi_kernel.adapters.gdpevo import solver_docker
    root, run_dir, champions, _ = tree
    tasks = pilot.frozen_tasks(root, "task_group_001")
    solver = DockerSolver(root=root, tasks=[t for t in tasks if t.subset == "train"],
                          evidence_dir=run_dir / "evidence", timeout=1)
    adapter = pilot._adapter(root, run_dir / "task_group_001", tasks, pilot._champion(champions["task_group_001"]),
                             solver, "stages")
    argvs = []

    def fake_run(argv, output=None, *, check=True):
        argvs.append(list(argv))
        if "propose-in-container" in argv:
            raise subprocess.TimeoutExpired(argv, 1)
        return subprocess.CompletedProcess(argv, 0, b"false\n" if "inspect" in argv else b"", b"")
    monkeypatch.setattr(solver, "_run", fake_run)
    monkeypatch.setattr(solver, "_docker_environment", lambda out: solver_docker._DOCKER_ENV.set({"PATH": ""}))
    calls = pilot._Calls(run_dir / "calls.jsonl")
    with pytest.raises(subprocess.TimeoutExpired):
        pilot.ContainerProposer(adapter, solver, run_dir / "proposer", "img")(
            adapter.get_artifact(), [], adapter.splits, calls)
    run = next(a for a in argvs if "propose-in-container" in a)
    name = run[run.index("--name") + 1]
    after = argvs[argvs.index(run) + 1:]
    assert after[0] == ["docker", "kill", name]
    assert after[1][:2] == ["docker", "inspect"] and after[1][-1] == name
    assert not any(a[:2] in (["docker", "rm"], ["docker", "network"]) for a in after)  # evidence kept


def test_rebind_cannot_swap_the_champion_even_if_the_record_agrees(tree, tmp_path, monkeypatch):
    """PR #37 review S1: frozen, current and recorded champion ids must all agree."""
    package = drift_package(tmp_path, monkeypatch)
    fakes = Fakes()
    optimise_all(tree, fakes)
    (package / "loop.py").write_text((package / "loop.py").read_text() + "# drift\n")
    path, group = addendum(tmp_path), "task_group_001"
    rebind(tree, group, path)
    config = tree[2][group]
    Path(config["path"]).write_text("# swapped champion\n")
    config["sha256"] = hashlib.sha256(Path(config["path"]).read_bytes()).hexdigest()
    swapped = pilot._champion(config).id
    record = json.loads((tree[1] / group / "rebind.json").read_text())
    record = {**record, "champion_id": swapped, "to": {**record["to"], "champion_id": swapped}}
    (tree[1] / group / "rebind.json").write_text(json.dumps(record))
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, group)
    assert not fakes.solver_calls and not fakes.replays


def test_existing_rebind_is_validated_even_without_drift(tree, tmp_path):
    """PR #37 review S2: a present rebind is never skipped, even when nothing drifted."""
    fakes = Fakes()
    optimise_all(tree, fakes)
    path, group = addendum(tmp_path), "task_group_001"
    rebind(tree, group, path)
    record = json.loads((tree[1] / group / "rebind.json").read_text())
    (tree[1] / group / "rebind.json").write_text(
        json.dumps({**record, "to": {**record["to"], "code_hash": "0" * 64}}))
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, group)
    assert not fakes.solver_calls and not fakes.replays


def test_report_lists_no_candidate_group_without_pairing_it(tree):
    """PR #37 review S2: a no-candidate group is reported, not fed to the paired estimator."""
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    state = tree[1] / "task_group_002/campaign.json"
    state.write_text(json.dumps({**json.loads(state.read_text()), "selected": None}))
    for group in pilot.GROUPS:
        final(tree, fakes, group)
    rows = pilot.report(tree[1], tree[0], "updated")
    assert [r["split"] for r in rows] == ["dev", "adjudication", "holdout"]
    assert all(r["no_candidate_groups"] == ["task_group_002"] for r in rows)
    assert all(r["paired_groups"] == ["task_group_001", "task_group_003"] for r in rows)


def test_null_rebind_record_is_malformed_not_absent(tree, tmp_path):
    """PR #37 re-check: a present rebind.json holding JSON null still STOPs."""
    fakes = Fakes()
    optimise_all(tree, fakes)
    (tree[1] / "task_group_001/rebind.json").write_text("null")
    with pytest.raises(pilot.PilotStop, match="malformed rebind"):
        final(tree, fakes, "task_group_001")
    assert not fakes.solver_calls and not fakes.replays


@pytest.mark.parametrize("selected", [(), ("task_group_001",)])
def test_report_marks_comparison_unavailable_below_two_paired_groups(tree, selected):
    """PR #37 re-check: zero or one candidate group reports status, not a crash."""
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    for group in pilot.GROUPS:
        if group not in selected:
            state = tree[1] / group / "campaign.json"
            state.write_text(json.dumps({**json.loads(state.read_text()), "selected": None}))
    for group in pilot.GROUPS:
        final(tree, fakes, group)
    rows = pilot.report(tree[1], tree[0], "no_improvement")
    assert [r["split"] for r in rows] == ["dev", "adjudication", "holdout"]
    assert all(r["comparison"] == "unavailable" and r["paired_groups"] == list(selected) for r in rows)
    assert all(r["champion_run_spread"] == 0.0 for r in rows)
