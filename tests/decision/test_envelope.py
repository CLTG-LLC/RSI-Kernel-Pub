"""Offline contract checks for the content-free SystemOne decision port."""

import json

import pytest

from rsi_kernel.decision.envelope import DevPublicView, EnvelopeBuilder, validate_envelope
from rsi_kernel.decision.backends import DeterministicBackend


CANARY = "RSI_CANARY_4f162_private_candidate"


def public_view(**state):
    return DevPublicView(
        state={"attempt_count": 2, "budget_used": 0.5, **state},
        traces=[CANARY],
        candidate_text=CANARY,
        component_descriptions={"c3": CANARY},
    )


@pytest.fixture
def builder():
    return EnvelopeBuilder(component_ids=("c3", "c8"), entry_ids=("e17",))


def test_d2_contract_and_canary(builder):
    envelope = builder.build(public_view(**{"c3.dev_pass_count": 3}), decisions=("D2",))
    assert envelope == {
        "state": {"attempt_count": 2, "budget_used": 0.5, "c3.dev_pass_count": 3},
        "questions": {
            "D2": {
                "type": "choice",
                "instructions": "Choose the next registered component to change using dev metrics only.",
                "criteria": {
                    "c3": "Change this registered component.",
                    "c8": "Change this registered component.",
                    "none": "Do not change a component.",
                },
            }
        },
    }
    assert CANARY not in json.dumps(envelope)


def test_d4_contract(builder):
    question = builder.build(public_view(), decisions=("D4",))["questions"]["D4"]
    assert question["type"] == "choice"
    assert question["criteria"] == {
        "add": "Add the proposed entry.",
        "merge:e17": "Merge with this registered entry.",
        "revise:e17": "Revise this registered entry.",
        "discard": "Discard the proposed entry.",
    }
    assert CANARY not in json.dumps(question)


def test_d5_contract_is_optional(builder):
    assert "D5" not in builder.build(public_view())["questions"]
    question = builder.build(public_view(), decisions=("D5",))["questions"]["D5"]
    assert question["criteria"] == {
        "cheap": "Use the cheap proposer.",
        "strong": "Use the strong proposer.",
    }


@pytest.mark.parametrize("state", [
    {"trace_text": CANARY},
    {"adjudication_score": 1},
    {"holdout_score": 1},
    {"candidate_hash": "abc"},
    {"c99.dev_pass_count": 1},
    {"attempt_count": CANARY},
    {"budget_used": True},
    {"budget_used": float("nan")},
    {"budget_used": float("inf")},
    {"budget_used": {}},
])
def test_unknown_or_non_numeric_state_is_rejected_without_echo(builder, state):
    with pytest.raises(ValueError) as error:
        builder.build(public_view(**state))
    assert CANARY not in str(error.value)


@pytest.mark.parametrize("kwargs", [
    {"component_ids": (CANARY,)},
    {"component_ids": ("c3",), "entry_ids": (CANARY,)},
    {"component_ids": ("c3", "c3")},
])
def test_registry_accepts_only_unique_kernel_ids(kwargs):
    with pytest.raises(ValueError) as error:
        EnvelopeBuilder(**kwargs)
    assert CANARY not in str(error.value)


def test_options_and_questions_cannot_escape_registered_contract(builder):
    with pytest.raises(ValueError):
        builder.build(public_view(), decisions=("accept",))
    with pytest.raises(ValueError):
        builder.build(public_view(), options={"D2": ("c99",)})
    with pytest.raises(ValueError):
        builder.build(public_view(), options={"D4": ("merge:e99",)})
    with pytest.raises(ValueError):
        builder.build(public_view(), options={"D5": (CANARY,)})


@pytest.mark.parametrize("decision, choices", [
    ("D4", ("add", "merge:e17", "revise:e17")),
    ("D5", ("cheap",)),
])
def test_builder_rejects_options_without_fixed_fallback(builder, decision, choices):
    with pytest.raises(ValueError, match="fallback"):
        builder.build(public_view(), decisions=(decision,), options={decision: choices})


@pytest.mark.parametrize("decision, fallback", [("D4", "discard"), ("D5", "strong")])
def test_validator_rejects_options_without_fixed_fallback(builder, decision, fallback):
    envelope = builder.build(public_view(), decisions=(decision,))
    question = envelope["questions"][decision]
    edited = {**envelope, "questions": {decision: {
        **question, "criteria": {choice: criterion for choice, criterion in question["criteria"].items()
                                 if choice != fallback},
    }}}
    with pytest.raises(ValueError, match="fallback"):
        validate_envelope(edited)


def test_registered_option_subset_and_snapshot(builder):
    view = public_view()
    envelope = builder.build(view, options={"D2": ("c8", "none")})
    assert tuple(envelope["questions"]["D2"]["criteria"]) == ("c8", "none")
    view.state["attempt_count"] = 99
    assert envelope["state"]["attempt_count"] == 2


def test_deterministic_round_robin_and_conservative_defaults(builder):
    backend = DeterministicBackend()
    envelope = builder.build(public_view(), decisions=("D2", "D4", "D5"))
    assert [backend.decide(envelope) for _ in range(3)] == [
        {"D2": "c3", "D4": "discard", "D5": "strong"},
        {"D2": "c8", "D4": "discard", "D5": "strong"},
        {"D2": "c3", "D4": "discard", "D5": "strong"},
    ]
    empty = EnvelopeBuilder(component_ids=()).build(public_view(), decisions=("D2",))
    assert backend.decide(empty) == {"D2": "none"}
