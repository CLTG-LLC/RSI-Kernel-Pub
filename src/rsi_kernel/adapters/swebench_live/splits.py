"""Adapter-local carve: post-cutoff pool, July-only holdout, repository-group dev split.

Rules are frozen by the registration, not chosen here: the cutover timestamp is the
bound model's documented knowledge-cutoff boundary, and the three bands follow the
lead disposition (July-only repositories are the holdout; the May-June pool is split
by repository group). The seed and the allocation ratio are required parameters with
no defaults, so neither can become policy by omission.

Group split: sklearn ``GroupShuffleSplit`` semantics,
https://github.com/scikit-learn/scikit-learn/blob/1.5.2/sklearn/model_selection/_split.py#L2082-L2110
(the same group never appears in two folds; a float test size is rounded up,
https://github.com/scikit-learn/scikit-learn/blob/1.5.2/sklearn/model_selection/_split.py#L2389-L2400).
The permutation itself comes from stdlib ``random.Random``, so fold membership is a
frozen function of the seed but is NOT claimed to reproduce sklearn's own indices
(those use ``numpy.random.RandomState``).
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence

from ...splits import Splits, load_splits
from .tasks import SweTask

# Documented cutoff boundary for the registered model: "Apr 30, 2026 knowledge cutoff"
# (https://developers.openai.com/api/docs/models/gpt-6.1-sol). The pool is therefore
# "created_at >= 2026-05-01T00:00:00Z", and the claim is contamination-controlled by
# this timestamp rule, never "contamination-free". Re-derive it if the model changes.
CUTOFF = datetime(2026, 5, 1, tzinfo=timezone.utc)
DEV_MONTHS = ((2026, 5), (2026, 6))
HOLDOUT_MONTH = (2026, 7)
COHORTS = DEV_MONTHS + (HOLDOUT_MONTH,)

# Exclusion reasons, reported per instance and never silently dropped.
UNPARSEABLE = "unparseable_created_at"
BEFORE_CUTOFF = "before_cutoff"
JULY_OUTSIDE_HOLDOUT = "july_outside_holdout"
OUTSIDE_COHORTS = "outside_cohorts"

PURPOSES = ("dev", "adjudication", "holdout")


@dataclass(frozen=True)
class CarvedSplits:
    dev: tuple[str, ...]
    adjudication: tuple[str, ...]
    holdout: tuple[str, ...]
    excluded: tuple[tuple[str, str], ...]
    seed: int
    adjudication_fraction: float

    def _items(self, purpose: str) -> tuple[str, ...]:
        return getattr(self, purpose)

    @property
    def excluded_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for _, reason in self.excluded:
            counts[reason] = counts.get(reason, 0) + 1
        return dict(sorted(counts.items()))

    def to_config(self) -> dict:
        """The kernel ``load_splits`` shape plus the frozen carve record."""
        return {
            "splits": [
                {"name": purpose, "purpose": purpose, "selection_eligible": purpose == "dev",
                 "item_ids": list(self._items(purpose))}
                for purpose in PURPOSES
            ],
            "carve": {"seed": self.seed, "adjudication_fraction": self.adjudication_fraction,
                      "cutoff": CUTOFF.isoformat(),
                      "excluded": [list(pair) for pair in self.excluded],
                      "excluded_counts": self.excluded_counts,
                      "dev_count": len(self.dev), "adjudication_count": len(self.adjudication),
                      "holdout_count": len(self.holdout)},
        }

    def to_splits(self) -> Splits:
        return load_splits(self.to_config())


def _month(task: SweTask) -> tuple[int, int]:
    assert task.created_at is not None
    return (task.created_at.year, task.created_at.month)


def _validate(seed: int, adjudication_fraction: float) -> None:
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("seed must be a non-negative int frozen by the registration")
    if (isinstance(adjudication_fraction, bool) or not isinstance(adjudication_fraction, float)
            or not math.isfinite(adjudication_fraction) or not 0 < adjudication_fraction < 1):
        raise ValueError("adjudication fraction must be a float in (0, 1)")


def _readable(task: SweTask) -> bool:
    return task.created_at is not None and task.created_at.tzinfo is not None


def carve(tasks: Sequence[SweTask], *, seed: int, adjudication_fraction: float) -> CarvedSplits:
    """Split the post-cutoff pool; every excluded instance is reported with a reason.

    The cutoff is not a parameter: selection and the recorded ``to_config()`` cutoff
    must come from one value, or a run could be carved on one rule and described by
    another. A different cutoff needs a new registration, not a carve argument.
    """
    _validate(seed, adjudication_fraction)
    ordered = sorted(tasks, key=lambda task: task.item_id)
    if len({task.item_id for task in ordered}) != len(ordered):
        raise ValueError("duplicate task identity")

    excluded: dict[str, str] = {}
    eligible: list[SweTask] = []
    for task in ordered:
        if not _readable(task):
            excluded[task.item_id] = UNPARSEABLE
        elif task.created_at < CUTOFF:
            excluded[task.item_id] = BEFORE_CUTOFF
        else:
            eligible.append(task)

    by_repo: dict[str, list[SweTask]] = {}
    for task in eligible:
        by_repo.setdefault(task.repo, []).append(task)

    holdout: list[str] = []
    pool_repos: list[str] = []
    for repo in sorted(by_repo):
        members = by_repo[repo]
        months = {_month(task) for task in members}
        if months == {HOLDOUT_MONTH}:
            holdout.extend(task.item_id for task in members)
            continue
        pool_repos.append(repo)
        for task in members:
            month = _month(task)
            if month == HOLDOUT_MONTH:
                excluded[task.item_id] = JULY_OUTSIDE_HOLDOUT
            elif month not in COHORTS:
                # Frozen pool max is 2026-07; a newer drop would need a new registration.
                excluded[task.item_id] = OUTSIDE_COHORTS

    # A float test size is rounded up over the group count (sklearn:2389-2400).
    shuffled = list(pool_repos)
    random.Random(seed).shuffle(shuffled)
    split_at = math.ceil(adjudication_fraction * len(shuffled))
    adjudication_repos = set(shuffled[:split_at])
    dev: list[str] = []
    adjudication: list[str] = []
    for repo in pool_repos:
        target = adjudication if repo in adjudication_repos else dev
        target.extend(task.item_id for task in by_repo[repo] if task.item_id not in excluded)
    return CarvedSplits(
        dev=tuple(sorted(dev)), adjudication=tuple(sorted(adjudication)),
        holdout=tuple(sorted(holdout)),
        excluded=tuple(sorted(excluded.items())),
        seed=seed, adjudication_fraction=adjudication_fraction,
    )
