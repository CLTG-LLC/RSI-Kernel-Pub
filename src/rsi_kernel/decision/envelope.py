"""Content-free SystemOne schema: named local exception in design.md section 3.

The kernel supplies registries, never candidate labels. Public text is deliberately
not inspected. All validation errors are fixed strings, not input representations.
"""

from dataclasses import dataclass, field
import math
import re


INSTRUCTIONS = {
    "D2": "Choose the next registered component to change using dev metrics only.",
    "D4": "Choose how to admit the proposed memory or skill entry using dev metrics only.",
    "D5": "Choose the proposer route using dev metrics only.",
}
CRITERIA = {
    "D2": {"none": "Do not change a component."},
    "D4": {"add": "Add the proposed entry.", "discard": "Discard the proposed entry."},
    "D5": {"cheap": "Use the cheap proposer.", "strong": "Use the strong proposer."},
}
COMPONENT_CRITERION = "Change this registered component."
ENTRY_CRITERIA = {
    "merge": "Merge with this registered entry.",
    "revise": "Revise this registered entry.",
}
STATE_FIELDS = ("attempt_count", "budget_used")
COMPONENT_METRICS = ("dev_pass_count", "dev_fail_count", "dev_paired_score_delta")


@dataclass(frozen=True)
class DevPublicView:
    """Dev numeric state plus public content that must never enter a request."""

    state: dict
    traces: object = None
    candidate_text: object = None
    component_descriptions: dict = field(default_factory=dict)


def _is_id(value, prefix):
    return type(value) is str and re.fullmatch(prefix + r"[0-9]+", value) is not None


def _registry(values, prefix):
    ids = tuple(values)
    if any(not _is_id(value, prefix) for value in ids) or len(set(ids)) != len(ids):
        raise ValueError("invalid kernel id registry")
    return ids


def _state(state, allowed):
    if type(state) is not dict or any(name not in allowed for name in state):
        raise ValueError("unknown state field")
    if any(type(value) not in (int, float) or
           (type(value) is float and not math.isfinite(value)) for value in state.values()):
        raise ValueError("state must contain finite numbers only")
    return dict(state)


class EnvelopeBuilder:
    """Build the whole request from registered ids and whitelisted dev metrics."""

    def __init__(self, component_ids=(), entry_ids=()):
        self.component_ids = _registry(component_ids, "c")
        self.entry_ids = _registry(entry_ids, "e")

    def build(self, public_view, decisions=("D2", "D4"), *, options=None):
        if type(public_view) is not DevPublicView:
            raise ValueError("expected a dev-only public view")
        allowed = (*STATE_FIELDS, *(f"{cid}.{metric}" for cid in self.component_ids
                                    for metric in COMPONENT_METRICS))
        state = _state(public_view.state, allowed)
        questions = {}
        for name in decisions:
            if name not in INSTRUCTIONS or name in questions:
                raise ValueError("unknown or duplicate decision")
            criteria = self._criteria(name)
            if options is not None and name in options:
                selected = tuple(options[name])
                if not selected or any(type(choice) is not str or choice not in criteria
                                       for choice in selected):
                    raise ValueError("option outside the registered choices")
                criteria = {choice: criteria[choice] for choice in selected}
            questions[name] = {"type": "choice", "instructions": INSTRUCTIONS[name],
                               "criteria": criteria}
        if not questions or (options is not None and set(options) - set(questions)):
            raise ValueError("unknown decision options")
        envelope = {"state": state, "questions": questions}
        validate_envelope(envelope)
        return envelope

    def _criteria(self, name):
        if name == "D2":
            return {**{cid: COMPONENT_CRITERION for cid in self.component_ids}, **CRITERIA[name]}
        if name == "D4":
            return {"add": CRITERIA[name]["add"],
                    **{f"{operation}:{eid}": criterion for eid in self.entry_ids
                       for operation, criterion in ENTRY_CRITERIA.items()},
                    "discard": CRITERIA[name]["discard"]}
        return dict(CRITERIA[name])


def validate_envelope(envelope):
    """Recheck the fixed schema before HTTP or logging, including edited envelopes."""
    if type(envelope) is not dict or set(envelope) != {"state", "questions"}:
        raise ValueError("invalid request envelope")
    questions = envelope["questions"]
    if type(questions) is not dict or not questions or set(questions) - set(INSTRUCTIONS):
        raise ValueError("invalid request questions")
    for name, question in questions.items():
        if (type(question) is not dict or set(question) != {"type", "instructions", "criteria"}
                or question["type"] != "choice" or question["instructions"] != INSTRUCTIONS[name]):
            raise ValueError("invalid request question")
        criteria = question["criteria"]
        if type(criteria) is not dict or not criteria:
            raise ValueError("invalid request criteria")
        if ((name == "D4" and "discard" not in criteria)
                or (name == "D5" and "strong" not in criteria)):
            raise ValueError("missing fixed fallback option")
        for choice, criterion in criteria.items():
            expected = CRITERIA[name].get(choice)
            if name == "D2" and _is_id(choice, "c"):
                expected = COMPONENT_CRITERION
            if name == "D4" and type(choice) is str and ":" in choice:
                operation, eid = choice.split(":", 1)
                if _is_id(eid, "e"):
                    expected = ENTRY_CRITERIA.get(operation)
            if expected is None or criterion != expected:
                raise ValueError("invalid request option")
    state = envelope["state"]
    if type(state) is not dict:
        raise ValueError("invalid request state")
    allowed = [name for name in state if name in STATE_FIELDS or
               (type(name) is str and "." in name and _is_id(name.split(".", 1)[0], "c")
                and name.split(".", 1)[1] in COMPONENT_METRICS)]
    _state(state, allowed)
