"""Frozen GDPevo task identities and explicit kernel carving (design §4).

Layout: GDPevo@5082a777 data/README.md:30–78.
The per-group dev task list is a NAMED LOCAL EXCEPTION, never a default ratio.
"""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping, Sequence

from ...splits import Splits, load_splits


def _segment(value: str) -> bool:
    return isinstance(value, str) and bool(value) and value not in {".", ".."} and "/" not in value and "\\" not in value


@dataclass(frozen=True)
class FrozenTask:
    group: str
    subset: str
    task_id: str
    hashes: Mapping[str, str]

    def __post_init__(self):
        if not _segment(self.group) or not _segment(self.task_id) or self.subset not in {"train", "test"}:
            raise ValueError("invalid frozen group/task path")
        for name, digest in self.hashes.items():
            path = PurePosixPath(name)
            if not name or path == PurePosixPath(".") or path.is_absolute() or ".." in path.parts or "\\" in name:
                raise ValueError("invalid hash manifest path")
            if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
                raise ValueError("invalid sha256 hash")
        if not {"input/prompt.txt", "eval/eval.sh"} <= self.hashes.keys():
            raise ValueError("hash manifest must bind input and official wrapper")
        object.__setattr__(self, "hashes", MappingProxyType(dict(self.hashes)))

    @property
    def item_id(self) -> str:
        return f"{self.group}/{self.subset}/{self.task_id}"

    def directory(self, root: Path) -> Path:
        return root / "data/task_groups" / self.group / f"{self.subset}_tasks" / self.task_id


def carve_splits(tasks: Sequence[FrozenTask], dev_tasks_by_group: Mapping[str, Sequence[str]]) -> Splits:
    groups = {task.group for task in tasks}
    if not groups or set(dev_tasks_by_group) != groups:
        raise ValueError("carving must explicitly cover exactly the frozen groups")
    dev = set()
    for group, ids in dev_tasks_by_group.items():
        train_ids = {task.task_id for task in tasks if task.group == group and task.subset == "train"}
        if len(ids) != len(set(ids)) or not set(ids) <= train_ids:
            raise ValueError("invalid dev task assignment")
        dev.update(f"{group}/train/{task_id}" for task_id in ids)
    return load_splits({"splits": [
        {"name": purpose, "purpose": purpose, "selection_eligible": purpose == "dev", "item_ids": [
            task.item_id for task in tasks if (
                "holdout" if task.subset == "test" else "dev" if task.item_id in dev else "adjudication"
            ) == purpose
        ]} for purpose in ("dev", "adjudication", "holdout")
    ]})
