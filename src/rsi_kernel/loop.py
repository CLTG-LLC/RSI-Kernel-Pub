"""Campaign driver (design §2) and one-shot acceptance, host-agnostic (§4 contract only).

Loop: TARGET (D2 via Decider) → PROPOSE → DEV EVAL (reserved, paired) → SELECT → LOG,
STOP on attempts, spend cap or evaluator reservation. No numbers live here: bounds,
the non-regression rule and the retention rule are injected (prereg, issue #4).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Callable, Optional, Sequence

from .archive import Archive
from .candidate import Candidate, content_id
from .compare import Comparison, paired_compare
from .decision.envelope import DevPublicView, EnvelopeBuilder
from .evaluator import Budget

OUTCOMES = ("updated", "not_updated", "no_improvement", "failed_gate")
_RUN = 0  # Existing zero-based compare/archive run identity.

Rule = Callable[[Comparison], bool]


class CampaignClosed(RuntimeError):
    """A campaign's candidate already went to adjudication; holdout was reported."""


def data_hash(item_ids: Sequence[str]) -> str:
    # JSON array: unambiguous, unlike joining ids with a separator they may contain.
    return content_id({"item_ids": json.dumps(sorted(item_ids))})


def _validate_runs(runs: int) -> None:
    if isinstance(runs, bool) or not isinstance(runs, int) or runs <= 0:
        raise ValueError("runs must be a positive frozen integer")


def _evaluate_runs(evaluate, candidate, item_ids, runs: int) -> list:
    # Host §4 stays unchanged: one fresh evaluation call per independent run.
    # Validate each invocation before combining; another invocation cannot fill
    # its missing pairs. Reuse compare.py and retain a blocking malformed marker.
    results = []
    for run in range(runs):
        rows = [{"run": run, **row} if isinstance(row, dict) else row
                for row in evaluate(candidate, item_ids)]
        if paired_compare(rows, rows, [(item, run) for item in item_ids]).blocks_acceptance:
            results.append(None)
        results.extend(row for row in rows if not isinstance(row, dict) or row.get("run") == run)
    return results


def _compare(base: Sequence[dict], cand: Sequence[dict], item_ids: Sequence[str], runs: int) -> Comparison:
    return paired_compare(base, cand, [(i, run) for i in item_ids for run in range(runs)])


def _evaluation_hash(item_ids, runs):
    # Bind the frozen repetitions as well as items to approval (design §5).
    return content_id({"items": data_hash(item_ids), "runs": str(runs)})


def _archive_valid(archive, comparison, champion_id, candidate_id, purpose, feedback=None) -> None:
    """Archive only rows compare.py validated (paired); malformed rows never get indexed."""
    for p in comparison.pairs:
        for cid, score, side in ((champion_id, p.baseline, "baseline"), (candidate_id, p.candidate, "candidate")):
            if cid is None:
                continue
            if feedback is None:
                archive.record_result(cid, p.item_id, p.run, score, purpose)
            else:
                archive.record_result(cid, p.item_id, p.run, score, purpose, feedback[side].get((p.item_id, p.run), ""))


def _feedback(results) -> dict:
    return {(r.get("item_id"), r.get("run", _RUN)): str(r.get("feedback", ""))
            for r in results if isinstance(r, dict) and isinstance(r.get("item_id"), str)
            and isinstance(r.get("run", _RUN), int)}


def _append(log, record: dict) -> None:
    log.seek(0, 2)
    log.write(json.dumps(record, sort_keys=True) + "\n")
    log.flush()


def _suppressed(log, context: dict) -> set[str]:
    """Exact hashes that showed a dev regression in this frozen context (design §2)."""
    log.seek(0)
    out = set()
    for line in log:
        if not line.strip():
            continue
        r = json.loads(line)
        if r.get("outcome") == "dev_regression" and all(r.get(k) == v for k, v in context.items()):
            out.add(r["candidate_id"])
    return out


@dataclass(frozen=True)
class CampaignResult:
    selected: Optional[Candidate]
    outcome: str  # "selected" or "no_improvement"
    stop_reason: str  # "attempts", "spend_cap" or "eval_cap"
    attempts: int
    evaluator_items_used: int


