"""FD2 registered arithmetic and metadata-only exposure regression checks."""
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools/fd2" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registered_formulas_and_smoke_projection():
    result = tool("budgets").formulas(58, 26, 86)
    assert result == {"eval_cap": 696, "spend_cap": 702, "final": 672,
                      "noise_floor": 78, "smoke_done": 1, "total_solves": 1447}
    assert tool("budgets").formulas(1, 2, 3)["eval_cap"] == 12


def test_join_rejects_missing_duplicate_and_unclassified_incomplete():
    join = tool("budgets").survivors
    sidecar = {"splits": {"dev": {"item_ids": ["c/a"]},
                           "adjudication": {"item_ids": []}, "holdout": {"item_ids": []}}}
    row = {"item_id": "c/a", "valid": True, "validation_incomplete": False}
    assert join(sidecar, {"instances": [row]}) == {"dev": ["c/a"], "adjudication": [], "holdout": []}
    for rows in ([], [row, row], [{**row, "valid": False, "validation_incomplete": True}]):
        with pytest.raises(ValueError):
            join(sidecar, {"instances": rows})


def test_exposure_reads_no_content_and_fails_closed(tmp_path, monkeypatch):
    exposure = tool("exposure")
    evidence = tmp_path / "fd2-smoke/evidence/swe-4117ba39"
    evidence.mkdir(parents=True)
    for name in exposure.SOLVE_FILES:
        (evidence / name).touch()
    monkeypatch.setattr(Path, "read_text", lambda *a, **k: pytest.fail("content read"))
    report, stops = exposure.reconcile(tmp_path)
    assert "rust/yvgude__lean-ctx-632: 1" in report
    assert not stops
    (evidence / "result.json").unlink()
    assert exposure.reconcile(tmp_path)[1]
    unknown = tmp_path / "fd2-unknown"
    unknown.mkdir()
    assert any("fd2-unknown" in stop for stop in exposure.reconcile(tmp_path)[1])


def test_empty_gold_targets_require_explicit_disposition(tmp_path):
    exposure = tool("exposure")
    evidence = tmp_path / "fd2-smoke/evidence/swe-4117ba39"
    evidence.mkdir(parents=True)
    for name in exposure.SOLVE_FILES:
        (evidence / name).touch()
    (tmp_path / "fd2-gold-smoke-1").mkdir()
    report, stops = exposure.reconcile(tmp_path)
    assert "lead-recorded" in report
    assert not stops
    (tmp_path / "fd2-gold-smoke-99").mkdir()
    assert tool("exposure").reconcile(tmp_path)[1]


@pytest.mark.parametrize("markers", [("attempt.json",), ("failure.json",),
                                       ("attempt-timing.json",), ("container-scope.txt",),
                                       ("attempt.json", "attempt-timing.json", "failure.json")])
def test_failed_attempt_without_patch_or_measurement_stops(tmp_path, markers):
    exposure = tool("exposure")
    smoke = tmp_path / "fd2-smoke/evidence/swe-4117ba39"
    smoke.mkdir(parents=True)
    for name in exposure.SOLVE_FILES:
        (smoke / name).touch()
    failed = smoke.parent / "failed-attempt"
    failed.mkdir()
    for name in markers:
        (failed / name).touch()
    report, stops = exposure.reconcile(tmp_path)
    assert stops
    assert any("failed-attempt" in stop for stop in stops)


def test_missing_registered_smoke_with_prerun_record_stops(tmp_path):
    prerun = tmp_path / "fd2-smoke-prerun/run"
    prerun.mkdir(parents=True)
    (prerun / "code-identity.txt").touch()
    report, stops = tool("exposure").reconcile(tmp_path)
    assert any("fd2-smoke/evidence/swe-4117ba39" in stop for stop in stops)


def test_pinned_inputs_and_content_id_match_existing_convention(tmp_path):
    from rsi_kernel.candidate import content_id
    import hashlib
    import json

    budgets = tool("budgets")
    path = tmp_path / "metadata.json"
    path.write_text('{"safe": true}')
    assert budgets.pinned_json(path, hashlib.sha256(path.read_bytes()).hexdigest()) == {"safe": True}
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        budgets.pinned_json(path, "0" * 64)
    identity = {"image": "example@sha256:" + "a" * 64}
    validity = {"instances": [{"item_id": "c/a", "receipt": {"evaluator_identity": identity}}]}
    assert budgets.evaluator_hash(validity) == content_id({
        "evaluator_identity": json.dumps({"c/a": identity}, sort_keys=True)})


def test_frozen_evaluator_hash_check_uses_git_tree(monkeypatch):
    import hashlib
    from types import SimpleNamespace

    budgets = tool("budgets")
    calls = []

    def git_show(command, **kwargs):
        calls.append(command)
        return SimpleNamespace(stdout=b"frozen bytes")

    monkeypatch.setattr(budgets.subprocess, "run", git_show)
    receipt = {"workflow_commit": "e3318b7cb672072da49d229ffbc8aa8e7cfb15dc",
               "evaluator_identity": {"files_sha256": {
                   "safe.py": hashlib.sha256(b"frozen bytes").hexdigest()}}}
    validity = {"instances": [{"receipt": receipt}, {"receipt": receipt}]}
    assert budgets.verify_evaluator(validity, "frozen-ref") == 1
    assert calls == [["git", "show", "frozen-ref:safe.py"]]
    receipt["evaluator_identity"]["files_sha256"]["safe.py"] = "0" * 64
    with pytest.raises(ValueError, match="frozen evaluator SHA-256 mismatch"):
        budgets.verify_evaluator(validity, "frozen-ref")


def test_exposure_rejects_unknown_solve_binding_and_symlink(tmp_path):
    exposure = tool("exposure")
    evidence = tmp_path / "fd2-smoke/evidence/unknown"
    evidence.mkdir(parents=True)
    for name in exposure.SOLVE_FILES:
        (evidence / name).touch()
    assert any("no content-free instance binding" in stop for stop in exposure.reconcile(tmp_path)[1])
    (evidence / "linked-directory").symlink_to(tmp_path, target_is_directory=True)
    assert any("symlink" in stop for stop in exposure.reconcile(tmp_path)[1])
