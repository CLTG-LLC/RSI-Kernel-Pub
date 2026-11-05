"""Paired comparison of candidate vs baseline per (item_id, run).

Alignment ported from Reef ``reef/evaluation/evaluators.py:60-81`` (pair on the
same item and run). Unlike Reef, which drops a pair when either side is
missing, any missing, corrupt, duplicate or unexpected result here is a failure
that blocks acceptance (design §5). Nothing is ever silently dropped.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

Key = tuple[str, int]


@dataclass(frozen=True)
class Pair:
    item_id: str
    run: int
    baseline: float
    candidate: float

    @property
    def delta(self) -> float:
        return self.candidate - self.baseline


@dataclass(frozen=True)
class Failure:
    item_id: str | None
    run: int | None
    reason: str


@dataclass(frozen=True)
class Comparison:
    pairs: list[Pair]
    failures: list[Failure]

    @property
    def outcome(self) -> str:
        return "fail" if self.failures else "ok"

    @property
    def blocks_acceptance(self) -> bool:
        return bool(self.failures)

    @property
    def mean_delta(self) -> float | None:
        if self.failures or not self.pairs:
            return None
        return sum(p.delta for p in self.pairs) / len(self.pairs)


def _valid_score(score: object) -> bool:
    if not isinstance(score, (int, float)) or isinstance(score, bool):
        return False
    try:
        return math.isfinite(float(score))
    except OverflowError:  # e.g. an int too large for a float
        return False


def _index(records: Iterable[dict], side: str, expected: set[Key]) -> tuple[dict[Key, float], list[Failure]]:
    scores: dict[Key, float] = {}
    failures: list[Failure] = []
    bad: set[Key] = set()
    for rec in records:
        if not isinstance(rec, dict):
            failures.append(Failure(None, None, f"malformed_{side}"))
            continue
        item, run = rec.get("item_id"), rec.get("run")
        if not isinstance(item, str) or not isinstance(run, int) or isinstance(run, bool):
            failures.append(Failure(None, None, f"malformed_{side}"))
            continue
        key = (item, run)
        if key not in expected:
            failures.append(Failure(item, run, f"unexpected_{side}"))
        elif key in scores or key in bad:
            failures.append(Failure(item, run, f"duplicate_{side}"))
            scores.pop(key, None)
            bad.add(key)
        elif not _valid_score(rec.get("score")):
            failures.append(Failure(item, run, f"corrupt_{side}"))
            bad.add(key)
        else:
            scores[key] = float(rec["score"])
    return scores, failures


def paired_compare(baseline: Iterable[dict], candidate: Iterable[dict], expected: Sequence[Key]) -> Comparison:
    """Compare on exactly the planned (item_id, run) keys, in planned order."""
    if not expected:
        raise ValueError("expected (item_id, run) keys must be non-empty")
    want = set(expected)
    if len(want) != len(expected):
        raise ValueError("expected (item_id, run) keys must be unique")
    base, base_fail = _index(baseline, "baseline", want)
    cand, cand_fail = _index(candidate, "candidate", want)
    failures = base_fail + cand_fail
    flagged = {(f.item_id, f.run) for f in failures}
    pairs: list[Pair] = []
    for key in expected:
        if key in flagged:
            continue
        if key not in base:
            failures.append(Failure(*key, "missing_baseline"))
        elif key not in cand:
            failures.append(Failure(*key, "missing_candidate"))
        else:
            pairs.append(Pair(key[0], key[1], base[key], cand[key]))
    return Comparison(pairs, failures)
