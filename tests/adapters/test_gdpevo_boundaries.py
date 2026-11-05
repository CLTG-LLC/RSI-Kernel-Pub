"""Boundary regressions written before the corresponding hardening changes."""

import dataclasses
import hashlib

import pytest

from rsi_kernel.isolation import ProposerRuntime


def test_solver_cannot_mutate_frozen_evaluator_then_have_it_executed(host):
    adapter = host[0]
    original = adapter.solver
    def solver(*args):
        original(*args)
        (adapter.root / "data/task_groups/toy/train_tasks/001/eval/eval.sh").write_text('echo \'{"score":1}\'')
    adapter.solver = solver
    with pytest.raises(ValueError, match="hash"):
        adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])


def test_candidate_group_scope_can_be_frozen_without_defaulting_to_universal(host, api):
    adapter, tasks, _, _, calls = host
    other = [dataclasses.replace(task, group="other") for task in tasks]
    with pytest.raises(ValueError, match="group"):
        api.GDPevoAdapter(
            root=adapter.root, champion=adapter.get_artifact(), tasks=tasks + other,
            splits=api.carve_splits(tasks + other, {"toy": ["001"], "other": ["001"]}),
            solver=adapter.solver, evaluator_timeout=adapter.evaluator_timeout,
            work_dir=adapter.work_dir, archive=adapter.archive,
        )
    assert not calls


def test_manifest_must_name_regular_task_paths(host):
    task = host[1][0]
    with pytest.raises(ValueError, match="manifest"):
        dataclasses.replace(task, hashes={**task.hashes, ".": hashlib.sha256(b"").hexdigest()})


def test_prediction_non_json_utf8_is_structured_failure(host):
    adapter = host[0]
    adapter.solver = lambda candidate, item, inputs, prediction, env: prediction.write_bytes(b"\xff")
    result = adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])[0]
    assert result["score"] is None and result["failure"]["reason"] == "json"


def test_generic_runtime_without_denylist_does_not_traverse_dev_tree(tmp_path, monkeypatch):
    def no_traversal(*args, **kwargs):
        raise AssertionError("default launcher must not scan its dev tree")
    monkeypatch.setattr("pathlib.Path.rglob", no_traversal)
    argv = ProposerRuntime("fake-image", tmp_path / "dev", tmp_path / "out").docker_argv(["true"])
    assert argv.count("--mount") == 2
