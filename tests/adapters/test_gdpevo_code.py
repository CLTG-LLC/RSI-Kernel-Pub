"""Synthetic T3 contracts; no GDPevo dataset or live model calls."""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from rsi_kernel.candidate import Candidate
from rsi_kernel.adapters.gdpevo_code import CodeDockerSolver, CodeLimits, GDPevoCodeAdapter, validate_code
from rsi_kernel.adapters.gdpevo_code import pilot as code_pilot
from test_gdpevo_solver_docker import build_solver, docker_solver

# NAMED LOCAL EXCEPTION T3-SYNTHETIC-VALUES, measured by the tiny real-container
# test: these are test feasibility values, NOT GDPevo workload recommendations.
LIMITS = CodeLimits(cpus=1, memory_bytes=256 * 1024 * 1024, file_bytes=1024 * 1024)
SOURCE = 'import json,sys\nprint(json.dumps({"prompt":sys.stdin.read()}))\n'


def champion():
    return Candidate({"solver.py": SOURCE}, "text/plain")


def test_harness_code_adapter_is_available():
    assert importlib.util.find_spec("rsi_kernel.adapters.gdpevo_code") is not None


@pytest.fixture
def code_solver(docker_solver, monkeypatch):
    mod, original, fake, incoming, prediction = docker_solver
    solver = CodeDockerSolver(champion=champion(), skill=Candidate({"SKILL.md": "fixed"}, "text/plain"),
                              limits=LIMITS, root=original.root, tasks=list(original.tasks.values()),
                              evidence_dir=original.evidence_dir, timeout=original.timeout)
    fake.solver = solver
    base = fake.__call__
    state = {"prompt": "synthetic changed prompt", "payload": None, "timeout": None,
             "running": True, "removed": set(), "forged_success": False, "grade": 1}

    def run(argv, **kwargs):
        name = argv[argv.index("--name") + 1] if "--name" in argv else None
        if name and name.endswith("-logic"):
            fake.calls.append((argv, kwargs))
            if state["timeout"] == "logic":
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            payload = state["payload"] if state["payload"] is not None else {"prompt": state["prompt"]}
            kwargs["stdout"].write((state.get("raw_payload") or json.dumps(payload)).encode())
            return subprocess.CompletedProcess(argv, 0)
        if argv[:2] == ["docker", "start"] and state["timeout"] == "agent":
            fake.calls.append((argv, kwargs))
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if argv[:2] == ["docker", "kill"]:
            state["running"] = False
        if argv[:3] == ["docker", "rm", "-f"]:
            state["removed"].update(argv[3:])
        if argv[:2] == ["docker", "inspect"] and "{{.State.Running}}" in argv:
            fake.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 0, str(state["running"]).lower().encode(), b"")
        if argv[:2] == ["docker", "inspect"] and argv[-1] in state["removed"]:
            fake.calls.append((argv, kwargs))
            return subprocess.CompletedProcess(argv, 1, b"", b"not found")
        if "/trusted/eval/eval.sh" in argv and "empty-prediction" not in " ".join(argv):
            fake.calls.append((argv, kwargs))
            kwargs["stdout"].write(json.dumps({"total_score": state["grade"]}).encode())
            return subprocess.CompletedProcess(argv, 0)
        result = base(argv, **kwargs)
        if argv[:2] == ["docker", "start"] and state["forged_success"]:
            work = fake.attempt() / "work"
            (work / "success.json").write_text('{"total_score":1}')
            (work / "score.json").write_text('{"total_score":1}')
            (work / "result.json").write_text('{"score":1}')
        return result

    monkeypatch.setattr(mod.subprocess, "run", run)
    # Fake the new trusted PIPE collector, not Docker itself; real tests exercise it.
    def collect(argv, output):
        try:
            solver._run(argv, output)
        except subprocess.TimeoutExpired:
            solver._stop_timed_out(output.parent, argv[argv.index("--name") + 1])
            raise
    monkeypatch.setattr(solver, "_collect_logic", collect)
    return solver, fake, incoming, prediction, state


def solve(fixture, candidate=None):
    solver, _, incoming, prediction, _ = fixture
    return solver(candidate or champion(), "task_group_001/train/001", incoming, prediction,
                  {"TASK_ENV_ENABLE_JUDGE": "0"})


@pytest.mark.parametrize("components", [{"SKILL.md": SOURCE}, {"solver.py": SOURCE, "extra": "x"},
                                        {"../solver.py": SOURCE}, {"/harness/solver.py": SOURCE},
                                        {"sub/../../solver.py": SOURCE}])
def test_wrong_extra_and_escape_keys_stop_before_execution(code_solver, components):
    result = solve(code_solver, Candidate(components, "text/plain"))
    assert result["failure"]["status"] == "STOP"
    assert not code_solver[1].calls


