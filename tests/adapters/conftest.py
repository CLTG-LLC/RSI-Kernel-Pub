"""Synthetic contract fixture; never reads the public GDPevo dataset."""

import hashlib
import importlib
import shutil
from pathlib import Path

import pytest

from rsi_kernel.archive import Archive
from rsi_kernel.candidate import Candidate


@pytest.fixture
def api():
    return importlib.import_module("rsi_kernel.adapters.gdpevo")


@pytest.fixture
def host(api, tmp_path):
    # These are fixture sizes, not pilot parameters or a recommended carving rule.
    source = Path(__file__).parent / "fixtures" / "toy"
    root = tmp_path / "gdpevo"
    tasks = []
    for subset, ids in (("train", ("001", "002")), ("test", ("001",))):
        for task_id in ids:
            target = root / "data/task_groups/toy" / f"{subset}_tasks" / task_id
            shutil.copytree(source, target)
            hashes = {
                p.relative_to(target).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in target.rglob("*") if p.is_file()
            }
            tasks.append(api.FrozenTask("toy", subset, task_id, hashes))
    splits = api.carve_splits(tasks, {"toy": ["001"]})
    archive = Archive(tmp_path / "public", tmp_path / "private")
    calls = []

    def solver(candidate, item_id, input_dir, prediction_path, env):
        calls.append((candidate, item_id, input_dir, prediction_path, dict(env)))
        assert sorted(p.relative_to(input_dir).as_posix() for p in input_dir.rglob("*") if p.is_file()) == ["prompt.txt"]
        assert prediction_path.is_absolute()
        prediction_path.write_text('{"answer": "toy-ok"}')

    champion = Candidate({"SKILL.md": "# Toy skill\nFollow the toy prompt.\n"}, "text/plain")
    adapter = api.GDPevoAdapter(
        root=root, champion=champion, tasks=tasks, splits=splits, solver=solver,
        evaluator_timeout=5, work_dir=tmp_path / "attempts", archive=archive,
    )
    # Five seconds is a test-only watchdog, not a pilot evaluator timeout.
    return adapter, tasks, splits, archive, calls
