import math

import pytest

from rsi_kernel.compare import paired_compare


def r(item, run, score, cid="x"):
    return {"candidate_id": cid, "item_id": item, "run": run, "score": score}


EXPECTED = [("i1", 0), ("i2", 0), ("i1", 1)]


def _base():
    return [r("i1", 0, 0.5, "b"), r("i2", 0, 0.5, "b"), r("i1", 1, 0.5, "b")]


def _cand():
    return [r("i1", 0, 1.0, "c"), r("i2", 0, 1.0, "c"), r("i1", 1, 0.0, "c")]


def test_complete_pairs_are_aligned_and_compared():
    out = paired_compare(_base(), _cand(), EXPECTED)
    assert out.outcome == "ok"
    assert out.blocks_acceptance is False
    assert [(p.item_id, p.run, p.delta) for p in out.pairs] == [("i1", 0, 0.5), ("i2", 0, 0.5), ("i1", 1, -0.5)]


def test_alignment_ignores_input_order():
    out = paired_compare(list(reversed(_base())), _cand(), EXPECTED)
    assert out.outcome == "ok"
    assert [(p.item_id, p.run) for p in out.pairs] == EXPECTED


def test_missing_candidate_result_fails_and_blocks():
    out = paired_compare(_base(), _cand()[:2], EXPECTED)
    assert out.outcome == "fail"
    assert out.blocks_acceptance is True
    assert ("i1", 1) in [(f.item_id, f.run) for f in out.failures]
    assert out.failures[0].reason == "missing_candidate"


def test_missing_baseline_result_fails():
    out = paired_compare(_base()[1:], _cand(), EXPECTED)
    assert out.outcome == "fail" and out.failures[0].reason == "missing_baseline"


@pytest.mark.parametrize(
    "bad",
    [None, "1.0", float("nan"), float("inf"), True, [1], 10**1000],
    ids=["none", "str", "nan", "inf", "bool", "list", "int-overflow"],
)
def test_corrupt_score_fails(bad):
    cand = _cand()
    cand[1]["score"] = bad
    out = paired_compare(_base(), cand, EXPECTED)
    assert out.outcome == "fail" and out.blocks_acceptance
    assert out.failures[0].reason == "corrupt_candidate"


def test_mismatched_identity_fails():
    cand = _cand()
    cand[2] = r("i1", 2, 0.0, "c")  # run 2 instead of run 1
    out = paired_compare(_base(), cand, EXPECTED)
    assert out.outcome == "fail"
    reasons = {f.reason for f in out.failures}
    assert "unexpected_candidate" in reasons and "missing_candidate" in reasons


def test_duplicate_result_fails():
    cand = _cand() + [r("i1", 0, 0.0, "c")]
    out = paired_compare(_base(), cand, EXPECTED)
    assert out.outcome == "fail" and out.failures[0].reason == "duplicate_candidate"


def test_malformed_record_fails_instead_of_crashing():
    cand = _cand()
    cand[0] = {"score": 1.0}
    out = paired_compare(_base(), cand, EXPECTED)
    assert out.outcome == "fail"


def test_suppressed_observation_is_never_a_pass():
    # an empty candidate side must never compare as ok, even with all deltas absent
    out = paired_compare(_base(), [], EXPECTED)
    assert out.outcome == "fail" and len(out.failures) == len(EXPECTED)
    assert out.pairs == []


def test_empty_expected_is_rejected():
    with pytest.raises(ValueError):
        paired_compare([], [], [])


def test_mean_delta_only_on_ok():
    assert math.isclose(paired_compare(_base(), _cand(), EXPECTED).mean_delta, 0.5 / 3)
    assert paired_compare(_base(), [], EXPECTED).mean_delta is None


@pytest.mark.parametrize("bad_record", [None, "i1", 3, ["i1", 0, 1.0]])
def test_non_dict_record_fails_instead_of_crashing(bad_record):
    out = paired_compare(_base(), _cand() + [bad_record], EXPECTED)
    assert out.outcome == "fail" and out.blocks_acceptance
    assert out.failures[0].reason == "malformed_candidate"


def test_duplicate_expected_keys_rejected():
    # review PR5 finding 5: duplicates would silently reweight the mean
    with pytest.raises(ValueError):
        paired_compare(_base(), _cand(), EXPECTED + [("i1", 0)])
