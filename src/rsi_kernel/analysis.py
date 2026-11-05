"""Pre-registered pilot analysis (docs/prereg-gdpevo-pilot.md, issue #20).

Aggregation: mean over runs per task, equal-task mean per group, equal-group
macro-mean (GDPevo ``metric_and_scoring.md:115-139``). Uncertainty: paired
bootstrap over group indices via ``scipy.stats.bootstrap(paired=True)`` with
SciPy's documented defaults (BCa, 95%, 9999 resamples); a degenerate BCa is
flagged, never replaced by another method. Record validation reuses the
conventions of ``compare.py``: any missing, duplicate, unexpected, corrupt or
malformed record blocks; nothing is dropped silently.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

import numpy as np
from scipy import stats

from rsi_kernel.compare import Failure, _valid_score

OUTCOMES = ("not_updated", "no_improvement", "failed_gate", "updated")


class AnalysisError(ValueError):
    def __init__(self, failures: list[Failure]):
        self.failures = failures
        super().__init__(f"{len(failures)} record failure(s): {sorted({f.reason for f in failures})}")


@dataclass(frozen=True)
class Aggregate:
    task_means: dict[str, float]
    group_means: dict[str, float]
    macro_mean: float


@dataclass(frozen=True)
class BootstrapResult:
    estimate: float
    ci_low: float
    ci_high: float
    degenerate: bool
    result: Any  # scipy BootstrapResult


@dataclass(frozen=True)
class Retention:
    passed: bool
    groups: dict[str, dict]


def aggregate(records: Iterable[dict], group_of: Mapping[str, str], runs: Sequence[int], side: str = "arm") -> Aggregate:
    """Within one arm: run mean per task -> equal-task group mean -> equal-group macro-mean."""
    if not group_of or not runs:
        raise ValueError("group_of and runs must be non-empty")
    if len(set(runs)) != len(runs):  # same rule as compare.py paired_compare
        raise ValueError("runs must be unique")
    expected = {(item, run) for item in group_of for run in runs}
    scores: dict[tuple[str, int], float] = {}
    bad: set[tuple[str, int]] = set()
    failures: list[Failure] = []
    for rec in records:
        item = rec.get("item_id") if isinstance(rec, dict) else None
        run = rec.get("run") if isinstance(rec, dict) else None
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
    failures += [Failure(*k, f"missing_{side}") for k in sorted(expected - scores.keys() - bad)]
    if failures:
        raise AnalysisError(failures)
    task_means = {item: sum(scores[(item, r)] for r in runs) / len(runs) for item in group_of}
    by_group: dict[str, list[float]] = {}
    for item, group in group_of.items():
        by_group.setdefault(group, []).append(task_means[item])
    group_means = {g: sum(v) / len(v) for g, v in sorted(by_group.items())}
    return Aggregate(task_means, group_means, sum(group_means.values()) / len(group_means))


def _paired_group_means(champion, candidate, group_of, runs):
    c = aggregate(champion, group_of, runs, "champion")
    k = aggregate(candidate, group_of, runs, "candidate")
    return c, k


def _macro_diff(champ, cand, axis=-1):
    return np.mean(cand - champ, axis=axis)


def paired_group_bootstrap(champion, candidate, group_of, runs, entropy) -> BootstrapResult:
    """Macro-mean of per-group (candidate - champion), CI over resampled groups.

    Tasks and runs stay paired inside a group because the group means are
    computed before resampling. Method, level and resample count are SciPy's
    documented defaults and are deliberately not passed.
    """
    c, k = _paired_group_means(champion, candidate, group_of, runs)
    groups = sorted(c.group_means)
    champ = np.array([c.group_means[g] for g in groups])
    cand = np.array([k.group_means[g] for g in groups])
    rng = np.random.default_rng(np.random.SeedSequence(entropy))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        res = stats.bootstrap((champ, cand), _macro_diff, paired=True, rng=rng)
    low, high = float(res.confidence_interval.low), float(res.confidence_interval.high)
    degenerate = math.isnan(low) or math.isnan(high) or any(
        issubclass(w.category, stats.DegenerateDataWarning) for w in caught
    )
    return BootstrapResult(float(np.mean(cand - champ)), low, high, degenerate, res)


def retention_per_group(champion, candidate, group_of, runs) -> Retention:
    """Zero margin: every group's candidate mean >= champion mean; ties pass."""
    c, k = _paired_group_means(champion, candidate, group_of, runs)
    groups = {
        g: {"champion": c.group_means[g], "candidate": k.group_means[g], "passed": k.group_means[g] >= c.group_means[g]}
        for g in c.group_means
    }
    return Retention(all(v["passed"] for v in groups.values()), groups)


def report_table(splits: Mapping[str, Mapping], runs: Sequence[int], entropy) -> list[dict]:
    """One plain-dict row per split. ``outcome`` must be one of OUTCOMES."""
    rows = []
    for split, s in splits.items():
        if s["outcome"] not in OUTCOMES:
            raise ValueError(f"unknown outcome {s['outcome']!r}; expected one of {OUTCOMES}")
        c, k = _paired_group_means(s["champion"], s["candidate"], s["group_of"], runs)
        boot = paired_group_bootstrap(s["champion"], s["candidate"], s["group_of"], runs, entropy)
        ret = retention_per_group(s["champion"], s["candidate"], s["group_of"], runs)
        rows.append({
            "split": split,
            "outcome": s["outcome"],
            "champion_macro_mean": c.macro_mean,
            "candidate_macro_mean": k.macro_mean,
            "estimate": boot.estimate,
            "ci_low": boot.ci_low,
            "ci_high": boot.ci_high,
            "degenerate": boot.degenerate,
            "retention_passed": ret.passed,
            "groups": ret.groups,
        })
    return rows
