"""Candidate harness artifact: data-only components, content-addressed (design §4, §5)."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Union

Component = Union[str, bytes]

# Data-only media types. No executable types are admitted (issue #1, design §6 T1).
ALLOWED_MEDIA_TYPES = frozenset(
    {"text/plain", "application/json", "application/yaml", "application/x-safetensors"}
)


def _as_bytes(value: Component) -> bytes:
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8")
    raise TypeError(f"component value must be str or bytes, got {type(value).__name__}")


def content_id(components: Mapping[str, Component]) -> str:
    """sha256 over components sorted by name; each name and value is length-prefixed."""
    h = hashlib.sha256()
    for name in sorted(components):
        for part in (name.encode("utf-8"), _as_bytes(components[name])):
            h.update(len(part).to_bytes(8, "big"))
            h.update(part)
    return h.hexdigest()


@dataclass(frozen=True)
class Candidate:
    components: Mapping[str, Component]
    media_type: str
    parent_ids: tuple[str, ...] = ()
    id: str = field(init=False)

    def __post_init__(self) -> None:
        if self.media_type not in ALLOWED_MEDIA_TYPES:
            raise ValueError(f"media type not allowed: {self.media_type!r}")
        frozen = MappingProxyType(dict(self.components))
        object.__setattr__(self, "components", frozen)
        object.__setattr__(self, "parent_ids", tuple(self.parent_ids))
        object.__setattr__(self, "id", content_id(frozen))