@pytest.mark.parametrize("parents", [(), ("wrong",), ("wrong", "extra")])
def test_parent_mismatch_stops_before_execution(code_solver, parents):
    candidate = Candidate({"solver.py": SOURCE + "# changed\n"}, "text/plain", parents)
    assert solve(code_solver, candidate)["score"] is None
    assert not code_solver[1].calls


def test_same_bytes_with_forged_parent_is_rejected(code_solver):
    assert solve(code_solver, Candidate({"solver.py": SOURCE}, "text/plain", ("wrong",)))["score"] is None
    assert not code_solver[1].calls


def test_symlink_destination_stops_before_execution(code_solver, monkeypatch):
    solver, fake, incoming, _, _ = code_solver
    target = solver.evidence_dir / "stage-only/harness"
    target.parent.mkdir(parents=True)
    outside = solver.evidence_dir.parent / "outside"
    outside.mkdir()
    target.symlink_to(outside, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        solver._stage(champion(), next(iter(solver.tasks.values())), incoming, target.parent, "stage-only")
    assert not fake.calls and not list(outside.iterdir())


def test_nonroot_limits_fixed_code_mapping_and_trusted_codex(code_solver):
    assert solve(code_solver)["score"] == 1
    _, fake, _, _, _ = code_solver
    logic = next(a for a, _ in fake.calls if "harness-code" in a)
    agent = next(a for a, _ in fake.calls if a[:2] == ["docker", "create"])
    for argv in (logic, agent):
        for flag, value in (("--user", "nobody"), ("--cpus", "1"),
                            ("--memory", str(LIMITS.memory_bytes)),
                            ("--ulimit", f"fsize={LIMITS.file_bytes}:{LIMITS.file_bytes}")):
            assert argv[argv.index(flag) + 1] == value
        assert "--pids-limit" not in argv and "--privileged" not in argv
    assert logic[logic.index("--network") + 1] == "none"
    assert agent[agent.index("--network") + 1].endswith("-net")
    assert "--read-only" in logic and "--tmpfs" in logic
    assert any("target=/harness,readonly" in a for a in logic)
    assert not any("target=/harness" in a for a in agent)
    assert agent[-1] == "synthetic changed prompt"
    assert 'model_reasoning_effort="xhigh"' in " ".join(agent)
    assert 'requires_openai_auth = false' in " ".join(agent)
    assert all(a[a.index("--network") + 1] == "none" for a, _ in fake.calls if "/trusted/eval/eval.sh" in a)
    manifest = json.loads((fake.attempt() / "code-manifest.json").read_text())
    assert set(manifest) == {"solver.py", "prompt.txt"}
    assert (fake.attempt() / "harness/solver.py").read_text() == SOURCE
    assert (fake.attempt() / "work/skill/SKILL.md").read_text() == "fixed"
    networks = [a for a, _ in fake.calls if a[:3] == ["docker", "network", "create"]]
    assert any("--internal" in a for a in networks)
    connections = [a for a, _ in fake.calls if a[:3] == ["docker", "network", "connect"]]
    assert len(connections) == 1 and connections[0][-1].endswith("-fwd")
    assert not any("/trusted/eval" in a or "/trusted/output" in a for a in logic + agent)


@pytest.mark.parametrize("payload", [{"prompt": ""}, {"prompt": "x", "score": 1},
                                    {"prompt": 1}, [], {"prompt": "x\0y"}])
def test_logic_output_exact_contract_stops_before_codex(code_solver, payload):
    code_solver[-1]["payload"] = payload
    assert solve(code_solver)["score"] is None
    assert not code_solver[1].attach_started


@pytest.mark.parametrize("prompt", ["--help", "--config=x", "resume"])
def test_candidate_prompt_is_positional_data_not_codex_options(code_solver, prompt):
    from rsi_kernel.adapters.gdpevo import solver_docker as sd
    state = code_solver[-1]
    state["prompt"] = prompt
    assert solve(code_solver)["score"] == 1
    argv = next(a for a, _ in code_solver[1].calls if a[:2] == ["docker", "create"])
    command = argv[argv.index("-c") + 1]
    assert '--json -- "$1" < /dev/null' in command
    assert argv[-1] == prompt
    assert '--json "$1" < /dev/null' in sd.SOLVER_COMMAND
    assert '--json -- "$1"' not in sd.SOLVER_COMMAND


@pytest.mark.parametrize("stream", ["logic.json", "logic.json.stderr"])
def test_oversized_logic_rejected_before_read_or_json(code_solver, monkeypatch, stream):
    solver, fake, _, _, state = code_solver
    def collect(argv, output):
        state["running"] = False
        (output.parent / "logic.json").write_text('{"prompt":"x"}')
        (output.parent / "logic.json.stderr").write_bytes(b"")
        (output.parent / stream).write_bytes(b"x" * (LIMITS.file_bytes + 1))
    monkeypatch.setattr(solver, "_collect_logic", collect)
    original = Path.read_text
    def read(path, *args, **kwargs):
        if path.name == "logic.json":
            pytest.fail("oversized output reached read_text")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", read)
    result = solve(code_solver)
    assert result["failure"] == {"status": "STOP", "reason": "logic_output_limit"}
    assert not fake.attach_started
    assert next(iter(state["removed"])).endswith("-logic")


def test_duplicate_logic_output_is_rejected(code_solver):
    code_solver[-1]["raw_payload"] = '{"prompt":"x","prompt":"y"}'
    assert solve(code_solver)["score"] is None
    assert not code_solver[1].attach_started


def test_candidate_authored_success_files_do_not_change_trusted_score(code_solver):
    code_solver[-1].update(forged_success=True, grade=0)
    result = solve(code_solver)
    assert result["score"] == 0
    assert json.loads((code_solver[1].attempt() / "work/score.json").read_text())["total_score"] == 1
    assert json.loads((code_solver[1].attempt() / "score.json").read_text())["total_score"] == 0


@pytest.mark.parametrize("role", ["logic", "agent", "grade", "sanity"])
def test_timeout_removes_only_owned_container(code_solver, monkeypatch, role):
    if role in ("logic", "agent"):
        code_solver[-1]["timeout"] = role
    else:
        mod = importlib.import_module("rsi_kernel.adapters.gdpevo.solver_docker")
        base = mod.subprocess.run
        def run(argv, **kwargs):
            if "/trusted/eval/eval.sh" in argv and any(a.endswith("-" + role) for a in argv):
                code_solver[1].calls.append((argv, kwargs))
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            return base(argv, **kwargs)
        monkeypatch.setattr(mod.subprocess, "run", run)
    assert solve(code_solver)["failure"]["status"] == "STOP"
    fake = code_solver[1]
    scope = (fake.attempt() / "container-scope.txt").read_text().strip()
    expected = {scope + "-" + role} | ({scope + "-logic"} if role in ("agent", "grade") else set())
    assert code_solver[-1]["removed"] == expected
    assert not code_solver[-1]["running"]
    assert any(a[:2] == ["docker", "inspect"] and a[-1] == scope + "-" + role for a, _ in fake.calls)
    assert (fake.attempt() / "failure.json").exists()


def test_code_adapter_reuses_trusted_scores_and_record_only_apply(code_solver, monkeypatch):
    from rsi_kernel.archive import Archive
    from rsi_kernel.adapters.gdpevo.tasks import carve_splits
    solver = code_solver[0]
    tasks = list(solver.tasks.values())
    adapter = GDPevoCodeAdapter(champion=champion(), root=solver.root, tasks=tasks,
        splits=carve_splits(tasks, {tasks[0].group: [tasks[0].task_id]}), solver=solver,
        evaluator_timeout=60, work_dir=solver.evidence_dir.parent / "stages",
        archive=Archive(solver.evidence_dir.parent / "public", solver.evidence_dir.parent / "private"))
    monkeypatch.setattr(adapter, "_grade", lambda *a: pytest.fail("host must not regrade"))
    assert adapter.evaluate(champion(), [tasks[0].item_id])[0]["score"] == 1
    adapter.apply(champion().id)
    assert adapter.get_artifact() == champion()
    with pytest.raises(ValueError):
        adapter.evaluate(Candidate({"solver.py": SOURCE + "# changed"}, "text/plain", ("wrong",)), [tasks[0].item_id])
    with pytest.raises(PermissionError):
        adapter.evaluate(champion(), ["task_group_001/test/001"])


@pytest.mark.parametrize("field,value", [("cpus", 0), ("cpus", True), ("cpus", float("nan")),
                                       ("memory_bytes", 0), ("file_bytes", -1), ("file_bytes", True)])
def test_limits_have_no_defaults_and_reject_invalid_values(field, value):
    from dataclasses import asdict
    with pytest.raises(TypeError):
        CodeLimits()
    with pytest.raises(ValueError):
        CodeLimits(**{**asdict(LIMITS), field: value})


def test_rewrite_hooks_use_one_call_and_frozen_parent(host, tmp_path):
    from rsi_kernel.adapters.gdpevo import pilot
    calls = []
    def model(prompt):
        calls.append(prompt)
        return '```python\n' + SOURCE + '# changed\n```'
    records = [{"item_id": "toy/train/001", "input": "synthetic", "output": "{}", "feedback": {"score": 0}}]
    meter = pilot._Calls(tmp_path / "calls.jsonl")
    candidate = pilot.in_process_proposer(model, code_pilot.CODE)(champion(), records, host[0].splits, meter)
    assert candidate.parent_ids == (champion().id,)
    assert validate_code(candidate, champion()) == SOURCE + "# changed"
    assert len(calls) == meter.count == 1
    assert "complete Python solver.py" in calls[0] and "not a diff" in calls[0]
    assert code_pilot.CODE.spend_cap == pilot.SPEND_CAP
    assert code_pilot.admit(champion(), SOURCE, None, ()) is None


def test_execution_identity_binds_frozen_skill_limits_and_timeout(code_solver):
    from dataclasses import replace
    from rsi_kernel.adapters.gdpevo import pilot
    solver = code_solver[0]
    tasks = list(solver.tasks.values())
    expected = pilot._identity(champion(), tasks, solver)
    wrapped = pilot._metered_solver(solver, None)
    assert pilot._identity(champion(), tasks, wrapped) == expected
    changed = CodeDockerSolver(champion=champion(), skill=Candidate({"SKILL.md": "changed"}, "text/plain"),
        limits=replace(LIMITS, cpus=2), root=solver.root, tasks=tasks,
        evidence_dir=solver.evidence_dir, timeout=solver.timeout)
    assert pilot._identity(champion(), tasks, changed) != expected
    assert pilot._identity(champion(), tasks)["code_hash"] == pilot._code_hash()


def test_factory_uses_hash_checked_champion_and_required_limits(code_solver, tmp_path):
    import hashlib
    from dataclasses import asdict
    solver = code_solver[0]
    source, skill = tmp_path / "source.py", tmp_path / "skill.md"
    source.write_text(SOURCE)
    skill.write_text("fixed")
    def pinned(path):
        return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    config = {"champions": {"g": pinned(source)}, "skills": {"g": pinned(skill)}, "code_limits": asdict(LIMITS)}
    kwargs = dict(root=solver.root, tasks=list(solver.tasks.values()), evidence_dir=solver.evidence_dir, timeout=solver.timeout)
    made = code_pilot.solver_factory(config, "g", **kwargs)
    assert made.champion == champion() and made.limits == LIMITS
    with pytest.raises(KeyError):
        code_pilot.solver_factory({k: v for k, v in config.items() if k != "code_limits"}, "g", **kwargs)
    with pytest.raises(ValueError):
        CodeDockerSolver(champion=champion(), skill=made.skill, limits=None, **kwargs)


def test_final_phase_per_item_parent_guard_runs_before_solver(code_solver, monkeypatch):
    from rsi_kernel.archive import Archive
    from rsi_kernel.adapters.gdpevo.tasks import carve_splits
    solver = code_solver[0]
    tasks = list(solver.tasks.values())
    adapter = GDPevoCodeAdapter(champion=champion(), root=solver.root, tasks=tasks,
        splits=carve_splits(tasks, {tasks[0].group: [tasks[0].task_id]}), solver=solver,
        evaluator_timeout=60, work_dir=solver.evidence_dir.parent / "stages",
        archive=Archive(solver.evidence_dir.parent / "public", solver.evidence_dir.parent / "private"))
    with pytest.raises(ValueError, match="parent"):
        adapter._evaluate_one(Candidate({"solver.py": SOURCE + "# changed"}, "text/plain", ("wrong",)),
                              tasks[0].item_id, tasks[0].directory(solver.root))
    assert not code_solver[1].calls


def test_hash_and_champion_path_drift_rejected(tmp_path):
    import hashlib
    path = tmp_path / "solver.py"
    path.write_text(SOURCE)
    config = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    assert code_pilot.load_champion(config) == champion()
    path.write_text(SOURCE + "# drift")
    with pytest.raises(Exception, match="hash"):
        code_pilot.load_champion(config)
    alias = tmp_path / "alias"
    alias.symlink_to(path)
    with pytest.raises(Exception, match="symlink"):
        code_pilot.load_champion({**config, "path": str(alias)})
    forged = champion()
    object.__setattr__(forged, "id", "wrong")
    with pytest.raises(ValueError, match="hash"):
        validate_code(forged)


def test_data_only_candidate_media_and_default_hooks_unchanged():
    from rsi_kernel.adapters.gdpevo.adapter import validate_skill
    from rsi_kernel.adapters.gdpevo.pilot import SKILL
    from rsi_kernel.adapters.gdpevo_memory.pilot import LIBRARY
    with pytest.raises(ValueError):
        Candidate({"solver.py": SOURCE}, "text/x-python")
    with pytest.raises(ValueError):
        validate_skill(champion())
    assert SKILL.solver_factory is LIBRARY.solver_factory is None
