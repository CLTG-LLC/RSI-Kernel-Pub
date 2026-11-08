"""Adopted review regressions: synthetic metadata and files only."""
import hashlib
import importlib
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIGEST = "sha256:" + "d" * 64
IMAGE = "registry.invalid/owner/image:latest"
SIDECAR = {"splits": {"dev": {"item_ids": ["go/demo-1"], "repos": ["owner/image"]}}}


def module(monkeypatch, name):
    monkeypatch.syspath_prepend(str(ROOT / "tools/fd2"))
    return importlib.import_module(name)


def mapping():
    return {"dataset": "SWE-bench-Live/MultiLang", "revision": "eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3",
            "platform": "linux/amd64", "items": [{"item_id": "go/demo-1", "split": "go",
            "instance_id": "demo-1", "docker_image": IMAGE}], "image_digests": {IMAGE: DIGEST}}


def test_frozen_mapping_verifies_bytes_membership_and_pins_every_matrix_item(monkeypatch):
    tool = module(monkeypatch, "image_digests")
    body = json.dumps(mapping()).encode()
    digest = hashlib.sha256(body).hexdigest()
    rows = tool.read_mapping("https://github.com/example/public/releases/download/freeze/images.json",
                             digest, SIDECAR, fetch=lambda _: io.BytesIO(body))
    assert rows == [{"item_id": "go/demo-1", "split": "go", "instance_id": "demo-1",
                     "source_image": IMAGE, "docker_image": "registry.invalid/owner/image@" + DIGEST,
                     "image_mapping_sha256": digest}]
    with pytest.raises(ValueError, match="SHA-256"):
        tool.read_mapping("https://github.com/example/public/releases/download/freeze/images.json",
                          "0" * 64, SIDECAR, fetch=lambda _: io.BytesIO(body))


@pytest.mark.parametrize("change", ["missing", "extra", "malformed", "revision", "platform"])
def test_mapping_rejects_incomplete_or_unfrozen_metadata(monkeypatch, change):
    tool = module(monkeypatch, "image_digests")
    payload = mapping()
    if change == "missing":
        payload["image_digests"] = {}
    elif change == "extra":
        payload["items"].append({**payload["items"][0], "item_id": "go/foreign"})
    elif change == "malformed":
        payload["image_digests"][IMAGE] = "sha256:mutable"
    else:
        payload[change] = "wrong"
    with pytest.raises(ValueError):
        tool.validate_mapping(payload, SIDECAR, "a" * 64)


def test_registry_resolver_only_reads_linux_amd64_manifest_metadata(monkeypatch):
    tool = module(monkeypatch, "image_digests")
    calls = []

    def inspect(argv, **kwargs):
        calls.append(argv)
        return json.dumps({"manifests": [
            {"platform": {"os": "linux", "architecture": "arm64"}, "digest": "sha256:" + "e" * 64},
            {"platform": {"os": "linux", "architecture": "amd64"}, "digest": DIGEST}]})

    assert tool.resolve_digest(IMAGE, inspect=inspect) == DIGEST
    assert len(calls) == 1
    assert calls[0][:4] == ["docker", "buildx", "imagetools", "inspect"]
    assert not any("pull" in call for call in calls)


def test_preparation_rejects_image_repository_or_digest_mismatch_before_evaluation(tmp_path, monkeypatch):
    tool = module(monkeypatch, "prepare_frozen")
    path = tmp_path / "frozen.jsonl"
    path.write_text(json.dumps({"instance_id": "demo-1", "docker_image": "registry.invalid/image@" + DIGEST}) + "\n")
    with pytest.raises(ValueError, match="digest"):
        tool.pin_image(path, "demo-1", "sha256:" + "e" * 64)


def test_publication_scan_decodes_string_values_and_fails_closed(tmp_path):
    from rsi_kernel.publication import scan_json_files
    path = tmp_path / "report.json"
    path.write_text(json.dumps({"safe": True}))
    assert scan_json_files([str(path)]) == [path]
    path.write_text(json.dumps({"nested": ["PL" + "AN § private"]}))
    with pytest.raises(ValueError, match="publication"):
        scan_json_files([str(path)])
    path.write_text("not json")
    with pytest.raises(ValueError):
        scan_json_files([str(path)])
    with pytest.raises(ValueError):
        scan_json_files([str(tmp_path / "missing.json")])


