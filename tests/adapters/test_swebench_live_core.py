"""Docker-free core of the SWE-bench-Live adapter: loader, carve, grading, feedback.

No Docker, no network, no dataset download. The parquet reader is injected, so
these tests never need pyarrow.
"""

import hashlib
import json
import sys
from datetime import datetime, timedelta, timezone

import pytest

from rsi_kernel.adapters.swebench_live import feedback as feedback_module
from rsi_kernel.adapters.swebench_live import grading as grading_module
from rsi_kernel.adapters.swebench_live import splits as carve_module
from rsi_kernel.adapters.swebench_live import tasks as task_module
from rsi_kernel.splits import load_splits

REVISION = "eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3"
DIGEST = "sha256:" + "1" * 64
FORBIDDEN = "FORBIDDEN-SENTINEL-VALUE"
# Columns the adapter must never touch; a read of any of these fails immediately.
FORBIDDEN_COLUMNS = ("patch", "test_patch", "hints_text", "FAIL_TO_PASS", "PASS_TO_PASS",
                     "test_cmd", "log_parser")
_INJECTED = object()  # sentinel: distinguishes "inject the fixture reader" from "use the real one"


class GuardedRow(dict):
    """A fixture row that raises on any forbidden-key access.

    A plain dict would let a mutated adapter read ``row["test_patch"]`` and still
    fail only if the assertion happened to inspect the result. This fails at the
    access itself, whatever the caller does with the value.
    """

    def __getitem__(self, key):
        if key in FORBIDDEN_COLUMNS:
            raise AssertionError(f"forbidden column read: {key}")
        return super().__getitem__(key)

    def get(self, key, default=None):
        if key in FORBIDDEN_COLUMNS:
            raise AssertionError(f"forbidden column read: {key}")
        return super().get(key, default)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _row(**over):
    row = GuardedRow({
        "instance_id": "acme__widget-1",
        "repo": "acme/widget",
        "created_at": "2026-05-10T00:00:00+00:00",
        "docker_image": "registry.example/img:1",
        "rebuild_cmds": ["true"],
        "problem_statement": "The widget breaks.",
    })
    row.update(over)
    return row


def _load(tmp_path, rows, *, lang="java", digest=DIGEST, reader=_INJECTED, hashes=None):
    name = f"data/{lang}-00000-of-00001.parquet"
    path = tmp_path / f"{lang}.parquet"
    path.write_bytes(b"parquet-placeholder-bytes")
    return task_module.load_tasks(
        {name: path},
        hashes if hashes is not None else {name: _sha(path.read_bytes())},
        dataset_revision=REVISION,
        image_digests={row["docker_image"]: digest for row in rows},
        reader=reader if reader is not _INJECTED else (lambda _path, _columns: rows),
    )


def _task(item_id, repo, created_at):
    return task_module.SweTask(
        lang="java", instance_id=item_id, repo=repo, created_at=created_at,
        docker_image="registry.example/img:1", rebuild_cmds=("true",),
        problem_statement_sha256="0" * 64, image_digest=DIGEST,
        dataset_revision=REVISION, parquet_sha256="3" * 64,
    )


def _utc(value):
    return datetime.fromisoformat(value).replace(tzinfo=timezone.utc)


def _grade(results, instance_id, report=None):
    grade = grading_module.score_from_report(instance_id, results, report)
    return grade.score, grade.category, grade.reason


def _results(success=(), failure=(), error=(), incomplete=(), empty=(), submitted=None):
    listed = [*success, *failure, *error, *incomplete, *empty]
    return {
        "submitted": len(submitted if submitted is not None else listed),
        "submitted_ids": list(submitted if submitted is not None else listed),
        "empty_patch": len(empty), "empty_patch_ids": list(empty),
        "success_ids": list(success), "failure_ids": list(failure),
        "error_ids": list(error), "incomplete_ids": list(incomplete),
    }


