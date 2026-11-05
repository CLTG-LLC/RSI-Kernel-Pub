import json
import os

import pytest

from rsi_kernel.archive import Archive, PrivateStore, PublicView
from rsi_kernel.candidate import Candidate


@pytest.fixture
def archive(tmp_path):
    return Archive(tmp_path / "public", tmp_path / "private")


def test_public_and_private_live_in_separate_directories(archive, tmp_path):
    assert archive.public_dir != archive.private_dir
    assert not str(archive.private_dir).startswith(str(archive.public_dir) + os.sep)
    assert not str(archive.public_dir).startswith(str(archive.private_dir) + os.sep)


def test_overlapping_directories_rejected(tmp_path):
    with pytest.raises(ValueError):
        Archive(tmp_path / "a", tmp_path / "a" / "private")
    with pytest.raises(ValueError):
        Archive(tmp_path / "a", tmp_path / "a")


def test_accepted_and_rejected_candidates_and_parents_recorded(archive):
    parent = Candidate({"p": "0"}, "text/plain")
    child = Candidate({"p": "1"}, "text/plain", parent_ids=(parent.id,))
    archive.record_candidate(parent, status="accepted")
    archive.record_candidate(child, status="rejected")
    view = archive.public_view()
    recs = view.candidates()
    assert [(r["id"], r["status"], r["parent_ids"]) for r in recs] == [
        (parent.id, "accepted", []),
        (child.id, "rejected", [parent.id]),
    ]


def test_unknown_candidate_status_rejected(archive):
    with pytest.raises(ValueError):
        archive.record_candidate(Candidate({"a": "1"}, "text/plain"), status="maybe")


def test_dev_results_go_public_private_results_go_private(archive):
    archive.record_result("c1", "d0", 0, 1.0, split_purpose="dev")
    archive.record_result("c1", "a0", 0, 0.0, split_purpose="adjudication")
    archive.record_result("c1", "h0", 0, 0.5, split_purpose="holdout")
    archive.record_decision({"candidate_id": "c1", "decision": "reject"})
    pub = archive.public_view()
    assert [r["item_id"] for r in pub.results()] == ["d0"]
    priv = archive.private_store()
    assert [r["item_id"] for r in priv.results()] == ["a0", "h0"]
    assert priv.decisions() == [{"candidate_id": "c1", "decision": "reject"}]
    # nothing private ever touches the public directory
    blob = "".join(p.read_text() for p in archive.public_dir.iterdir())
    assert "a0" not in blob and "h0" not in blob and "reject" not in blob


def test_unknown_split_purpose_rejected(archive):
    with pytest.raises(ValueError):
        archive.record_result("c1", "x", 0, 1.0, split_purpose="train")


def test_public_view_has_no_private_access(archive):
    view = archive.public_view()
    assert isinstance(view, PublicView)
    assert not hasattr(view, "decisions")
    assert not any("private" in name for name in dir(view) if not name.startswith("__"))
    # the public reader is built from the public directory alone
    standalone = PublicView(archive.public_dir)
    assert standalone.results() == []


def test_public_reader_refuses_private_directory(archive):
    archive.record_result("c1", "a0", 0, 0.0, split_purpose="adjudication")
    with pytest.raises(PermissionError):
        PublicView(archive.private_dir)


def test_append_only_existing_lines_are_preserved(archive):
    archive.record_result("c1", "d0", 0, 1.0, split_purpose="dev")
    path = archive.public_dir / "results.jsonl"
    first = path.read_bytes()
    archive.record_result("c1", "d1", 0, 0.0, split_purpose="dev")
    assert path.read_bytes().startswith(first)
    lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [line["item_id"] for line in lines] == ["d0", "d1"]


def test_private_store_type(archive):
    assert isinstance(archive.private_store(), PrivateStore)
