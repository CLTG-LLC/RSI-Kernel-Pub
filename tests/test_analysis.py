import inspect
import math
import warnings

import numpy as np
import pytest
from scipy import stats

from rsi_kernel import analysis
from rsi_kernel.analysis import (
    AnalysisError,
    aggregate,
    paired_group_bootstrap,
    report_table,
    retention_per_group,
)

GROUP_OF = {"a1": "A", "a2": "A", "b1": "B"}
RUNS = (1, 2)


def rec(item, run, score):
    return {"item_id": item, "run": run, "score": score}


def arm(scores):
    """scores: {item: [score per run in RUNS]}"""
    return [rec(i, r, s) for i, ss in scores.items() for r, s in zip(RUNS, ss)]


CHAMP = arm({"a1": [0.0, 1.0], "a2": [1.0, 1.0], "b1": [0.2, 0.4]})
CAND = arm({"a1": [1.0, 1.0], "a2": [1.0, 1.0], "b1": [0.1, 0.3]})


# --- aggregation ---------------------------------------------------------

def test_aggregate_hand_computed():
    out = aggregate(CHAMP, GROUP_OF, RUNS)
    # task means: a1 .5, a2 1, b1 .3; groups: A .75, B .3; macro .525
    assert out.task_means == pytest.approx({"a1": 0.5, "a2": 1.0, "b1": 0.3})
    assert out.group_means == pytest.approx({"A": 0.75, "B": 0.3})
    assert out.macro_mean == pytest.approx(0.525)


def test_groups_weighted_equally_not_by_task_count():
    out = aggregate(CAND, GROUP_OF, RUNS)
    # task-weighted would be (1+1+.2)/3 = .7333; equal-group is (1+.2)/2 = .6
    assert out.macro_mean == pytest.approx(0.6)


@pytest.mark.parametrize(
    "records, reason",
    [
        (CHAMP[:-1], "missing_champion"),
        (CHAMP + [rec("a1", 1, 0.0)], "duplicate_champion"),
        (CHAMP + [rec("zz", 1, 0.0)], "unexpected_champion"),
        (CHAMP + [rec("a1", 9, 0.0)], "unexpected_champion"),
        (CHAMP[:-1] + [rec("b1", 2, float("nan"))], "corrupt_champion"),
        (CHAMP + ["junk"], "malformed_champion"),
    ],
)
def test_aggregate_rejects_bad_records(records, reason):
    with pytest.raises(AnalysisError) as err:
        aggregate(records, GROUP_OF, RUNS, side="champion")
    assert reason in [f.reason for f in err.value.failures]


def test_aggregate_rejects_empty_plan():
    with pytest.raises(ValueError):
        aggregate([], {}, RUNS)
    with pytest.raises(ValueError):
        aggregate([], GROUP_OF, ())


def test_duplicate_run_ids_in_plan_rejected():
    # Plan (1,1,2,3) would double-weight run 1 and can flip retention.
    group_of = {"t": "A"}
    plan = (1, 1, 2, 3)
    champ = [rec("t", 1, 0.0), rec("t", 2, 0.0), rec("t", 3, 1.0)]
    cand = [rec("t", 1, 0.0), rec("t", 2, 0.5), rec("t", 3, 0.25)]
    with pytest.raises(ValueError, match="unique"):
        aggregate(champ, group_of, plan)
    with pytest.raises(ValueError, match="unique"):
        retention_per_group(champ, cand, group_of, plan)


# --- bootstrap -----------------------------------------------------------

def _groups(n, rng=0):
    g = np.random.default_rng(rng)
    group_of, champ, cand = {}, [], []
    for k in range(n):
        for t in range(2):
            item = f"g{k}t{t}"
            group_of[item] = f"G{k}"
            for r in RUNS:
                champ.append(rec(item, r, float(g.random())))
                cand.append(rec(item, r, float(g.random())))
    return group_of, champ, cand


def test_bootstrap_matches_direct_scipy_call():
    group_of, champ, cand = _groups(8)
    out = paired_group_bootstrap(champ, cand, group_of, RUNS, entropy=12345)
    gc = aggregate(champ, group_of, RUNS).group_means
    gk = aggregate(cand, group_of, RUNS).group_means
    groups = sorted(gc)
    c = np.array([gc[g] for g in groups])
    k = np.array([gk[g] for g in groups])
    direct = stats.bootstrap(
        (c, k),
        lambda x, y, axis=-1: np.mean(y - x, axis=axis),
        paired=True,
        rng=np.random.default_rng(np.random.SeedSequence(12345)),
    )
    assert out.estimate == pytest.approx(float(np.mean(k - c)))
    assert out.ci_low == direct.confidence_interval.low
    assert out.ci_high == direct.confidence_interval.high
    assert out.degenerate is False
    assert out.result is not None


def test_bootstrap_is_deterministic_for_entropy():
    group_of, champ, cand = _groups(5)
    a = paired_group_bootstrap(champ, cand, group_of, RUNS, entropy=7)
    b = paired_group_bootstrap(champ, cand, group_of, RUNS, entropy=7)
    assert (a.ci_low, a.ci_high) == (b.ci_low, b.ci_high)


