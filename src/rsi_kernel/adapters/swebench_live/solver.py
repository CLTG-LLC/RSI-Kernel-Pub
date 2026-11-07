"""One isolated Codex attempt inside a pinned SWE-bench Live instance image.

Docker plumbing is reused from the live-verified GDPevo runner. The instance
container stays alive for repository discovery, the solve and patch extraction.
Only staged issue text, skill text and verified read-only Codex tools are mounted:
no dataset, cache, grader, evidence, private store or Docker socket.

The injected grader owns the official harness command and its documented network,
and must run it in a fresh container named by ``container_name``. The prompt is a
required frozen host input because its template is selected at preregistration.
No live Docker or model call is made by this module's tests.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import secrets
import subprocess
import tarfile
import time
from pathlib import Path, PurePosixPath
from types import MappingProxyType, SimpleNamespace
from typing import Callable, Mapping, Sequence

from ...candidate import Candidate
from ..gdpevo.adapter import validate_skill
from ..gdpevo.solver_docker import (
    MODEL, SOLVER_COMMAND as GDP_SOLVER_COMMAND, DockerSolver,
    _bind, _digest, _json, _manifest, _Stop as _DockerStop, _DOCKER_ENV,
)
from .grading import predictions, read_report, score_from_report
from .tasks import SweTask

PLATFORM = "linux/amd64"
CODEX_HOME = "/tmp/swe-codex-home"
SOLVER_COMMAND = GDP_SOLVER_COMMAND.replace("/tmp/gdpevo-codex-home", CODEX_HOME)

# Official release API asset.digest values (the complete .tar.gz bytes), fetched
# from https://api.github.com/repos/openai/codex/releases/tags/rust-v0.166.0 .
# Extraction adopts the single-regular-file layout in adapters/gdpevo/Dockerfile.
CODEX_ASSETS = {
    "codex": ("codex-x86_64-unknown-linux-musl.tar.gz",
              "a0bf572d2f93f056c6712a6da348e96078dc84f3885fd7be67807ef389cb3978",
              "/usr/local/bin/codex"),
    "bwrap": ("bwrap-x86_64-unknown-linux-musl.tar.gz",
              "a37212d853eec479c6ad4f0852ccf857dec422b76747f0349c70a382954be56f",
              "/usr/local/bin/codex-resources/bwrap"),
    "codex-code-mode-host": ("codex-code-mode-host-x86_64-unknown-linux-musl.tar.gz",
              "7588334fd47bc4003d970b70dfd4d1e4578491b1e9baa72976a4c2d7e97590da",
              "/usr/local/bin/codex-code-mode-host"),
}
OFFICIAL_CODEX_DIGESTS = MappingProxyType({name: value[1] for name, value in CODEX_ASSETS.items()})

Grader = Callable[..., tuple[Mapping, Mapping | None]]



def _image_repository(name: str) -> str:
    # RepoDigests hold "repository@digest" with no tag, so drop any digest and any
    # tag (a ':' after the last '/'; a registry port sits before it).
    # https://docs.docker.com/reference/cli/docker/image/tag/
    name = name.split("@", 1)[0]
    head, _, last = name.rpartition("/")
    return f"{head}/{last.split(':', 1)[0]}" if head else last.split(":", 1)[0]

class _Stop(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _prepare_codex(directory: Path, pins=CODEX_ASSETS) -> dict[str, Path]:
    """Verify the three release archives and extract their one executable."""
    tools = directory / ".swe-codex-0.166.0"
    tools.mkdir(mode=0o700, exist_ok=True)
    result = {}
    for name, (filename, expected, _) in pins.items():
        archive_path = directory / filename
        if not archive_path.is_file() or archive_path.is_symlink() or _digest(archive_path) != expected:
            raise _Stop("codex_asset_digest")
        with tarfile.open(archive_path, mode="r:gz") as archive:
            members = [member for member in archive.getmembers() if member.isfile()]
            if len(members) != 1 or not members[0].isreg():
                raise _Stop("codex_asset_layout")
            body = archive.extractfile(members[0]).read()
        path = tools / name
        path.write_bytes(body)
        path.chmod(0o700)
        result[name] = path
    return result


class HarnessGrader:
    """Run the pinned official harness as a host process, as the gold smoke does.

    evaluation.py is a host-side driver: RepoLaunch calls the Docker SDK's
    ``from_env()``, pulls the (digest-pinned) instance image and creates its own
    per-instance container, bind-mounting ``cwd/tmp`` into it. That container is
    the fresh grading container; the solver container is never reused. The
    driver therefore runs with cwd = the writable pinned harness checkout, the
    harness's own Python, and DOCKER_HOST bound to the intended daemon.
    https://github.com/microsoft/RepoLaunch/blob/c4b623d930f3728e5338664bb634021b98492cbf/launch/core/platforms/linux.py
    """

    def __init__(self, *, harness_dir: Path, python: Path, grading_data: Path, image: str, timeout: float):
        if not image.startswith(("sha256:",)) and "@sha256:" not in image:
            raise ValueError("grading image must be digest-pinned")
        harness_dir, python, grading_data = Path(harness_dir), Path(python), Path(grading_data)
        if not all(p.is_absolute() for p in (harness_dir, python, grading_data)):
            raise ValueError("harness, interpreter and grading data paths must be absolute")
        if not grading_data.is_file() or not harness_dir.is_dir() or not python.is_file():
            raise ValueError("frozen harness, interpreter and grading data must exist")
        if not os.access(harness_dir, os.W_OK):
            raise ValueError("harness checkout must be writable (RepoLaunch binds cwd/tmp)")
        if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("grading timeout must be positive")
        self.harness_dir, self.python, self.grading_data = harness_dir, python, grading_data
        self.image, self.timeout = image, timeout

    def __call__(self, task: SweTask, prediction: Path, output: Path, *, run: int,
                 image: str, container_name: str) -> tuple[Mapping, Mapping | None]:
        # container_name is the solver's scope; the harness names its own container.
        if image != self.image:
            raise ValueError("grading image does not match the frozen image")
        environment = _DOCKER_ENV.get()
        if environment is None or not environment.get("DOCKER_HOST"):
            raise ValueError("grading requires the resolved Docker daemon endpoint")
        argv = [str(self.python), "-m", "evaluation.evaluation",
                "--dataset", str(self.grading_data), "--split", task.lang,
                "--platform", "linux", "--patch_dir", str(Path(prediction).resolve()),
                "--output_dir", str(Path(output).resolve()), "--workers", "1", "--overwrite", "0",
                "--instance_ids", task.instance_id]
        subprocess.run(argv, cwd=self.harness_dir, env=dict(environment), timeout=self.timeout,
                       check=True, capture_output=True)
        try:
            results = json.loads((output / "results.json").read_text(encoding="utf-8"))
        except (OSError, ValueError) as error:
            raise ValueError("harness results are missing or invalid") from error
        return results, read_report(output / task.instance_id / "report.json", task.instance_id)


class SweSolver(DockerSolver):
    """DockerSolver supplies only its scoped Docker/forwarder/timeout helpers."""

    def __init__(self, *, tasks: Sequence[SweTask], evidence_dir: Path, timeout: float,
                 codex_assets: Path, grader: Grader, grading_image: str, prompt: str):
        if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive frozen config value")
        if not evidence_dir.is_absolute() or not grading_image or not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("absolute evidence path, grading image and frozen prompt are required")
        self.tasks = {task.item_id: task for task in tasks}
        if not self.tasks or len(self.tasks) != len(tasks):
            raise ValueError("tasks must be non-empty with unique item ids")
        self.evidence_dir, self.timeout = evidence_dir.resolve(), timeout
        self.codex_assets, self.grader, self.grading_image = Path(codex_assets), grader, grading_image
        self.prompt = prompt
        self._pins = SimpleNamespace(codex_assets=CODEX_ASSETS)

    def __call__(self, candidate: Candidate, item_id: str, *, run: int = 0) -> dict:
        if isinstance(run, bool) or not isinstance(run, int) or run < 0:
            raise ValueError("run must be a non-negative integer")
        self.evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        scope = "swe-" + secrets.token_hex(4)
        out = self.evidence_dir / scope
        out.mkdir(mode=0o700)
        (out / "container-scope.txt").write_text(scope + "\n")
        _json(out / "attempt.json", {"item_id": item_id, "candidate_id": candidate.id, "run": run})
        phase = "staging"
        try:
            task = self.tasks[item_id]
            stage = self._stage(candidate, task, out)
            tools = _prepare_codex(self.codex_assets, self._pins.codex_assets)
            phase = "docker_connection"
            self._docker_environment(out)
            phase = "image_pull"
            image = self._verify_image(task, out)
            phase = "network"
            network = scope + "-net"
            self._run(["docker", "network", "create", "--internal", network], out / "network-id.txt")
            self._forwarder(out, scope, network)
            phase = "container"
            self._create(scope, image, stage, tools)
            self._run(["docker", "start", scope + "-agent"], out / "agent-start.txt")
            phase = "repo_discovery"
            repo, base = self._repository(scope, out)
            phase = "solver"
            self._solve(out, scope, repo)
            phase = "trace"
            self._trace_repo(out, scope, repo)
            phase = "staging"
            self._check_stage(out, stage)
            phase = "solver_exit"
            self._check_exit(out, scope)
            phase = "patch_extract"
            patch = self._extract(scope, repo, base, out)
            phase = "grading"
            result = self._grade(task, patch, out, scope, run)
            phase = "cleanup"
            self._cleanup(scope)
            return result
        except (KeyError, OSError, ValueError, RecursionError, tarfile.TarError,
                subprocess.SubprocessError, _Stop, _DockerStop) as error:
            reason = error.reason if isinstance(error, (_Stop, _DockerStop)) else "timeout" if isinstance(error, subprocess.TimeoutExpired) else phase
            result = {"item_id": item_id, "score": None, "evidence_dir": str(out),
                      "failure": {"status": "STOP", "reason": reason}}
            _json(out / "failure.json", result)
            return result

    def _stage(self, candidate: Candidate, task: SweTask, out: Path) -> Path:
        statement = task.statement
        if hashlib.sha256(statement.encode("utf-8")).hexdigest() != task.problem_statement_sha256:
            raise _Stop("problem_statement")
        stage = out / "stage"
        (stage / "skill").mkdir(parents=True, mode=0o700)
        (stage / "problem_statement.md").write_text(statement, encoding="utf-8")
        (stage / "skill/SKILL.md").write_text(validate_skill(candidate), encoding="utf-8")
        _json(out / "stage-manifest.json", _manifest(stage))
        return stage

    def _check_stage(self, out: Path, stage: Path) -> None:
        if _manifest(stage) != json.loads((out / "stage-manifest.json").read_text()):
            raise _Stop("stage_mutated")

    def _verify_image(self, task: SweTask, out: Path) -> str:
        # Docker digest references are NAME[:TAG|@DIGEST], not bare image IDs:
        # https://docs.docker.com/reference/cli/docker/image/pull/
        reference = _image_repository(task.docker_image) + "@" + task.image_digest
        self._run(["docker", "image", "inspect", "--format", "{{.Os}}/{{.Architecture}}",
                   reference], out / "image-platform.txt")
        if (out / "image-platform.txt").read_text().strip() != PLATFORM:
            raise _Stop("image_architecture")
        self._run(["docker", "image", "inspect", "--format", "{{json .RepoDigests}}", reference],
                  out / "image-digests.json")
        values = json.loads((out / "image-digests.json").read_text())
        if not isinstance(values, list) or reference not in values:
            raise _Stop("image_digest")
        self._run(["docker", "image", "inspect", "--format", "{{.Config.WorkingDir}}", reference],
                  out / "image-workdir.txt")
        workdir = (out / "image-workdir.txt").read_text().strip()
        if not PurePosixPath(workdir).is_absolute():
            raise _Stop("repo_workdir")
        (out / "image-workdir.txt").write_text(workdir + "\n")
        return reference

    def _create(self, scope: str, image: str, stage: Path, tools: Mapping[str, Path]) -> None:
        mounts = [*_bind(stage / "problem_statement.md", "/work/problem_statement.md"),
                  *_bind(stage / "skill", "/work/skill")]
        for name, path in tools.items():
            mounts.extend(_bind(path, CODEX_ASSETS[name][2]))
        # The instance entrypoint is replaced so no task service can consume the solve.
        self._run(["docker", "create", "--name", scope + "-agent", "--platform", PLATFORM,
                   "--network", scope + "-net", "--entrypoint", "", *mounts,
                   image, "sleep", "infinity"], Path(self.evidence_dir) / scope / "agent-id.txt")

    def _repository(self, scope: str, out: Path) -> tuple[str, str]:
        workdir = (out / "image-workdir.txt").read_text().strip()
        try:
            completed = self._run(["docker", "exec", scope + "-agent", "git", "-C", workdir,
                                   "rev-parse", "--show-toplevel", "HEAD"])
        except subprocess.CalledProcessError as error:
            raise _Stop("repo_head") from error
        lines = completed.stdout.decode().splitlines()
        (out / "repository.txt").write_text("\n".join(lines) + "\n")
        if len(lines) != 2 or not PurePosixPath(lines[0]).is_absolute() or not lines[1].strip():
            raise _Stop("repo_head")
        return lines[0], lines[1]

    def _solve(self, out: Path, scope: str, repo: str) -> None:
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        begin, attached = time.monotonic(), None
        command = SOLVER_COMMAND.replace("-C /work", "-C " + repo)
        try:
            attached = self._run(["docker", "exec", scope + "-agent", "bash", "-c", command,
                                  "run-one", self.prompt], out / "exec-stdout.jsonl", check=False)
        except subprocess.TimeoutExpired:
            self._stop_timed_out(out, scope + "-agent")
            raise
        finally:
            _json(out / "attempt-timing.json", {"started_utc": started,
                  "elapsed_seconds": time.monotonic() - begin,
                  "docker_attach_exit_code": attached.returncode if attached else None,
                  "container_exit_code": None})

    def _check_exit(self, out: Path, scope: str) -> None:
        timing = json.loads((out / "attempt-timing.json").read_text())
        if timing["docker_attach_exit_code"] != 0:
            raise _Stop("solver_exit")

    def _trace_repo(self, out: Path, scope: str, repo: str) -> None:
        sessions = out / "sessions"
        sessions.mkdir(mode=0o700)
        self._run(["docker", "cp", scope + "-agent:" + CODEX_HOME + "/sessions/.", str(sessions)])
        matching = []
        for path in sessions.rglob("rollout-*.jsonl"):
            if path.is_symlink():
                raise _Stop("unsafe_trace")
            text = path.read_text()
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            if any(not isinstance(row, dict) or not isinstance(row.get("payload"), dict) for row in rows):
                raise _Stop("trace_json")
            meta = [row["payload"] for row in rows if row.get("type") == "session_meta"]
            if len(meta) == 1 and meta[0].get("cwd") == repo:
                matching.append((path, rows, meta[0]))
        if len(matching) != 1:
            raise _Stop("primary_rollout")
        path, rows, meta = matching[0]
        if meta.get("model_provider") != "proxy":
            raise _Stop("trace_provider")
        turns = [row["payload"] for row in rows if row.get("type") == "turn_context"]
        if not turns or any(turn.get("model") != MODEL for turn in turns):
            raise _Stop("trace_model")
        usage = [row["payload"]["info"] for row in rows if row.get("type") == "event_msg"
                 and row["payload"].get("type") == "token_count" and row["payload"].get("info")]
        _json(out / "measurement.json", {"eval_attempt_id": scope, "condition": "self", "model": MODEL,
              "model_provider": "proxy", "trace": str(path), "trace_sha256": _digest(path),
              "token_usage": usage[-1].get("total_token_usage") if usage else None,
              "token_usage_source": "codex_session_trace" if usage else "missing", "cost_usd": None})
        path.chmod(0o600)

    def _extract(self, scope: str, repo: str, base: str, out: Path) -> str:
        # OpenHands/SWE-agent submit convention: index everything, then diff the frozen HEAD.
        self._run(["docker", "exec", scope + "-agent", "git", "-C", repo, "add", "-A"], out / "patch-add.log")
        self._run(["docker", "exec", scope + "-agent", "git", "-C", repo, "diff", "--cached",
                   base, "--no-color"], out / "model_patch.diff")
        patch = (out / "model_patch.diff").read_text(encoding="utf-8")
        (out / "model_patch.diff").write_text(patch, encoding="utf-8")
        _json(out / "patch-manifest.json", {"base": base, "sha256": hashlib.sha256(patch.encode()).hexdigest()})
        return patch

    def _grade(self, task: SweTask, patch: str, out: Path, scope: str, run: int) -> dict:
        prediction = out / "predictions.json"
        _json(prediction, predictions({task.instance_id: patch}, [task.instance_id]))
        output = out / "harness" / f"run-{run}"
        output.mkdir(parents=True, mode=0o700)
        try:
            results, report = self.grader(task, prediction, output, run=run, image=self.grading_image,
                                          container_name=scope + "-grade")
        except (OSError, TypeError, ValueError, subprocess.SubprocessError) as error:
            raise _Stop("harness_error") from error
        grade = score_from_report(task.instance_id, results, report)
        _json(out / "grade.json", {"category": grade.category, "score": grade.score})
        if grade.score is None:
            raise _Stop(grade.reason or "harness_error")
        result = {"item_id": task.item_id, "score": grade.score, "evidence_dir": str(out),
                  "grade_category": grade.category}
        _json(out / "result.json", result)
        return result

    def _cleanup(self, scope: str) -> None:
        # Durable result and patch precede cleanup; only this attempt's names are removed.
        self._run(["docker", "stop", scope + "-agent"], self.evidence_dir / scope / "agent-stop.log")
        self._run(["docker", "rm", "-f", scope + "-agent", scope + "-fwd"])
        self._run(["docker", "network", "rm", scope + "-net", scope + "-egress"])
