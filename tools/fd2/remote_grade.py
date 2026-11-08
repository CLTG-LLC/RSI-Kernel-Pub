"""Digest-bound runner entry point. Uses HarnessGrader, never a second grader."""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
from urllib.request import urlopen

from rsi_kernel.adapters.gdpevo.solver_docker import _DOCKER_ENV
from rsi_kernel.adapters.swebench_live.solver import HarnessGrader
from rsi_kernel.publication import PATTERN
from gold_validity import matrix
from prepare_frozen import EXPECTED_SHA256, image_repository, pin_image, write_selected_jsonl
from select_smoke import DATASET, REVISION

ROOT = Path(__file__).resolve().parents[2]
HARNESS = "091279261203b243386adf256b2b107656013dbf"
LAUNCH = "c4b623d930f3728e5338664bb634021b98492cbf"
IDENTITY_PATHS = (
    ".github/workflows/fd2-grade.yml", ".github/workflows/fd2-gold-validity.yml",
    ".github/actions/fd2-setup/action.yml", "tools/fd2/harness-requirements.lock",
    "tools/fd2/harness-requirements.in", "docs/prereg-fd2-items.json",
    "tools/fd2/gold_smoke.sh", "tools/fd2/remote_grade.py", "tools/fd2/prepare_frozen.py",
    "tools/fd2/select_smoke.py", "tools/fd2/gold_validity.py", "tools/fd2/image_digests.py", "src/rsi_kernel/publication.py",
    "src/rsi_kernel/adapters/swebench_live/remote.py", "src/rsi_kernel/adapters/swebench_live/solver.py",
    "src/rsi_kernel/adapters/swebench_live/grading.py",
)


def evaluator_identity(image):
    return {"harness": HARNESS, "repolaunch": LAUNCH, "dataset_revision": REVISION,
            "parquet_sha256": EXPECTED_SHA256, "image": image,
            "files_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in IDENTITY_PATHS},
            "grading_argv": ["python", "-m", "evaluation.evaluation", "--dataset", "{frozen.jsonl}",
                             "--split", "{split}", "--platform", "linux", "--patch_dir", "{predictions.json}",
                             "--output_dir", "{output}", "--workers", "1", "--overwrite", "0",
                             "--instance_ids", "{instance_id}"]}


def runner_image_build():
    build = {key: os.environ[key] for key in ("ImageOS", "ImageVersion")}
    if os.environ.get("ImageProvisionerVersion"):
        build["ImageProvisionerVersion"] = os.environ["ImageProvisionerVersion"]
    else:
        # Runner's own metadata, not a guessed hosted-image version. The runner
        # reads .setup_info at its binary directory's parent (HostContext.cs).
        # https://github.com/actions/runner/blob/main/src/Runner.Worker/JobExtension.cs
        for executable in Path("/proc").glob("[0-9]*/exe"):
            try:
                binary = executable.resolve(strict=True)
            except OSError:
                continue  # Other processes may exit or deny procfs access.
            if binary.name != "Runner.Listener":
                continue
            setup = binary.parent.parent / ".setup_info"
            if setup.is_file():
                groups = json.loads(setup.read_text())
                details = [entry["Detail"] for entry in groups
                           if entry.get("Group") == "Runner Image Provisioner"]
                if len(details) == 1:
                    build["ImageProvisionerVersion"] = details[0]
                    break
        if not build.get("ImageProvisionerVersion"):
            raise ValueError("runner provisioner metadata missing")
    return build


