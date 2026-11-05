"""PR #12 review fixes: corrupt observations and frozen authority."""

import dataclasses
import subprocess
from pathlib import Path

import pytest

from rsi_kernel.compare import paired_compare
from rsi_kernel.isolation import ProposerRuntime
from rsi_kernel.splits import Splits


def assert_blocks(result):
    assert result["score"] is None
    assert result["feedback"] == {"score": None, "correct": False}
    assert result["failure"]["reason"] == "json"
    item = result["item_id"]
    comparison = paired_compare(
        [{"item_id": item, "run": 0, "score": 1}],
        [{**result, "run": 0}], [(item, 0)],
    )
    assert comparison.blocks_acceptance


@pytest.mark.parametrize("payload", [
    b'{"earned": NaN, "total": 1}',
    b'{"earned": Infinity, "total": 1}',
    b'{"earned": 1e999, "total": 1}',
    b'{"earned": 1e999, "total": 1e999}',
    b'{"score": 1, "details": {"nested": [1e999]}}',
    b'{"score": 1, "details": [-Infinity]}',
])
def test_nonfinite_json_never_becomes_a_correct_observation(host, monkeypatch, payload):
    def run(argv, **kwargs):
        stdout = payload.decode("utf-8") if kwargs.get("text") else payload
        stderr = "" if kwargs.get("text") else b""
        return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr=stderr)
    monkeypatch.setattr("rsi_kernel.adapters.gdpevo.adapter.subprocess.run", run)
    assert_blocks(host[0].evaluate(host[0].get_artifact(), ["toy/train/001"])[0])


@pytest.mark.parametrize("stream", ["stdout", "stderr"])
def test_invalid_evaluator_encoding_is_structured_failure(host, monkeypatch, stream):
    original = subprocess.run
    def run(argv, **kwargs):
        # Use a real child to exercise subprocess's text-decoding failure path.
        script = "printf '\\377'" if stream == "stdout" else "printf '{\"score\":1}'; printf '\\377' >&2"
        return original(["/bin/sh", "-c", script], **kwargs)
    monkeypatch.setattr("rsi_kernel.adapters.gdpevo.adapter.subprocess.run", run)
    assert_blocks(host[0].evaluate(host[0].get_artifact(), ["toy/train/001"])[0])


def test_loaded_carving_cannot_change_host_or_proposer_permissions(host, api):
    adapter, _, splits, _, solver_calls = host
    before = splits.dev_item_ids()
    replacement = dataclasses.replace(splits.by_name["dev"], item_ids=frozenset({"toy/test/001"}))
    with pytest.raises(TypeError):
        splits.by_name["dev"] = replacement
    assert splits.dev_item_ids() == before
    with pytest.raises(PermissionError):
        adapter.evaluate(adapter.get_artifact(), ["toy/test/001"])
    prompts = []
    with pytest.raises(PermissionError):
        api.propose(adapter.get_artifact(), [{
            "item_id": "toy/test/001", "input": "HOLDOUT_CANARY", "output": "toy",
            "feedback": {"score": 1, "correct": True},
        }], splits, lambda prompt: prompts.append(prompt) or "")
    assert not solver_calls and not prompts


def test_direct_split_construction_copies_then_freezes_mapping(host):
    original = dict(host[2].by_name)
    splits = Splits(original)
    before = splits.dev_item_ids()
    original["dev"] = dataclasses.replace(original["dev"], item_ids=frozenset({"toy/test/001"}))
    assert splits.dev_item_ids() == before
    with pytest.raises(TypeError):
        del splits.by_name["dev"]


def test_protected_mount_root_rejected_before_descendant_scan(tmp_path, monkeypatch):
    def no_scan(*args, **kwargs):
        pytest.fail("protected mount root must fail before scanning descendants")
    monkeypatch.setattr(Path, "rglob", no_scan)
    runtime = ProposerRuntime("fake-image", tmp_path / "protected", tmp_path / "out", deny_paths=(tmp_path / "protected",))
    with pytest.raises(PermissionError):
        runtime.docker_argv(["true"])


def test_descendant_scan_stops_at_first_protected_alias(tmp_path, monkeypatch):
    protected = tmp_path / "protected"
    staged = tmp_path / "staged"
    staged.mkdir()
    alias = staged / "alias"
    alias.symlink_to(protected, target_is_directory=True)
    def descendants(*args, **kwargs):
        yield alias
        pytest.fail("denylist materialized or continued past the protected descendant")
    monkeypatch.setattr(Path, "rglob", descendants)
    runtime = ProposerRuntime("fake-image", staged, tmp_path / "out", deny_paths=(protected,))
    with pytest.raises(PermissionError):
        runtime.docker_argv(["true"])
