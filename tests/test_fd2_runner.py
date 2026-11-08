"""Runner boundary tests use synthetic payloads, never benchmark row contents."""

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_runner(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools/fd2"))
    spec = importlib.util.spec_from_file_location("remote_grade", ROOT / "tools/fd2/remote_grade.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_runner_checks_digest_before_decoding_and_never_accepts_another_request(monkeypatch):
    module = load_runner(monkeypatch)
    payload = json.dumps({"binding": {"request_id": "request-1"}, "predictions": {}}).encode()
    url = "https://github.com/example/public/releases/download/payload/request-1.json"
    digest = hashlib.sha256(payload).hexdigest()
    fetch = lambda _: io.BytesIO(payload)
    assert module.read_payload(url, digest, "request-1", "example/public", fetch=fetch)["predictions"] == {}
    with pytest.raises(ValueError, match="SHA-256"):
        module.read_payload(url, "0" * 64, "request-1", "example/public", fetch=fetch)
    with pytest.raises(ValueError, match="identity"):
        module.read_payload(url, digest, "request-2", "example/public", fetch=fetch)


@pytest.mark.parametrize("url", [
    "https://example.invalid/payload", "http://github.com/example/public/releases/download/x/payload.json",
    "https://github.com/foreign/repo/releases/download/x/payload.json",
    "https://github.com@example.invalid/example/public/releases/download/x/payload.json",
    "https://github.com/example/public/releases/download/x/payload.json?secret=value",
])
def test_runner_rejects_non_mirror_transport_without_fetch(monkeypatch, url):
    module = load_runner(monkeypatch)

    def fetch(_):
        pytest.fail("unsafe URL was fetched")

    with pytest.raises(ValueError):
        module.read_payload(url, "0" * 64, "request-1", "example/public", fetch=fetch)


def test_runner_marker_guard_checks_decoded_json_strings(monkeypatch):
    module = load_runner(monkeypatch)
    payload = json.dumps({"binding": {"request_id": "request-1"}, "predictions": {"patch": "PL" + "AN § private"}}).encode()
    with pytest.raises(ValueError, match="marker"):
        module.read_payload("https://github.com/example/public/releases/download/x/payload.json",
                            hashlib.sha256(payload).hexdigest(), "request-1", "example/public",
                            fetch=lambda _: io.BytesIO(payload))


def test_aggregate_keeps_missing_jobs_incomplete_and_reports_survivor_counts(tmp_path, monkeypatch):
    runner = load_runner(monkeypatch)
    from gold_validity import aggregate, summarize
    sidecar = {"splits": {"dev": {"item_ids": ["go/owner__repo-1", "go/owner__repo-2"], "repos": ["owner/repo"]}}}
    path = tmp_path / "fd2-gold-validity-owner__repo-1"
    path.mkdir()
    rows = [{"run": n, "resolved": True, "command_status": 0, "reason": None} for n in (1, 2, 3)]
    (path / "summary.json").write_text(json.dumps(summarize("go/owner__repo-1", rows)))
    (path / "runner.json").write_text(json.dumps({"item_id": "go/owner__repo-1", "workflow_commit": "frozen",
        "run_id": "42", "evaluator_identity": {"frozen": True}, "runner_image_build": {"ImageVersion": "actual"}}))
    summary = aggregate(sidecar, tmp_path)
    assert summary["validation_incomplete"]
    assert summary["surviving_instances"] == summary["surviving_repositories"] == summary["surviving_languages"] == 1
    assert len(summary["instances"]) == 2
    assert all(row["status"] == "unexecuted" for row in summary["instances"][1]["runs"])
    identity = runner.evaluator_identity("synthetic@sha256:" + "a" * 64)
    assert identity["harness"] == runner.HARNESS
    assert identity["files_sha256"]["tools/fd2/harness-requirements.lock"] == hashlib.sha256(
        (ROOT / "tools/fd2/harness-requirements.lock").read_bytes()).hexdigest()


def test_active_attempt_without_a_completed_record_is_aborted_not_unexecuted(tmp_path):
    source = tmp_path / "raw"
    source.mkdir()
    (source / "active-run.json").write_text(json.dumps({"instance_id": "demo-1", "split": "go", "run": 1, "executed": True}))
    result = subprocess.run([sys.executable, str(ROOT / "tools/fd2/gold_validity.py"), "summary", "--item-id", "go/demo-1",
                             "--sidecar", str(ROOT / "docs/prereg-fd2-items.json"),
                             "--input", str(source / "summary.json")], check=True, capture_output=True, text=True)
    summary = json.loads(result.stdout)
    assert [row["status"] for row in summary["runs"]] == ["aborted", "unexecuted", "unexecuted"]
    assert summary["runs"][0]["reason"] == "silent_termination"
    assert summary["validation_incomplete"]


def test_runner_reuses_harness_command_with_zero_based_run_and_uploadable_binding(tmp_path, monkeypatch):
    from types import ModuleType, SimpleNamespace
    module = load_runner(monkeypatch)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/prereg-fd2-items.json").write_text(json.dumps({"splits": {"dev": {
        "item_ids": ["go/owner__repo-1"], "repos": ["owner/repo"]}}}))
    (tmp_path / "SWE-bench-Live/launch").mkdir(parents=True)
    source = tmp_path / "dataset/data/go.parquet"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"synthetic parquet")
    monkeypatch.setattr(module, "EXPECTED_SHA256", {"data/go.parquet": hashlib.sha256(source.read_bytes()).hexdigest()})
    fake_arrow = ModuleType("pyarrow")
    fake_parquet = ModuleType("pyarrow.parquet")
    fake_parquet.read_table = lambda _: SimpleNamespace(to_pylist=lambda: [
        {"instance_id": "owner__repo-1", "docker_image": "example.invalid/image:latest"}])
    monkeypatch.setitem(sys.modules, "pyarrow", fake_arrow)
    monkeypatch.setitem(sys.modules, "pyarrow.parquet", fake_parquet)
    image = "example.invalid/image@sha256:" + "a" * 64
    payload = {"binding": {"request_id": "request-1", "instance_id": "owner__repo-1", "split": "go", "run": 0,
                           "image": image}, "predictions": {"owner__repo-1": {"model_patch": "synthetic"}},
               "workflow_commit": "frozen", "evaluator_identity": {"frozen": True}}
    monkeypatch.setattr(module, "read_payload", lambda *args: payload)
    monkeypatch.setattr(module, "evaluator_identity", lambda image: {"frozen": True})
    monkeypatch.setattr(module, "runner_image_build", lambda: {"frozen": True})
    for key, value in {"PREDICTION_SHA256": "d" * 64, "REQUEST_ID": "request-1", "PAYLOAD_URL": "unused",
                       "GITHUB_REPOSITORY": "example/public", "GITHUB_SHA": "frozen", "GITHUB_RUN_ID": "42"}.items():
        monkeypatch.setenv(key, value)

    def check_output(argv, **kwargs):
        if argv[0] == "git":
            return module.LAUNCH if argv[2].endswith("launch") else module.HARNESS
        if argv[0] == "hf":
            return str(source.parents[1])
        return "unix:///synthetic.sock"

    commands = []

    def run(argv, **kwargs):
        commands.append(argv)
        if argv[0] == "docker":
            return subprocess.CompletedProcess(argv, 0)
        output = tmp_path / "grade-output"
        assert argv[1:] == ["-m", "evaluation.evaluation", "--dataset", str(output / "frozen.jsonl"),
                            "--split", "go", "--platform", "linux", "--patch_dir", str(output / "predictions.json"),
                            "--output_dir", str(output), "--workers", "1", "--overwrite", "0",
                            "--instance_ids", "owner__repo-1"]
        assert kwargs["env"]["DOCKER_HOST"] == "unix:///synthetic.sock"
        (output / "results.json").write_text("{}")
        (output / "owner__repo-1").mkdir()
        (output / "owner__repo-1/report.json").write_text(json.dumps({"instance_id": "owner__repo-1", "resolved": True}))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(module.subprocess, "check_output", check_output)
    monkeypatch.setattr(module.subprocess, "run", run)
    module.main()
    binding = json.loads((tmp_path / "grade-output/binding.json").read_text())
    assert binding == {**payload["binding"], "prediction_sha256": "d" * 64, "workflow_commit": "frozen", "run_id": 42,
                       "evaluator_identity": {"frozen": True}, "runner_image_build": {"frozen": True}}
    assert len(commands) == 2


