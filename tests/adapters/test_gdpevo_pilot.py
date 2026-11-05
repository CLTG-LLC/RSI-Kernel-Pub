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


def final(tree, fakes, wait=approve_matching):
    root, run_dir, champions, answer = tree
    return pilot.final_phase(root=root, run_dir=run_dir, champions=champions, solver=fakes.solver,
                             calibration_answer=answer, calibration_replay=fakes.replay, wait=wait)


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


def test_full_run_270_observations_in_prereg_order(tree):
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    fakes.solver_calls.clear()
    results = final(tree, fakes)
    rows = [json.loads(line) for line in (tree[1] / "final/observations.jsonl").read_text().splitlines()]
    assert len(rows) == len(fakes.solver_calls) == 270
    expected = [(g, run, item, arm) for g in pilot.GROUPS for run in range(pilot.RUNS)
                for item in sorted(t.item_id for t in pilot.frozen_tasks(tree[0], g)) for arm in pilot.ARMS]
    assert [(r["group"], r["run"], r["item_id"], r["arm"]) for r in rows] == expected
    assert len({(r["arm"], r["item_id"], r["run"]) for r in rows}) == 270
    assert {r.outcome for r in results.values()} == {"updated"}
    assert (tree[1] / "entropy.json").is_file()


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
    results = final(tree, fakes)
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
        final(tree, fakes)
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
    results = final(tree, fakes, wait)
    assert {r.outcome for r in results.values()} == {"not_updated"}
    decisions = [json.loads(line) for line in (tree[1] / "task_group_001/private/decisions.jsonl").read_text().splitlines()]
    assert not any(d.get("mode") == "record-only" for d in decisions)


def test_matching_approval_is_updated_record_only(tree):
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    results = final(tree, fakes)
    group = "task_group_001"
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
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    final(tree, fakes)
    rows = pilot.report(tree[1], tree[0], "updated")
    assert [r["split"] for r in rows] == ["dev", "adjudication", "holdout", "control"]
    assert all(r["retention_passed"] for r in rows)


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
        final(tree, fakes)
    assert not fakes.solver_calls and not fakes.replays


def test_code_change_between_phases_stops_before_solver(tree, tmp_path, monkeypatch):
    package, lock = tmp_path / "src/rsi_kernel", tmp_path / "uv.lock"
    shutil.copytree(pilot.PACKAGE_DIR, package, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(pilot.LOCK_FILE, lock)
    monkeypatch.setattr(pilot, "PACKAGE_DIR", package)
    monkeypatch.setattr(pilot, "LOCK_FILE", lock)
    fakes = Fakes()
    optimise_all(tree, fakes)
    (package / "loop.py").write_text((package / "loop.py").read_text() + "# drift\n")
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes)
    assert not fakes.solver_calls and not fakes.replays


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


# Schedule order per group: test/001..005 then train/001..005, arms champion, candidate, control.
FAILED = {"score": None, "failure": {"status": "STOP", "reason": "solver"}}


@pytest.mark.parametrize("call,where", [(3, "control on holdout"), (16, "champion on dev")])
def test_invalid_control_or_dev_row_fails_gate_without_approval(tree, call, where):
    fakes = Fakes()
    optimise_all(tree, fakes)
    fakes.overrides = {call: FAILED}
    approvals = []
    results = final(tree, fakes, lambda path: approvals.append(path))
    group = "task_group_001"
    assert results[group].outcome == "failed_gate"
    assert not (tree[1] / group / "approval-request.json").exists()
    assert all(p.parent.name != group for p in approvals)
    assert len(approvals) == 2  # the other, valid groups still reach approval
    decisions = [json.loads(line) for line in (tree[1] / group / "private/decisions.jsonl").read_text().splitlines()]
    assert not any(d.get("mode") == "record-only" for d in decisions)


def test_valid_low_control_score_never_vetoes(tree):
    fakes = Fakes()
    optimise_all(tree, fakes)
    per_group = 10 * pilot.RUNS * len(pilot.ARMS)
    fakes.overrides = {i: {"score": 0.0} for i in range(3, per_group + 1, 3)}  # every control row of group 001
    results = final(tree, fakes)
    assert results["task_group_001"].outcome == "updated"


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
