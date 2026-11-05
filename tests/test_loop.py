"""Campaign driver and one-shot acceptance on a fake host (issue #15, design §2/§4)."""

import io
import json

import pytest

from rsi_kernel.archive import Archive
from rsi_kernel.candidate import Candidate
from rsi_kernel.decision.backends import DeterministicBackend
from rsi_kernel.decision.envelope import EnvelopeBuilder
from rsi_kernel.decision.log import Decider
from rsi_kernel.loop import (
    ApprovalRecord,
    CampaignClosed,
    accept,
    run_campaign,
)

DEV = ("d1", "d2")
ADJ = ("a1", "a2")
HOLD = ("h1",)
EVAL_HASH = "evaluator-v1"


def cand(text):
    return Candidate({"SKILL.md": text}, "text/plain")


class FakeHost:
    """§4 contract; scores come from a table keyed by candidate text."""

    def __init__(self, champion, scores):
        self.champion, self.scores = champion, scores
        self.eval_calls, self.eval_items, self.applied = 0, 0, []

    def get_artifact(self):
        return self.champion

    def _score(self, candidate, item_ids):
        return rows(self.scores[candidate.components["SKILL.md"]], item_ids)

    def evaluate(self, candidate, item_ids):
        self.eval_calls += 1
        self.eval_items += len(item_ids)
        return self._score(candidate, item_ids)

    def apply(self, approved_candidate_hash):
        self.applied.append(approved_candidate_hash)


def rows(spec, item_ids):
    """A score, or a callable building raw (possibly malformed) rows."""
    if callable(spec):
        return spec(item_ids)
    return [{"item_id": i, "score": spec} for i in item_ids]


class SeqProposer:
    def __init__(self, texts, meter=None, cost=0):
        self.texts, self.calls, self.meter, self.cost = list(texts), 0, meter, cost

    def __call__(self, champion, component_id, dev_results):
        text = self.texts[self.calls % len(self.texts)]
        self.calls += 1
        if self.meter is not None:
            self.meter["spent"] += self.cost
        return None if text is None else cand(text)


class AlwaysC1:
    def decide(self, envelope):
        return {"D2": "c1"}


def ge_zero(comparison):
    return comparison.mean_delta >= 0


@pytest.fixture
def archive(tmp_path):
    return Archive(tmp_path / "pub", tmp_path / "priv")


def campaign(host, proposer, archive, *, log=None, decider=None, max_attempts=3,
             spend_cap=100, eval_cap=100, meter=None, dev=DEV, evaluator_hash=EVAL_HASH, runs=1):
    meter = meter if meter is not None else {"spent": 0}
    return run_campaign(
        adapter=host, proposer=proposer, decider=decider or AlwaysC1(),
        envelope_builder=EnvelopeBuilder(component_ids=("c1",)),
        dev_item_ids=dev, evaluator_hash=evaluator_hash, archive=archive,
        outcome_log=log if log is not None else io.StringIO(),
        non_regression=ge_zero, spend=lambda: meter["spent"],
        max_attempts=max_attempts, spend_cap=spend_cap, eval_cap=eval_cap, runs=runs,
    )


def records(log):
    log.seek(0)
    return [json.loads(line) for line in log if line.strip()]


# -- loop -------------------------------------------------------------------

def test_bounds_are_required_and_have_no_defaults(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5})
    with pytest.raises(TypeError):
        run_campaign(adapter=host, proposer=SeqProposer(["x"]), decider=AlwaysC1(),
                     envelope_builder=EnvelopeBuilder(component_ids=("c1",)),
                     dev_item_ids=DEV, evaluator_hash=EVAL_HASH, archive=archive,
                     outcome_log=io.StringIO(), non_regression=ge_zero, spend=lambda: 0)


