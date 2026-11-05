"""Synthetic S5 contracts; no pilot data, network, or live model calls."""

import importlib
import io
import json
from pathlib import Path

import pytest

from rsi_kernel.candidate import Candidate
from rsi_kernel.compare import paired_compare
from rsi_kernel.decision.envelope import DevPublicView
from rsi_kernel.decision.log import Decider, ReplayBackend


CANARY = "SYNTHETIC_ENTRY_CANARY"


def brief(action=CANARY):
    return {"task_pattern": "Toy JSON tasks", "action": action,
            "completion_criteria": "The toy answer passes", "pointers": ["toy/input/prompt.txt"]}


@pytest.fixture
def memory():
    return importlib.import_module("rsi_kernel.adapters.gdpevo_memory")


@pytest.fixture
def memory_host(memory, host):
    adapter = host[0]
    return memory.GDPevoMemoryAdapter(
        champion=memory.library_candidate([brief()]), root=adapter.root,
        tasks=tuple(adapter.tasks.values()), splits=adapter.splits, solver=adapter.solver,
        evaluator_timeout=adapter.evaluator_timeout, work_dir=adapter.work_dir,
        archive=adapter.archive,
    )


class ChoiceBackend:
    name = "fake"
    model = "synthetic"

    def __init__(self, choice):
        self.choice = choice
        self.requests = []

    def decide(self, envelope):
        self.requests.append(envelope)
        return {"D4": self.choice}


def reflection(item_id="toy/train/001"):
    return {"item_id": item_id, "input": "Toy input", "output": "Toy answer",
            "feedback": {"score": 1.0, "details": "SYNTHETIC_GOLD"},
            "raw_payload": "SYNTHETIC_GOLD"}


def proposal(memory, champion, splits, choice, entry=None, log=None):
    backend = ChoiceBackend(choice)
    log = io.StringIO() if log is None else log
    decider = Decider(backend, log)
    prompts = []

    def model(prompt):
        prompts.append(prompt)
        return "```json\n" + json.dumps(brief("Changed") if entry is None else entry) + "\n```"

    candidate = memory.propose(champion, [reflection()], splits, model, decider,
                               DevPublicView({"attempt_count": 1}, candidate_text=CANARY))
    return candidate, backend, log, prompts


def test_library_canonical_hash_and_opaque_kernel_ids(memory):
    entry = brief()
    champion = memory.library_candidate([entry, brief("Other")])
    reversed_keys = {key: entry[key] for key in reversed(entry)}
    assert champion.id == memory.library_candidate([reversed_keys, brief("Other")]).id
    assert champion.media_type == "application/json"
    assert set(champion.components) == {"entries/e1.json", "entries/e2.json"}
    assert memory.read_library(champion) == {"e1": entry, "e2": brief("Other")}
    entry["action"] = "alias drift"
    assert memory.read_library(champion)["e1"]["action"] == CANARY


def test_renderer_is_fixed_and_deterministic(memory):
    champion = memory.library_candidate([brief()])
    rendered = memory.render_skill(champion)
    assert rendered.media_type == "text/plain"
    assert rendered.components == {"SKILL.md": (
        "# Memory / skill library\n\n## e1\n"
        "Task pattern: Toy JSON tasks\nAction / intent: SYNTHETIC_ENTRY_CANARY\n"
        "Completion criteria: The toy answer passes\nPointers:\n- toy/input/prompt.txt\n"
    )}
    assert rendered.parent_ids == (champion.id,)
    assert rendered.id == memory.render_skill(champion).id


@pytest.mark.parametrize("target", ["../e1.json", "entries/../e1.json", "/entries/e1.json",
    "entries/e1.json/extra", "entries/e1.json\n", "entries/e1.json.bak", "entries/e01.json",
    "entries/e0.json", "entries/e1.py", "SKILL.md", "entries/e1\\.json", "entries/é1.json"])
def test_library_write_targets_are_allowlisted(memory, target):
    with pytest.raises(ValueError):
        memory.read_library(Candidate({target: json.dumps(brief())}, "application/json"))


@pytest.mark.parametrize("entry", [{}, {**brief(), "id": "e999"}, {**brief(), "path": "../x"},
    {**brief(), "action": ""}, {**brief(), "task_pattern": None},
    {**brief(), "completion_criteria": "   "}, {**brief(), "pointers": "x"},
    {**brief(), "pointers": [None]}, {**brief(), "pointers": [""]}])