def _report(instance_id, resolved):
    return {"instance_id": instance_id, "resolved": resolved,
            "PASS_TO_PASS": {"success": [], "failure": []},
            "FAIL_TO_PASS": {"success": [], "failure": []}}


# --- task model and loader -------------------------------------------------


def test_item_id_is_language_scoped(tmp_path):
    (task,) = _load(tmp_path, [_row()])
    assert task.item_id == "java/acme__widget-1"
    assert task.created_at == _utc("2026-05-10T00:00:00")


def test_loader_reads_only_allowlisted_columns(tmp_path):
    seen = []

    def reader(path, columns):
        seen.append(columns)
        # Rows carry forbidden columns; any read of one raises inside the loader.
        return [_row(test_patch=FORBIDDEN, patch=FORBIDDEN, FAIL_TO_PASS=[FORBIDDEN],
                     hints_text=FORBIDDEN, log_parser=FORBIDDEN)]

    (task,) = _load(tmp_path, [_row()], reader=reader)
    assert seen == [task_module.ALLOWED_COLUMNS]
    assert FORBIDDEN not in json.dumps([task.item_id, task.repo, task.identity, repr(task)])


def test_guarded_row_catches_a_forbidden_read():
    # The guard itself must fail: a sentinel that cannot fire proves nothing.
    row = _row(test_patch=FORBIDDEN)
    with pytest.raises(AssertionError, match="test_patch"):
        row["test_patch"]
    with pytest.raises(AssertionError, match="patch"):
        row.get("patch")
    assert row["repo"] == "acme/widget"


def test_pyarrow_reader_requests_exactly_the_six_columns(tmp_path, monkeypatch):
    """The real projection, with pyarrow absent: ParquetFile.read is mocked."""
    import types

    requested = []

    class FakeChannel:
        def __init__(self, values):
            self._values = values

        def to_pylist(self):
            return list(self._values)

    class FakeTable:
        def __init__(self, columns):
            self.columns = [FakeChannel([f"value-of-{name}"]) for name in columns]

    class FakeParquetFile:
        def __init__(self, path):
            self.path = path

        def read(self, columns):
            requested.append(list(columns))
            return FakeTable(columns)

    module = types.ModuleType("pyarrow.parquet")
    module.ParquetFile = FakeParquetFile
    package = types.ModuleType("pyarrow")
    package.parquet = module
    monkeypatch.setitem(sys.modules, "pyarrow", package)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", module)

    rows = task_module._pyarrow_reader(tmp_path / "x.parquet", task_module.ALLOWED_COLUMNS)
    assert requested == [["instance_id", "repo", "created_at", "docker_image",
                          "rebuild_cmds", "problem_statement"]]
    assert len(rows) == 1 and set(rows[0]) == set(task_module.ALLOWED_COLUMNS)


def test_parquet_hash_mismatch_stops_before_parsing(tmp_path):
    calls = []

    def reader(path, columns):
        calls.append(path)
        return []

    with pytest.raises(task_module.SweStop):
        _load(tmp_path, [], reader=reader, hashes={"data/java-00000-of-00001.parquet": "0" * 64})
    assert calls == []


def test_missing_pyarrow_is_a_clear_stop(tmp_path, monkeypatch):
    # reader=None is the default path, so the lazy import is the one that must fail.
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with pytest.raises(task_module.SweStop, match="pyarrow"):
        _load(tmp_path, [_row()], reader=None)


def test_task_identity_binds_problem_statement_and_digest(tmp_path):
    (base,) = _load(tmp_path, [_row()])
    assert base.identity == _load(tmp_path, [_row()])[0].identity
    assert base.identity != _load(tmp_path, [_row(problem_statement="Different text.")])[0].identity
    assert base.identity != _load(tmp_path, [_row()], digest="sha256:" + "9" * 64)[0].identity
    assert base.problem_statement_sha256 == _sha(b"The widget breaks.")


def test_duplicate_instance_ids_are_rejected(tmp_path):
    with pytest.raises(task_module.SweStop):
        _load(tmp_path, [_row(), _row()])