def test_stops_on_attempt_bound_and_selects_best_frozen_candidate(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5, "a": 0.6, "b": 0.9, "c": 0.7})
    log = io.StringIO()
    result = campaign(host, SeqProposer(["a", "b", "c", "a"]), archive, log=log, max_attempts=3)
    assert result.stop_reason == "attempts" and result.attempts == 3
    assert result.selected.id == cand("b").id and result.outcome == "selected"
    assert [r["outcome"] for r in records(log)][:3] == ["dev_pass"] * 3
    assert result.selected.id in {c["id"] for c in archive.public_view().candidates()}


def test_stops_at_first_check_past_spend_cap(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5, "a": 0.6})
    meter = {"spent": 0}
    result = campaign(host, SeqProposer(["a"], meter, cost=4), archive,
                      max_attempts=50, spend_cap=10, meter=meter)
    assert result.stop_reason == "spend_cap"
    # 4, 8 are within the cap; the third proposal makes 12 and is never evaluated.
    assert host.eval_calls == 1 + 2


def test_evaluator_invocations_never_exceed_reservation(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5, "a": 0.6, "b": 0.7})
    result = campaign(host, SeqProposer(["a", "b"]), archive, max_attempts=50, eval_cap=5)
    assert result.stop_reason == "eval_cap"
    assert host.eval_items <= 5 and host.eval_items == 4  # champion 2 + one candidate 2


def test_champion_eval_unreservable_stops_before_any_attempt(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5})
    result = campaign(host, SeqProposer(["a"]), archive, eval_cap=1)
    assert result.stop_reason == "eval_cap" and host.eval_calls == 0 and result.attempts == 0


def test_no_candidate_and_none_target_are_logged_without_eval(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5})

    class NoneTarget:
        def decide(self, envelope):
            return {"D2": "none"}

    log = io.StringIO()
    r1 = campaign(host, SeqProposer([None]), archive, log=log, max_attempts=2)
    r2 = campaign(host, SeqProposer(["a"]), archive, log=log, decider=NoneTarget(), max_attempts=1)
    assert [r["outcome"] for r in records(log)] == ["no_candidate", "no_candidate", "no_target"]
    assert r1.outcome == r2.outcome == "no_improvement" and r1.selected is None
    assert host.eval_calls == 2  # champion only, once per campaign


def test_dev_regression_is_suppressed_within_same_context(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5, "bad": 0.1})
    log = io.StringIO()
    campaign(host, SeqProposer(["bad"]), archive, log=log, max_attempts=2)
    assert [r["outcome"] for r in records(log)] == ["dev_regression", "suppressed"]
    calls = host.eval_calls
    campaign(host, SeqProposer(["bad"]), archive, log=log, max_attempts=1)
    assert records(log)[-1]["outcome"] == "suppressed"
    assert host.eval_calls == calls + 1  # champion only; "bad" not re-evaluated


@pytest.mark.parametrize("change", ["champion", "dev", "evaluator"])
def test_suppression_is_cleared_when_context_hash_changes(archive, change):
    host = FakeHost(cand("champ"), {"champ": 0.5, "champ2": 0.5, "bad": 0.1})
    log = io.StringIO()
    campaign(host, SeqProposer(["bad"]), archive, log=log, max_attempts=1)
    kwargs = {}
    if change == "champion":
        host.champion = cand("champ2")
    elif change == "dev":
        kwargs["dev"] = ("d1", "d2", "d3")
    else:
        kwargs["evaluator_hash"] = "evaluator-v2"
    campaign(host, SeqProposer(["bad"]), archive, log=log, max_attempts=1, **kwargs)
    assert records(log)[-1]["outcome"] == "dev_regression"  # re-admitted and re-evaluated


def test_operational_failure_is_not_suppressed(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5, "broken": None})
    log = io.StringIO()
    campaign(host, SeqProposer(["broken"]), archive, log=log, max_attempts=2)
    assert [r["outcome"] for r in records(log)] == ["dev_failure", "dev_failure"]