def test_every_artifact_upload_has_an_always_scan_and_success_guard():
    for name in ("fd2-grade", "fd2-gold-validity"):
        workflow = json.loads((ROOT / ".github/workflows" / f"{name}.yml").read_text())
        for job in workflow["jobs"].values():
            steps = job["steps"]
            for n, step in enumerate(steps):
                if step.get("uses", "").startswith("actions/upload-artifact@"):
                    scan = steps[n - 1]
                    assert scan["if"] == "always()"
                    assert "rsi_kernel.publication" in scan["run"]
                    assert f"steps.{scan['id']}.outcome == 'success'" in step["if"]
                    assert all(line.endswith(".json") for line in step["with"]["path"].splitlines())
        assert all(any("receipt" in step.get("run", "") for step in job["steps"])
                   for job in workflow["jobs"].values())
    validity = json.loads((ROOT / ".github/workflows/fd2-gold-validity.yml").read_text())
    assert {"image_digests_url", "image_digests_sha256"} <= set(validity["on"]["workflow_dispatch"]["inputs"])


def test_gold_summary_preserves_per_run_digest_and_timing(monkeypatch):
    tool = module(monkeypatch, "gold_validity")
    row = {"run": 1, "executed": True, "command_status": 0, "resolved": True,
           "image_digests": ["registry.invalid/image@" + DIGEST], "wall_seconds": 12,
           "started_at": "2026-11-08T00:00:00Z", "completed_at": "2026-11-08T00:00:12Z"}
    summary = tool.summarize("go/demo-1", [row])
    for key in ("image_digests", "wall_seconds", "started_at", "completed_at"):
        assert summary["runs"][0][key] == row[key]


def test_aggregation_preserves_receipts_groups_builds_and_authoritative_timestamps(tmp_path, monkeypatch):
    tool = module(monkeypatch, "gold_validity")
    path = tmp_path / "fd2-gold-validity-demo-1"
    path.mkdir()
    (path / "summary.json").write_text(json.dumps(tool.summarize("go/demo-1", [
        {"run": n, "command_status": 0, "resolved": True} for n in (1, 2, 3)])))
    receipt = {"item_id": "go/demo-1", "runner_image_build": {"ImageOS": "ubuntu26", "ImageVersion": "build-1"},
               "workflow_commit": "a" * 40, "run_id": "42", "evaluator_identity": {"frozen": True}}
    (path / "runner.json").write_text(json.dumps(receipt))
    jobs = [{"name": "gold-validity (go/demo-1)", "created_at": "queue", "started_at": "start",
             "completed_at": "end", "status": "completed", "conclusion": "success"}]
    result = tool.aggregate(SIDECAR, tmp_path, jobs=jobs)
    assert result["instances"][0]["receipt"] == receipt
    assert result["by_runner_build"][0]["item_ids"] == ["go/demo-1"]
    assert result["job_timestamps"] == jobs


def test_aggregation_groups_same_image_despite_per_machine_metadata(tmp_path, monkeypatch):
    tool = module(monkeypatch, "gold_validity")
    item_ids = ["go/demo-1", "go/demo-2"]
    sidecar = {"splits": {"dev": {"item_ids": item_ids, "repos": ["owner/image"]}}}
    build = {"ImageOS": "ubuntu26", "ImageVersion": "build-1"}
    receipts = []
    for item_id in item_ids:
        path = tmp_path / f"fd2-gold-validity-{item_id.split('/', 1)[1]}"
        path.mkdir()
        (path / "summary.json").write_text(json.dumps(tool.summarize(item_id, [
            {"run": n, "command_status": 0, "resolved": True} for n in (1, 2, 3)])))
        receipt = {"item_id": item_id, "runner_image_build": {**build, "Worker ID": item_id},
                   "workflow_commit": "a" * 40, "run_id": "42", "evaluator_identity": {"frozen": True}}
        (path / "runner.json").write_text(json.dumps(receipt))
        receipts.append(receipt)
    result = tool.aggregate(sidecar, tmp_path)
    assert len(result["by_runner_build"]) == 1
    assert result["by_runner_build"][0]["item_ids"] == item_ids
    assert result["by_runner_build"][0]["runner_image_build"] == build
    assert [row["receipt"] for row in result["instances"]] == receipts