def test_unresolvable_image_digest_is_a_stop(tmp_path):
    name = "data/java-00000-of-00001.parquet"
    path = tmp_path / "java.parquet"
    path.write_bytes(b"x")
    with pytest.raises(task_module.SweStop):
        task_module.load_tasks({name: path}, {name: _sha(b"x")}, dataset_revision=REVISION,
                               image_digests={}, reader=lambda _p, _c: [_row()])


# --- carve -----------------------------------------------------------------


def _carve(tasks, seed=7, fraction=0.5):
    return carve_module.carve(tasks, seed=seed, adjudication_fraction=fraction)


def _mixed_tasks():
    return [
        _task("may-a", "acme/one", _utc("2026-05-03T00:00:00")),
        _task("may-b", "acme/two", _utc("2026-05-04T00:00:00")),
        _task("jun-c", "acme/three", _utc("2026-06-05T00:00:00")),
        _task("jun-d", "acme/four", _utc("2026-06-06T00:00:00")),
        _task("jul-e", "acme/july", _utc("2026-07-07T00:00:00")),
        _task("jul-f", "acme/july", _utc("2026-07-08T00:00:00")),
        _task("may-g", "acme/span", _utc("2026-05-09T00:00:00")),
        _task("jul-h", "acme/span", _utc("2026-07-10T00:00:00")),
    ]


def test_carve_keeps_every_repository_in_one_split():
    tasks = _mixed_tasks()
    by_item = {task.item_id: task.repo for task in tasks}
    carved = _carve(tasks)
    owner = {}
    for name in ("dev", "adjudication", "holdout"):
        for item in getattr(carved, name):
            owner.setdefault(by_item[item], set()).add(name)
    assert all(len(names) == 1 for names in owner.values()), owner


def test_carve_holdout_is_the_july_only_repository():
    carved = _carve(_mixed_tasks())
    assert set(carved.holdout) == {"java/jul-e", "java/jul-f"}
    # A July row of a repository that also has May/June rows is excluded, not held out.
    assert ("java/jul-h", "july_outside_holdout") in carved.excluded
    assert "java/jul-h" not in set(carved.holdout) | set(carved.dev) | set(carved.adjudication)


def test_carve_cutoff_boundary_is_inclusive_at_midnight():
    tasks = [
        _task("edge-in", "acme/in", _utc("2026-05-01T00:00:00")),
        _task("edge-out", "acme/out", _utc("2026-04-30T23:59:59")),
        _task("may", "acme/may", _utc("2026-05-02T00:00:00")),
    ]
    carved = _carve(tasks)
    eligible = set(carved.dev) | set(carved.adjudication)
    assert "java/edge-in" in eligible
    assert ("java/edge-out", "before_cutoff") in carved.excluded
    assert "java/edge-out" not in eligible


def test_carve_excludes_missing_and_unparseable_dates():
    tasks = [
        _task("no-date", "acme/a", None),
        _task("good", "acme/b", _utc("2026-05-02T00:00:00")),
    ]
    carved = _carve(tasks)
    assert ("java/no-date", "unparseable_created_at") in carved.excluded
    assert "java/no-date" not in set(carved.dev) | set(carved.adjudication)


def test_carve_is_deterministic_for_a_frozen_seed():
    tasks = _mixed_tasks()
    first = _carve(tasks, seed=11)
    assert first == _carve(tasks, seed=11)
    # Input order is not part of the frozen identity: the seed alone decides.
    assert first == _carve(list(reversed(tasks)), seed=11)


def test_carve_membership_moves_with_the_seed():
    # Many groups, so an identical fold under every seed is not a coincidence.
    tasks = [_task(f"i{n:02d}", f"acme/r{n:02d}", _utc("2026-06-01T00:00:00")) for n in range(12)]
    folds = {_carve(tasks, seed=seed).adjudication for seed in range(8)}
    assert len(folds) > 1
    assert all(len(fold) == 6 for fold in folds)  # ceil(0.5 * 12)


