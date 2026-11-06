"""Synthetic pre-agent prompt guard checks; no Docker, dataset or model calls."""

import json

import pytest

from test_gdpevo_code_live import _guard_agent_solve
from rsi_kernel.adapters.gdpevo.solver_docker import DockerSolver


@pytest.mark.parametrize("logic_prompt,final_prompt,blocked", [
    ("prompt", b"prompt\n", False),
    ("changed", b"prompt\n", True),
    ("prompt", b"changed\n", True),
])
def test_prompt_identity_checked_before_agent_solve(
        monkeypatch, tmp_path, logic_prompt, final_prompt, blocked):
    (tmp_path / "harness").mkdir()
    (tmp_path / "harness/prompt.txt").write_bytes(b"prompt\n\n")
    (tmp_path / "logic.json").write_text(json.dumps({"prompt": logic_prompt}))
    (tmp_path / "prompt.txt").write_bytes(final_prompt)
    calls = []

    def agent_solve(self, out, scope, image):
        calls.append((self, out, scope, image))
        return "agent-result"

    monkeypatch.setattr(DockerSolver, "_solve", agent_solve)
    _guard_agent_solve(monkeypatch)
    solver = object()
    if blocked:
        with pytest.raises(AssertionError):
            DockerSolver._solve(solver, tmp_path, "synthetic", "synthetic-image")
        assert not calls
    else:
        assert DockerSolver._solve(solver, tmp_path, "synthetic", "synthetic-image") == "agent-result"
        assert calls == [(solver, tmp_path, "synthetic", "synthetic-image")]