@pytest.mark.parametrize("field", ["displayTitle", "headSha"])
def test_dispatch_response_run_is_validated_without_a_run_search(tmp_path, monkeypatch, field):
    from test_fd2_remote import make_grader
    grader, fake, invoke = make_grader(tmp_path)
    original = fake.run
    fake.run = lambda: {**original(), field: "foreign"}
    assert invoke() is None
    assert grader.failure["reason"] == "binding_mismatch"
    assert not any(call[1:3] in (["run", "list"], ["run", "download"]) for call in fake.calls)
    # The dispatch-returned run is owned even when it ran the wrong commit: cancel exactly it.
    cancels = [call for call in fake.calls if call[1:3] == ["run", "cancel"]]
    assert [call[3] for call in cancels] == ["42"]
    assert sum(call[1:3] == ["workflow", "run"] for call in fake.calls) == 1


def test_new_runner_build_is_accepted_and_preserved_not_compared(tmp_path):
    from test_fd2_remote import make_grader
    grader, fake, invoke = make_grader(tmp_path)
    original = fake.__call__

    def runner(argv, *, timeout):
        result = original(argv, timeout=timeout)
        if argv[1:3] == ["run", "download"]:
            path = Path(argv[argv.index("--dir") + 1]) / "binding.json"
            binding = json.loads(path.read_text())
            binding["runner_image_build"] = {"ImageOS": "ubuntu26", "ImageVersion": "new-build"}
            path.write_text(json.dumps(binding))
        return result

    grader.runner = runner
    assert invoke() is not None
    assert json.loads((tmp_path / "output/receipt.json").read_text())["runner_image_build"]["ImageVersion"] == "new-build"


@pytest.mark.parametrize("platform", [("linux", "amd64"), ("linux", "arm64")])
def test_single_manifest_resolution_checks_pinned_configuration(monkeypatch, platform):
    tool = module(monkeypatch, "image_digests")
    calls = []

    def inspect(argv, **kwargs):
        calls.append(argv)
        return json.dumps({"digest": DIGEST} if len(calls) == 1 else
                          {"os": platform[0], "architecture": platform[1]})

    if platform[1] == "amd64":
        assert tool.resolve_digest(IMAGE, inspect=inspect) == DIGEST
    else:
        with pytest.raises(ValueError, match="linux/amd64"):
            tool.resolve_digest(IMAGE, inspect=inspect)
    assert calls[1][4] == "registry.invalid/owner/image@" + DIGEST


def test_mapping_generator_uses_metadata_and_does_not_pull_or_evaluate(tmp_path, monkeypatch):
    tool = module(monkeypatch, "image_digests")
    metadata = module(monkeypatch, "select_smoke")
    monkeypatch.setattr(metadata, "load_tables", lambda: {"go": [{"instance_id": "demo-1", "docker_image": IMAGE}]})
    seen = []
    monkeypatch.setattr(tool, "resolve_digest", lambda image: seen.append(image) or DIGEST)
    sidecar = tmp_path / "items.json"
    sidecar.write_text(json.dumps(SIDECAR))
    output = tmp_path / "images.json"
    monkeypatch.setattr(sys, "argv", ["image_digests.py", "--sidecar", str(sidecar), "--output", str(output)])
    tool.main()
    assert seen == [IMAGE]
    assert json.loads(output.read_text()) == mapping()
    with pytest.raises(FileExistsError):
        tool.main()


