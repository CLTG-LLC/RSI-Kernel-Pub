"""No network, Docker, model, or Actions dispatch: the transport is a fake gh."""

import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "a" * 40
IMAGE = "example.invalid/instance@sha256:" + "b" * 64
BUILD = {"ImageOS": "ubuntu26", "ImageVersion": "20261101.186.1"}
IDENTITY = {"harness": "frozen", "lock": "c" * 64}


class Clock:
    now = 0

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class FakeGh:
    def __init__(self, mode="happy"):
        self.mode = mode
        self.calls = []
        self.payload = None
        self.request = None

    def __call__(self, argv, *, timeout):
        assert timeout > 0
        self.calls.append(argv)
        command = argv[1:3]
        if command == ["release", "upload"]:
            self.payload = Path(argv[4])
            self.request = json.loads(self.payload.read_text())
        if command == ["workflow", "run"] and self.mode == "dispatch_failure":
            raise subprocess.CalledProcessError(1, argv)
        if command == ["workflow", "run"]:
            return "" if self.mode == "no_run" else "https://github.com/example/public/actions/runs/42\n"
        if command == ["run", "list"]:
            runs = [] if self.mode == "no_run" else [self.run()]
            # A concurrent foreign run must never be selected or cancelled.
            return json.dumps([{"databaseId": 99, "displayTitle": "foreign", "headSha": COMMIT}] + runs)
        if command == ["run", "view"]:
            if self.mode == "disappeared":
                raise subprocess.CalledProcessError(1, argv)
            return json.dumps(self.run())
        if command == ["run", "download"]:
            if self.mode == "missing_artifact":
                raise subprocess.CalledProcessError(1, argv)
            output = Path(argv[argv.index("--dir") + 1])
            output.mkdir(parents=True, exist_ok=True)
            binding = {**self.request["binding"], "prediction_sha256": hashlib.sha256(self.payload.read_bytes()).hexdigest(),
                       "workflow_commit": COMMIT, "run_id": 42, "runner_image_build": BUILD,
                       "evaluator_identity": IDENTITY}
            if self.mode.startswith("mismatch:"):
                binding[self.mode.split(":")[1]] = "wrong"
            (output / "binding.json").write_text(json.dumps(binding))
            if self.mode != "silent_termination":
                (output / "results.json").write_text(json.dumps({
                    "submitted": 1, "submitted_ids": ["demo-1"], "success_ids": ["demo-1"],
                    "failure_ids": [], "empty_patch_ids": [], "error_ids": [], "incomplete_ids": [],
                }))
                (output / "demo-1").mkdir()
                (output / "demo-1/report.json").write_text(json.dumps({"instance_id": "demo-1", "resolved": True}))
        return ""

    def run(self):
        state = {"queue_expiry": ("queued", None), "timeout": ("in_progress", None),
                 "cancellation": ("completed", "cancelled"), "job_timeout": ("completed", "timed_out"),
                 "failed_job": ("completed", "failure")}.get(self.mode, ("completed", "success"))
        return {"databaseId": 42, "displayTitle": self.request["binding"]["request_id"],
                "headSha": COMMIT, "status": state[0], "conclusion": state[1]}


def make_grader(tmp_path, mode="happy", **overrides):
    from rsi_kernel.adapters.swebench_live.remote import RemoteGrader
    fake, clock = FakeGh(mode), Clock()
    options = dict(repository="example/public", release_tag="predictions", workflow_ref="main",
                   workflow_commit=COMMIT, evaluator_identity=IDENTITY,
                   deadline=10, runner=fake, clock=clock, sleep=clock.sleep)
    options.update(overrides)
    grader = RemoteGrader(**options)
    prediction = tmp_path / "predictions.json"
    prediction.write_text(json.dumps({"demo-1": {"model_patch": "synthetic patch"}}))
    task = SimpleNamespace(instance_id="demo-1", lang="go", image_digest="sha256:" + "b" * 64)
    return grader, fake, lambda: grader(task, prediction, tmp_path / "output", run=2,
                                      image=IMAGE, container_name="owned-grade")


