"""T3 execution: separate candidate prompt logic from trusted Codex config/meter.

NAMED LOCAL EXCEPTION T3-RESOURCE-VALUES: callers freeze all values; no defaults
or workload feasibility claim. Docker run resource/user/ulimit/security options:
https://docs.docker.com/reference/cli/docker/container/run/
"""

import json
import math
import os
import selectors
import subprocess
import time
from contextlib import ExitStack
from dataclasses import asdict, dataclass
from pathlib import Path

from ...candidate import Candidate
from ..gdpevo import solver_docker as sd
from ..gdpevo.adapter import validate_skill
from .adapter import COMPONENT, validate_code

DESTINATION = "/harness/solver.py"
# Trusted dispatch, not candidate bytes. Only T3 adds an option terminator before
# its untrusted positional prompt (Codex rust-v0.166.0 exec/src/cli.rs:81–85).
# The shared S4 command and its identity remain unchanged.
SOLVER_COMMAND = '''if [[ "$0" == "harness-code" ]]; then
  set -euo pipefail
  python3 /harness/solver.py < /harness/prompt.txt > /tmp/solver-result.json 2> /tmp/solver-stderr.log
  cat /tmp/solver-result.json
  cat /tmp/solver-stderr.log >&2
  exit
fi
''' + sd.SOLVER_COMMAND.replace('--json "$1"', '--json -- "$1"')


@dataclass(frozen=True)
class CodeLimits:
    cpus: float
    memory_bytes: int
    file_bytes: int

    def __post_init__(self):
        if (isinstance(self.cpus, bool) or not isinstance(self.cpus, (int, float))
                or not math.isfinite(self.cpus) or self.cpus <= 0):
            raise ValueError("cpus must be positive and finite")
        for value in (self.memory_bytes, self.file_bytes):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError("memory/file bytes must be positive integers")

    @staticmethod
    def _host_ids():
        uid, gid = os.getuid(), os.getgid()
        if uid == 0:
            raise sd._Stop("root_host_uid")
        return uid, gid

    def agent_argv(self):
        uid, gid = self._host_ids()
        return ["--user", f"{uid}:{gid}", "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges"]

    def docker_argv(self):
        uid, gid = self._host_ids()
        return ["--user", f"{uid}:{gid}", "--cpus", str(self.cpus),
                "--memory", str(self.memory_bytes), "--memory-swap", str(self.memory_bytes),
                "--ulimit", f"fsize={self.file_bytes}:{self.file_bytes}",
                "--cap-drop", "ALL", "--security-opt", "no-new-privileges"]


def _unique_object(pairs):
    # Same exact-field boundary as gdpevo_memory.library._unique_object.
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate solver output field")
    return dict(pairs)