def test_runner_reads_actual_provisioner_from_runner_setup_metadata(tmp_path, monkeypatch):
    from types import SimpleNamespace
    tool = module(monkeypatch, "remote_grade")
    binary = tmp_path / "runner/bin/Runner.Listener"
    binary.parent.mkdir(parents=True)
    binary.touch()
    (binary.parent.parent / ".setup_info").write_text(json.dumps([
        {"Group": "Runner Image Provisioner", "Detail": "2.0.synthetic"}]))
    proc = tmp_path / "exe"
    proc.symlink_to(binary)
    monkeypatch.setattr(tool, "Path", lambda _: SimpleNamespace(glob=lambda _: [proc]))
    monkeypatch.setenv("ImageOS", "ubuntu26")
    monkeypatch.setenv("ImageVersion", "actual-build")
    monkeypatch.delenv("ImageProvisionerVersion", raising=False)
    assert tool.runner_image_build() == {"ImageOS": "ubuntu26", "ImageVersion": "actual-build",
                                         "ImageProvisionerVersion": "2.0.synthetic"}


def test_receipt_binds_identity_item_workflow_mapping_and_actual_build(monkeypatch):
    tool = module(monkeypatch, "gold_validity")
    monkeypatch.setenv("ImageOS", "ubuntu26")
    monkeypatch.setenv("ImageVersion", "actual-build")
    monkeypatch.setenv("ImageProvisionerVersion", "synthetic-provisioner")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)
    monkeypatch.setenv("GITHUB_RUN_ID", "42")
    image = "registry.invalid/owner/image@" + DIGEST
    record = tool.receipt("go/demo-1", image, "b" * 64)
    assert record["evaluator_identity"]["image"] == image
    assert record["workflow_commit"] == "a" * 40
    assert record["run_id"] == "42" and record["item_id"] == "go/demo-1"
    assert record["image_mapping_sha256"] == "b" * 64
    assert record["runner_image_build"]["ImageVersion"] == "actual-build"


def test_authoritative_timestamp_extraction_keeps_all_pages_without_logs(tmp_path, monkeypatch):
    tool = module(monkeypatch, "gold_validity")
    path = tmp_path / "jobs.json"
    job = {"id": 1, "name": "gold-validity / go/demo-1", "created_at": "queue", "started_at": "start",
           "completed_at": "end", "status": "completed", "conclusion": "success", "private_log": "do not copy"}
    path.write_text(json.dumps([{"jobs": [job]}, {"jobs": [{**job, "id": 2}]}]))
    result = tool.job_timestamps(path)
    assert [row["id"] for row in result] == [1, 2]
    assert result[0]["created_at"] == "queue" and result[0]["completed_at"] == "end"
    assert "private_log" not in result[0]


@pytest.mark.parametrize("selected", ["registry.invalid/other@" + DIGEST,
                                      "registry.invalid/owner/image@sha256:" + "e" * 64])
def test_prepared_rows_reject_frozen_repository_and_digest_mismatch(tmp_path, monkeypatch, selected):
    tool = module(monkeypatch, "prepare_frozen")
    source = tmp_path / "synthetic.parquet"
    source.write_bytes(b"synthetic")
    item = {"instance_id": "demo-1", "docker_image": selected}
    with pytest.raises(ValueError, match="mismatch"):
        tool.write_selected_jsonl({"data": source}, {"data": hashlib.sha256(source.read_bytes()).hexdigest()},
                                  [item], tmp_path / "output.jsonl", lambda _: [
                                      {"instance_id": "demo-1", "docker_image": "registry.invalid/owner/image@" + DIGEST}])
    assert not (tmp_path / "output.jsonl").exists()


def test_transport_diagnostic_keeps_explanation_and_redacts_credentials():
    import subprocess
    from rsi_kernel.adapters.swebench_live import remote
    error = subprocess.CalledProcessError(
        1, ["gh", "workflow", "run"],
        stderr="HTTP 403: synthetic dispatch refusal token=ghp_" + "a" * 36
               + " https://user:pass@example.invalid/x")
    record = remote._diagnostic(error)
    assert record["returncode"] == 1
    assert "HTTP 403: synthetic dispatch refusal" in record["stderr"]
    assert "ghp_" + "a" * 36 not in record["stderr"] and "user:pass" not in record["stderr"]
    assert "argv" not in record and "cmd" not in record