def test_entry_brief_schema_validated(memory, entry):
    with pytest.raises(ValueError):
        memory.library_candidate([entry])


@pytest.mark.parametrize("payload", ["not-json", "[]", "null", '{"action":NaN}',
    '{"task_pattern":"x","task_pattern":"y","action":"a","completion_criteria":"c","pointers":[]}'])
def test_invalid_or_ambiguous_json_rejected(memory, payload):
    with pytest.raises(ValueError):
        memory.read_library(Candidate({"entries/e1.json": payload}, "application/json"))


def test_library_media_and_hash_drift_rejected(memory):
    candidate = memory.library_candidate([brief()])
    with pytest.raises(ValueError):
        memory.read_library(Candidate(dict(candidate.components), "text/plain"))
    object.__setattr__(candidate, "id", "drift")
    with pytest.raises(ValueError, match="hash"):
        memory.read_library(candidate)


@pytest.mark.parametrize("choice,target", [("add", "e2"), ("merge:e1", "e1"), ("revise:e1", "e1")])
def test_admission_inside_propose_preserves_ids_and_parent(memory, memory_host, choice, target):
    champion = memory_host.get_artifact()
    candidate, backend, log, prompts = proposal(memory, champion, memory_host.splits, choice)
    entries = memory.read_library(candidate)
    assert entries[target] == brief("Changed")
    assert candidate.parent_ids == (champion.id,)
    assert memory.read_library(champion) == {"e1": brief()}
    assert set(entries) == ({"e1", "e2"} if choice == "add" else {"e1"})
    assert len(prompts) == len(backend.requests) == 1
    assert "SYNTHETIC_GOLD" not in prompts[0]
    assert CANARY in prompts[0]
    request = backend.requests[0]
    assert set(request["questions"]["D4"]["criteria"]) == {"add", "merge:e1", "revise:e1", "discard"}
    assert CANARY not in json.dumps(request)
    assert CANARY not in log.getvalue()


@pytest.mark.parametrize("choice", ["discard", "revise:e99", "merge:e99", "attacker-choice"])
def test_discard_or_off_list_fallback_yields_no_candidate(memory, memory_host, choice):
    candidate, _, log, _ = proposal(memory, memory_host.get_artifact(), memory_host.splits, choice)
    assert candidate is None
    assert json.loads(log.getvalue())["answer"] == {"D4": "discard"}


def test_timeout_uses_decider_discard_fallback(memory, memory_host):
    class Timeout(ChoiceBackend):
        def decide(self, envelope):
            raise TimeoutError(CANARY)
    log = io.StringIO()
    assert memory.propose(memory_host.get_artifact(), [reflection()], memory_host.splits,
                          lambda prompt: "```json\n" + json.dumps(brief()) + "\n```",
                          Decider(Timeout("add"), log), DevPublicView({})) is None
    assert json.loads(log.getvalue())["fallback_reason"] == "timeout"
    assert CANARY not in log.getvalue()


@pytest.mark.parametrize("choice", ["add", "merge:e1", "revise:e1"])
def test_duplicate_add_and_unchanged_replacement_skipped(memory, memory_host, choice):
    assert proposal(memory, memory_host.get_artifact(), memory_host.splits, choice, brief())[0] is None


@pytest.mark.parametrize("choice", ["merge:e9", "revise:e9", "merge:../e1", "revise:e1:extra", "add:e1", "unknown"])
def test_write_guard_rejects_absent_or_unsafe_operations(memory, memory_host, choice):
    with pytest.raises(ValueError):
        memory.admit(memory_host.get_artifact(), brief("Changed"), choice)


def test_new_id_follows_existing_highest_not_entry_count(memory):
    champion = Candidate({"entries/e17.json": json.dumps(brief())}, "application/json")
    candidate = memory.admit(champion, brief("Changed"), "add")
    assert set(memory.read_library(candidate)) == {"e17", "e18"}


def test_empty_library_admission_only_offers_add_and_discard(memory, host):
    champion = memory.library_candidate([])
    candidate, backend, _, _ = proposal(memory, champion, host[2], "add")
    assert memory.read_library(candidate) == {"e1": brief("Changed")}
    assert set(backend.requests[0]["questions"]["D4"]["criteria"]) == {"add", "discard"}


