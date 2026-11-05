"""Append-only archive with a public (dev) view and a separate private store.

Public: candidates (accepted and rejected), parents, dev results. This is the
only view the loop and decision model may read (design §3).
Private: adjudication/holdout results and acceptance decisions, kept in a
different directory that is never mounted into the proposer runtime (E0).
Pattern: ShinkaEvolve public/private metrics (design §5).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .candidate import Candidate

CANDIDATE_STATUSES = frozenset({"proposed", "accepted", "rejected"})
PUBLIC_PURPOSES = frozenset({"dev"})
PRIVATE_PURPOSES = frozenset({"adjudication", "holdout"})
_MARKER = ".rsi-store"


def paths_overlap(a: str | Path, b: str | Path) -> bool:
    """True if two resolved paths are equal or one is an ancestor of the other."""
    a, b = Path(a).resolve(), Path(b).resolve()
    return a == b or a in b.parents or b in a.parents


def _append(path: Path, record: dict) -> None:
    # O_APPEND: writes only ever go to the end of the file.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    with os.fdopen(fd, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")


def _read(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _init_dir(path: Path, kind: str) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    marker = path / _MARKER
    if marker.exists() and marker.read_text() != kind:
        raise ValueError(f"{path} is a {marker.read_text()} store, not {kind}")
    marker.write_text(kind)
    return path


def _check_dir(path: Path, kind: str) -> Path:
    marker = path / _MARKER
    if marker.exists() and marker.read_text() != kind:
        raise PermissionError(f"{path} is not a {kind} store")
    return path


class PublicView:
    """Read-only access to the public (dev) side. Holds no private path."""

    def __init__(self, public_dir: str | Path) -> None:
        self._dir = _check_dir(Path(public_dir), "public")

    def candidates(self) -> list[dict]:
        return _read(self._dir / "candidates.jsonl")

    def results(self) -> list[dict]:
        return _read(self._dir / "results.jsonl")


class PrivateStore:
    """Read access to adjudication/holdout results and decisions."""

    def __init__(self, private_dir: str | Path) -> None:
        self._dir = _check_dir(Path(private_dir), "private")

    def results(self) -> list[dict]:
        return _read(self._dir / "results.jsonl")

    def decisions(self) -> list[dict]:
        return _read(self._dir / "decisions.jsonl")


class Archive:
    def __init__(self, public_dir: str | Path, private_dir: str | Path) -> None:
        pub, priv = Path(public_dir).resolve(), Path(private_dir).resolve()
        if paths_overlap(pub, priv):
            raise ValueError("public and private stores must be separate, non-nested directories")
        self.public_dir = _init_dir(pub, "public")
        self.private_dir = _init_dir(priv, "private")

    def record_candidate(self, candidate: Candidate, status: str) -> None:
        if status not in CANDIDATE_STATUSES:
            raise ValueError(f"unknown candidate status {status!r}")
        _append(
            self.public_dir / "candidates.jsonl",
            {
                "id": candidate.id,
                "media_type": candidate.media_type,
                "parent_ids": list(candidate.parent_ids),
                "status": status,
            },
        )

    def record_result(
        self, candidate_id: str, item_id: str, run: int, score: Any, split_purpose: str, feedback: str = ""
    ) -> None:
        record = {"candidate_id": candidate_id, "item_id": item_id, "run": run, "score": score}
        if split_purpose in PUBLIC_PURPOSES:
            _append(self.public_dir / "results.jsonl", {**record, "feedback": feedback})
        elif split_purpose in PRIVATE_PURPOSES:
            _append(self.private_dir / "results.jsonl", {**record, "split_purpose": split_purpose})
        else:
            raise ValueError(f"unknown split purpose {split_purpose!r}")

    def record_decision(self, decision: dict) -> None:
        _append(self.private_dir / "decisions.jsonl", decision)

    def public_view(self) -> PublicView:
        return PublicView(self.public_dir)

    def private_store(self) -> PrivateStore:
        return PrivateStore(self.private_dir)
