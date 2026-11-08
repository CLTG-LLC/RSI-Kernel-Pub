"""Single-dispatch grading; ownership comes only from gh's dispatch response.

https://github.com/cli/cli/blob/v2.102.0/pkg/cmd/workflow/run/run.go
The deadline and evaluator identity are frozen; runner builds are record-only.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import quote

from ...publication import PATTERN
from . import grading


def gh(argv: list[str], *, timeout: float) -> str:
    return subprocess.run(argv, check=True, capture_output=True, text=True, timeout=timeout).stdout


class _RemoteStop(Exception):
    pass


_SECRET = (re.compile(r"(gh[pousr]_|github_pat_)[A-Za-z0-9_]+"),
           re.compile(r"(?i)(authorization|token|password)\s*[:=]\s*\S+"),
           re.compile(r"(https?://)[^/\s@]+@"))


def _redact(text):
    # Private evidence keeps the explanation (e.g. "HTTP 403: ...") but never
    # credential-bearing parts. argv is never stored.
    text = _SECRET[0].sub(r"\1<redacted>", text)
    text = _SECRET[1].sub(r"\1=<redacted>", text)
    return _SECRET[2].sub(r"\1<redacted>@", text)


def _diagnostic(error):
    record = {"exception_type": type(error).__name__}
    if isinstance(error, subprocess.CalledProcessError):
        record["returncode"] = error.returncode
        if error.stderr:
            record["stderr"] = _redact(error.stderr if isinstance(error.stderr, str)
                                       else error.stderr.decode("utf-8", "replace"))
    elif isinstance(error, subprocess.TimeoutExpired):
        record["timeout"] = error.timeout
    elif isinstance(error, OSError):
        record["errno"] = error.errno
    return record


class RemoteGrader:
    def __init__(self, *, repository: str, release_tag: str, workflow_ref: str,
                 workflow_commit: str, evaluator_identity: dict,
                 deadline: float, runner=gh, clock=time.monotonic, sleep=time.sleep):
        if isinstance(deadline, bool) or not isinstance(deadline, (int, float)) or not math.isfinite(deadline) or deadline <= 0:
            raise ValueError("remote grading requires an explicit positive finite deadline")
        if not re.fullmatch(r"[\w.-]+/[\w.-]+", repository) or not re.fullmatch(r"[0-9a-f]{40}", workflow_commit):
            raise ValueError("expected a repository and frozen workflow commit")
        if not release_tag or not workflow_ref or not evaluator_identity:
            raise ValueError("release, ref and evaluator identity must be frozen")
        self.repository, self.release_tag, self.workflow_ref = repository, release_tag, workflow_ref
        self.workflow_commit = workflow_commit
        self.evaluator_identity = dict(evaluator_identity)
        self.deadline, self.runner, self.clock, self.sleep = deadline, runner, clock, sleep
        self.failure = None

    def _call(self, *args):
        remaining = self._expires - self.clock()
        if remaining <= 0:
            raise _RemoteStop("queue_expiry" if self._queued else "timeout")
        return self.runner(["gh", *args, "--repo", self.repository], timeout=remaining)

    def _pause(self):
        # Reuse gold_smoke.sh's operational watchdog cadence, not a grading budget.
        self.sleep(min(5, max(0, self._expires - self.clock())))

    def _wait(self, run_id, request_id):
        while True:
            record = json.loads(self._call("run", "view", str(run_id), "--json",
                                           "databaseId,displayTitle,headSha,status,conclusion,createdAt,startedAt,updatedAt"))
            if (record.get("databaseId"), record.get("displayTitle"), record.get("headSha")) != (
                    run_id, request_id, self.workflow_commit):
                raise _RemoteStop("binding_mismatch")
            self._run_record = record
            status = record.get("status")
            self._queued = status in {"queued", "waiting", "pending", "requested"}
            if status == "completed":
                conclusion = record.get("conclusion")
                if conclusion != "success":
                    raise _RemoteStop({"cancelled": "cancellation", "timed_out": "timeout"}.get(
                        conclusion, "silent_termination"))
                return
            if status not in {"queued", "waiting", "pending", "requested", "in_progress"}:
                raise _RemoteStop("silent_termination")
            self._pause()

    def __call__(self, task, prediction: Path, output: Path, *, run: int,
                 image: str, container_name: str):
        self.failure = None
        self._expires, self._queued = self.clock() + self.deadline, True
        self._owned, self._run_record = False, {}
        output = Path(output)
        output.mkdir(parents=True, exist_ok=True)
        run_id, completed, phase = None, False, "dispatch_failure"
        try:
            request_id = "fd2-" + uuid.uuid4().hex
            patches = json.loads(Path(prediction).read_text(encoding="utf-8"))
            if (set(patches) != {task.instance_id} or not isinstance(patches[task.instance_id], dict)
                    or set(patches[task.instance_id]) != {"model_patch"}
                    or not isinstance(patches[task.instance_id]["model_patch"], str)):
                raise _RemoteStop("binding_mismatch")
            if not image.endswith("@" + task.image_digest):
                raise _RemoteStop("binding_mismatch")
            binding = {"request_id": request_id, "instance_id": task.instance_id,
                       "run": run, "split": task.lang, "image": image}
            payload = json.dumps({"binding": binding, "predictions": patches,
                                  "workflow_commit": self.workflow_commit,
                                  "evaluator_identity": self.evaluator_identity}, sort_keys=True, ensure_ascii=False).encode()
            if PATTERN.search(payload.decode()):
                raise _RemoteStop("publication_marker")
            path = output / f"{request_id}.json"
            path.write_bytes(payload)
            digest = hashlib.sha256(payload).hexdigest()
            self._call("release", "upload", self.release_tag, str(path))
            url = f"https://github.com/{self.repository}/releases/download/{quote(self.release_tag, safe='')}/{path.name}"
            response = self._call("workflow", "run", "fd2-grade.yml", "--ref", self.workflow_ref,
                                  "-f", "payload_url=" + url, "-f", "sha256=" + digest,
                                  "-f", "request_id=" + request_id)
            match = re.fullmatch(r"https://github\.com/" + re.escape(self.repository)
                                 + r"/actions/runs/([1-9][0-9]*)", response.strip())
            if not match:
                raise _RemoteStop("dispatch_failure")
            run_id = int(match[1])
            # The dispatch response alone establishes ownership; binding validity is separate.
            self._owned = True
            phase = "silent_termination"
            self._wait(run_id, request_id)
            completed = True
            phase = "missing_artifact"
            artifact = output / "artifact"
            self._call("run", "download", str(run_id), "--name", request_id, "--dir", str(artifact))
            if not (artifact / "binding.json").is_file():
                raise _RemoteStop("missing_artifact")
            phase = "binding_mismatch"
            actual = json.loads((artifact / "binding.json").read_text(encoding="utf-8"))
            build = actual.pop("runner_image_build")
            expected = {**binding, "prediction_sha256": digest, "run_id": run_id,
                        "workflow_commit": self.workflow_commit, "evaluator_identity": self.evaluator_identity}
            if actual != expected or not isinstance(build, dict):
                raise _RemoteStop("binding_mismatch")
            # Private receipt preserves the actual build, not a caller constraint.
            (output / "receipt.json").write_text(json.dumps({**actual, "runner_image_build": build,
                                                           "workflow_run": self._run_record}) + "\n")
            phase = "silent_termination"
            results = json.loads((artifact / "results.json").read_text(encoding="utf-8"))
            report = grading.read_report(artifact / task.instance_id / "report.json", task.instance_id)
            grade = grading.score_from_report(task.instance_id, results, report)
            if grade.score is None:
                raise _RemoteStop(grade.reason or "silent_termination")
            if self.clock() >= self._expires:
                raise _RemoteStop("timeout")
            return results, report
        except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError, _RemoteStop) as error:
            reason = str(error) if isinstance(error, _RemoteStop) else (
                "queue_expiry" if self._queued else "timeout") if isinstance(error, subprocess.TimeoutExpired) else phase
            failure = {"reason": reason, "transport_diagnostic": _diagnostic(error),
                       "workflow_conclusion": self._run_record.get("conclusion"),
                       "run_id": run_id, "cancellation": {"outcome": "not_required"}}
            if run_id is not None and self._owned and not completed:
                try:
                    self.runner(["gh", "run", "cancel", str(run_id), "--repo", self.repository], timeout=self.deadline)
                    failure["cancellation"] = {"outcome": "requested"}
                except (OSError, subprocess.SubprocessError) as cancel_error:
                    failure["cancellation"] = {"outcome": "failed", "diagnostic": _diagnostic(cancel_error)}
            self.failure = failure
            # Private only. Write after cancellation, so the file reflects its outcome.
            (output / "failure.json").write_text(json.dumps({"failure": failure}) + "\n", encoding="utf-8")
            return None