@pytest.mark.parametrize("item_id", ["toy/train/002", "toy/test/001", "unknown"])
def test_nondev_reflection_cannot_reach_model_or_decider(memory, memory_host, item_id):
    calls = []
    backend = ChoiceBackend("add")
    with pytest.raises(PermissionError):
        memory.propose(memory_host.get_artifact(), [reflection(item_id)], memory_host.splits,
                       lambda prompt: calls.append(prompt), Decider(backend, io.StringIO()), DevPublicView({}))
    assert not calls and not backend.requests


@pytest.mark.parametrize("response", ["", "```json\n\n```"])
def test_empty_proposal_skips_admission(memory, memory_host, response):
    backend = ChoiceBackend("add")
    assert memory.propose(memory_host.get_artifact(), [reflection()], memory_host.splits,
                          lambda prompt: response, Decider(backend, io.StringIO()), DevPublicView({})) is None
    assert not backend.requests


def test_malformed_draft_rejected_before_decider(memory, memory_host):
    backend = ChoiceBackend("add")
    with pytest.raises(ValueError):
        memory.propose(memory_host.get_artifact(), [reflection()], memory_host.splits,
                       lambda prompt: "```json\n{}\n```", Decider(backend, io.StringIO()), DevPublicView({}))
    assert not backend.requests


def test_equivalent_candidate_order_produces_identical_d4_envelopes(memory, host):
    champion = memory.library_candidate([brief(), brief("Other")])
    reversed_components = Candidate(dict(reversed(list(champion.components.items()))), "application/json")
    assert reversed_components.id == champion.id
    first = proposal(memory, champion, host[2], "discard")[1].requests
    second = proposal(memory, reversed_components, host[2], "discard")[1].requests
    assert list(first[0]["questions"]["D4"]["criteria"]) == list(second[0]["questions"]["D4"]["criteria"])


def test_no_reflection_skips_model_and_decider(memory, memory_host):
    calls = []
    backend = ChoiceBackend("add")
    assert memory.propose(memory_host.get_artifact(), [], memory_host.splits,
                          lambda prompt: calls.append(prompt), Decider(backend, io.StringIO()), DevPublicView({})) is None
    assert not calls and not backend.requests


@pytest.mark.parametrize("score", [None, True, -1, 2, float("nan"), float("inf")])
def test_unscoreable_reflection_cannot_reach_model(memory, memory_host, score):
    calls = []
    record = reflection()
    record["feedback"] = {"score": score}
    with pytest.raises(ValueError):
        memory.propose(memory_host.get_artifact(), [record], memory_host.splits,
                       lambda prompt: calls.append(prompt), Decider(ChoiceBackend("add"), io.StringIO()), DevPublicView({}))
    assert not calls


def test_unknown_state_rejected_before_model_and_without_canary(memory, memory_host):
    calls = []
    backend = ChoiceBackend("add")
    with pytest.raises(ValueError) as error:
        memory.propose(memory_host.get_artifact(), [reflection()], memory_host.splits,
                       lambda prompt: calls.append(prompt), Decider(backend, io.StringIO()),
                       DevPublicView({CANARY: 1}))
    assert CANARY not in str(error.value)
    assert not calls and not backend.requests


def test_private_outcomes_do_not_change_proposal_or_d4_envelope(memory, memory_host, host):
    champion = memory_host.get_artifact()
    first, backend1, _, _ = proposal(memory, champion, memory_host.splits, "add")
    host[3].record_result(champion.id, "toy/train/002", 0, 0.0, "adjudication", CANARY)
    host[3].record_result(champion.id, "toy/test/001", 0, 1.0, "holdout", CANARY)
    second, backend2, _, _ = proposal(memory, champion, memory_host.splits, "add")
    assert first.id == second.id
    assert backend1.requests == backend2.requests


def test_decision_replay_reproduces_candidate_without_query(memory, memory_host):
    champion = memory_host.get_artifact()
    candidate, _, log, _ = proposal(memory, champion, memory_host.splits, "add")
    replayed = memory.propose(champion, [reflection()], memory_host.splits,
                             lambda prompt: "```json\n" + json.dumps(brief("Changed")) + "\n```",
                             Decider(ReplayBackend(log), io.StringIO()), DevPublicView({"attempt_count": 1}))
    assert replayed.id == candidate.id


