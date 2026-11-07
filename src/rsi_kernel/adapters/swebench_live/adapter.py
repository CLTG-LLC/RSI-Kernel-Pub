"""SWE-bench Live host adapter: dev-only evaluation and record-only apply.

Adjudication and holdout callbacks are named separately for ``loop.accept``;
unlike the public dev contract, they do not add feedback to their result rows.
The proposer receives only ``feedback.proposer_input`` projections, never raw
result rows, and its runtime denies the evidence and private-store paths.
"""

from __future__ import annotations

import math
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from ...archive import Archive
from ...candidate import Candidate
from ...isolation import ProposerRuntime
from ...splits import Splits
from ..gdpevo.adapter import validate_skill
from .feedback import proposer_input
from .tasks import SweTask

Solver = Callable[[Candidate, str], dict]


def _result(item_id: str, score: float | None, reason: str | None = None) -> dict:
    result = {"item_id": item_id, "score": score, "feedback": {"score": score, "correct": score == 1.0}}
    if reason:
        result["failure"] = {"reason": reason}
    return result


class SweAdapter:
    def __init__(self, *, champion: Candidate, tasks: Sequence[SweTask], splits: Splits,
                 solver: Solver, archive: Archive, evidence_dir: Path):
        validate_skill(champion)
        self.tasks = MappingProxyType({task.item_id: task for task in tasks})
        if not self.tasks or len(self.tasks) != len(tasks):
            raise ValueError("tasks must be non-empty with unique item ids")
        if set(self.tasks) != set().union(*(split.item_ids for split in splits.by_name.values())):
            raise ValueError("splits must cover exactly the registered tasks")
        self.splits, self.solver, self.archive = splits, solver, archive
        self.evidence_dir = Path(evidence_dir).resolve()
        self._champion = champion

    def get_artifact(self) -> Candidate:
        validate_skill(self._champion)
        return self._champion

    def apply(self, approved_candidate_hash: str) -> None:
        known = {self._champion.id} | {record["id"] for record in self.archive.public_view().candidates()}
        if approved_candidate_hash not in known:
            raise ValueError("unknown candidate hash")
        self.archive.record_decision({"candidate_id": approved_candidate_hash, "mode": "record-only"})

    def proposer_runtime(self, image: str, dev_data_dir, output_dir) -> ProposerRuntime:
        return ProposerRuntime(image, dev_data_dir, output_dir,
                               deny_paths=(self.evidence_dir, self.archive.private_dir))

    def project_results(self, rows) -> list[dict]:
        return proposer_input(rows)

    def proposer(self, real_proposer: Callable) -> Callable:
        """Adapt the kernel's raw dev rows to the proposer's allowlisted contract."""
        def propose(champion: Candidate, component: str, rows):
            return real_proposer(champion, component, proposer_input(rows))
        return propose

    def evaluate(self, candidate: Candidate, item_ids: Sequence[str]) -> list[dict]:
        return self._evaluate(candidate, item_ids, "dev", private=False)

    def adjudication_callback(self, candidate: Candidate, item_ids: Sequence[str]) -> list[dict]:
        return self._evaluate(candidate, item_ids, "adjudication", private=True)

    def holdout_callback(self, candidate: Candidate, item_ids: Sequence[str]) -> list[dict]:
        return self._evaluate(candidate, item_ids, "holdout", private=True)

    def _evaluate(self, candidate: Candidate, item_ids: Sequence[str], purpose: str, *, private: bool) -> list[dict]:
        validate_skill(candidate)
        if not item_ids or len(set(item_ids)) != len(item_ids):
            raise ValueError("item ids must be a non-empty unique sequence")
        if purpose != "dev" and not private:
            raise PermissionError("non-dev evaluation is private-only")
        if not set(item_ids) <= self.splits.item_ids(purpose):
            raise PermissionError(f"only {purpose} items may be evaluated by this adapter")
        results = []
        for item_id in item_ids:
            try:
                solved = self.solver(candidate, item_id, run=0)
            except Exception:
                solved = None
            results.append(self._consume(item_id, solved, private=private))
        return results

    def _consume(self, item_id: str, solved: object, *, private: bool) -> dict:
        failure = solved.get("failure") if isinstance(solved, Mapping) else None
        reason = (failure.get("reason") if isinstance(failure, Mapping)
                  and isinstance(failure.get("reason"), str) and failure["reason"] else "solver_result")
        score = solved.get("score") if isinstance(solved, Mapping) else None
        if (not isinstance(solved, Mapping) or solved.get("item_id") != item_id
                or (score is not None and (isinstance(score, bool) or not isinstance(score, (int, float))
                                           or not math.isfinite(score) or not 0 <= score <= 1))
                or (score is not None and solved.get("failure"))):
            score, reason = None, "solver_result"
        result = {"item_id": item_id, "score": score}
        if not private:
            result["feedback"] = {"score": score, "correct": score == 1.0}
        if score is None:
            result["failure"] = {"reason": reason}
        if isinstance(solved, Mapping) and isinstance(solved.get("evidence_dir"), str):
            result["evidence_dir"] = solved["evidence_dir"]
        return result
