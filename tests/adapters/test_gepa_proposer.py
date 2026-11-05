import pytest


def record(item_id="toy/train/001", feedback=None):
    return {"item_id": item_id, "input": "toy prompt", "output": "toy answer",
            "feedback": feedback or {"score": .5, "correct": False}}


def test_gepa_real_signature_with_fake_model_returns_one_edit(host, api):
    adapter = host[0]
    prompts = []
    def fake_model(prompt):
        prompts.append(prompt)
        return "```markdown\n# Improved toy skill\nCheck the JSON.\n```"
    proposal = api.propose(adapter.get_artifact(), [record()], host[2], fake_model)
    assert proposal.components == {"SKILL.md": "# Improved toy skill\nCheck the JSON."}
    assert proposal.parent_ids == (adapter.get_artifact().id,)
    assert len(prompts) == 1
    assert "toy prompt" in prompts[0] and "toy answer" in prompts[0]
    assert "0.5" in prompts[0]
    # Core GEPA is installed as a dev dependency: this exercises upstream code,
    # not a monkeypatched replacement for run_proposal.
    from gepa.strategies.instruction_proposal import InstructionProposalSignature, run_proposal
    assert callable(run_proposal) and InstructionProposalSignature.input_keys


@pytest.mark.parametrize("response", ["", "```\n\n```", "# Toy skill\nFollow the toy prompt."])
def test_empty_or_unchanged_proposal_means_no_candidate(host, api, response):
    assert api.propose(host[0].get_artifact(), [record()], host[2], lambda prompt: response) is None


@pytest.mark.parametrize("item_id", ["toy/train/002", "toy/test/001", "unknown"])
def test_proposer_refuses_non_dev_reflection_before_model(host, api, item_id):
    calls = []
    with pytest.raises(PermissionError):
        api.propose(host[0].get_artifact(), [record(item_id)], host[2], lambda prompt: calls.append(prompt))
    assert not calls


def test_raw_evaluator_details_never_reach_gepa(host, api):
    prompts = []
    reflection = record(feedback={"score": .5, "correct": False, "details": "SYNTHETIC_GOLD"})
    reflection["raw_payload"] = "SYNTHETIC_GOLD"
    api.propose(host[0].get_artifact(), [reflection], host[2], lambda prompt: prompts.append(prompt) or "")
    assert len(prompts) == 1 and "SYNTHETIC_GOLD" not in prompts[0]


def test_no_reflection_means_no_model_call(host, api):
    calls = []
    assert api.propose(host[0].get_artifact(), [], host[2], lambda prompt: calls.append(prompt)) is None
    assert not calls


def test_failed_reflection_is_not_a_scoreable_example(host, api):
    with pytest.raises(ValueError):
        api.propose(host[0].get_artifact(), [record(feedback={"score": None, "correct": False})], host[2], lambda prompt: "")