def _safe(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink in code staging path")


class CodeDockerSolver(sd.DockerSolver):
    solver_command = SOLVER_COMMAND

    def __init__(self, *, champion: Candidate, skill: Candidate, limits: CodeLimits, **config):
        validate_code(champion, champion)
        validate_skill(skill)
        if not isinstance(limits, CodeLimits):
            raise ValueError("frozen CodeLimits required")
        self.champion, self.skill, self.limits = champion, skill, limits
        super().__init__(**config)
        # Bind non-code runtime values before optimise/final; changing a fixed skill
        # or resource value is identity drift, not a silent acceptance rerun.
        self.execution_identity = json.dumps({"champion": champion.id, "skill": skill.id,
            "limits": asdict(limits), "timeout": self.timeout}, sort_keys=True)

    def _stage(self, candidate, task, input_dir, out, scope):
        self.limits.docker_argv()  # Refuse root before staging's external commands.
        text = validate_code(candidate, self.champion)
        code = out / "harness"
        _safe(code / COMPONENT)
        trusted, work, group, task_path = super()._stage(self.skill, task, input_dir, out, scope)
        code.mkdir(mode=0o755)
        (code / COMPONENT).write_text(text, encoding="utf-8")
        (code / COMPONENT).chmod(0o444)
        (code / "prompt.txt").write_bytes((out / "prompt.txt").read_bytes())
        (code / "prompt.txt").chmod(0o444)
        sd._json(out / "code-manifest.json", sd._manifest(code))
        # Same-UID containers need no cross-user chmods; /work stays private.
        return trusted, work, group, task_path

    def _check_stage(self, out, work):
        super()._check_stage(out, work)
        code = out / "harness"
        _safe(code)
        if sd._manifest(code) != json.loads((out / "code-manifest.json").read_text()):
            raise ValueError("code stage hash mismatch")

    def _solver_options(self, out):
        return self.limits.agent_argv()

    def _collect_logic(self, argv, output):
        """Drain both PIPEs with bounded writes, never communicate()'s unbounded buffer.

        Stdlib Popen PIPE + selectors: https://docs.python.org/3/library/selectors.html
        Read only the remaining frozen allowance plus one overflow-detection byte.
        This boundary applies only to candidate logic, not the data-only runner.
        """
        env = sd._DOCKER_ENV.get()
        if env is None:
            raise sd._Stop("docker_environment")
        name = argv[argv.index("--name") + 1]
        deadline = time.monotonic() + self.timeout
        with ExitStack() as stack:
            outputs = [stack.enter_context(path.open("wb"))
                       for path in (output, output.with_suffix(output.suffix + ".stderr"))]
            for file in outputs:
                os.fchmod(file.fileno(), 0o600)
            with selectors.DefaultSelector() as selector, subprocess.Popen(
                    argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=dict(env)) as process:
                for pipe, file in zip((process.stdout, process.stderr), outputs):
                    selector.register(pipe, selectors.EVENT_READ, [file, self.limits.file_bytes])
                try:
                    while selector.get_map():
                        remaining = deadline - time.monotonic()
                        if remaining <= 0:
                            raise subprocess.TimeoutExpired(argv, self.timeout)
                        for key, _ in selector.select(remaining):
                            file, budget = key.data
                            chunk = os.read(key.fd, budget + 1)
                            if not chunk:
                                selector.unregister(key.fileobj)
                                continue
                            file.write(chunk[:budget])
                            if len(chunk) > budget:
                                raise sd._Stop("logic_output_limit")
                            key.data[1] -= len(chunk)
                    status = process.wait(timeout=max(0, deadline - time.monotonic()))
                except BaseException:
                    process.kill()
                    process.wait()
                    self._stop_timed_out(output.parent, name)
                    raise
                finally:
                    process.stdout.close()
                    process.stderr.close()
            if status:
                raise subprocess.CalledProcessError(status, argv)

    def _logic_payload(self, out, name):
        output = out / "logic.json"
        streams = (output, output.with_suffix(output.suffix + ".stderr"))
        if any(path.stat().st_size > self.limits.file_bytes for path in streams):
            self._stop_timed_out(out, name)
            raise sd._Stop("logic_output_limit")
        return json.loads(output.read_text(), object_pairs_hook=_unique_object)

    def _solve(self, out, scope, image):
        self._check_stage(out, out / "work")
        name = scope + "-logic"
        self._collect_logic(["docker", "run", "--name", name, "--platform", sd.PLATFORM,
                             "--network", "none", *self.limits.docker_argv(),
                             "--read-only", "--tmpfs", "/tmp",
                             *sd._bind(out / "work", "/work"), *sd._bind(out / "harness", "/harness"),
                             image, "bash", "-c", SOLVER_COMMAND, "harness-code"],
                            out / "logic.json")
        payload = self._logic_payload(out, name)
        if (not isinstance(payload, dict) or set(payload) != {"prompt"}
                or not isinstance(payload["prompt"], str) or not payload["prompt"].strip()
                or "\0" in payload["prompt"]):
            raise ValueError("solver logic output must contain only a prompt")
        self._check_stage(out, out / "work")
        (out / "prompt.txt").write_text(payload["prompt"] + "\n")
        self._run(["docker", "rm", "-f", name])
        # No code mount in the trusted agent; its configuration and sessions are private.
        super()._solve(out, scope, image)

    def _stop_timed_out(self, out, name):
        super()._stop_timed_out(out, name)
        self._run(["docker", "rm", "-f", name], out / (name + "-remove.log"))
        state = self._run(["docker", "inspect", name], check=False)
        if state.returncode == 0:
            raise sd._Stop("timeout_container_retained")