def test_remote_happy_path_uses_existing_parser_and_exact_owned_run(tmp_path, monkeypatch):
    from rsi_kernel.adapters.swebench_live import grading
    called = []
    original = grading.score_from_report

    def parser(*args):
        called.append(args)
        return original(*args)

    monkeypatch.setattr(grading, "score_from_report", parser)
    grader, fake, invoke = make_grader(tmp_path)
    result = invoke()
    assert result[1] == {"instance_id": "demo-1", "resolved": True}
    assert called and called[0][0] == "demo-1"
    assert grader.failure is None
    assert not any(call[1:3] == ["run", "list"] for call in fake.calls)
    assert "runner_image_build" not in fake.request
    receipt = json.loads((tmp_path / "output/receipt.json").read_text())
    assert receipt["runner_image_build"] == BUILD
    assert sum(call[1:3] == ["workflow", "run"] for call in fake.calls) == 1
    assert not any(call[1:3] == ["run", "cancel"] for call in fake.calls)
    assert fake.request["binding"]["instance_id"] == "demo-1"
    assert fake.request["binding"]["run"] == 2
    dispatch = next(call for call in fake.calls if call[1:3] == ["workflow", "run"])
    assert any("payload_url=https://github.com/example/public/releases/download/" in arg for arg in dispatch)


@pytest.mark.parametrize("mode,reason", [
    ("dispatch_failure", "dispatch_failure"), ("no_run", "dispatch_failure"),
    ("queue_expiry", "queue_expiry"), ("cancellation", "cancellation"),
    ("timeout", "timeout"), ("job_timeout", "timeout"),
    ("missing_artifact", "missing_artifact"), ("silent_termination", "silent_termination"),
    ("failed_job", "silent_termination"), ("disappeared", "silent_termination"),
])
def test_remote_failure_is_none_with_distinct_reason_and_never_redispatches(tmp_path, mode, reason):
    grader, fake, invoke = make_grader(tmp_path, mode)
    assert invoke() is None
    assert grader.failure["reason"] == reason
    assert json.loads((tmp_path / "output/failure.json").read_text())["failure"]["reason"] == reason
    assert sum(call[1:3] == ["workflow", "run"] for call in fake.calls) == 1
    cancels = [call for call in fake.calls if call[1:3] == ["run", "cancel"]]
    assert all(call[3] == "42" for call in cancels)
    if mode in {"timeout", "queue_expiry"}:
        assert len(cancels) == 1
    if mode in {"no_run", "dispatch_failure"}:
        assert not cancels


@pytest.mark.parametrize("field", ["request_id", "prediction_sha256", "workflow_commit", "run_id",
                                    "instance_id", "run", "image", "evaluator_identity"])
def test_every_binding_mismatch_is_rejected(tmp_path, field):
    grader, _, invoke = make_grader(tmp_path, "mismatch:" + field)
    assert invoke() is None
    assert grader.failure["reason"] == "binding_mismatch"


@pytest.mark.parametrize("deadline", [None, 0, -1, float("inf"), True])
def test_remote_requires_explicit_positive_finite_deadline(tmp_path, deadline):
    with pytest.raises((TypeError, ValueError)):
        make_grader(tmp_path, deadline=deadline)


def test_payload_marker_guard_precedes_upload(tmp_path):
    grader, fake, invoke = make_grader(tmp_path)
    (tmp_path / "predictions.json").write_text(json.dumps({"demo-1": {"model_patch": "/" + "Users/private"}}))
    assert invoke() is None
    assert grader.failure["reason"] == "publication_marker"
    assert not fake.calls


def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools/fd2" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_matrix_is_exactly_the_222_included_sidecar_items():
    expected = json.loads((ROOT / "docs/prereg-fd2-items.json").read_text())
    ids = [item for split in expected["splits"].values() for item in split["item_ids"]]
    matrix = tool("gold_validity").matrix(expected)
    assert len(matrix) == len(ids) == 222
    assert len(matrix) < 256
    assert {row["item_id"] for row in matrix} == set(ids)
    assert all(row["item_id"] == row["split"] + "/" + row["instance_id"] for row in matrix)