def test_partial_run_journal_survives_a_missing_final_smoke_summary(tmp_path):
    source = tmp_path / "raw"
    source.mkdir()
    (source / "runs.ndjson").write_text(json.dumps({"instance_id": "demo-1", "split": "go", "run": 1,
                                                   "executed": True, "command_status": 0, "resolved": True}) + "\n")
    (source / "active-run.json").write_text(json.dumps({"instance_id": "demo-1", "split": "go", "run": 2, "executed": True}))
    result = subprocess.run([sys.executable, str(ROOT / "tools/fd2/gold_validity.py"), "summary", "--item-id", "go/demo-1",
                             "--sidecar", str(ROOT / "docs/prereg-fd2-items.json"),
                             "--input", str(source / "summary.json")], check=True, capture_output=True, text=True)
    assert [row["status"] for row in json.loads(result.stdout)["runs"]] == ["completed", "aborted", "unexecuted"]


@pytest.mark.parametrize("mode", ["matrix", "select", "summary", "receipt", "aggregate"])
def test_validity_cli_modes_write_content_free_outputs(tmp_path, monkeypatch, mode):
    load_runner(monkeypatch)
    import gold_validity
    import select_smoke
    import image_digests
    monkeypatch.setenv("ImageOS", "synthetic-os")
    monkeypatch.setenv("ImageVersion", "synthetic-build")
    monkeypatch.setenv("ImageProvisionerVersion", "synthetic-provisioner")
    item_id = "go/owner__repo-1"
    sidecar = tmp_path / "items.json"
    sidecar.write_text(json.dumps({"splits": {"dev": {"item_ids": [item_id], "repos": ["owner/repo"]}}}))
    rows = [{"run": n, "resolved": True, "command_status": 0} for n in (1, 2, 3)]
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps({"instances": [{"runs": rows}]}))
    artifacts = tmp_path / "artifacts/fd2-gold-validity-owner__repo-1"
    artifacts.mkdir(parents=True)
    (artifacts / "summary.json").write_text(json.dumps(gold_validity.summarize(item_id, rows)))
    monkeypatch.setattr(select_smoke, "load_tables", lambda: {"go": [
        {"instance_id": "owner__repo-1", "docker_image": "synthetic/image:latest"}]})
    (artifacts / "runner.json").write_text(json.dumps({"item_id": item_id, "workflow_commit": "frozen",
        "run_id": "42", "evaluator_identity": {"frozen": True}, "runner_image_build": {"ImageVersion": "actual"}}))
    monkeypatch.setattr(image_digests, "read_mapping", lambda *args: [{"item_id": item_id}])
    output = tmp_path / "output.json"
    monkeypatch.setattr(sys, "argv", ["gold_validity.py", mode, "--sidecar", str(sidecar), "--item-id", item_id,
                                    "--input", str(artifacts.parent if mode == "aggregate" else raw),
                                    "--output", str(output), "--image", "synthetic/image@sha256:" + "a" * 64,
                                    "--source-image", "synthetic/image:latest"])
    gold_validity.main()
    result = json.loads(output.read_text())
    assert result
    if mode == "select":
        assert result["instances"][0]["item_id"] == item_id
    if mode == "aggregate":
        assert not result["validation_incomplete"] and result["surviving_instances"] == 1
    assert not {"patch", "test_patch", "problem_statement"}.intersection(result)


