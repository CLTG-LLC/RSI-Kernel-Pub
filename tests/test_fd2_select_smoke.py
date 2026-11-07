"""Unit tests for the content-free gold-smoke selection rule."""

import hashlib
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / "fd2" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


select_smoke = load_tool("select_smoke").select_smoke
write_selected_jsonl = load_tool("prepare_frozen").write_selected_jsonl
pin_image = load_tool("prepare_frozen").pin_image


def test_selects_newest_per_split_and_breaks_ties_by_lowest_id():
    newest = datetime(2026, 7, 2, tzinfo=timezone.utc)
    rows = [
        {"instance_id": "z__newer", "created_at": newest, "docker_image": "example/z"},
        {"instance_id": "b__tied", "created_at": newest, "docker_image": "example/b"},
        {"instance_id": "a__tied", "created_at": newest, "docker_image": "example/a"},
        {"instance_id": "old", "created_at": datetime(2026, 6, 1), "docker_image": "example/old"},
    ]

    selected = select_smoke({"c": rows, "go": [rows[3]]})

    assert [row["instance_id"] for row in selected] == ["a__tied", "old"]
    assert [row["split"] for row in selected] == ["c", "go"]
    assert selected[0]["created_at"] == newest.isoformat()
    assert selected[0]["docker_image"] == "example/a"
    assert all(set(row) == {"instance_id", "split", "created_at", "docker_image"}
               for row in selected)


def test_frozen_file_requires_matching_hashes_and_exact_selection(tmp_path):
    table = [
        {"instance_id": "selected", "patch": "gold", "test_patch": "test"},
        {"instance_id": "other", "patch": "other gold", "test_patch": "other test"},
    ]
    source = tmp_path / "data" / "c-00000-of-00001.parquet"
    source.parent.mkdir()
    source.write_bytes(b"synthetic reader input")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()

    def read_rows(path):
        assert path == source
        return table

    output = write_selected_jsonl({f"data/{source.name}": source}, {f"data/{source.name}": digest},
                                  [{"instance_id": "selected"}], tmp_path / "frozen.jsonl", read_rows)

    assert output.read_text() == '{"instance_id": "selected", "patch": "gold", "test_patch": "test"}\n'
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        write_selected_jsonl({f"data/{source.name}": source}, {f"data/{source.name}": "0" * 64},
                             [{"instance_id": "selected"}], tmp_path / "other.jsonl", read_rows)


def test_image_pinning_replaces_only_image_and_preserves_rebuilds(tmp_path):
    path = tmp_path / "frozen.jsonl"
    rows = [
        {"instance_id": "selected", "docker_image": "example/image:latest", "rebuild_cmds": ["build"]},
        {"instance_id": "other", "docker_image": "example/other:latest", "rebuild_cmds": ["other"]},
    ]
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    digest = "sha256:" + "a" * 64

    pin_image(path, "selected", digest)

    updated = [json.loads(line) for line in path.read_text().splitlines()]
    assert updated[0] == {**rows[0], "docker_image": f"example/image@{digest}"}
    assert updated[1] == rows[1]