def test_validity_distinguishes_completed_aborted_and_unexecuted():
    summary = tool("gold_validity").summarize("go/demo-1", [
        {"run": 1, "resolved": False, "command_status": 0, "reason": None},
        {"run": 2, "resolved": False, "command_status": 137, "reason": "low_disk"},
        {"run": 3, "resolved": False, "command_status": 137, "reason": "low_disk", "executed": False},
    ])
    assert [row["status"] for row in summary["runs"]] == ["completed", "aborted", "unexecuted"]
    assert not summary["valid"]
    missing = tool("gold_validity").summarize("go/demo-1", [])
    assert all(row["status"] == "unexecuted" for row in missing["runs"])
    assert missing["validation_incomplete"]


def test_workflows_are_parseable_yaml_and_reuse_the_locked_setup():
    # JSON is a YAML 1.2 subset; use stdlib parsing, not a new project dependency.
    # https://yaml.org/spec/1.2.2/#10212-json-schema
    for name in ("fd2-grade", "fd2-gold-validity"):
        workflow = json.loads((ROOT / ".github/workflows" / f"{name}.yml").read_text())
        assert "workflow_dispatch" in workflow["on"]
        assert all(job["runs-on"] == "ubuntu-26.04" for job in workflow["jobs"].values())
    validity = json.loads((ROOT / ".github/workflows/fd2-gold-validity.yml").read_text())
    job = validity["jobs"]["gold-validity"]
    assert job["strategy"]["fail-fast"] is False
    assert job["strategy"]["max-parallel"] == 20
    assert "aggregate" in validity["jobs"]
    assert "gold_smoke.sh" in json.dumps(job)
    setup = (ROOT / ".github/actions/fd2-setup/action.yml").read_text()
    assert "--require-hashes" in setup and "--no-deps" in setup
    assert "--no-build-isolation" in setup
    assert "containerd-snapshotter" in setup
    lock = (ROOT / "tools/fd2/harness-requirements.lock").read_text()
    assert "--hash=sha256:" in lock
    grade = json.loads((ROOT / ".github/workflows/fd2-grade.yml").read_text())
    assert set(grade["on"]["workflow_dispatch"]["inputs"]) == {"payload_url", "sha256", "request_id"}
    assert grade["run-name"] == "${{ inputs.request_id }}"


@pytest.mark.parametrize("resolved", [(False, False, False), (True, False, False),
                                      (True, True, False), (True, True, True)])
def test_gold_validity_requires_three_completed_successes(resolved):
    summary = tool("gold_validity").summarize("go/demo-1", [
        {"run": n, "resolved": result, "command_status": 0, "executed": True}
        for n, result in enumerate(resolved, 1)])
    assert summary["valid"] is all(resolved)
    assert not summary["validation_incomplete"]


def test_deadline_expiring_during_report_parse_is_none(tmp_path, monkeypatch):
    from rsi_kernel.adapters.swebench_live import grading
    grader, _, invoke = make_grader(tmp_path)
    original = grading.score_from_report

    def parse(*args):
        result = original(*args)
        grader.clock.now = grader._expires
        return result

    monkeypatch.setattr(grading, "score_from_report", parse)
    assert invoke() is None
    assert grader.failure["reason"] == "timeout"


def test_failure_records_conclusion_and_cancellation_outcome_privately(tmp_path):
    grader, _, invoke = make_grader(tmp_path, "failed_job")
    assert invoke() is None
    failure = json.loads((tmp_path / "output/failure.json").read_text())["failure"]
    assert failure["workflow_conclusion"] == "failure"
    grader, fake, invoke = make_grader(tmp_path, "timeout")
    original = fake.__call__

    def runner(argv, *, timeout):
        if argv[1:3] == ["run", "cancel"]:
            raise subprocess.CalledProcessError(23, ["never", "persist", "argv"])
        return original(argv, timeout=timeout)

    grader.runner = runner
    assert invoke() is None
    failure = json.loads((tmp_path / "output/failure.json").read_text())["failure"]
    assert failure["cancellation"]["outcome"] == "failed"
    assert failure["cancellation"]["diagnostic"]["returncode"] == 23
    assert "argv" not in json.dumps(failure)
