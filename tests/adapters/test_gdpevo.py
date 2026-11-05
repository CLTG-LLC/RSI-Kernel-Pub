import dataclasses
import json
import subprocess

import pytest

from rsi_kernel.candidate import Candidate
from rsi_kernel.compare import paired_compare


def test_artifact_is_hash_bound_and_apply_is_record_only(host):
    adapter, _, _, archive, _ = host
    champion = adapter.get_artifact()
    assert champion.id == Candidate(dict(champion.components), "text/plain").id
    adapter.apply(champion.id)
    assert adapter.get_artifact() is champion
    assert archive.private_store().decisions() == [{"candidate_id": champion.id, "mode": "record-only"}]
    with pytest.raises(ValueError):
        adapter.apply("unknown")


@pytest.mark.parametrize("components,media", [
    ({}, "text/plain"), ({"SKILL.md": "ok", "helper.py": "x"}, "text/plain"),
    ({"../SKILL.md": "ok"}, "text/plain"), ({"SKILL.md": b"\xff"}, "text/plain"),
    ({"SKILL.md": "ok"}, "application/json"),
])
def test_only_utf8_skill_package_is_admitted(api, components, media):
    with pytest.raises((ValueError, UnicodeError)):
        api.validate_skill(Candidate(components, media))


def test_kernel_carving_is_explicit_and_complete(host, api):
    _, tasks, splits, _, _ = host
    assert splits.dev_item_ids() == frozenset({"toy/train/001"})
    assert splits.item_ids("adjudication") == frozenset({"toy/train/002"})
    assert splits.item_ids("holdout") == frozenset({"toy/test/001"})
    assert api.carve_splits(tasks, {"toy": ["002"]}).dev_item_ids() == {"toy/train/002"}


@pytest.mark.parametrize("carving", [{}, {"toy": ["absent"]}, {"toy": ["001", "001"]}, {"other": []}])
def test_invalid_carving_refused(host, api, carving):
    with pytest.raises(ValueError):
        api.carve_splits(host[1], carving)


def test_official_wrapper_score_and_feedback_projection(host):
    adapter, _, _, _, calls = host
    results = adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])
    assert results == [{"item_id": "toy/train/001", "score": 1.0, "feedback": {"score": 1.0, "correct": True}}]
    assert "SYNTHETIC_GOLD" not in json.dumps(results)
    assert calls[0][1] == "toy/train/001"
    assert calls[0][4] == {"TASK_ENV_ENABLE_JUDGE": "0"}
    assert "eval" not in calls[0][2].parts


@pytest.mark.parametrize("items", [["toy/train/002"], ["toy/test/001"], ["unknown"], ["toy/train/001", "toy/test/001"], ["toy/train/001"] * 2, []])
def test_host_rejects_non_dev_and_bad_batches_before_solver(host, items):
    adapter, _, _, _, calls = host
    with pytest.raises((ValueError, PermissionError)):
        adapter.evaluate(adapter.get_artifact(), items)
    assert not calls


@pytest.mark.parametrize("payload,expected", [
    ({"normalized_score": .2, "total_score": .7, "score": .9}, .2),
    ({"normalized_score": True, "total_score": .7}, .7),
    ({"total_score": 7, "earned_score": 3, "max_score": 4, "score": .1}, .75),
    ({"earned_weight": 2, "total_weight": 4}, .5),
    ({"earned_points": 3, "total_points": 4}, .75),
    ({"earned": 2, "total": 4}, .5),
    ({"raw_score": 2, "raw_total": 4}, .5),
    ({"score": 2, "max_score": 4}, .5),
    ({"score": .4}, .4), ({"earned": -1, "total": 2}, 0),
    ({"earned": 3, "total": 2}, 1), ({"earned": 1, "total": 0}, None),
    ({"score": True}, None), ({"score": "0.5"}, None), ([], None),
    ({"score": float("nan")}, None), ({"score": 2}, None),
])
def test_upstream_normalization_precedence(api, payload, expected):
    assert api.score_from_evaluator(payload) == expected


