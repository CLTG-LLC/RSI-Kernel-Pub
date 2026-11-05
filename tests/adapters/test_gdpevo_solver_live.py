"""Lead-only live model smoke; explicit opt-in AND never enabled in CI.

Requires RSI_GDPEVO_ROOT (pinned Git checkout), RSI_GDPEVO_SKILL and its frozen
RSI_GDPEVO_SKILL_SHA256, RSI_GDPEVO_EVIDENCE (outside repos, Docker-visible),
and caller-frozen RSI_GDPEVO_TIMEOUT. No credential is read or forwarded.
"""

import hashlib
import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RSI_LIVE_GDPEVO") != "1" or bool(os.environ.get("CI")),
    reason="lead-only model smoke, opt in with RSI_LIVE_GDPEVO=1; never CI",
)


def test_live_gdpevo_group001_train001():
    from rsi_kernel.adapters.gdpevo import GDPevoAdapter, carve_splits
    from rsi_kernel.adapters.gdpevo.solver_docker import DockerSolver
    from rsi_kernel.adapters.gdpevo.tasks import FrozenTask
    from rsi_kernel.archive import Archive
    from rsi_kernel.candidate import Candidate

    root = Path(os.environ["RSI_GDPEVO_ROOT"])
    skill = Path(os.environ["RSI_GDPEVO_SKILL"])
    evidence = Path(os.environ["RSI_GDPEVO_EVIDENCE"])
    timeout = float(os.environ["RSI_GDPEVO_TIMEOUT"])
    assert root.is_absolute() and skill.is_absolute() and evidence.is_absolute()
    assert skill.is_file() and not skill.is_symlink()
    payload = skill.read_bytes()
    assert hashlib.sha256(payload).hexdigest() == os.environ["RSI_GDPEVO_SKILL_SHA256"].lower()
    # Explicitly authorized dev task only. Never enumerate train siblings/test data.
    directory = root / "data/task_groups/task_group_001/train_tasks/001"
    hashes = {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in directory.rglob("*") if p.is_file()}
    task = FrozenTask("task_group_001", "train", "001", hashes)
    candidate = Candidate({"SKILL.md": payload}, "text/plain")
    solver = DockerSolver(root=root, tasks=[task], evidence_dir=evidence / "attempts", timeout=timeout)
    adapter = GDPevoAdapter(root=root, champion=candidate, tasks=[task],
        splits=carve_splits([task], {task.group: [task.task_id]}), solver=solver,
        evaluator_timeout=timeout, work_dir=evidence / "stages",
        archive=Archive(evidence / "public", evidence / "private"))
    result = adapter.evaluate(candidate, [task.item_id])[0]
    assert "failure" not in result, result
    assert 0 <= result["score"] <= 1
    out = Path(result["evidence_dir"])
    timing = json.loads((out / "attempt-timing.json").read_text())
    measured = json.loads((out / "measurement.json").read_text())
    assert timing["container_exit_code"] == timing["docker_attach_exit_code"] == 0
    assert timing["elapsed_seconds"] > 0
    assert measured["token_usage"] is not None
    assert measured["trace_sha256"] == hashlib.sha256(Path(measured["trace"]).read_bytes()).hexdigest()
    from rsi_kernel.adapters.gdpevo.scoring import score_from_evaluator
    assert score_from_evaluator(json.loads((out / "score.json").read_text())) == result["score"]
    print("Live attempt evidence: " + str(out))
