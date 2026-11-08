"""The production grader runs the pinned harness as a host-side driver (no outer container)."""

import json
import subprocess

import pytest

from test_swebench_live_solver import task


def test_harness_grader_runs_fresh_container_with_frozen_inputs(tmp_path, monkeypatch):
    from rsi_kernel.adapters.gdpevo.solver_docker import _DOCKER_ENV
    from rsi_kernel.adapters.swebench_live.solver import HarnessGrader

    dataset = tmp_path / "frozen/grading.jsonl"
    dataset.parent.mkdir()
    dataset.write_text("{}\n")
    prediction = tmp_path / "attempt/predictions.json"
    prediction.parent.mkdir()
    prediction.write_text("{}")
    output = tmp_path / "attempt/harness/run-0"
    output.mkdir(parents=True)
    harness = tmp_path / "harness"
    harness.mkdir()
    image = "registry.invalid/grader@sha256:" + "c" * 64
    calls = []

    python = tmp_path / "harness-venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text("")

    def run(argv, **kwargs):
        calls.append((list(argv), dict(kwargs)))
        # Host-side driver: no outer container; RepoLaunch creates its own.
        assert argv[0] == str(python) and "docker" not in argv[:2]
        assert kwargs["cwd"] == harness
        assert kwargs["env"]["DOCKER_HOST"] == "unix:///synthetic.sock"
        assert argv[1:] == [
            "-m", "evaluation.evaluation", "--dataset", str(dataset),
            "--split", "go", "--platform", "linux", "--patch_dir", str(prediction.resolve()),
            "--output_dir", str(output.resolve()), "--workers", "1", "--overwrite", "0",
            "--instance_ids", task().instance_id,
        ]
        assert not any("synthetic-agent" in arg or "synthetic-grade" in arg for arg in argv)
        (output / task().instance_id).mkdir()
        (output / task().instance_id / "report.json").write_text(json.dumps({
            "instance_id": task().instance_id, "resolved": True,
        }))
        (output / "results.json").write_text(json.dumps({
            "submitted": 1, "submitted_ids": [task().instance_id], "empty_patch_ids": [],
            "success_ids": [task().instance_id], "failure_ids": [], "error_ids": [], "incomplete_ids": [],
        }))
        return subprocess.CompletedProcess(argv, 0, b"", b"")

    monkeypatch.setattr("rsi_kernel.adapters.swebench_live.solver.subprocess.run", run)
    token = _DOCKER_ENV.set({"PATH": "/usr/bin", "DOCKER_HOST": "unix:///synthetic.sock"})
    try:
        grader = HarnessGrader(harness_dir=harness, python=python, grading_data=dataset, image=image, timeout=30)
        results, report = grader(task(), prediction, output, run=0, image=image,
                                 container_name="synthetic-grade")
    finally:
        _DOCKER_ENV.reset(token)
    assert results["success_ids"] == [task().instance_id]
    assert report == {"instance_id": task().instance_id, "resolved": True}
    assert len(calls) == 1


def test_harness_grader_requires_digest_pinned_image_and_local_data(tmp_path):
    from rsi_kernel.adapters.swebench_live.solver import HarnessGrader

    with pytest.raises(ValueError):
        HarnessGrader(harness_dir=tmp_path, python=tmp_path / "py", grading_data=tmp_path / "missing", image="grader:latest", timeout=30)


def test_harness_grader_requires_daemon_endpoint(tmp_path):
    from rsi_kernel.adapters.gdpevo.solver_docker import _DOCKER_ENV
    from rsi_kernel.adapters.swebench_live.solver import HarnessGrader

    (tmp_path / "py").write_text("")
    (tmp_path / "d.jsonl").write_text("{}\n")
    image = "registry.invalid/grader@sha256:" + "c" * 64
    grader = HarnessGrader(harness_dir=tmp_path, python=tmp_path / "py", grading_data=tmp_path / "d.jsonl",
                           image=image, timeout=30)
    token = _DOCKER_ENV.set({"PATH": "/usr/bin"})
    try:
        with pytest.raises(ValueError):
            grader(task(), tmp_path / "p.json", tmp_path, run=0, image=image, container_name="x")
    finally:
        _DOCKER_ENV.reset(token)


@pytest.mark.parametrize("reason", ["dispatch_failure", "queue_expiry", "cancellation", "timeout",
                                    "missing_artifact", "binding_mismatch", "silent_termination"])
def test_remote_none_is_preserved_as_solver_failure(tmp_path, monkeypatch, reason):
    from test_swebench_live_solver import fixture as solver_fixture, CANDIDATE

    # Reuse the established full fake-Docker solver fixture, without a real daemon.
    _, solver, _, _ = solver_fixture.__wrapped__(tmp_path, monkeypatch)

    class MissingGrade:
        failure = {"reason": reason}

        def __call__(self, *args, **kwargs):
            return None

    solver.grader = MissingGrade()
    solved = solver(CANDIDATE, task().item_id, run=0)
    assert solved["score"] is None and solved["failure"]["reason"] == reason