def test_single_instance_repository_is_not_excluded():
    tasks = [_task("lone", "acme/lone", _utc("2026-06-01T00:00:00")),
             _task("other", "acme/other", _utc("2026-06-02T00:00:00"))]
    carved = _carve(tasks)
    assert not [item for item, _ in carved.excluded if item.startswith("java/lone")]
    assert "java/lone" in set(carved.dev) | set(carved.adjudication)


def test_carve_output_loads_in_the_kernel_split_format():
    carved = _carve(_mixed_tasks())
    splits = load_splits(carved.to_config())
    assert splits.dev_item_ids() == frozenset(carved.dev)
    assert splits.item_ids("holdout") == frozenset(carved.holdout)
    assert carved.to_splits().item_ids("adjudication") == frozenset(carved.adjudication)


def test_selection_and_recorded_cutoff_agree():
    """The recorded cutoff must be the one selection actually used, byte for byte."""
    recorded = _carve(_mixed_tasks()).to_config()["carve"]["cutoff"]
    assert recorded == carve_module.CUTOFF.isoformat()
    # A task one microsecond below the recorded boundary is excluded, and the
    # timestamp just at it is eligible: the record describes the real rule.
    edge = carve_module.CUTOFF
    tasks = [_task("below", "acme/b", edge - timedelta(microseconds=1)),
             _task("at", "acme/a", edge)]
    carved = _carve(tasks)
    assert ("java/below", "before_cutoff") in carved.excluded
    assert "java/at" in set(carved.dev) | set(carved.adjudication)
    assert carved.to_config()["carve"]["cutoff"] == recorded


def test_a_divergent_cutoff_cannot_be_recorded_as_the_fixed_one():
    """Any caller-supplied rule is either refused or recorded faithfully.

    Restoring a ``cutoff`` argument that selects on one timestamp while
    ``to_config()`` still writes ``CUTOFF`` is the exact bug this forbids.
    """
    shifted = carve_module.CUTOFF + timedelta(days=400)
    tasks = [_task("mid", "acme/mid", carve_module.CUTOFF + timedelta(days=1))]
    try:
        carved = carve_module.carve(tasks, seed=7, adjudication_fraction=0.5, cutoff=shifted)
    except TypeError:
        return  # the rule is not configurable at all: nothing can diverge
    assert carved.to_config()["carve"]["cutoff"] == shifted.isoformat()


# --- grading ---------------------------------------------------------------


def test_predictions_are_keyed_by_instance_id():
    preds = grading_module.predictions({"acme__widget-1": "diff --git a b"}, ["acme__widget-1"])
    assert preds == {"acme__widget-1": {"model_patch": "diff --git a b"}}
    assert json.dumps(preds) == '{"acme__widget-1": {"model_patch": "diff --git a b"}}'


@pytest.mark.parametrize("patches,expected", [
    ({}, ["a"]),
    ({"a": "x"}, ["a", "b"]),
    ({"a": "x", "b": "y"}, ["a"]),
    ({"a": 1}, ["a"]),
    ({"a": "x"}, []),
])
def test_predictions_reject_identity_mismatch(patches, expected):
    with pytest.raises(ValueError):
        grading_module.predictions(patches, expected)


def test_resolved_report_scores_one():
    assert _grade(_results(success=["i"]), "i", _report("i", True))[:2] == (1.0, "resolved")


def test_unresolved_report_scores_zero():
    assert _grade(_results(failure=["i"]), "i", _report("i", False))[:2] == (0.0, "unresolved")


def test_empty_submission_is_zero_with_its_category_kept():
    assert _grade(_results(empty=["i"]), "i") == (0.0, "empty_patch", None)


def test_error_and_incomplete_are_unscored():
    assert _grade(_results(error=["i"]), "i") == (None, "error", "harness_error")
    assert _grade(_results(incomplete=["i"]), "i") == (None, "incomplete", "harness_error")


