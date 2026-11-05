"""Admission inside PROPOSE (design §2), reusing standalone GDPevo/GEPA.

Only the injected proposer sees entry text. D4 receives the unchanged kernel's
fixed envelope with ids and numeric dev state; fallback is Decider-owned discard.
"""

from typing import Callable, Mapping, Sequence

from ...candidate import Candidate
from ...decision.envelope import DevPublicView, EnvelopeBuilder
from ...decision.log import Decider
from ...splits import Splits
from ..gdpevo.proposer import propose as propose_text
from ..gdpevo.adapter import validate_skill
from .library import admit, parse_entry, read_library, render_skill


DRAFT_INSTRUCTION = (
    "\nDraft exactly one complete memory/skill brief for future work, not a narrative. "
    "Return only a JSON object inside the markdown code block, with exactly "
    "task_pattern (string), action (string), completion_criteria (string), "
    "and pointers (list of strings). Do not supply ids, paths, operations or other fields. "
    "For a merge or revision this is the complete replacement brief."
)


def propose(champion: Candidate, reflection_records: Sequence[Mapping], splits: Splits,
            model: Callable[[str], str], decider: Decider,
            public_view: DevPublicView) -> Candidate | None:
    entries = read_library(champion)
    # Validate the content-free authority before invoking any proposer or backend.
    envelope = EnvelopeBuilder(entry_ids=tuple(entries)).build(public_view, decisions=("D4",))
    drafted = propose_text(render_skill(champion), reflection_records, splits,
                           lambda prompt: model(prompt + DRAFT_INSTRUCTION))
    if drafted is None:
        return None
    draft = parse_entry(validate_skill(drafted))
    return admit(champion, draft, decider.decide(envelope)["D4"])


def d4_comparisons(records: Sequence[Mapping]) -> list[dict]:
    """Read actual baseline_answer records only; older logs are not fabricated."""
    comparisons = []
    for record in records:
        answer = record.get("answer", {}).get("D4")
        baseline = record.get("baseline_answer", {}).get("D4")
        if answer is not None and baseline is not None:
            comparisons.append({"seq": record["seq"], "answer": answer,
                                "baseline_answer": baseline, "disagrees": answer != baseline})
    return comparisons