def run_campaign(*, adapter, proposer, decider, envelope_builder: EnvelopeBuilder,
                 dev_item_ids: Sequence[str], evaluator_hash: str, archive: Archive, outcome_log,
                 non_regression: Rule, spend: Callable[[], float],
                 max_attempts: int, spend_cap: float, eval_cap: int, runs: int) -> CampaignResult:
    """``proposer(champion, component_id, champion_dev_results) -> Candidate | None``.

    ``spend()`` meters proposer, evaluated-agent and Jev calls (failed ones included);
    the campaign halts at the first check past ``spend_cap``. Evaluator items are hard
    reserved against ``eval_cap`` before each call (evaluator.Budget).
    """
    _validate_runs(runs)
    dev = list(dev_item_ids)
    budget = Budget(eval_cap)
    champion = adapter.get_artifact()
    context = {"champion_id": champion.id, "dev_hash": data_hash(dev), "evaluator_hash": evaluator_hash, "runs": runs}
    suppressed = _suppressed(outcome_log, context)
    best: tuple[float, Candidate] | None = None
    attempts, stop = 0, "attempts"

    def finish(reason):
        sel = best[1] if best else None
        return CampaignResult(sel, "selected" if sel else "no_improvement", reason, attempts, budget.used)

    if not budget.reserve(len(dev) * runs):
        return finish("eval_cap")
    champ_results = _evaluate_runs(adapter.evaluate, champion, dev, runs)
    # Self-pairing validates the champion rows; malformed ones block every later comparison.
    _archive_valid(archive, _compare(champ_results, champ_results, dev, runs), champion.id, None, "dev",
                   {"baseline": _feedback(champ_results), "candidate": {}})

    def log(outcome, candidate=None, delta=None):
        _append(outcome_log, {**context, "attempt": attempts, "outcome": outcome,
                              "candidate_id": candidate.id if candidate else None, "mean_delta": delta})

    # D2 is asked to choose "using dev metrics only" (decision/envelope.py), so pass the
    # schema's COMPONENT_METRICS: champion dev pass/fail (correct = score 1.0, as in
    # proposer feedback) per registered component, artifact-level, and the last valid
    # paired dev delta for a component once it has one. Numbers only.
    passed = sum(1 for r in champ_results if isinstance(r, dict) and r.get("score") == 1.0)
    champion_metrics = {}
    for cid in getattr(envelope_builder, "component_ids", ()):
        champion_metrics[f"{cid}.dev_pass_count"] = passed
        champion_metrics[f"{cid}.dev_fail_count"] = len(champ_results) - passed
    last_delta: dict[str, float] = {}

    while attempts < max_attempts:
        if spend() > spend_cap:
            stop = "spend_cap"
            break
        attempts += 1
        state = {"attempt_count": attempts - 1, "budget_used": budget.used, **champion_metrics,
                 **{f"{cid}.dev_paired_score_delta": d for cid, d in last_delta.items()}}
        envelope = envelope_builder.build(DevPublicView(state), decisions=("D2",))
        component = decider.decide(envelope)["D2"]
        if component == "none":
            log("no_target")
            continue
        candidate = proposer(champion, component, champ_results)
        if candidate is None or candidate.id == champion.id:  # unchanged champion is no candidate
            log("no_candidate")
            continue
        if spend() > spend_cap:
            stop = "spend_cap"
            break
        if candidate.id in suppressed:
            log("suppressed", candidate)
            continue
        if not budget.reserve(len(dev) * runs):
            stop = "eval_cap"
            break
        archive.record_candidate(candidate, "proposed")
        try:
            results = _evaluate_runs(adapter.evaluate, candidate, dev, runs)
        except Exception:  # operational failure: logged, never suppressed
            log("dev_failure", candidate)
            continue
        comparison = _compare(champ_results, results, dev, runs)
        _archive_valid(archive, comparison, None, candidate.id, "dev",
                       {"baseline": {}, "candidate": _feedback(results)})
        if comparison.blocks_acceptance:
            log("dev_failure", candidate)
            continue
        last_delta[component] = comparison.mean_delta
        if not non_regression(comparison):
            suppressed.add(candidate.id)
            log("dev_regression", candidate, comparison.mean_delta)
        else:
            log("dev_pass", candidate, comparison.mean_delta)
            if best is None or comparison.mean_delta > best[0]:
                best = (comparison.mean_delta, candidate)
    return finish(stop)