def test_instance_missing_from_the_harness_report_is_unscored():
    assert _grade(_results(), "i") == (None, "missing", "harness_report_missing")
    assert _grade(_results(submitted=["other"]), "i")[2] == "harness_report_missing"


def test_unaccounted_instance_is_unscored():
    assert _grade(_results(submitted=["i"]), "i") == (None, "unaccounted", "harness_error")


@pytest.mark.parametrize("other", ["failure_ids", "error_ids", "incomplete_ids", "empty_patch_ids"])
def test_conflicting_outcome_lists_are_unscored(other):
    # success+error with a resolved report is the trap: first-match would score 1.0.
    results = _results(success=["i"], submitted=["i"])
    results[other] = [*results[other], "i"]
    assert _grade(results, "i", _report("i", True)) == (None, "conflict", "harness_error")


def test_success_plus_error_regression_is_unscored():
    results = _results(success=["i"], error=["i"], submitted=["i"])
    assert _grade(results, "i", _report("i", True)) == (None, "conflict", "harness_error")


def test_report_disagreeing_with_the_summary_is_unscored():
    assert _grade(_results(success=["i"]), "i", _report("i", False))[0] is None
    assert _grade(_results(success=["i"]), "i", _report("other", True))[2] == "harness_error"
    assert _grade(_results(success=["i"]), "i")[2] == "harness_report_missing"


def test_malformed_results_structure_fails_fast():
    with pytest.raises(ValueError):
        _grade({"success_ids": "i"}, "i", _report("i", True))


def test_report_is_read_from_disk_by_instance(tmp_path):
    path = tmp_path / "report.json"
    path.write_text(json.dumps(_report("i", True)))
    assert grading_module.read_report(path, "i")["resolved"] is True
    assert grading_module.read_report(path, "other") is None
    assert grading_module.read_report(tmp_path / "absent.json", "i") is None
    path.write_text("{not json")
    assert grading_module.read_report(path, "i") is None


def test_score_all_and_summary_counts_keep_stop_categories_apart():
    results = _results(success=["a"], failure=["b"], error=["c"], incomplete=["d"], empty=["e"],
                       submitted=["a", "b", "c", "d", "e", "f"])
    reports = {"a": _report("a", True), "b": _report("b", False)}
    grades = grading_module.score_all(["a", "b", "c", "d", "e", "f"], results, reports)
    assert {k: v.score for k, v in grades.items()} == {
        "a": 1.0, "b": 0.0, "c": None, "d": None, "e": 0.0, "f": None}
    assert grading_module.summary_counts(grades.values()) == {
        "empty_patch": 1, "error": 1, "incomplete": 1, "resolved": 1, "unaccounted": 1, "unresolved": 1}


# --- feedback --------------------------------------------------------------


def test_feedback_has_exactly_score_and_correct():
    assert feedback_module.feedback(1.0) == {"score": 1.0, "correct": True}
    assert feedback_module.feedback(0.0) == {"score": 0.0, "correct": False}
    assert feedback_module.feedback(None) == {"score": None, "correct": False}
    assert set(feedback_module.feedback(1.0)) == {"score", "correct"}

def test_proposer_input_drops_everything_outside_the_allowlist():
    rows = [{
        "item_id": "java/acme__widget-1", "run": 0, "score": 1.0,
        "feedback": {"score": 1.0, "correct": True},
        "failure": {"reason": "solver"}, "evidence_dir": "/private/evidence/attempt-1",
        "problem_statement": "ground truth text", "test_patch": "diff --git",
    }]
    assert feedback_module.proposer_input(rows) == [
        {"item_id": "java/acme__widget-1", "score": 1.0, "correct": True}
    ]


def test_proposer_input_rejects_malformed_rows():
    with pytest.raises(ValueError):
        feedback_module.proposer_input([{"score": "high"}])
    with pytest.raises(ValueError):
        feedback_module.proposer_input("not a row list")