def read_payload(url, digest, request_id, repository, *, fetch=urlopen):
    parsed = urlparse(url)
    prefix = f"/{repository}/releases/download/"
    if (parsed.scheme != "https" or parsed.netloc != "github.com" or not parsed.path.startswith(prefix)
            or parsed.query or parsed.fragment or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", request_id)):
        raise ValueError("expected a digest-bound public mirror release asset and safe request id")
    with fetch(url) as response:
        body = response.read()
    if hashlib.sha256(body).hexdigest() != digest:
        raise ValueError("payload SHA-256 mismatch")
    payload = json.loads(body)
    if payload["binding"]["request_id"] != request_id or PATTERN.search(json.dumps(payload, ensure_ascii=False)):
        raise ValueError("payload identity or publication marker mismatch")
    return payload


def main():
    output = ROOT / "grade-output"
    output.mkdir(exist_ok=True)
    digest, request_id = os.environ["PREDICTION_SHA256"], os.environ["REQUEST_ID"]
    payload = read_payload(os.environ["PAYLOAD_URL"], digest, request_id, os.environ["GITHUB_REPOSITORY"])
    binding = payload["binding"]
    item = next(row for row in matrix(json.loads((ROOT / "docs/prereg-fd2-items.json").read_text()))
                if (row["split"], row["instance_id"]) == (binding["split"], binding["instance_id"]))
    if (not re.fullmatch(r"[^\s@]+@sha256:[0-9a-f]{64}", binding["image"])
            or type(binding["run"]) is not int or binding["run"] < 0
            or set(payload["predictions"]) != {item["instance_id"]}
            or set(payload["predictions"][item["instance_id"]]) != {"model_patch"}
            or not isinstance(payload["predictions"][item["instance_id"]]["model_patch"], str)):
        raise ValueError("invalid single-instance prediction")
    identity, build = evaluator_identity(binding["image"]), runner_image_build()
    if (payload["workflow_commit"] != os.environ["GITHUB_SHA"]
            or payload["evaluator_identity"] != identity):
        raise ValueError("frozen evaluator mismatch")
    harness = ROOT / "SWE-bench-Live"
    for directory, expected in ((harness, HARNESS), (harness / "launch", LAUNCH)):
        actual = subprocess.check_output(["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()
        if actual != expected:
            raise ValueError("harness checkout mismatch")
    # hf's revision pin plus prepare_frozen's byte hashes, exactly as gold smoke.
    dataset = Path(subprocess.check_output([
        "hf", "download", DATASET, "--repo-type", "dataset", "--revision", REVISION,
        "--include", "data/*.parquet", "--quiet"], text=True).strip())
    import pyarrow.parquet as pq
    frozen = output / "frozen.jsonl"
    write_selected_jsonl({name: dataset / name for name in EXPECTED_SHA256}, EXPECTED_SHA256,
                         [item], frozen, lambda path: pq.read_table(path).to_pylist())
    repository, image_digest = binding["image"].split("@")
    row = json.loads(frozen.read_text())
    if image_repository(row["docker_image"]) != repository:
        raise ValueError("prediction image repository differs from frozen dataset")
    pin_image(frozen, item["instance_id"], image_digest)
    subprocess.run(["docker", "pull", binding["image"]], check=True, capture_output=True)
    prediction = output / "predictions.json"
    prediction.write_text(json.dumps(payload["predictions"]))
    host = subprocess.check_output(["docker", "context", "inspect", "--format",
                                    '{{(index .Endpoints "docker").Host}}'], text=True).strip()
    environment = {key: os.environ[key] for key in ("PATH", "HOME")}
    token = _DOCKER_ENV.set({**environment, "DOCKER_HOST": host})
    try:
        # 360 minutes is the existing hosted-job ceiling; the caller's independent
        # dispatch-to-result deadline is required and enforced by RemoteGrader.
        grader = HarnessGrader(harness_dir=harness, python=Path(sys.executable), grading_data=frozen,
                               image=binding["image"], timeout=360 * 60)
        grader(SimpleNamespace(lang=item["split"], instance_id=item["instance_id"]), prediction, output,
               run=binding["run"], image=binding["image"],
               container_name=request_id)
    finally:
        _DOCKER_ENV.reset(token)
    record = {**binding, "prediction_sha256": digest, "workflow_commit": os.environ["GITHUB_SHA"],
              "run_id": int(os.environ["GITHUB_RUN_ID"]), "runner_image_build": build, "evaluator_identity": identity}
    (output / "binding.json").write_text(json.dumps(record, sort_keys=True) + "\n")
    # Only binding + results + report are uploaded, never this directory wholesale.


if __name__ == "__main__":
    main()