def test_real_decider_records_baseline_alongside(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5, "a": 0.6})
    dlog = io.StringIO()
    campaign(host, SeqProposer(["a"]), archive, decider=Decider(DeterministicBackend(), dlog), max_attempts=2)
    dlog.seek(0)
    lines = [json.loads(line) for line in dlog]
    assert len(lines) == 2 and all("baseline_answer" in r for r in lines)
    assert set(lines[0]["envelope"]["questions"]) == {"D2"}


# -- accept -----------------------------------------------------------------

class Adjudicator:
    def __init__(self, scores):
        self.scores, self.calls = scores, []

    def __call__(self, candidate, item_ids):
        self.calls.append(tuple(item_ids))
        return rows(self.scores[candidate.components["SKILL.md"]], item_ids)


def do_accept(host, archive, candidate, *, approval, scores=None, campaign_id="camp-1", holdout=True,
              adj_ids=ADJ, runs=1):
    adj = scores if isinstance(scores, Adjudicator) else Adjudicator(scores or {"champ": 0.5, "b": 0.9})
    result = accept(
        campaign_id=campaign_id, candidate=candidate, champion=host.get_artifact(),
        adjudicate=adj, adjudication_item_ids=adj_ids, evaluator_hash=EVAL_HASH,
        retain=ge_zero, approval=approval, adapter=host, archive=archive, runs=runs,
        holdout=adj if holdout else None, holdout_item_ids=HOLD if holdout else (),
    )
    return result, adj


def approve_exact(request):
    return ApprovalRecord(request.candidate_hash, request.evaluator_hash, request.data_hash, "approver")


def test_accept_applies_only_with_matching_approval(archive):
    host = FakeHost(cand("champ"), {})
    result, _ = do_accept(host, archive, cand("b"), approval=approve_exact)
    assert result.outcome == "updated" and host.applied == [cand("b").id]
    assert result.request.candidate_hash == cand("b").id and result.request.evaluator_hash == EVAL_HASH


@pytest.mark.parametrize("field", ["candidate_hash", "evaluator_hash", "data_hash"])
def test_hash_mismatch_is_refused(archive, field):
    host = FakeHost(cand("champ"), {})

    def wrong(request):
        rec = approve_exact(request)
        return ApprovalRecord(**{**rec.__dict__, field: "other"})

    result, _ = do_accept(host, archive, cand("b"), approval=wrong)
    assert host.applied == [] and result.outcome == "not_updated"


def test_no_approval_keeps_champion_and_is_not_success(archive):
    host = FakeHost(cand("champ"), {})
    result, _ = do_accept(host, archive, cand("b"), approval=lambda request: None)
    assert result.outcome == "not_updated" and not result.success and host.applied == []


def test_failed_gate_never_asks_for_approval(archive):
    host = FakeHost(cand("champ"), {})
    asked = []
    result, _ = do_accept(host, archive, cand("b"), scores={"champ": 0.5, "b": 0.1},
                          approval=lambda r: asked.append(r))
    assert result.outcome == "failed_gate" and asked == [] and host.applied == []


def test_blocking_failure_is_failed_gate(archive):
    host = FakeHost(cand("champ"), {})
    result, _ = do_accept(host, archive, cand("b"), scores={"champ": 0.5, "b": None},
                          approval=approve_exact)
    assert result.outcome == "failed_gate" and result.comparison.blocks_acceptance


def test_no_candidate_is_no_improvement(archive):
    host = FakeHost(cand("champ"), {})
    result, adj = do_accept(host, archive, None, approval=approve_exact)
    assert result.outcome == "no_improvement" and adj.calls == [] and not result.success


def test_outcomes_are_distinct():
    from rsi_kernel.loop import OUTCOMES
    assert {"not_updated", "no_improvement", "failed_gate"} <= set(OUTCOMES)
    assert len(set(OUTCOMES)) == len(OUTCOMES)