@dataclass(frozen=True)
class ApprovalRequest:
    campaign_id: str
    candidate_hash: str
    evaluator_hash: str
    data_hash: str
    code_hash: str  # full kernel + adapter code identity (prereg "Acceptance", #42)


@dataclass(frozen=True)
class ApprovalRecord:
    candidate_hash: str
    evaluator_hash: str
    data_hash: str
    code_hash: str
    approver: str


@dataclass(frozen=True)
class AcceptResult:
    outcome: str  # one of OUTCOMES
    comparison: Optional[Comparison] = None
    request: Optional[ApprovalRequest] = None
    holdout_results: Optional[Comparison] = None

    @property
    def success(self) -> bool:
        return self.outcome == "updated"  # keeping the champion is not success (#4)


def accept(*, campaign_id: str, candidate: Optional[Candidate], champion: Candidate,
           adjudicate: Callable[[Candidate, Sequence[str]], Sequence[dict]],
           adjudication_item_ids: Sequence[str], evaluator_hash: str, code_hash: str, retain: Rule,
           approval: Callable[[ApprovalRequest], Optional[ApprovalRecord]], adapter,
           archive: Archive, runs: int, holdout: Optional[Callable[[Candidate, Sequence[str]], Sequence[dict]]] = None,
           holdout_item_ids: Sequence[str] = ()) -> AcceptResult:
    """One frozen candidate, outside the loop. Results go to the private store only."""
    _validate_runs(runs)
    if candidate is None or candidate.id == champion.id:  # unchanged champion is not an update
        return AcceptResult("no_improvement")
    store = archive.private_store()
    if any(d.get("kind") == "adjudication" and d.get("campaign_id") == campaign_id for d in store.decisions()):
        raise CampaignClosed(campaign_id)
    adj = list(adjudication_item_ids)
    comparison = _paired_private(archive, adjudicate, champion, candidate, adj, "adjudication", runs)
    holdout_cmp = (_paired_private(archive, holdout, champion, candidate, list(holdout_item_ids), "holdout", runs)
                   if holdout is not None and holdout_item_ids else None)
    # Closed only once evaluation completed; a host crash above leaves the campaign open.
    archive.record_decision({"kind": "adjudication", "campaign_id": campaign_id, "candidate_id": candidate.id})
    if (comparison.blocks_acceptance or (holdout_cmp is not None and holdout_cmp.blocks_acceptance)
            or not retain(comparison)):
        return _decided(archive, campaign_id, "failed_gate", comparison, None, holdout_cmp)
    request = ApprovalRequest(campaign_id, candidate.id, evaluator_hash, _evaluation_hash(adj, runs), code_hash)
    archive.record_decision({"kind": "approval_request", **request.__dict__})
    record = approval(request)
    matches = (isinstance(record, ApprovalRecord) and
               (record.candidate_hash, record.evaluator_hash, record.data_hash, record.code_hash)
               == (request.candidate_hash, request.evaluator_hash, request.data_hash, request.code_hash))
    if not matches:
        return _decided(archive, campaign_id, "not_updated", comparison, request, holdout_cmp)
    archive.record_decision({"kind": "approval", "campaign_id": campaign_id, **record.__dict__})
    adapter.apply(candidate.id)
    return _decided(archive, campaign_id, "updated", comparison, request, holdout_cmp)


def _paired_private(archive, evaluate, champion, candidate, item_ids, purpose, runs) -> Comparison:
    base = _evaluate_runs(evaluate, champion, item_ids, runs)
    cand = _evaluate_runs(evaluate, candidate, item_ids, runs)
    comparison = _compare(base, cand, item_ids, runs)
    _archive_valid(archive, comparison, champion.id, candidate.id, purpose)
    return comparison


def _decided(archive, campaign_id, outcome, comparison, request, holdout_cmp) -> AcceptResult:
    archive.record_decision({"kind": "outcome", "campaign_id": campaign_id, "outcome": outcome})
    return AcceptResult(outcome, comparison, request, holdout_cmp)
