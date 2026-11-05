"""Docker integration: staged synthetic data, no model transport or network.

Reuse E0's real-runtime pattern; inspect an existing image, never pull in this
suite. Existing tests/e0 owns image provisioning. Configuration denial tests
also run without Docker, but they are not a substitute for this runtime check.
"""

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from rsi_kernel.adapters.gdpevo.runtime import GDPevoProposerRuntime

from test_gdpevo_isolation import EXCLUSIONS


SCRIPT = r'''
import json
import os
from pathlib import Path
from rsi_kernel.adapters.gdpevo import propose
from rsi_kernel.candidate import Candidate
from rsi_kernel.splits import load_splits

assert os.environ["TASK_ENV_ENABLE_JUDGE"] == "0"
config = json.loads(Path("/data/dev/config.json").read_text())
for path in config["forbidden"]:
    try:
        Path(path).read_bytes()
    except (FileNotFoundError, PermissionError, IsADirectoryError):
        pass
    else:
        raise AssertionError("protected read succeeded")
champion = Candidate({"SKILL.md": "# Toy original"}, "text/plain")
splits = load_splits({"splits": [
    {"name": "dev", "purpose": "dev", "selection_eligible": True,
     "item_ids": ["toy/train/001"]}
]})
records = [{"item_id": "toy/train/001", "input": "toy prompt", "output": "toy answer",
            "feedback": {"score": .5, "correct": False}}]
for response in ("```\n# Toy changed\n```", ""):
    calls = []
    def model(prompt):
        calls.append(prompt)
        return response
    candidate = propose(champion, records, splits, model)
    assert len(calls) == 1
    if response:
        assert dict(candidate.components) == {"SKILL.md": "# Toy changed"}
    else:
        assert candidate is None
Path("/out/result.json").write_text(json.dumps({"denied": len(config["forbidden"]), "proposal": "ok", "no_candidate": "ok"}))
'''


def test_real_container_denies_gdpevo_paths_and_runs_standalone_fake_gepa():
    image = "python:3.12-slim"  # Existing E0 image precedent, not a release digest.
    ready = shutil.which("docker") and subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode == 0
    if not ready:
        if os.environ.get("CI"):
            pytest.fail("GDPevo runtime E0 requires the existing E0 Docker image")
        pytest.skip("existing E0 Docker image unavailable")
    # Docker on this Mac shares home paths, not pytest's system temp directory.
    with tempfile.TemporaryDirectory(prefix="runtime-", dir=Path(__file__).parent) as temporary:
        root = Path(temporary)
        source, stage, output = root / "gdpevo", root / "staged", root / "out"
        stage.mkdir()
        output.mkdir()
        protected = []
        for relative in EXCLUSIONS:
            path = source / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("SYNTHETIC_PROTECTED_CANARY")
            protected.append(path)
        before = {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected}
        lib = stage / "lib"
        shutil.copytree(Path(__file__).parents[2] / "src/rsi_kernel", lib / "rsi_kernel", ignore=shutil.ignore_patterns("__pycache__"))
        gepa = importlib.util.find_spec("gepa")
        assert gepa and gepa.origin
        shutil.copytree(Path(gepa.origin).parent, lib / "gepa", ignore=shutil.ignore_patterns("__pycache__"))
        forbidden = [str(path) for path in protected] + [f"/data/dev/{relative}" for relative in EXCLUSIONS]
        (stage / "config.json").write_text(json.dumps({"forbidden": forbidden}))
        runtime = GDPevoProposerRuntime(image, stage, output, deny_paths=(source,))
        result = subprocess.run(runtime.docker_argv(["python", "-c", SCRIPT], {"PYTHONPATH": "/data/dev/lib"}), capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        assert json.loads((output / "result.json").read_text()) == {"denied": len(forbidden), "proposal": "ok", "no_candidate": "ok"}
        assert {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in protected} == before
