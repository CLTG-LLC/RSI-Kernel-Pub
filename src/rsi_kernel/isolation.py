"""Proposer runtime launcher: Docker container with no network, an allowlisted
environment, and only the dev data (read-only) and an output dir mounted.

- ``--network none``: https://docs.docker.com/engine/network/drivers/none/
- Allowlist environment: only variables passed explicitly via ``-e NAME=VALUE``
  (Harness² allowlist env pattern, design §5/§6). ``docker run`` does not
  inherit the host environment.
- Mounts: ``--mount type=bind,...,readonly`` (Docker bind-mount docs:
  https://docs.docker.com/engine/storage/bind-mounts/).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .archive import paths_overlap

DEV_TARGET = "/data/dev"
OUT_TARGET = "/out"
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _mount(source: Path, target: str, readonly: bool) -> str:
    src = str(Path(source).resolve())
    if "," in src or "=" in src:
        raise ValueError(f"mount source contains a reserved character: {src}")
    return f"type=bind,source={src},target={target}" + (",readonly" if readonly else "")


@dataclass(frozen=True)
class ProposerRuntime:
    image: str
    dev_data_dir: Path
    output_dir: Path
    deny_paths: tuple[Path, ...] = ()

    def docker_argv(self, command: Sequence[str], env: Mapping[str, str] | None = None) -> list[str]:
        for source in (self.dev_data_dir, self.output_dir) if self.deny_paths else ():
            # Reject ancestors too: mounting a parent exposes protected children.
            if any(paths_overlap(source, protected) for protected in self.deny_paths):
                raise PermissionError("mount overlaps a protected path")
            if any(paths_overlap(path, protected) for path in Path(source).rglob("*") for protected in self.deny_paths):
                raise PermissionError("mount overlaps a protected path")
        if paths_overlap(self.dev_data_dir, self.output_dir):
            raise ValueError("dev data and output must be separate, non-nested directories")
        argv = ["docker", "run", "--rm", "--network", "none"]
        for name, value in (env or {}).items():
            if not _ENV_NAME.match(name):
                raise ValueError(f"invalid environment variable name {name!r}")
            argv += ["-e", f"{name}={value}"]
        argv += ["--mount", _mount(self.dev_data_dir, DEV_TARGET, readonly=True)]
        argv += ["--mount", _mount(self.output_dir, OUT_TARGET, readonly=False)]
        return argv + [self.image, *command]