def test_holdout_reported_once_per_campaign(archive):
    host = FakeHost(cand("champ"), {})
    result, adj = do_accept(host, archive, cand("b"), approval=approve_exact)
    assert adj.calls[-1] == HOLD and result.holdout_results
    assert adj.calls.count(HOLD) == 2  # one paired report: champion + candidate
    second = Adjudicator({"champ": 0.5, "b": 0.9})
    with pytest.raises(CampaignClosed):
        accept(campaign_id="camp-1", candidate=cand("b"), champion=host.get_artifact(),
               adjudicate=second, adjudication_item_ids=ADJ, evaluator_hash=EVAL_HASH,
               retain=ge_zero, approval=approve_exact, adapter=host, archive=archive,
               holdout=second, holdout_item_ids=HOLD, runs=1)
    assert second.calls == []
    # A different campaign may report its own holdout.
    do_accept(host, archive, cand("b"), approval=approve_exact, campaign_id="camp-2")


def test_adjudication_results_stay_private(archive):
    host = FakeHost(cand("champ"), {})
    do_accept(host, archive, cand("b"), approval=approve_exact)
    assert archive.public_view().results() == []
    purposes = {r["split_purpose"] for r in archive.private_store().results()}
    assert purposes == {"adjudication", "holdout"}


# -- PR #17 review fixes ---------------------------------------------------

def run1(item_ids):
    return [{"item_id": i, "run": 1, "score": 0.9} for i in item_ids]


def test_fix1_dev_run_mismatch_blocks(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5, "r1": run1})
    log = io.StringIO()
    result = campaign(host, SeqProposer(["r1"]), archive, log=log, max_attempts=1)
    assert records(log)[-1]["outcome"] == "dev_failure" and result.selected is None


def test_fix1_accept_run_mismatch_blocks(archive):
    host = FakeHost(cand("champ"), {})
    result, _ = do_accept(host, archive, cand("b"), scores={"champ": 0.5, "b": run1},
                          approval=approve_exact)
    assert result.outcome == "failed_gate" and host.applied == []


def test_fix1_explicit_matching_run_ids_are_kept(archive):
    host = FakeHost(cand("champ"), {})
    run0 = lambda ids: [{"item_id": i, "run": 0, "score": 0.9} for i in ids]
    result, _ = do_accept(host, archive, cand("b"), scores={"champ": 0.5, "b": run0},
                          approval=approve_exact)
    assert result.outcome == "updated"


def test_fix2_loop_unchanged_champion_is_no_candidate(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5})
    log = io.StringIO()
    result = campaign(host, SeqProposer(["champ"]), archive, log=log, max_attempts=2)
    assert [r["outcome"] for r in records(log)] == ["no_candidate", "no_candidate"]
    assert result.selected is None and result.outcome == "no_improvement"
    assert host.eval_calls == 1  # champion baseline only


def test_fix2_accept_unchanged_champion_is_no_improvement(archive):
    host = FakeHost(cand("champ"), {})
    asked = []
    result, adj = do_accept(host, archive, cand("champ"), approval=lambda r: asked.append(r) or approve_exact(r))
    assert result.outcome == "no_improvement" and not result.success
    assert adj.calls == [] and asked == [] and host.applied == []


COLLIDE_A, COLLIDE_B = ("a", "b\nc"), ("a\nb", "c")


def test_fix3_data_hash_is_unambiguous():
    from rsi_kernel.loop import data_hash
    assert data_hash(COLLIDE_A) != data_hash(COLLIDE_B)


def test_fix3_approval_not_reusable_across_colliding_lists(archive, tmp_path):
    host = FakeHost(cand("champ"), {})
    first, _ = do_accept(host, archive, cand("b"), approval=lambda r: None, adj_ids=COLLIDE_A)
    old = approve_exact(first.request)
    other = Archive(tmp_path / "pub2", tmp_path / "priv2")
    result, _ = do_accept(host, other, cand("b"), approval=lambda r: old, adj_ids=COLLIDE_B)
    assert result.outcome == "not_updated" and host.applied == []


