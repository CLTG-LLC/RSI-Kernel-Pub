"""Draft admission inside PROPOSE, reusing standalone GDPevo/GEPA.

The pilot's host validates and exact-deduplicates drafts into isolated candidates
without a D4 veto; paired dev evaluation decides selection (#45). The in-process
``propose`` helper retains its content-free D4 envelope for compatibility.
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


def draft(rendered: Candidate, reflection_records: Sequence[Mapping], splits: Splits,
          model: Callable[[str], str]) -> str | None:
    """Container side of PROPOSE: one model call, no ids and no decider."""
    drafted = propose_text(rendered, reflection_records, splits,
                           lambda prompt: model(prompt + DRAFT_INSTRUCTION))
    return None if drafted is None else validate_skill(drafted)


def _envelope(champion: Candidate, public_view: DevPublicView) -> dict:
    # Host-owned ids only; c1 is the artifact-level component whose dev counts D2 sees (#33).
    return EnvelopeBuilder(component_ids=("c1",), entry_ids=tuple(read_library(champion))).build(
        public_view, decisions=("D4",))


def _admit(champion: Candidate, drafted: str | None, decider: Decider, envelope: dict) -> Candidate | None:
    if drafted is None:
        return None
    # parse_entry rejects anything but the four brief fields, so a container-supplied
    # operation, entry id or envelope can never reach admission.
    return admit(champion, parse_entry(drafted), decider.decide(envelope)["D4"])


def admit_draft(champion: Candidate, drafted: str | None, decider: Decider,
                dev_results: Sequence[Mapping]) -> Candidate | None:
    """Validate and exact-dedupe a draft for evaluation; retain the pilot hook signature."""
    if drafted is None:
        return None
    return admit(champion, parse_entry(drafted), "add")


def propose(champion: Candidate, reflection_records: Sequence[Mapping], splits: Splits,
            model: Callable[[str], str], decider: Decider,
            public_view: DevPublicView) -> Candidate | None:
    """In-process PROPOSE for tests and one-shot use: validate, draft, then admit."""
    envelope = _envelope(champion, public_view)  # validate the authority before any model call
    return _admit(champion, draft(render_skill(champion), reflection_records, splits, model), decider, envelope)


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