def test_missing_jobs_write_aggregate_and_fail_the_completion_gate(tmp_path, monkeypatch):
    load_runner(monkeypatch)
    import gold_validity
    sidecar = tmp_path / "items.json"
    sidecar.write_text(json.dumps({"splits": {"dev": {"item_ids": ["go/owner__repo-1"], "repos": ["owner/repo"]}}}))
    output = tmp_path / "output.json"
    monkeypatch.setattr(sys, "argv", ["gold_validity.py", "aggregate", "--sidecar", str(sidecar),
                                    "--input", str(tmp_path / "missing"), "--output", str(output)])
    with pytest.raises(SystemExit, match="incomplete"):
        gold_validity.main()
    assert json.loads(output.read_text())["validation_incomplete"]


def test_runner_build_records_observed_image_versions(monkeypatch):
    module = load_runner(monkeypatch)
    monkeypatch.setenv("ImageOS", "synthetic-os")
    monkeypatch.setenv("ImageVersion", "synthetic-build")
    monkeypatch.delenv("ImageProvisionerVersion", raising=False)
    with pytest.raises(ValueError, match="provisioner metadata missing"):
        module.runner_image_build()
    monkeypatch.setenv("ImageProvisionerVersion", "synthetic-provisioner")
    assert module.runner_image_build()["ImageProvisionerVersion"] == "synthetic-provisioner"