def test_fix3_suppression_readmitted_for_colliding_dev_list(archive):
    host = FakeHost(cand("champ"), {"champ": 0.5, "bad": 0.1})
    log = io.StringIO()
    campaign(host, SeqProposer(["bad"]), archive, log=log, max_attempts=1, dev=COLLIDE_A)
    campaign(host, SeqProposer(["bad"]), archive, log=log, max_attempts=1, dev=COLLIDE_B)
    assert records(log)[-1]["outcome"] == "dev_regression"


def missing_score(item_ids):
    return [{"item_id": i} for i in item_ids]


def non_dict(item_ids):
    return ["garbage" for _ in item_ids]


def unhashable(item_ids):
    return [{"item_id": [i], "run": [0], "score": 0.9} for i in item_ids]


@pytest.mark.parametrize("bad", [missing_score, non_dict, unhashable])
def test_fix4_malformed_dev_rows_are_logged_dev_failure(archive, bad):
    host = FakeHost(cand("champ"), {"champ": 0.5, "x": bad})
    log = io.StringIO()
    result = campaign(host, SeqProposer(["x"]), archive, log=log, max_attempts=1)
    assert records(log)[-1]["outcome"] == "dev_failure" and result.selected is None
    assert {r["candidate_id"] for r in archive.public_view().results()} == {cand("champ").id}


@pytest.mark.parametrize("bad", [missing_score, non_dict, unhashable])
def test_fix4_malformed_champion_dev_rows_do_not_crash(archive, bad):
    host = FakeHost(cand("champ"), {"champ": bad, "a": 0.6})
    log = io.StringIO()
    result = campaign(host, SeqProposer(["a"]), archive, log=log, max_attempts=1)
    assert records(log)[-1]["outcome"] == "dev_failure" and result.selected is None


@pytest.mark.parametrize("bad", [missing_score, non_dict, unhashable])
def test_fix4_malformed_accept_rows_are_failed_gate(archive, bad):
    host = FakeHost(cand("champ"), {})
    result, _ = do_accept(host, archive, cand("b"), scores={"champ": 0.5, "b": bad},
                          approval=approve_exact)
    assert result.outcome == "failed_gate" and host.applied == []


def test_fix4_crash_does_not_close_campaign(archive):
    host = FakeHost(cand("champ"), {})

    class Boom(Adjudicator):
        def __call__(self, candidate, item_ids):
            raise RuntimeError("host down")

    with pytest.raises(RuntimeError):
        do_accept(host, archive, cand("b"), scores=Boom({}), approval=approve_exact)
    result, _ = do_accept(host, archive, cand("b"), approval=approve_exact)
    assert result.outcome == "updated"


# Issue #18: repeats use compare.py's existing (item_id, run) identity.
def test_three_runs_campaign_complete_and_reserved(archive):
    host = FakeHost(cand("champ"), {"champ": .5, "b": .9})
    result = campaign(host, SeqProposer(["b"]), archive, runs=3, max_attempts=1)
    assert result.selected.id == cand("b").id
    assert result.evaluator_items_used == host.eval_items == 12
    assert host.eval_calls == 6
    stored = archive.public_view().results()
    assert {(r["item_id"], r["run"]) for r in stored} == {(i, r) for i in DEV for r in range(3)}


def test_three_runs_budget_reserved_before_any_solver(archive):
    host = FakeHost(cand("champ"), {"champ": .5})
    result = campaign(host, SeqProposer(["b"]), archive, runs=3, eval_cap=5)
    assert result.stop_reason == "eval_cap" and host.eval_calls == 0


def test_three_runs_accept_and_holdout_pair_complete(archive):
    host = FakeHost(cand("champ"), {})
    result, adj = do_accept(host, archive, cand("b"), approval=approve_exact, runs=3)
    assert result.outcome == "updated"
    assert {(p.item_id, p.run) for p in result.comparison.pairs} == {(i, r) for i in ADJ for r in range(3)}
    assert {(p.item_id, p.run) for p in result.holdout_results.pairs} == {(i, r) for i in HOLD for r in range(3)}
    assert len(adj.calls) == 12


