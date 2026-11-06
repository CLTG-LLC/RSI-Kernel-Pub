"""Lead-only T3 live smoke; explicit opt-in AND never enabled in CI.

Requires RSI_GDPEVO_ROOT (pinned Git checkout), RSI_GDPEVO_SKILL and frozen
RSI_GDPEVO_SKILL_SHA256, RSI_GDPEVO_SOLVER and frozen RSI_GDPEVO_SOLVER_SHA256,
RSI_GDPEVO_EVIDENCE (outside repos, Docker-visible), RSI_GDPEVO_TIMEOUT,
and frozen RSI_T3_CPUS, RSI_T3_MEMORY_BYTES, RSI_T3_FILE_BYTES; no defaults.
No credential is read or forwarded. Precedent: test_gdpevo_solver_live.py.

The campaign seed is tests/fixtures/t3_seed_solver.py::

    import json, sys
    print(json.dumps({"prompt": sys.stdin.read().rstrip("\\n")}))
"""

import hashlib
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RSI_LIVE_GDPEVO") != "1" or bool(os.environ.get("CI")),
    reason="lead-only T3 model smoke, opt in with RSI_LIVE_GDPEVO=1; never CI",
)


def _guard_agent_solve(monkeypatch):
    from rsi_kernel.adapters.gdpevo.solver_docker import DockerSolver

    agent_solve = DockerSolver._solve

    def checked_solve(self, out, scope, image):
        # T3 has finished its logic stage; the inherited agent has not started.
        expected = (out / "harness/prompt.txt").read_bytes().rstrip(b"\n")
        payload = json.loads((out / "logic.json").read_text())
        assert payload["prompt"].encode() == expected
        assert (out / "prompt.txt").read_bytes() == expected + b"\n"
        return agent_solve(self, out, scope, image)

    monkeypatch.setattr(DockerSolver, "_solve", checked_solve)


def test_live_gdpevo_code_group001_train001(monkeypatch):
    from rsi_kernel.adapters.gdpevo import carve_splits
    from rsi_kernel.adapters.gdpevo.scoring import score_from_evaluator
    from rsi_kernel.adapters.gdpevo.tasks import FrozenTask
    from rsi_kernel.adapters.gdpevo_code import CodeDockerSolver, CodeLimits, GDPevoCodeAdapter
    from rsi_kernel.archive import Archive
    from rsi_kernel.candidate import Candidate

    root = Path(os.environ["RSI_GDPEVO_ROOT"])
    skill = Path(os.environ["RSI_GDPEVO_SKILL"])
    source = Path(os.environ["RSI_GDPEVO_SOLVER"])
    evidence = Path(os.environ["RSI_GDPEVO_EVIDENCE"])
    timeout = float(os.environ["RSI_GDPEVO_TIMEOUT"])
    limits = CodeLimits(cpus=float(os.environ["RSI_T3_CPUS"]),
                        memory_bytes=int(os.environ["RSI_T3_MEMORY_BYTES"]),
                        file_bytes=int(os.environ["RSI_T3_FILE_BYTES"]))
    assert all(path.is_absolute() for path in (root, skill, source, evidence))
    assert all(path.is_file() and not path.is_symlink() for path in (skill, source))
    skill_bytes, source_bytes = skill.read_bytes(), source.read_bytes()
    assert hashlib.sha256(skill_bytes).hexdigest() == os.environ["RSI_GDPEVO_SKILL_SHA256"].lower()
    assert hashlib.sha256(source_bytes).hexdigest() == os.environ["RSI_GDPEVO_SOLVER_SHA256"].lower()
    assert source_bytes == (Path(__file__).parents[1] / "fixtures/t3_seed_solver.py").read_bytes()
    # Explicitly authorized dev task only. Never enumerate train siblings/test data.
    directory = root / "data/task_groups/task_group_001/train_tasks/001"
    hashes = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in directory.rglob("*") if p.is_file()}
    task = FrozenTask("task_group_001", "train", "001", hashes)
    candidate = Candidate({"solver.py": source_bytes}, "text/plain")
    solver = CodeDockerSolver(champion=candidate, skill=Candidate({"SKILL.md": skill_bytes}, "text/plain"),
        limits=limits, root=root, tasks=[task], evidence_dir=evidence / "attempts", timeout=timeout)

    # Success cleanup removes the agent. Retain native inspect evidence first;
    # no memory sampler or new solver instrumentation. Docker inspect precedent:
    # https://docs.docker.com/reference/cli/docker/inspect/
    cleanup = solver._cleanup

    def inspect_before_cleanup(scope):
        out = solver.evidence_dir / scope
        agent = scope + "-agent"
        checks = {
            "agent": agent,
            "agent_user": solver._run(["docker", "inspect", "--format", "{{.Config.User}}", agent]).stdout.decode().strip(),
            "agent_state": json.loads(solver._run(["docker", "inspect", "--format", "{{json .State}}", agent]).stdout),
            "logic": scope + "-logic",
            "logic_inspect_exit_code": solver._run(["docker", "inspect", scope + "-logic"], check=False).returncode,
        }
        receipt = out / "container-checks.json"
        receipt.write_text(json.dumps(checks, indent=2) + "\n", encoding="utf-8")
        receipt.chmod(0o600)
        cleanup(scope)

    _guard_agent_solve(monkeypatch)
    monkeypatch.setattr(solver, "_cleanup", inspect_before_cleanup)
    adapter = GDPevoCodeAdapter(root=root, champion=candidate, tasks=[task],
        splits=carve_splits([task], {task.group: [task.task_id]}), solver=solver,
        evaluator_timeout=timeout, work_dir=evidence / "stages",
        archive=Archive(evidence / "public", evidence / "private"))
    results = adapter.evaluate(candidate, [task.item_id])
    assert len(results) == 1, results
    result = results[0]
    assert "failure" not in result, result
    assert 0 <= result["score"] <= 1
    out = Path(result["evidence_dir"])
    timing = json.loads((out / "attempt-timing.json").read_text())
    measured = json.loads((out / "measurement.json").read_text())
    assert timing["container_exit_code"] == timing["docker_attach_exit_code"] == 0
    assert timing["elapsed_seconds"] > 0
    assert measured["token_usage"] is not None
    assert measured["trace_sha256"] == hashlib.sha256(Path(measured["trace"]).read_bytes()).hexdigest()
    assert score_from_evaluator(json.loads((out / "score.json").read_text())) == result["score"]

    checks = json.loads((out / "container-checks.json").read_text())
    assert checks["agent_user"] == f"{os.getuid()}:{os.getgid()}"
    uid = int(checks["agent_user"].split(":")[0])
    assert uid != 0
    assert checks["agent_state"]["ExitCode"] == 0
    assert checks["logic_inspect_exit_code"] != 0
    for name in ("work", "sessions"):
        directory = out / name
        assert directory.is_dir()
        for path in directory.rglob("*"):
            if path.is_file():
                assert path.stat().st_size <= limits.file_bytes, str(path)
    print("Live T3 attempt evidence: " + str(out))
    print("T3 agent OOM evidence: " + json.dumps({"OOMKilled": checks["agent_state"].get("OOMKilled")}))
    print("T3 memory peak: not recorded by CodeDockerSolver or Docker inspect .State")
