"""Standalone GEPA proposer; injected model only, never GEPA's optimizer loop.

GEPA@3d34469165f0d604df3b48f1d5c776e9080f3da0,
src/gepa/strategies/instruction_proposal.py:138,147.
https://github.com/gepa-ai/gepa/blob/3d34469165f0d604df3b48f1d5c776e9080f3da0/src/gepa/strategies/instruction_proposal.py#L138-L147
"""

import math
from typing import Callable, Mapping, Sequence

from ...candidate import Candidate
from ...splits import Splits
from .adapter import validate_skill


def propose(champion: Candidate, reflection_records: Sequence[Mapping], splits: Splits,
            model: Callable[[str], str]) -> Candidate | None:
    current = validate_skill(champion)
    records = []
    for record in reflection_records:
        if record.get("item_id") not in splits.dev_item_ids():
            raise PermissionError("only dev reflection records may reach proposer")
        feedback = record.get("feedback", {})
        score = feedback.get("score")
        if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("reflection requires a valid evaluator score")
        if not isinstance(record.get("input"), str) or not isinstance(record.get("output"), str):
            raise ValueError("reflection input and output must be selected dev text")
        records.append({"input": record["input"], "output": record["output"],
                        "feedback": {"score": score, "correct": score == 1.0}})
    if not records:
        return None
    # Lazy optional import; the host injects the model transport in its container.
    from gepa.strategies.instruction_proposal import InstructionProposalSignature, run_proposal

    parsed, _, _ = run_proposal(InstructionProposalSignature, model, {
        "current_instruction_doc": current, "dataset_with_feedback": records,
        "prompt_template": None,
    })
    if parsed.text is None or parsed.text.strip() == current.strip():
        return None
    return Candidate({"SKILL.md": parsed.text}, "text/plain", parent_ids=(champion.id,))