def test_missing_third_run_blocks_acceptance(archive):
    host = FakeHost(cand("champ"), {})

    class Missing(Adjudicator):
        def __call__(self, candidate, item_ids):
            result = super().__call__(candidate, item_ids)
            if candidate.components["SKILL.md"] == "b" and self.calls.count(tuple(item_ids)) == 6:
                return result[:-1]
            return result

    result, _ = do_accept(host, archive, cand("b"), scores=Missing({"champ": .5, "b": .9}),
                          approval=approve_exact, runs=3, holdout=False)
    assert result.outcome == "failed_gate" and host.applied == []
    assert any(f.item_id == ADJ[-1] and f.run == 2 for f in result.comparison.failures)


@pytest.mark.parametrize("runs", [0, -1, True, 1.5])
def test_invalid_runs_rejected_before_evaluation(archive, runs):
    host = FakeHost(cand("champ"), {"champ": .5})
    with pytest.raises(ValueError, match="runs"):
        campaign(host, SeqProposer(["b"]), archive, runs=runs)
    with pytest.raises(ValueError, match="runs"):
        do_accept(host, archive, cand("b"), approval=approve_exact, runs=runs)
    assert host.eval_calls == 0


def test_missing_holdout_run_blocks_acceptance(archive):
    host = FakeHost(cand("champ"), {})

    class Missing(Adjudicator):
        def __call__(self, candidate, item_ids):
            result = super().__call__(candidate, item_ids)
            if tuple(item_ids) == HOLD and len(self.calls) == 12:
                return []
            return result

    result, _ = do_accept(host, archive, cand("b"), scores=Missing({"champ": .5, "b": .9}),
                          approval=approve_exact, runs=3)
    assert result.outcome == "failed_gate" and result.holdout_results.blocks_acceptance


def test_missing_dev_run_is_not_selected(archive):
    class Missing(FakeHost):
        def evaluate(self, candidate, item_ids):
            result = super().evaluate(candidate, item_ids)
            return result[:-1] if self.eval_calls == 6 else result

    host = Missing(cand("champ"), {"champ": .5, "b": .9})
    log = io.StringIO()
    result = campaign(host, SeqProposer(["b"]), archive, log=log, runs=3, max_attempts=1)
    assert result.selected is None and records(log)[-1]["outcome"] == "dev_failure"


def test_approval_is_bound_to_run_count(archive, tmp_path):
    host = FakeHost(cand("champ"), {})
    first, _ = do_accept(host, archive, cand("b"), approval=lambda r: None, runs=1)
    old = approve_exact(first.request)
    other = Archive(tmp_path / "public2", tmp_path / "private2")
    result, _ = do_accept(host, other, cand("b"), approval=lambda r: old, runs=3)
    assert result.outcome == "not_updated" and host.applied == []


@pytest.mark.parametrize("phase", ["dev", "adjudication"])
def test_fix_invocation_cannot_supply_other_runs(archive, phase):
    calls = 0
    def forged(item_ids):
        nonlocal calls
        calls += 1
        return [{"item_id": item, "run": run, "score": .9}
                for item in item_ids for run in range(3)] if calls == 1 else []
    if phase == "dev":
        host = FakeHost(cand("champ"), {"champ": .5, "b": forged})
        result = campaign(host, SeqProposer(["b"]), archive, runs=3, max_attempts=1)
        assert result.selected is None
    else:
        host = FakeHost(cand("champ"), {})
        result, _ = do_accept(host, archive, cand("b"), scores={"champ": .5, "b": forged},
                              approval=approve_exact, runs=3, holdout=False)
        assert result.outcome == "failed_gate" and host.applied == []
