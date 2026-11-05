"""Kernel-carved splits with purposes, validated at load (design §4).

Pattern: Proteus recipes/config.py:146-154 (purpose validated at config load),
plus an ``adjudication`` purpose. Only dev may be selection-eligible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

PURPOSES = frozenset({"dev", "adjudication", "holdout"})
SELECTION_ELIGIBLE_PURPOSES = frozenset({"dev"})


class SplitConfigError(ValueError):
    pass


@dataclass(frozen=True)
class Split:
    name: str
    purpose: str
    selection_eligible: bool
    item_ids: frozenset[str]


@dataclass(frozen=True)
class Splits:
    by_name: Mapping[str, Split]

    def __post_init__(self) -> None:
        # Freeze authority at construction, including caller-owned dict aliases.
        object.__setattr__(self, "by_name", MappingProxyType(dict(self.by_name)))

    def item_ids(self, purpose: str) -> frozenset[str]:
        return frozenset().union(*(s.item_ids for s in self.by_name.values() if s.purpose == purpose))

    def dev_item_ids(self) -> frozenset[str]:
        return self.item_ids("dev")


def _parse(entry: Any) -> Split:
    if not isinstance(entry, dict):
        raise SplitConfigError("each split must be an object")
    name, purpose, eligible, ids = (
        entry.get("name"),
        entry.get("purpose"),
        entry.get("selection_eligible"),
        entry.get("item_ids"),
    )
    if not isinstance(name, str) or not name:
        raise SplitConfigError("split name must be a non-empty string")
    if purpose not in PURPOSES:
        raise SplitConfigError(f"split {name!r}: unknown purpose {purpose!r}")
    if not isinstance(eligible, bool):
        raise SplitConfigError(f"split {name!r}: selection_eligible must be a boolean")
    if eligible and purpose not in SELECTION_ELIGIBLE_PURPOSES:
        raise SplitConfigError(f"split {name!r}: {purpose} split cannot be selection-eligible")
    if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
        raise SplitConfigError(f"split {name!r}: item_ids must be a list of strings")
    if len(set(ids)) != len(ids):
        raise SplitConfigError(f"split {name!r}: duplicate item ids")
    return Split(name, purpose, eligible, frozenset(ids))


def load_splits(config: Mapping[str, Any]) -> Splits:
    entries = config.get("splits")
    if not isinstance(entries, list) or not entries:
        raise SplitConfigError("config must contain a non-empty 'splits' list")
    by_name: dict[str, Split] = {}
    seen: dict[str, str] = {}
    for entry in entries:
        split = _parse(entry)
        if split.name in by_name:
            raise SplitConfigError(f"duplicate split name {split.name!r}")
        for item in split.item_ids:
            if item in seen:
                raise SplitConfigError(f"item {item!r} overlaps splits {seen[item]!r} and {split.name!r}")
            seen[item] = split.name
        by_name[split.name] = split
    return Splits(by_name)


def load_splits_file(path: str | Path) -> Splits:
    return load_splits(json.loads(Path(path).read_text(encoding="utf-8")))
