"""Docker solver runner, ported from a live-verified shell recipe.

Docker's internal network isolates solver/task egress. Only the per-run nginx
forwarder joins a normal bridge, proxying to the fixed local model endpoint. Registered
train/dev tasks and trusted candidates only; no sealed inputs. Failed attempts
retain private evidence and scoped resources without retry.
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import tarfile
import time
from contextvars import ContextVar
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from ...archive import paths_overlap
from ...candidate import Candidate
from .adapter import _check_finite, _reject_constant, _verify_task, validate_skill
from .scoring import score_from_evaluator
from .tasks import FrozenTask

# Per-call CLI connection/config only; ContextVar keeps parallel attempts scoped.
_DOCKER_ENV: ContextVar[Mapping[str, str] | None] = ContextVar("gdpevo_docker_env", default=None)

# Source: the live-verified reference recipe (internal network, forwarder, healthcheck).
UPSTREAM_COMMIT = "5082a777379156a048881e94940d640702e5e09a"
MODEL = "gpt-6.1-sol"
EFFORT = "xhigh"
PLATFORM = "linux/arm64"
PYTHON_IMAGE = "python:3.12-slim@sha256:b224e2fe306f9d303251ada22961635e5b52a69c0414a0050611be31c59f5f5b"
NGINX_IMAGE = "nginx@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de"
DOCKERFILE_SHA256 = "c4328964e7b35edc85d3824ea07b37e6f7d5010e8274e9e4ed034216103efba6"
PROMPT_PATH = "evaluation/eval_workspace/codex/guides/agent_prompts.md"
# Source: the reference recipe. Every other archived byte is Git-blob verified.
UPSTREAM_HASHES = {
    PROMPT_PATH: "41414d77d66712ed9f7f385685838b3233639434978e3d7e4fce4076195d55c0",
    "data/task_groups/task_group_001/task_group.yaml": "d17786bab6f8626478a0d82b44007310b42a0f8b8ea66e8c5c396a6ae24f17bb",
    "data/task_groups/task_group_001/env/Dockerfile": "3b1f48fd54b080d6e90fccd3773570da3dc870271f7d97dd10a7fa873c2fc384",
    "data/task_groups/task_group_001/env/server.py": "796d594c537779be301088420e10cab36eefafbf05d8727b07004d2391a30073",
    "data/task_groups/task_group_001/train_tasks/001/eval/eval.sh": "4b0b49b98dac34b6c9111c5d766a323dbaa827f4cffb2f58b1b85fa4632a4cf1",
    "data/task_groups/task_group_001/train_tasks/001/eval/evaluate.py": "f175e20717e9d5e6064a33370ebf61e515baedda4439e6ee9ee7925035f5ec74",
}
# Verbatim from the live-verified reference recipe.
FORWARDER_CONF = '''events {}
http {
  server {
    listen 8080;
    location / {
      proxy_pass http://host.docker.internal:10100;
      proxy_set_header Host 127.0.0.1:10100;
      proxy_set_header Origin "";
      proxy_http_version 1.1;
      proxy_buffering off;
      proxy_read_timeout 3600s;
    }
  }
}
'''
# Verbatim permitted access note, the reference recipe.
ACCESS_NOTE = '''Environment base URL: http://task-env:9001/
No credentials are required. Allowed GET endpoints: /health; /api/policies;
/api/events and its event/orders/sponsor_packages/badges resources;
/api/finance/invoices; /api/crm/accounts, contacts, opportunities, campaign_members;
/api/tradeshows and its exhibitors/meeting_interest resources;
/api/import_batches and its raw_contacts/suppression resources.
The environment is read-only. The judge is disabled; do not call /api/judge.
'''
# Verbatim disposable check, the reference recipe.
ENVIRONMENT_CHECK = '''import json,urllib.request,urllib.error
base="http://task-env:9001"
health=json.load(urllib.request.urlopen(base+"/health"))
if health.get("status")!="ok": raise SystemExit("STOP: unhealthy environment")
request=urllib.request.Request(base+"/api/judge",data=b"{}",headers={"Content-Type":"application/json"},method="POST")
try:
    urllib.request.urlopen(request)
    raise SystemExit("STOP: judge unexpectedly accessible")
except urllib.error.HTTPError as error:
    if error.code!=404: raise SystemExit("STOP: judge-disable check did not return 404")
print(json.dumps({"health_status":health["status"],"judge_http_status":404}))
'''
# Recipe-v6/run-one.sh:181–202. No env-key provider, login or host auth.json.
SOLVER_COMMAND = '''set -euo pipefail
umask 077
export CODEX_HOME=/tmp/gdpevo-codex-home
install -d -m 700 "$CODEX_HOME"
cat > "$CODEX_HOME/config.toml" <<"CONFIG"
model_provider = "proxy"
[model_providers.proxy]
name = "proxy"
base_url = "http://model-fwd:8080/v1"
wire_api = "responses"
requires_openai_auth = false
CONFIG
version=$(codex --version)
[[ $version == "codex-cli 0.166.0" ]] || { echo "STOP: Codex version mismatch" >&2; exit 2; }
printf "%s\\n" "$version"
exec codex exec -C /work -m MODEL \\
  -c 'model_reasoning_effort="EFFORT"' \\
  -c 'approval_policy="never"' \\
  --sandbox danger-full-access --skip-git-repo-check --json "$1" < /dev/null
'''.replace("MODEL", MODEL).replace("EFFORT", EFFORT)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, value) -> None:
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    path.chmod(0o600)


def _manifest(root: Path) -> dict[str, str]:
    result = {}
    for path in root.rglob("*"):
        if path.is_symlink():
            raise ValueError("symlink in stage")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = _digest(path)
    return result


def _bind(source: Path, target: str, readonly: bool = True) -> list[str]:
    # Docker --mount uses comma-delimited fields; reject ambiguous source paths.
    if "," in str(source):
        raise ValueError("comma in bind source")
    return ["--mount", f"type=bind,source={source},target={target}" + (",readonly" if readonly else "")]


class _Stop(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class DockerSolver:
    """Existing Solver callable; returned score is consumed by GDPevoAdapter.

    ``tasks`` registers the caller-authorized dev train tasks, never adjudication
    or test tasks. ``timeout`` is caller-frozen, used for CLI operations, the
    health-state wait and attached solve; Docker healthcheck settings stay default.
    Evidence lives outside both the source repository and the transient stage.
    """

    upstream_commit = UPSTREAM_COMMIT

    def __init__(self, *, root: Path, tasks: Sequence[FrozenTask], evidence_dir: Path, timeout: float):
        if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be a positive frozen config value")
        root, evidence_dir = Path(root), Path(evidence_dir)
        if not root.is_absolute() or not evidence_dir.is_absolute():
            raise ValueError("source and evidence paths must be absolute")
        if paths_overlap(root.resolve(), evidence_dir.resolve()):
            raise ValueError("evidence must be separate from upstream source")
        if any(p.is_symlink() for p in (evidence_dir, *evidence_dir.parents)):
            raise ValueError("symlink in evidence path")
        if not tasks or any(t.subset != "train" for t in tasks):
            raise ValueError("register only authorized dev train tasks")
        self.tasks = {task.item_id: task for task in tasks}
        if len(self.tasks) != len(tasks):
            raise ValueError("duplicate task identity")
        self.root, self.evidence_dir, self.timeout = root.resolve(), evidence_dir.resolve(), timeout

    def __call__(self, candidate: Candidate, item_id: str, input_dir: Path,
                 prediction: Path, env: Mapping[str, str]) -> dict:
        # Keep host evidence on a Docker-visible caller-selected filesystem.
        self.evidence_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        scope = "gdp-" + secrets.token_hex(4)  # the reference recipe
        out = self.evidence_dir / scope
        out.mkdir(mode=0o700)
        _json(out / "attempt.json", {"item_id": item_id, "candidate_id": candidate.id})
        (out / "container-scope.txt").write_text(scope + "\n")
        token = _DOCKER_ENV.set(None)
        phase = "staging"
        try:
            task = self.tasks[item_id]
            if dict(env) != {"TASK_ENV_ENABLE_JUDGE": "0"}:
                raise _Stop("solver_env")
            if paths_overlap(out, Path(input_dir).resolve()) or paths_overlap(out, Path(prediction).resolve()):
                raise _Stop("staging_overlap")
            trusted, work, group, task_path = self._stage(candidate, task, Path(input_dir), out, scope)
            phase = "docker_connection"
            self._docker_environment(out)
            phase = "images"
            solver_image, task_image = self._images(out, group, scope)
            phase = "grader_sanity"
            (out / "empty-prediction.json").write_text("{}\n")
            sanity = self._grade(out, task_path, solver_image, out / "empty-prediction.json", scope + "-sanity", "grader-sanity.json")
            if score_from_evaluator(sanity) != 0 or "error" in sanity:
                raise _Stop("grader_sanity")
            phase = "environment"
            self._environment(out, scope, solver_image, task_image)
            phase = "solver"
            self._solve(out, scope, solver_image)
            phase = "trace"
            self._trace(out, scope)
            phase = "prediction"
            self._prediction(out, work)
            phase = "grading"
            payload = self._grade(out, task_path, solver_image, work / "answer.json", scope + "-grade", "score.json")
            score = score_from_evaluator(payload)
            if "error" in payload or score is None:
                raise _Stop("grader_score")
            # Verify immutable inputs/evaluator AGAIN after the solve and grading.
            self._verify_archive(trusted)
            self._check_stage(out, work)
            result = self._publish_result(out, work, prediction, item_id, score)
            phase = "cleanup"
            self._cleanup(scope)
            return result
        except (KeyError, OSError, ValueError, RecursionError, tarfile.TarError, subprocess.SubprocessError, _Stop) as error:
            # Never surface command/output, model content, rubric or secret-bearing errors.
            reason = error.reason if isinstance(error, _Stop) else phase
            result = {"item_id": item_id, "score": None, "evidence_dir": str(out),
                      "failure": {"status": "STOP", "reason": reason}}
            _json(out / "failure.json", result)
            return result
        finally:
            _DOCKER_ENV.reset(token)

    def _publish_result(self, out, work, prediction, item_id, score):
        if prediction.is_symlink() or any(p.is_symlink() for p in prediction.parents):
            raise _Stop("unsafe_prediction")
        shutil.copyfile(work / "answer.json", prediction)
        result = {"item_id": item_id, "score": float(score), "evidence_dir": str(out)}
        _json(out / "result.json", result)
        return result

    def _docker_environment(self, out):
        # Client proxies auto-inject container env/build args; never reuse config.
        # https://docs.docker.com/engine/cli/proxy/
        config = out / "docker-config"
        config.mkdir(mode=0o700)
        env = {"PATH": os.environ.get("PATH", os.defpath), "HOME": str(Path.home()),
               "DOCKER_CONFIG": str(config)}
        # DOCKER_CONTEXT overrides DOCKER_HOST. Resolve local context once instead
        # of copying metadata/auth/proxies. --config below is read-only discovery.
        # https://docs.docker.com/reference/cli/docker/#environment-variables
        # https://docs.docker.com/engine/manage-resources/contexts/
        # Keep only plugin discovery (buildx); without it the CLI silently uses
        # the legacy builder, which ignores Dockerfile heredocs. BuildKit=1 makes
        # a missing buildx an error instead of a fallback.
        # https://github.com/docker/docs/blob/main/content/manuals/scout/install.md
        # https://github.com/docker/cli/blob/master/cli-plugins/manager/manager.go
        original = os.environ.get("DOCKER_CONFIG", str(Path.home() / ".docker"))
        plugins = str(Path(original, "cli-plugins").absolute())
        _json(config / "config.json", {"cliPluginsExtraDirs": [plugins]})
        env["DOCKER_BUILDKIT"] = "1"
        context, host = os.environ.get("DOCKER_CONTEXT"), os.environ.get("DOCKER_HOST")
        _DOCKER_ENV.set(env)
        if context or not host:
            argv = ["docker", "--config", original, "context", "inspect"]
            if context:
                argv.append(context)
            endpoint = json.loads(self._run([*argv, "--format", "{{json .Endpoints.docker}}"]).stdout)
            host = endpoint.get("Host") if isinstance(endpoint, dict) else None
            # Endpoint-only binding cannot preserve a remote TLS context's certs.
            if not isinstance(host, str) or not host.startswith("unix://"):
                raise _Stop("docker_context_endpoint")
        _DOCKER_ENV.set({**env, "DOCKER_HOST": host})

    def _run(self, argv: Sequence[str], output: Path | None = None, *, check: bool = True):
        kwargs = {"timeout": self.timeout, "check": check}
        if argv[0] == "docker":
            env = _DOCKER_ENV.get()
            if env is None:
                raise _Stop("docker_environment")
            kwargs["env"] = dict(env)
        if output is None:
            return subprocess.run(list(argv), **kwargs, capture_output=True)
        with output.open("wb") as stdout, output.with_suffix(output.suffix + ".stderr").open("wb") as stderr:
            output.chmod(0o600)
            output.with_suffix(output.suffix + ".stderr").chmod(0o600)
            return subprocess.run(list(argv), **kwargs, stdout=stdout, stderr=stderr)

    def _stop_timed_out(self, out, name):
        # docker start -a timeout kills the CLI, not its daemon-owned container.
        # Docker kill uses its documented default SIGKILL; retain the container.
        # https://docs.docker.com/reference/cli/docker/container/kill/
        self._run(["docker", "kill", name], out / (name + "-kill.log"), check=False)
        running = self._run(["docker", "inspect", "--format", "{{.State.Running}}", name]).stdout.decode().strip()
        _json(out / (name + "-timeout-state.json"), {"container": name, "running": running})
        if running != "false":
            raise _Stop("timeout_container_running")

    def _git(self, *args: str) -> str:
        return self._run(["git", "-C", str(self.root), *args]).stdout.decode().strip()

    def _stage(self, candidate, task, input_dir, out, scope):
        skill = validate_skill(candidate)
        if self._git("rev-parse", "HEAD") != self.upstream_commit:
            raise _Stop("upstream_commit")
        directory = _verify_task(self.root, task)
        if any(p.is_symlink() for p in (input_dir, *input_dir.parents)):
            raise _Stop("staging_symlink")
        if _manifest(input_dir) != _manifest(directory / "input"):
            raise _Stop("staging_manifest_mismatch")
        group_rel = f"data/task_groups/{task.group}"
        task_rel = f"{group_rel}/train_tasks/{task.task_id}"
        selected = [f"{group_rel}/env", f"{group_rel}/task_group.yaml", f"{task_rel}/input", f"{task_rel}/eval", PROMPT_PATH]
        archived = self._run(["git", "-C", str(self.root), "archive", self.upstream_commit, *selected]).stdout
        trusted = out / "trusted"
        trusted.mkdir(mode=0o700)
        # Stdlib manual extraction admits regular files/directories only, no links.
        with tarfile.open(fileobj=io.BytesIO(archived)) as archive:
            for member in archive:
                rel = PurePosixPath(member.name)
                if rel.is_absolute() or ".." in rel.parts or not (member.isfile() or member.isdir()):
                    raise _Stop("unsafe_archive")
                path = trusted / rel
                path.parent.mkdir(parents=True, exist_ok=True)
                if member.isdir():
                    path.mkdir(exist_ok=True)
                else:
                    path.write_bytes(archive.extractfile(member).read())
                    path.chmod(member.mode)
        _json(out / "trusted-manifest.json", _manifest(trusted))
        self._verify_archive(trusted)
        group, task_path = trusted / group_rel, trusted / task_rel
        if "state_mode: read_only" not in (group / "task_group.yaml").read_text():
            raise _Stop("environment_not_readonly")
        # the reference recipe archives input/eval, never task gold/notes.
        # Full source remains verified above; exact staged subset stays hash-bound.
        staged_task = FrozenTask(task.group, task.subset, task.task_id,
                                 {name: digest for name, digest in task.hashes.items()
                                  if name.startswith(("input/", "eval/"))})
        try:
            _verify_task(trusted, staged_task)
        except ValueError as error:
            raise _Stop("staging_task_manifest_mismatch") from error
        work = out / "work"
        work.mkdir(mode=0o700)
        shutil.copytree(task_path / "input", work / "input")
        (work / "skill").mkdir()
        (work / "skill/SKILL.md").write_text(skill, encoding="utf-8")
        (work / "environment_access.md").write_text(ACCESS_NOTE)
        _json(out / "stage-manifest.json", _manifest(work))
        self._prompt(trusted, out, scope)
        return trusted, work, group, task_path

    def _prompt(self, trusted, out, scope):
        text = (trusted / PROMPT_PATH).read_text()
        if "## Test Solver\n" not in text:
            raise _Stop("prompt")
        text = text.split("## Test Solver\n", 1)[1]
        prompt = re.search(r"```text\n(.*?)\n```", text, re.S)
        if prompt is None:
            raise _Stop("prompt")
        prompt = prompt.group(1).replace("<unique_eval_attempt_id>", scope).replace("<base|fewshot|self|reflect-3>", "self")
        if "<" in prompt or ">" in prompt:
            raise _Stop("prompt")
        (out / "prompt.txt").write_text(prompt + "\n")

    def _verify_archive(self, trusted):
        manifest = _manifest(trusted)
        if manifest != json.loads((trusted.parent / "trusted-manifest.json").read_text()):
            raise _Stop("upstream_manifest")
        for rel, digest in manifest.items():
            if rel in UPSTREAM_HASHES and digest != UPSTREAM_HASHES[rel]:
                raise _Stop("upstream_hash")
            body = (trusted / rel).read_bytes()
            actual = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            if self._git("rev-parse", self.upstream_commit + ":" + rel) != actual:
                raise _Stop("upstream_blob")

    def _images(self, out, group, scope):
        build = out / "build"
        build.mkdir(mode=0o700)
        dockerfile = Path(__file__).with_name("Dockerfile")
        if _digest(dockerfile) != DOCKERFILE_SHA256:
            raise _Stop("dockerfile_hash")
        shutil.copyfile(dockerfile, build / "Dockerfile")
        task_dockerfile = (group / "env/Dockerfile").read_text()
        old = "FROM python:3.12-slim\n"
        if not task_dockerfile.startswith(old):
            raise _Stop("task_base")
        (build / "task.Dockerfile").write_text("FROM " + PYTHON_IMAGE + "\n" + task_dockerfile[len(old):])
        self._run(["docker", "version", "--format", "{{.Server.Version}}"], out / "docker-version.txt")
        self._run(["docker", "build", "--platform", PLATFORM, "-t", scope + "-solver", str(build)], out / "solver-build.log")
        self._run(["docker", "build", "--platform", PLATFORM, "-t", scope + "-task", "-f", str(build / "task.Dockerfile"), str(group / "env")], out / "task-build.log")
        images = [self._run(["docker", "image", "inspect", "--format", "{{.Id}}", scope + suffix]).stdout.decode().strip()
                  for suffix in ("-solver", "-task")]
        if not all(images):
            raise _Stop("image_identity")
        (out / "image-ids.txt").write_text("\n".join(images) + "\n")
        platform = self._run(["docker", "image", "inspect", "--format", "{{.Os}}/{{.Architecture}}", *images]).stdout.decode()
        (out / "image-platforms.txt").write_text(platform)
        if platform.splitlines() != [PLATFORM, PLATFORM]:
            raise _Stop("image_architecture")
        return images

    def _grade(self, out, task_path, image, prediction, name, filename):
        # Trusted official eval.sh is NEVER mounted in the solver container.
        try:
            self._run(["docker", "run", "--name", name, "--network", "none",
                       *_bind(task_path / "eval", "/trusted/eval"), *_bind(prediction, "/prediction/answer.json"),
                       image, "bash", "/trusted/eval/eval.sh", "/prediction/answer.json"], out / filename)
        except subprocess.TimeoutExpired:
            self._stop_timed_out(out, name)
            raise
        payload = json.loads((out / filename).read_text(), parse_constant=_reject_constant)
        _check_finite(payload)
        if not isinstance(payload, dict):
            raise _Stop("grader_json")
        return payload

    def _environment(self, out, scope, solver_image, task_image):
        network = scope + "-net"
        # Coordinator addition: Docker-native egress boundary; no host firewall.
        # https://docs.docker.com/reference/cli/docker/network/create/#internal
        self._run(["docker", "network", "create", "--internal", network], out / "network-id.txt")
        self._run(["docker", "network", "create", scope + "-egress"], out / "egress-network-id.txt")
        conf = out / "build/model-fwd.conf"
        conf.write_text(FORWARDER_CONF)
        self._run(["docker", "run", "-d", "--name", scope + "-fwd", "--network", scope + "-egress",
                   "--add-host", "host.docker.internal:host-gateway",
                   *_bind(conf, "/etc/nginx/nginx.conf"), NGINX_IMAGE], out / "fwd-id.txt")
        self._run(["docker", "network", "connect", "--alias", "model-fwd", network, scope + "-fwd"], out / "fwd-connect.txt")
        self._run(["docker", "run", "-d", "--name", scope + "-env", "--network", network,
                   "--network-alias", "task-env", "-e", "TASK_ENV_BIND=0.0.0.0", "-e", "TASK_ENV_PORT=9001",
                   "-e", "TASK_ENV_ENABLE_JUDGE=0", "--health-cmd",
                   'python3 -c "import urllib.request;urllib.request.urlopen(\\"http://127.0.0.1:9001/health\\")"',
                   task_image], out / "env-id.txt")
        deadline = time.monotonic() + self.timeout
        while True:
            state = self._run(["docker", "inspect", "--format", "{{.State.Health.Status}}", scope + "-env"]).stdout.decode().strip()
            if state == "healthy":
                break
            if state == "unhealthy":
                raise _Stop("environment_unhealthy")
            if state != "starting":
                raise _Stop("environment_health_state")
            if time.monotonic() >= deadline:
                raise _Stop("environment_timeout")
            time.sleep(1)  # reference recipe, local state poll; no health-budget invention.
        self._run(["docker", "run", "--name", scope + "-check", "--network", network,
                   solver_image, "python3", "-c", ENVIRONMENT_CHECK], out / "environment-check.json")
        if json.loads((out / "environment-check.json").read_text()) != {"health_status": "ok", "judge_http_status": 404}:
            raise _Stop("environment_check")

    def _solve(self, out, scope, image):
        work = out / "work"
        self._run(["docker", "create", "--name", scope + "-agent", "--platform", PLATFORM,
                   "--network", scope + "-net", *_bind(work, "/work", False),
                   *_bind(work / "input", "/work/input"), *_bind(work / "skill", "/work/skill"),
                   *_bind(work / "environment_access.md", "/work/environment_access.md"),
                   image, "bash", "-c", SOLVER_COMMAND, "run-one", (out / "prompt.txt").read_text().rstrip("\n")], out / "agent-id.txt")
        started = datetime.datetime.now(datetime.timezone.utc).isoformat()
        begin, attached = time.monotonic(), None
        try:
            attached = self._run(["docker", "start", "-a", scope + "-agent"], out / "exec-stdout.jsonl", check=False)
        except subprocess.TimeoutExpired:
            self._stop_timed_out(out, scope + "-agent")
            raise
        finally:
            # Save wall time even on a timeout, before any trace or exit inspection.
            _json(out / "attempt-timing.json", {"started_utc": started, "elapsed_seconds": time.monotonic() - begin,
                  "docker_attach_exit_code": attached.returncode if attached else None, "container_exit_code": None})
        status = int(self._run(["docker", "inspect", "--format", "{{.State.ExitCode}}", scope + "-agent"]).stdout)
        timing = json.loads((out / "attempt-timing.json").read_text())
        _json(out / "attempt-timing.json", {**timing, "container_exit_code": status})

    def _trace(self, out, scope):
        sessions = out / "sessions"
        sessions.mkdir(mode=0o700)
        self._run(["docker", "cp", scope + "-agent:/tmp/gdpevo-codex-home/sessions/.", str(sessions)])
        matching = []
        for path in sessions.rglob("rollout-*.jsonl"):
            if path.is_symlink():
                raise _Stop("unsafe_trace")
            text = path.read_text()
            rows = [json.loads(line) for line in text.splitlines() if line.strip()]
            if any(not isinstance(row, dict) or not isinstance(row.get("payload"), dict) for row in rows):
                raise _Stop("trace_json")
            meta = [r["payload"] for r in rows if r.get("type") == "session_meta"]
            if len(meta) == 1 and meta[0].get("cwd") == "/work" and scope in text:
                matching.append((path, rows, meta[0]))
        if len(matching) != 1:
            raise _Stop("primary_rollout")
        path, rows, meta = matching[0]
        if meta.get("model_provider") != "proxy":
            raise _Stop("trace_provider")
        turns = [r["payload"] for r in rows if r.get("type") == "turn_context"]
        if not turns or any(t.get("model") != MODEL for t in turns):
            raise _Stop("trace_model")
        usage = [r["payload"]["info"] for r in rows if r.get("type") == "event_msg"
                 and r.get("payload", {}).get("type") == "token_count" and r["payload"].get("info")]
        _json(out / "measurement.json", {"eval_attempt_id": scope, "condition": "self", "model": MODEL,
              "model_provider": "proxy", "trace": str(path), "trace_sha256": _digest(path),
              "token_usage": usage[-1].get("total_token_usage") if usage else None,
              "token_usage_source": "codex_session_trace" if usage else "missing", "cost_usd": None})
        path.chmod(0o600)

    def _check_stage(self, out, work):
        before = json.loads((out / "stage-manifest.json").read_text())
        for rel, digest in before.items():
            path = work / rel
            if path.is_symlink() or _digest(path) != digest:
                raise _Stop("stage_mutated")
        for directory in ("input", "skill"):
            if _manifest(work / directory) != {k[len(directory) + 1:]: v for k, v in before.items() if k.startswith(directory + "/")}:
                raise _Stop("stage_mutated")

    def _prediction(self, out, work):
        self._check_stage(out, work)
        if (work / "contamination_report.txt").exists():
            raise _Stop("contamination")
        timing = json.loads((out / "attempt-timing.json").read_text())
        if timing["container_exit_code"] != 0 or timing["docker_attach_exit_code"] != 0:
            raise _Stop("solver_exit")
        answer = work / "answer.json"
        if answer.is_symlink() or not answer.is_file():
            raise _Stop("missing_prediction")
        payload = json.loads(answer.read_text(), parse_constant=_reject_constant)
        _check_finite(payload)

    def _cleanup(self, scope):
        # All evidence is durable before cleanup. Never touch another run or prune.
        self._run(["docker", "rm", "-f", *[scope + suffix for suffix in ("-sanity", "-check", "-grade", "-agent", "-env", "-fwd")]])
        self._run(["docker", "network", "rm", scope + "-net", scope + "-egress"])
        self._run(["docker", "image", "rm", scope + "-solver", scope + "-task"])
