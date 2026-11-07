"""Host-contract tests for the SWE-bench Live adapter; all solver calls are fake."""

from dataclasses import replace
from pathlib import Path

import pytest

from rsi_kernel.archive import Archive
from rsi_kernel.candidate import Candidate
from rsi_kernel.compare import paired_compare
from rsi_kernel.splits import load_splits

from test_swebench_live_solver import CANDIDATE, task


def splits(item):
    return load_splits({"splits": [
        {"name": "dev", "purpose": "dev", "selection_eligible": True, "item_ids": [item.item_id]},
        {"name": "adjudication", "purpose": "adjudication", "selection_eligible": False, "item_ids": ["go/private-adjudication"]},
        {"name": "holdout", "purpose": "holdout", "selection_eligible": False, "item_ids": ["go/private-holdout"]},
    ]})


def make_adapter(tmp_path, solved=None):
    from rsi_kernel.adapters.swebench_live.adapter import SweAdapter

    item = task()
    private_task = replace(item, instance_id="private-adjudication")
    holdout_task = replace(item, instance_id="private-holdout")
    result = solved or {"item_id": item.item_id, "score": 1.0}
    calls = []

    def solver(candidate, item_id, *, run=0):
        calls.append((candidate, item_id, run))
        return {"item_id": item_id, "score": 1.0} if solved is None else result

    adapter = SweAdapter(
        champion=CANDIDATE, tasks=[item, private_task, holdout_task], splits=splits(item), solver=solver,
        archive=Archive(tmp_path / "public", tmp_path / "private"),
        evidence_dir=tmp_path / "evidence",
    )
    return adapter, calls


def test_off_dev_evaluate_is_permission_error_before_solver(tmp_path):
    adapter, calls = make_adapter(tmp_path)
    with pytest.raises(PermissionError):
        adapter.evaluate(CANDIDATE, ["go/private-holdout"])
    assert not calls


def test_dev_feedback_is_exact_and_apply_is_record_only(tmp_path):
    adapter, _ = make_adapter(tmp_path)
    result = adapter.evaluate(CANDIDATE, [task().item_id])[0]
    assert result["feedback"] == {"score": 1.0, "correct": True}
    assert adapter.get_artifact() == CANDIDATE
    adapter.apply(CANDIDATE.id)
    assert adapter.get_artifact() == CANDIDATE


def test_missing_result_gets_reason_and_blocks_compare(tmp_path):
    item = task()
    adapter, _ = make_adapter(tmp_path, {"item_id": item.item_id, "score": None})
    result = adapter.evaluate(CANDIDATE, [item.item_id])[0]
    assert result["failure"]["reason"] == "solver_result"
    assert result["feedback"] == {"score": None, "correct": False}
    assert paired_compare([], [{**result, "run": 0}], [(item.item_id, 0)]).blocks_acceptance


def test_private_adjudication_and_holdout_callbacks_are_separate(tmp_path):
    adapter, calls = make_adapter(tmp_path)
    adjudicate = adapter.adjudication_callback
    holdout = adapter.holdout_callback
    assert adjudicate != holdout
    assert adjudicate(CANDIDATE, ["go/private-adjudication"]) == [{"item_id": "go/private-adjudication", "score": 1.0}]
    assert holdout(CANDIDATE, ["go/private-holdout"]) == [{"item_id": "go/private-holdout", "score": 1.0}]
    assert [call[1] for call in calls] == ["go/private-adjudication", "go/private-holdout"]


def test_private_invalid_result_has_no_feedback(tmp_path):
    adapter, _ = make_adapter(tmp_path)
    result = adapter.adjudication_callback(CANDIDATE, ["go/private-adjudication"])[0]
    assert result == {"item_id": "go/private-adjudication", "score": 1.0}
    with pytest.raises(PermissionError):
        adapter.holdout_callback(CANDIDATE, ["go/private-adjudication"])


def test_run_campaign_proposer_receives_only_projected_rows(tmp_path):
    import io

    from rsi_kernel.decision.envelope import EnvelopeBuilder
    from rsi_kernel.loop import run_campaign

    adapter, _ = make_adapter(tmp_path, {
        "item_id": task().item_id, "score": 0.0,
        "evidence_dir": "SENTINEL_PRIVATE_EVIDENCE",
    })
    seen = []

    def real_proposer(champion, component, rows):
        seen.extend(rows)
        return None

    class Decider:
        def decide(self, envelope):
            return {"D2": "c1"}

    run_campaign(adapter=adapter, proposer=adapter.proposer(real_proposer), decider=Decider(),
                 envelope_builder=EnvelopeBuilder(component_ids=("c1",)),
                 dev_item_ids=[task().item_id], evaluator_hash="synthetic-evaluator", archive=adapter.archive,
                 outcome_log=io.StringIO(), non_regression=lambda comparison: comparison.mean_delta >= 0,
                 spend=lambda: 0, max_attempts=1, spend_cap=1, eval_cap=2, runs=1)
    assert seen == [{"item_id": task().item_id, "score": 0.0, "correct": False}]
    assert "SENTINEL_PRIVATE_EVIDENCE" not in repr(seen)


def test_proposer_runtime_denies_private_evidence_and_uses_projection(tmp_path):
    adapter, _ = make_adapter(tmp_path)
    output = tmp_path / "output"
    runtime = adapter.proposer_runtime("synthetic-image", tmp_path / "staged", output)
    argv = runtime.docker_argv(["true"])
    assert argv[3:5] == ["--network", "none"]
    assert not any("docker.sock" in arg for arg in argv)
    with pytest.raises(PermissionError):
        adapter.proposer_runtime("synthetic-image", tmp_path / "evidence", output).docker_argv(["true"])
    with pytest.raises(PermissionError):
        adapter.proposer_runtime("synthetic-image", tmp_path / "private", output).docker_argv(["true"])
    projected = adapter.project_results([{
        "item_id": task().item_id, "score": 0.0, "feedback": {"score": 0.0, "correct": False},
        "failure": {"reason": "private"}, "evidence_dir": "/private"}])
    assert projected == [{"item_id": task().item_id, "score": 0.0, "correct": False}]
