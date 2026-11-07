"""Issue #113 lead-run health check, on the synthetic faked-Docker fixture only."""

import json

import pytest

from test_gdpevo_solver_docker import GROUP_001_ENDPOINTS, build_solver  # noqa: F401

from rsi_kernel.adapters.gdpevo import health


def run(build_solver, tmp_path, group="task_group_004", failure=None, state=None):
    mod, solver, fake, _, _ = build_solver({group: GROUP_001_ENDPOINTS})
    fake.failure = failure
    if state:
        fake.health = [state]
    return health.main(["--root", str(solver.root), "--group", group,
                        "--evidence-dir", str(tmp_path / "health-evidence")]), fake


def test_healthy_group_with_judge_disabled_passes(build_solver, tmp_path, capsys):
    code, fake = run(build_solver, tmp_path)
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out == {"group": "task_group_004", "status": "ok", "health": {"ok": True},
                   "judge_http_status": 404, "judge_env": "TASK_ENV_ENABLE_JUDGE=0",
                   "evidence_dir": out["evidence_dir"]}
    env = next(a for a, _ in fake.calls if "TASK_ENV_ENABLE_JUDGE=0" in a)
    assert "TASK_ENV_PORT=9004" in env
    # No solve and no grade: only the environment and its check are started.
    assert not any("/trusted/eval/eval.sh" in a or a[1:2] == ["create"] for a, _ in fake.calls)
    removed = [a for a, _ in fake.calls if a[1:3] == ["rm", "-f"]]
    assert removed and {n.rsplit("-", 1)[1] for n in removed[0][3:]} == {"check", "env", "fwd"}


@pytest.mark.parametrize("failure, state, reason", [
    (None, "unhealthy", "environment_unhealthy"),
    ("judge", None, "environment"),
])
def test_unhealthy_or_judge_reachable_is_a_stop(build_solver, tmp_path, capsys, failure, state, reason):
    code, _ = run(build_solver, tmp_path, failure=failure, state=state)
    assert code == 1
    assert json.loads(capsys.readouterr().out) == {"group": "task_group_004", "status": "STOP", "reason": reason}


def test_unregistered_group_is_refused(tmp_path):
    with pytest.raises(SystemExit):
        health.main(["--root", str(tmp_path), "--group", "task_group_022", "--evidence-dir", str(tmp_path / "e")])