def test_evaluate_uses_admitted_library_in_existing_staging(memory, memory_host, host):
    candidate = proposal(memory, memory_host.get_artifact(), memory_host.splits, "add")[0]
    original = memory_host.solver
    seen = []
    # The guarded solver wraps the injected callable, never a real solver.
    injected = memory_host._memory_solver

    def observe(rendered, item_id, input_dir, prediction, env):
        staged = input_dir.parent / "SKILL.md"
        seen.append(staged.read_bytes())
        assert Candidate({"SKILL.md": staged.read_bytes()}, "text/plain").id == rendered.id
        assert b"Changed" in staged.read_bytes()
        assert not (input_dir.parent / "eval").exists()
        return injected(rendered, item_id, input_dir, prediction, env)

    memory_host._memory_solver = observe
    result = memory_host.evaluate(candidate, ["toy/train/001"])
    assert result == [{"item_id": "toy/train/001", "score": 1.0,
                       "feedback": {"score": 1.0, "correct": True}}]
    assert seen == [memory.render_skill(candidate).components["SKILL.md"].encode()]
    assert memory_host.solver is original
    assert host[4][0][0].id == memory.render_skill(candidate).id


@pytest.mark.parametrize("tamper", ["replace", "remove", "symlink"])
def test_staged_skill_drift_is_structured_failure_and_blocks(memory_host, tamper):
    original = memory_host._memory_solver

    def solver(candidate, item_id, input_dir, prediction, env):
        original(candidate, item_id, input_dir, prediction, env)
        staged = input_dir.parent / "SKILL.md"
        if tamper == "replace":
            staged.write_text("catalog precedence drift")
        else:
            staged.unlink()
            if tamper == "symlink":
                staged.symlink_to(input_dir / "prompt.txt")

    memory_host._memory_solver = solver
    result = memory_host.evaluate(memory_host.get_artifact(), ["toy/train/001"])[0]
    assert result["score"] is None and result["failure"]["reason"] == "solver"
    assert paired_compare([{ "item_id": result["item_id"], "run": 0, "score": 1.0}],
                          [{**result, "run": 0}], [(result["item_id"], 0)]).blocks_acceptance


def test_bad_skill_write_stops_before_solver(memory_host, host, monkeypatch):
    original = Path.write_bytes

    def corrupt(path, value):
        return original(path, b"watcher drift" if path.name == "SKILL.md" else value)

    monkeypatch.setattr(Path, "write_bytes", corrupt)
    result = memory_host.evaluate(memory_host.get_artifact(), ["toy/train/001"])[0]
    assert result["failure"]["reason"] == "solver"
    assert not host[4]


@pytest.mark.parametrize("items", [["toy/train/002"], ["toy/test/001"], []])
def test_existing_evaluate_split_guards_still_apply(memory_host, host, items):
    with pytest.raises((ValueError, PermissionError)):
        memory_host.evaluate(memory_host.get_artifact(), items)
    assert not host[4]


def test_memory_adapter_reuses_existing_no_network_mount_boundary(memory_host):
    runtime = memory_host.proposer_runtime("fake-image", memory_host.work_dir.parent / "staged-dev",
                                          memory_host.work_dir.parent / "proposals")
    argv = runtime.docker_argv(["python", "-c", "pass"])
    assert argv[argv.index("--network") + 1] == "none"
    assert "TASK_ENV_ENABLE_JUDGE=0" in argv
    forbidden = memory_host.proposer_runtime("fake-image", memory_host.root, memory_host.work_dir.parent / "out")
    with pytest.raises(PermissionError):
        forbidden.docker_argv(["true"])


def test_record_only_apply_uses_library_hash(memory, memory_host, host):
    champion = memory_host.get_artifact()
    candidate = memory.admit(champion, brief("Changed"), "add")
    host[3].record_candidate(candidate, "proposed")
    memory_host.apply(champion.id)
    memory_host.apply(candidate.id)
    assert memory_host.get_artifact() is champion
    assert host[3].private_store().decisions()[-1] == {"candidate_id": candidate.id, "mode": "record-only"}
    with pytest.raises(ValueError):
        memory_host.apply("unknown")


def test_optional_baseline_comparisons_use_recorded_answers_only(memory):
    records = [{"seq": 1, "answer": {"D4": "add"}},
               {"seq": 2, "answer": {"D4": "revise:e1"}, "baseline_answer": {"D4": "discard"}},
               {"seq": 3, "answer": {"D2": "c1"}, "baseline_answer": {"D2": "c1"}},
               {"seq": 4, "answer": {"D4": "discard"}, "baseline_answer": {"D4": "discard"}}]
    assert memory.d4_comparisons(records) == [
        {"seq": 2, "answer": "revise:e1", "baseline_answer": "discard", "disagrees": True},
        {"seq": 4, "answer": "discard", "baseline_answer": "discard", "disagrees": False},
    ]


