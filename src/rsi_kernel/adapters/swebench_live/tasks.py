"""Frozen SWE-bench-Live task identities read from receipt-hashed parquet files.

Only the six allowlisted columns are decoded; ``patch``/``test_patch``/``hints*``/
``FAIL_TO_PASS``/``PASS_TO_PASS`` are never read by adapter code (the pinned
harness loads them itself from the frozen dataset copy). Column choice is a
restriction, not a substitute for the dataset card:
https://huggingface.co/datasets/SWE-bench-Live/MultiLang/blob/eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3/README.md
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from typing import Callable, Iterable, Mapping

from ...candidate import content_id

# Harness split names; the evaluation command takes one of these as --split.
LANGUAGES = ("c", "cpp", "cs", "go", "java", "js", "rust", "ts")
ALLOWED_COLUMNS = ("instance_id", "repo", "created_at", "docker_image", "rebuild_cmds", "problem_statement")
# "<split>-<ordinal>-of-<total>.parquet" is the dataset repository layout.
PARQUET_NAME = re.compile(r"^data/(?P<lang>[a-z]+)-(?P<index>\d{5})-of-(?P<total>\d{5})\.parquet$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
# OCI content digest as written by "docker image inspect" RepoDigests.
_DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

Reader = Callable[[Path, tuple[str, ...]], Iterable[Mapping]]


class SweStop(RuntimeError):
    """Frozen-input STOP; nothing was parsed or solved after it."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _utc(value: object) -> datetime | None:
    """ISO-8601 to UTC; ``None`` when absent or unparseable.

    A naive timestamp is refused rather than guessed: the pinned revision has no
    such rows, and assuming a zone would misplace the cutoff boundary.
    """
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
    else:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _rebuild_sha256(cmds: tuple[str, ...]) -> str:
    # JSON canonical form: unambiguous for commands that contain separators.
    return hashlib.sha256(json.dumps(list(cmds), separators=(",", ":")).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SweTask:
    lang: str
    instance_id: str
    repo: str
    created_at: datetime | None
    docker_image: str
    rebuild_cmds: tuple[str, ...]
    problem_statement_sha256: str
    image_digest: str
    dataset_revision: str
    parquet_sha256: str
    rebuild_cmds_sha256: str = field(init=False)
    _statement: str = field(default="", repr=False, compare=False)

    def __post_init__(self):
        if self.lang not in LANGUAGES:
            raise ValueError(f"unknown harness split {self.lang!r}")
        for name in ("instance_id", "repo", "docker_image", "dataset_revision"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise ValueError(f"{name} must be a non-empty string")
        if self.created_at is not None and self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware UTC")
        if not _DIGEST.match(self.image_digest):
            raise ValueError("invalid image digest")
        if not all(isinstance(cmd, str) for cmd in self.rebuild_cmds):
            raise ValueError("rebuild_cmds must be strings")
        # Derived, never adopted from a caller: one canonical form of one field.
        object.__setattr__(self, "rebuild_cmds_sha256", _rebuild_sha256(self.rebuild_cmds))
        for digest in (self.problem_statement_sha256, self.rebuild_cmds_sha256, self.parquet_sha256):
            if not _SHA256.match(digest):
                raise ValueError("invalid sha256")

    @property
    def item_id(self) -> str:
        return f"{self.lang}/{self.instance_id}"

    @property
    def statement(self) -> str:
        """The only dataset text the solver receives; empty when not loaded here."""
        return self._statement

    @property
    def identity(self) -> str:
        # Task identity binds the statement bytes and the pinned image, not just the id.
        return content_id({
            "lang": self.lang, "instance_id": self.instance_id, "repo": self.repo,
            "created_at": "" if self.created_at is None else self.created_at.isoformat(),
            "docker_image": self.docker_image,
            "rebuild_cmds": json.dumps(list(self.rebuild_cmds)),
            "problem_statement_sha256": self.problem_statement_sha256,
            "rebuild_cmds_sha256": self.rebuild_cmds_sha256,
            "image_digest": self.image_digest,
            "dataset_revision": self.dataset_revision,
            "parquet_sha256": self.parquet_sha256,
        })


def _pyarrow_reader(path: Path, columns: tuple[str, ...]) -> list[dict]:
    # Optional at runtime: pyarrow is not a project dependency, only the freeze host needs it.
    # https://arrow.apache.org/docs/python/generated/pyarrow.parquet.ParquetFile.html#pyarrow.parquet.ParquetFile.read
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise SweStop("pyarrow is required to read the frozen parquet files; "
                      "install it on the freeze host or inject a reader") from exc
    table = pq.ParquetFile(path).read(columns=list(columns))
    return [dict(zip(columns, row)) for row in zip(*(column.to_pylist() for column in table.columns))]


def _verify(files: Mapping[str, Path], hashes: Mapping[str, str]) -> list[str]:
    if set(files) != set(hashes):
        raise SweStop("parquet file set does not match the frozen receipt")
    for name, digest in hashes.items():
        if not isinstance(digest, str) or not _SHA256.match(digest):
            raise SweStop(f"invalid receipt hash for {name}")
        try:
            actual = _sha256_file(files[name])
        except OSError as exc:
            raise SweStop(f"cannot read frozen parquet {name}") from exc
        if actual != digest:
            raise SweStop(f"parquet hash mismatch: {name}")
    return sorted(files)


def load_tasks(files: Mapping[str, Path], hashes: Mapping[str, str], *,
               dataset_revision: str, image_digests: Mapping[str, str],
               reader: Reader | None = None) -> tuple[SweTask, ...]:
    """Hash-verify every parquet, then read the six allowlisted columns.

    ``image_digests`` maps a ``docker_image`` name to the digest resolved once at
    freeze; the tag alone is mutable, so a row without one is a STOP.
    """
    if not isinstance(dataset_revision, str) or not dataset_revision:
        raise ValueError("dataset_revision must be a pinned revision")
    read = reader or _pyarrow_reader
    tasks: dict[str, SweTask] = {}
    # Hashes are checked for the whole set before a single row is decoded.
    for name in _verify(files, hashes):
        match = PARQUET_NAME.match(name)
        if match is None:
            raise SweStop(f"unexpected parquet path {name}")
        lang = match.group("lang")
        if lang not in LANGUAGES:
            raise SweStop(f"unknown harness split {lang!r}")
        parquet_sha256 = hashes[name]
        for row in read(Path(files[name]), ALLOWED_COLUMNS):
            try:
                instance_id, repo, created_at, docker_image, rebuild_cmds, statement = (
                    row[column] for column in ALLOWED_COLUMNS)
            except (KeyError, TypeError) as exc:
                raise SweStop(f"row missing an allowlisted column in {name}") from exc
            if not isinstance(instance_id, str) or not instance_id:
                raise SweStop(f"invalid instance_id in {name}")
            if not isinstance(repo, str) or not repo:
                raise SweStop(f"invalid repo for {instance_id}")
            if not isinstance(statement, str) or not isinstance(docker_image, str) or not docker_image:
                raise SweStop(f"invalid text field for {instance_id}")
            if rebuild_cmds is None:
                cmds: tuple[str, ...] = ()
            elif isinstance(rebuild_cmds, (list, tuple)) and all(isinstance(c, str) for c in rebuild_cmds):
                cmds = tuple(rebuild_cmds)
            else:
                raise SweStop(f"invalid rebuild_cmds for {instance_id}")
            digest = image_digests.get(docker_image)
            if not isinstance(digest, str):
                raise SweStop(f"no frozen image digest for {instance_id}")
            try:
                task = SweTask(
                    lang=lang, instance_id=instance_id, repo=repo, created_at=_utc(created_at),
                    docker_image=docker_image, rebuild_cmds=cmds,
                    problem_statement_sha256=hashlib.sha256(statement.encode("utf-8")).hexdigest(),
                    image_digest=digest,
                    dataset_revision=dataset_revision, parquet_sha256=parquet_sha256,
                    _statement=statement,
                )
            except ValueError as exc:
                raise SweStop(f"invalid task {instance_id}: {exc}") from exc
            if task.item_id in tasks:
                raise SweStop(f"duplicate instance {task.item_id}")
            tasks[task.item_id] = task
    if not tasks:
        raise SweStop("no task parsed")
    return tuple(tasks[key] for key in sorted(tasks))