@pytest.mark.parametrize("failure", ["timeout", "exit", "json", "score", "solver", "missing_prediction"])
def test_operational_failures_are_structured_not_zero(host, monkeypatch, failure):
    adapter = host[0]
    if failure == "solver":
        adapter.solver = lambda *args: (_ for _ in ()).throw(RuntimeError("SYNTHETIC_GOLD"))
    elif failure == "missing_prediction":
        adapter.solver = lambda *args: None
    else:
        def run(*args, **kwargs):
            if failure == "timeout":
                raise subprocess.TimeoutExpired(args[0], kwargs["timeout"], output="SYNTHETIC_GOLD")
            if failure == "exit":
                raise subprocess.CalledProcessError(1, args[0], output="SYNTHETIC_GOLD")
            return subprocess.CompletedProcess(args[0], 0, stdout=b"bad" if failure == "json" else b'{"details": "SYNTHETIC_GOLD"}', stderr=b"")
        monkeypatch.setattr("rsi_kernel.adapters.gdpevo.adapter.subprocess.run", run)
    result = adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])[0]
    assert result["score"] is None
    assert result["failure"]["reason"] == failure
    assert result["feedback"] == {"score": None, "correct": False}
    assert "SYNTHETIC_GOLD" not in json.dumps(result)
    records = [{**result, "run": 0}]
    assert paired_compare([{"item_id": result["item_id"], "run": 0, "score": 1}], records, [(result["item_id"], 0)]).blocks_acceptance


@pytest.mark.parametrize("relative", ["input/prompt.txt", "eval/eval.sh"])
def test_frozen_file_drift_is_stop_before_solver(host, relative):
    adapter, _, _, _, calls = host
    path = adapter.root / "data/task_groups/toy/train_tasks/001" / relative
    path.write_text("drift")
    with pytest.raises(ValueError, match="hash"):
        adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])
    assert not calls


def test_symlink_in_frozen_task_refused(host):
    adapter = host[0]
    path = adapter.root / "data/task_groups/toy/train_tasks/001/input/prompt.txt"
    original = path.read_text()
    path.unlink()
    target = adapter.work_dir.parent / "outside"
    target.write_text(original)
    path.symlink_to(target)
    with pytest.raises(ValueError, match="symlink"):
        adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])


@pytest.mark.parametrize("field,value", [("group", "../escape"), ("subset", "unknown"), ("task_id", "../escape")])
def test_task_paths_are_validated(host, field, value):
    with pytest.raises(ValueError):
        dataclasses.replace(host[1][0], **{field: value})


def test_task_hash_manifest_is_immutable(host):
    task = host[1][0]
    with pytest.raises(TypeError):
        task.hashes["input/prompt.txt"] = "changed"


def test_entire_batch_frozen_before_any_solver(host, api):
    adapter, tasks, _, _, calls = host
    adapter.splits = api.carve_splits(tasks, {"toy": ["001", "002"]})
    path = adapter.root / "data/task_groups/toy/train_tasks/002/eval/eval.sh"
    path.write_text("drift")
    with pytest.raises(ValueError):
        adapter.evaluate(adapter.get_artifact(), ["toy/train/001", "toy/train/002"])
    assert not calls


def test_solver_attempts_use_fresh_staged_dirs(host):
    adapter, _, _, _, calls = host
    for _ in range(2):
        adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])
    assert calls[0][2] != calls[1][2]


def test_evaluator_argv_uses_official_absolute_wrapper_and_timeout(host, monkeypatch):
    adapter = host[0]
    original = subprocess.run
    observed = []
    def run(argv, **kwargs):
        observed.append((argv, kwargs))
        return original(argv, **kwargs)
    monkeypatch.setattr("rsi_kernel.adapters.gdpevo.adapter.subprocess.run", run)
    adapter.evaluate(adapter.get_artifact(), ["toy/train/001"])
    argv, kwargs = observed[0]
    assert argv[0] == "/bin/sh"
    assert argv[1] == str(adapter.root / "data/task_groups/toy/train_tasks/001/eval/eval.sh")
    assert argv[2].startswith(str(adapter.work_dir))
    assert kwargs["timeout"] == adapter.evaluator_timeout
    assert kwargs["check"] is True
    assert kwargs["env"]["TASK_ENV_ENABLE_JUDGE"] == "0"