# S5 addendum: host-side D4 admission and DockerSolver result preservation (issue #35).


def test_dict_solver_result_survives_without_host_regrade(memory_host, host):
    """DockerSolver already graded in isolation; the host must not regrade (addendum D4 placement)."""
    memory_host._memory_solver = lambda rendered, item_id, input_dir, prediction, env: {
        "item_id": item_id, "score": 0.25, "evidence_dir": "/synthetic/evidence",
        "failure": {"status": "STOP", "reason": "solver"}}
    result = memory_host.evaluate(memory_host.get_artifact(), ["toy/train/001"])[0]
    # The toy evaluator always scores 1.0, so 0.25 with its failure metadata proves no regrade.
    assert result["score"] == 0.25
    assert result["failure"] == {"status": "STOP", "reason": "solver"}
    assert result["evidence_dir"] == "/synthetic/evidence"
    assert result["feedback"] == {"score": 0.25, "correct": False}
    assert not host[4]  # the injected callable already ran once and only once


def test_final_phase_render_happens_once_per_evaluation(memory_host, monkeypatch):
    from rsi_kernel.adapters.gdpevo.adapter import _verify_task
    adapter_module = importlib.import_module("rsi_kernel.adapters.gdpevo_memory.adapter")
    renders, original = [], adapter_module.render_skill
    monkeypatch.setattr(adapter_module, "render_skill",
                        lambda candidate: renders.append(candidate.id) or original(candidate))
    # evaluate() renders the batch once; the solver then receives that rendered artifact.
    memory_host.evaluate(memory_host.get_artifact(), ["toy/train/001"])
    assert len(renders) == 1
    # The final phase calls _evaluate_one directly with the host library: exactly one render.
    task = memory_host.tasks["toy/train/002"]
    memory_host._evaluate_one(memory_host.get_artifact(), "toy/train/002", _verify_task(memory_host.root, task))
    assert len(renders) == 2


def test_admit_draft_state_is_artifact_counts_only(memory, memory_host):
    backend = ChoiceBackend("add")
    rows = [{"score": 1.0}, {"score": 0.0}, {"score": None, "failure": {"reason": "solver"}}]
    candidate = memory.admit_draft(memory_host.get_artifact(),
                                   json.dumps(brief("Changed")), Decider(backend, io.StringIO()), rows)
    assert memory.read_library(candidate) == {"e1": brief(), "e2": brief("Changed")}
    request = backend.requests[0]
    assert request["state"] == {"c1.dev_pass_count": 1, "c1.dev_fail_count": 2}
    assert CANARY not in json.dumps(request)


@pytest.mark.parametrize("extra", [{"choice": "add"}, {"id": "e9"}, {"entry_id": "e9"},
                                   {"operation": "add"}, {"envelope": {}}, {"state": {}}])
def test_container_draft_cannot_supply_d4_fields(memory, memory_host, extra):
    with pytest.raises(ValueError):
        memory.admit_draft(memory_host.get_artifact(), json.dumps({**brief("Changed"), **extra}),
                           Decider(ChoiceBackend("add"), io.StringIO()), [{"score": 1.0}])


def test_container_draft_is_ignored_for_ids_and_operation(memory, memory_host):
    backend = ChoiceBackend("add")
    # The host issues ids and the operation; the draft only supplies brief text.
    candidate = memory.admit_draft(memory_host.get_artifact(), json.dumps(brief("Changed")),
                                   Decider(backend, io.StringIO()), [{"score": 1.0}])
    assert set(memory.read_library(candidate)) == {"e1", "e2"}
    assert list(backend.requests[0]["questions"]["D4"]["criteria"]) == ["add", "merge:e1", "revise:e1", "discard"]


def test_malformed_or_empty_draft_skips_d4(memory, memory_host):
    backend = ChoiceBackend("add")
    assert memory.admit_draft(memory_host.get_artifact(), None, Decider(backend, io.StringIO()),
                              [{"score": 1.0}]) is None
    assert not backend.requests
    with pytest.raises(ValueError):
        memory.admit_draft(memory_host.get_artifact(), "{}", Decider(backend, io.StringIO()), [{"score": 1.0}])
    assert not backend.requests
