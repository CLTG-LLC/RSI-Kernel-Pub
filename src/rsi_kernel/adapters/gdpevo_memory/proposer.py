"""Admission inside PROPOSE (design §2), reusing standalone GDPevo/GEPA.

Only the injected proposer sees entry text. D4 receives the unchanged kernel's
fixed envelope with ids and numeric dev state; fallback is Decider-owned discard.

The proposer container has no credentials (prereg "Isolation"), so it only drafts
text. D4 runs on the host: ``admit_draft`` validates the draft and builds the
envelope from host-owned ids, never from container-supplied fields (#35).
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
    """Host side of PROPOSE: D4 state from the champion dev results D2 also saw (#33)."""
    if drafted is None:
        return None
    passed = sum(1 for row in dev_results if isinstance(row, Mapping) and row.get("score") == 1.0)
    view = DevPublicView({"c1.dev_pass_count": passed, "c1.dev_fail_count": len(dev_results) - passed})
    return _admit(champion, drafted, decider, _envelope(champion, view))


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
