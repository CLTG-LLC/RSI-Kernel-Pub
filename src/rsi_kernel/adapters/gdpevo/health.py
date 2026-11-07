"""Lead-run pre-run health check for one registered group (E2 prereg §3 STOP 3, issue #113).

Reuses DockerSolver's own staging, image build and environment start/check (Docker
health ``healthy``, ``/health`` answers, judge POST returns 404 with
``TASK_ENV_ENABLE_JUDGE=0``). No solve and no grading run; nothing staged is printed.

    python -m rsi_kernel.adapters.gdpevo.health --root ROOT --group G --evidence-dir DIR
"""

from __future__ import annotations

import argparse
import json
import secrets
import subprocess
import sys
from pathlib import Path

from ...candidate import Candidate
from . import solver_docker as sd
from .pilot import REGISTERED_GROUPS, TIMEOUT, _sha
from .tasks import FrozenTask


def check(root: Path, group: str, evidence_dir: Path) -> dict:
    directory = root / "data/task_groups" / group / "train_tasks/001"
    task = FrozenTask(group, "train", "001", {p.relative_to(directory).as_posix(): _sha(p)
                                              for p in sorted(directory.rglob("*")) if p.is_file()})
    solver = sd.DockerSolver(root=root, tasks=[task], evidence_dir=evidence_dir, timeout=TIMEOUT)
    scope = "gdp-" + secrets.token_hex(4)
    out = solver.evidence_dir / scope
    out.mkdir(parents=True, mode=0o700)
    token = sd._DOCKER_ENV.set(None)
    phase = "staging"
    try:
        # Same base staging as the calibration replay; the placeholder skill is never solved.
        _, _, group_dir, _ = sd.DockerSolver._stage(
            solver, Candidate({"SKILL.md": "health check\n"}, "text/plain"), task, directory / "input", out, scope)
        phase = "docker_connection"
        solver._docker_environment(out)
        phase = "images"
        solver_image, task_image = solver._images(out, group_dir, scope)
        phase = "environment"
        solver._environment(out, scope, solver_image, task_image, sd._environment_port(group))
        checked = json.loads((out / "environment-check.json").read_text())
        phase = "cleanup"
        solver._run(["docker", "rm", "-f", *[scope + s for s in ("-check", "-env", "-fwd")]])
        solver._run(["docker", "network", "rm", scope + "-net", scope + "-egress"])
        solver._run(["docker", "image", "rm", scope + "-solver", scope + "-task"])
        return {"group": group, "status": "ok", "health": checked["health"],
                "judge_http_status": checked["judge_http_status"], "judge_env": "TASK_ENV_ENABLE_JUDGE=0",
                "evidence_dir": str(out)}
    except (KeyError, OSError, ValueError, subprocess.SubprocessError, sd._Stop) as error:
        # Resources are retained as evidence on a STOP, as in DockerSolver.
        return {"group": group, "status": "STOP", "reason": error.reason if isinstance(error, sd._Stop) else phase}
    finally:
        sd._DOCKER_ENV.reset(token)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m rsi_kernel.adapters.gdpevo.health")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--group", required=True, choices=REGISTERED_GROUPS)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    result = check(args.root, args.group, args.evidence_dir)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
