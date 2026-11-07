"""Proposer-facing projection: a score and a boolean, and nothing else.

Feedback reaches the proposer through the kernel's own shape (`adapter.py:76-80`
in the text adapter tier): ``{"score": s, "correct": s == 1.0}``. Test names,
harness logs, patches, tracebacks, image names, failure reasons and evidence paths
never leave the host, and raw result rows are projected through an allowlist
before the proposer sees them. Adjudication and holdout rows go to the kernel's
private store instead, so nothing here is ever called for them.
"""

from __future__ import annotations

import math
from typing import Iterable, Mapping

# The only keys a proposer input row may carry.
PROPOSER_FIELDS = ("item_id", "score", "correct")


def _score(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("score must be a real number or None")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError("score must be finite and within [0, 1]")
    return float(value)


def feedback(score: float | None) -> dict:
    """Exactly two keys; ``correct`` mirrors the kernel's ``score == 1.0`` rule."""
    value = _score(score)
    return {"score": value, "correct": value == 1.0}


def row(feedback_value: Mapping) -> dict:
    """Project one validated feedback object onto the allowlist."""
    if not isinstance(feedback_value, Mapping) or set(feedback_value) != {"score", "correct"}:
        raise ValueError("feedback must carry exactly score and correct")
    return feedback(feedback_value["score"])


def proposer_input(rows: Iterable[Mapping]) -> list[dict]:
    """Drop every field outside the allowlist; refuse a row that cannot be projected.

    The input is the kernel's result rows; only ``item_id`` plus the two feedback
    keys survive. A row without a usable identity is an error, not a silent skip.
    """
    if isinstance(rows, (str, bytes, Mapping)) or not isinstance(rows, Iterable):
        raise ValueError("proposer input must be a list of result rows")
    projected = []
    for value in rows:
        if not isinstance(value, Mapping) or not isinstance(value.get("item_id"), str) or not value["item_id"]:
            raise ValueError("each proposer input row needs an item_id")
        projected.append({"item_id": value["item_id"], **row(value.get("feedback", {}))})
    return projected