def test_bootstrap_uses_scipy_documented_defaults(monkeypatch):
    sig = inspect.signature(stats.bootstrap).parameters
    # Documented defaults (scipy.stats.bootstrap reference page).
    assert sig["method"].default == "BCa"
    assert sig["confidence_level"].default == 0.95
    assert sig["n_resamples"].default == 9999
    assert sig["alternative"].default == "two-sided"
    seen = {}

    def spy(*args, **kwargs):
        seen.update(kwargs)
        return real(*args, **kwargs)

    real = stats.bootstrap
    monkeypatch.setattr(analysis.stats, "bootstrap", spy)
    group_of, champ, cand = _groups(4)
    paired_group_bootstrap(champ, cand, group_of, RUNS, entropy=1)
    assert seen["paired"] is True
    for name in ("method", "confidence_level", "n_resamples", "alternative"):
        assert name not in seen


def test_bootstrap_degenerate_at_three_groups_is_flagged_not_switched():
    # Identical per-group differences: every resample gives the same value,
    # so BCa is degenerate (NaN + DegenerateDataWarning). Reported as-is.
    group_of = {"x": "A", "y": "B", "z": "C"}
    champ = [rec(i, r, 0.5) for i in group_of for r in RUNS]
    cand = [rec(i, r, 0.7) for i in group_of for r in RUNS]
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # nothing must leak to the caller
        out = paired_group_bootstrap(champ, cand, group_of, RUNS, entropy=3)
    assert out.degenerate is True
    assert out.estimate == pytest.approx(0.2)
    assert math.isnan(out.ci_low) and math.isnan(out.ci_high)
    assert out.result.confidence_interval is not None


def test_bootstrap_three_distinct_groups_flag_matches_direct_scipy():
    # n=3: flag must equal what a direct SciPy call reports (NaN CI or
    # DegenerateDataWarning), whichever way it falls.
    group_of, champ, cand = _groups(3, rng=11)
    out = paired_group_bootstrap(champ, cand, group_of, RUNS, entropy=99)
    gc = aggregate(champ, group_of, RUNS).group_means
    gk = aggregate(cand, group_of, RUNS).group_means
    c = np.array([gc[g] for g in sorted(gc)])
    k = np.array([gk[g] for g in sorted(gk)])
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        direct = stats.bootstrap(
            (c, k), lambda x, y, axis=-1: np.mean(y - x, axis=axis), paired=True,
            rng=np.random.default_rng(np.random.SeedSequence(99)),
        )
    ci = direct.confidence_interval
    expected = math.isnan(ci.low) or math.isnan(ci.high) or any(
        issubclass(w.category, stats.DegenerateDataWarning) for w in caught
    )
    assert out.degenerate is expected
    assert (out.ci_low, out.ci_high) == pytest.approx((ci.low, ci.high), nan_ok=True)


def test_bootstrap_propagates_record_failures():
    with pytest.raises(AnalysisError):
        paired_group_bootstrap(CHAMP, CAND[:-1], GROUP_OF, RUNS, entropy=1)


# --- retention -----------------------------------------------------------

def test_retention_ties_pass():
    out = retention_per_group(CHAMP, CHAMP, GROUP_OF, RUNS)
    assert out.passed is True
    assert all(g["passed"] for g in out.groups.values())


def test_retention_any_group_decrease_fails():
    out = retention_per_group(CHAMP, CAND, GROUP_OF, RUNS)
    # A: .75 -> 1.0 passes, B: .3 -> .2 fails (zero margin)
    assert out.groups["A"]["passed"] is True
    assert out.groups["B"]["passed"] is False
    assert out.passed is False


# --- reporting -----------------------------------------------------------

def test_report_table_rows_keep_outcomes_distinct():
    splits = {
        "dev": {"champion": CHAMP, "candidate": CHAMP, "group_of": GROUP_OF, "outcome": "not_updated"},
        "adjudication": {"champion": CHAMP, "candidate": CAND, "group_of": GROUP_OF, "outcome": "failed_gate"},
    }
    rows = report_table(splits, RUNS, entropy=5)
    assert [r["split"] for r in rows] == ["dev", "adjudication"]
    assert [r["outcome"] for r in rows] == ["not_updated", "failed_gate"]
    adj = rows[1]
    assert adj["champion_macro_mean"] == pytest.approx(0.525)
    assert adj["candidate_macro_mean"] == pytest.approx(0.6)
    assert adj["estimate"] == pytest.approx(0.075)
    assert adj["retention_passed"] is False
    assert set(adj) >= {"ci_low", "ci_high", "degenerate", "groups"}
    assert all(isinstance(r, dict) for r in rows)
    assert set(analysis.OUTCOMES) == {"not_updated", "no_improvement", "failed_gate", "updated"}


def test_report_table_rejects_unknown_outcome():
    with pytest.raises(ValueError):
        report_table({"dev": {"champion": CHAMP, "candidate": CHAMP, "group_of": GROUP_OF, "outcome": "pass"}}, RUNS, entropy=1)
