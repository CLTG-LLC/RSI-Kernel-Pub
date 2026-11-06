"""File-based owner approval: file the request, wait for the owner's record (issue #60).

Moved from the GDPevo pilot (``_file_approval`` / ``_wait_for_owner``) so the console
entry can share it without GDPevo imports. Same local-state poll as the runner's health
wait; no timeout (the operator stops it). The request is published atomically with
``os.replace``, so a reader never sees a partial file, and the owner publishes the
approval the same way: https://docs.python.org/3/library/os.html#os.replace
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Callable

from .loop import ApprovalRecord


def wait_for_file(path: Path, interval: float = 1.0) -> None:
    while not Path(path).exists():
        time.sleep(interval)


def _publish(path: Path, text: str) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.unlink(missing_ok=True)  # a stale temp, or a symlink planted at its name
    with open(temp, "x", encoding="utf-8") as stream:  # O_EXCL: never follows a symlink
        stream.write(text)
    os.replace(temp, path)  # replaces a symlink at path rather than following it


def file_approval(request_path: Path, approval_path: Path, wait: Callable[[], None]):
    def approval(request):
        _publish(Path(request_path), json.dumps(request.__dict__, indent=2, sort_keys=True, allow_nan=False) + "\n")
        wait()
        try:
            return ApprovalRecord(**json.loads(Path(approval_path).read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return None  # malformed: accept() records not_updated
    return approval
