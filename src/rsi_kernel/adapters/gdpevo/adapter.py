"""Thin text-only host adapter, design §4; no solver implementation or LLM calls.

GDPevo@5082a777: codex/guides/workflow.md:189–222 (staging/eval.sh),
judge_api.py:30–62 (score precedence), :168–179 (answer-safe feedback).
design §4/§7: host checks dev permissions; raw grader details never enter reflection.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping, Sequence

from ...archive import Archive, paths_overlap
from ...candidate import Candidate, content_id
from ...splits import Splits
from .runtime import GDPevoProposerRuntime, judge_off
from .scoring import score_from_evaluator
from .tasks import FrozenTask

Solver = Callable[[Candidate, str, Path, Path, Mapping[str, str]], dict | None]


def validate_skill(candidate: Candidate) -> str:
    """NAMED LOCAL RESTRICTION: exactly one UTF-8 SKILL.md, no support files."""
    if candidate.media_type != "text/plain" or set(candidate.components) != {"SKILL.md"}:
        raise ValueError("only a text-only SKILL.md package is admitted")
    if content_id(candidate.components) != candidate.id:
        raise ValueError("candidate hash mismatch")
    value = candidate.components["SKILL.md"]
    return value.decode("utf-8") if isinstance(value, bytes) else value


def _verify_task(root: Path, task: FrozenTask) -> Path:
    directory = task.directory(root)
    if any(path.is_symlink() for path in (directory, *directory.parents)):
        raise ValueError("symlink in frozen task path")
    files = {}
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("symlink in frozen task")
        if path.is_file():
            files[path.relative_to(directory).as_posix()] = path
    if set(files) != set(task.hashes):
        raise ValueError("frozen task hash manifest file set mismatch")
    for name, digest in task.hashes.items():
        if hashlib.sha256(files[name].read_bytes()).hexdigest() != digest:
            raise ValueError("frozen task hash mismatch")
    return directory


def _reject_constant(value: str) -> None:
    # RFC 8259 §6 excludes NaN and Infinity from JSON numbers.
    raise ValueError("non-finite evaluator JSON number")


def _check_finite(value: object) -> None:
    # parse_constant does not catch exponent overflow such as 1e999.
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite evaluator JSON number")
    if isinstance(value, dict):
        for child in value.values():
            _check_finite(child)
    elif isinstance(value, list):
        for child in value:
            _check_finite(child)


def _result(item_id: str, score: float | None, reason: str | None = None) -> dict:
    result = {"item_id": item_id, "score": score, "feedback": {"score": score, "correct": score == 1.0}}
    if reason:
        result["failure"] = {"reason": reason}
    return result


class GDPevoAdapter:
    def __init__(self, *, root: Path, champion: Candidate, tasks: Sequence[FrozenTask],
                 splits: Splits, solver: Solver, evaluator_timeout: float, work_dir: Path,
                 archive: Archive, solver_env: Mapping[str, str] | None = None):
        validate_skill(champion)
        if isinstance(evaluator_timeout, bool) or not math.isfinite(evaluator_timeout) or evaluator_timeout <= 0:
            raise ValueError("evaluator timeout must be a positive frozen config value")
        self.root, self.work_dir = Path(root).resolve(), Path(work_dir).resolve()
        if paths_overlap(self.root, self.work_dir):
            raise ValueError("attempt workspace must be separate from frozen source")
        if len({task.group for task in tasks}) != 1:
            raise ValueError("register a separate champion adapter for each task group")
        by_id = {task.item_id: task for task in tasks}
        if len(by_id) != len(tasks):
            raise ValueError("duplicate frozen task identity")
        if set(by_id) != set().union(*(split.item_ids for split in splits.by_name.values())):
            raise ValueError("splits must cover exactly the frozen tasks")
        for task in tasks:
            if (task.item_id in splits.item_ids("holdout")) != (task.subset == "test"):
                raise ValueError("test tasks must be holdout; train tasks must not be holdout")
        self.tasks = MappingProxyType(by_id)
        self.splits, self.solver, self.evaluator_timeout = splits, solver, evaluator_timeout
        self.solver_env = judge_off(solver_env)
        self.archive, self._champion = archive, champion

    def get_artifact(self) -> Candidate:
        validate_skill(self._champion)
        return self._champion

    def apply(self, approved_candidate_hash: str) -> None:
        # Approval is owned by the lead/host. This operation never swaps bytes.
        known = {self._champion.id} | {record["id"] for record in self.archive.public_view().candidates()}
        if approved_candidate_hash not in known:
            raise ValueError("unknown candidate hash")
        self.archive.record_decision({"candidate_id": approved_candidate_hash, "mode": "record-only"})

    def proposer_runtime(self, image: str, dev_data_dir: Path, output_dir: Path) -> GDPevoProposerRuntime:
        # design §7 (S3): source-repository mounts forbidden, staged dev inputs allowed.
        return GDPevoProposerRuntime(image, dev_data_dir, output_dir, deny_paths=(self.root, self.archive.private_dir))

    def evaluate(self, candidate: Candidate, item_ids: Sequence[str]) -> list[dict]:
        validate_skill(candidate)
        if not item_ids or len(set(item_ids)) != len(item_ids):
            raise ValueError("item ids must be a non-empty unique sequence")
        if not set(item_ids) <= self.splits.dev_item_ids():
            raise PermissionError("only dev items may be evaluated by this adapter")
        # STOP on drift before ANY solver runs, including later items in a batch.
        directories = [_verify_task(self.root, self.tasks[item]) for item in item_ids]
        self.work_dir.mkdir(parents=True, exist_ok=True)
        return [self._evaluate_one(candidate, item, directory) for item, directory in zip(item_ids, directories)]

    def _evaluate_one(self, candidate: Candidate, item_id: str, directory: Path) -> dict:
        # A fresh stage contains only input files; solver never receives eval/gold.
        with tempfile.TemporaryDirectory(dir=self.work_dir, prefix="attempt-") as temporary:
            # pathlib.resolve canonicalizes macOS /var and /tmp parent aliases;
            # solver boundary checks still reject links inside the canonical stage.
            # https://docs.python.org/3/library/pathlib.html#pathlib.Path.resolve
            stage = Path(temporary).resolve(strict=True)
            shutil.copytree(directory / "input", stage / "input")
            prediction = stage / "answer.json"
            try:
                solved = self.solver(candidate, item_id, stage / "input", prediction, self.solver_env)
            except Exception:
                return _result(item_id, None, "solver")
            if isinstance(solved, dict):
                # DockerSolver already used the isolated official grader and saved
                # persistent evidence; never regrade that answer on the host.
                # Legacy file-writing callables may return write()'s byte count.
                if solved.get("item_id") != item_id:
                    return _result(item_id, None, "solver_result")
                score = solved.get("score")
                if score is not None and (isinstance(score, bool) or not isinstance(score, (int, float))
                                          or not math.isfinite(score) or not 0 <= score <= 1):
                    return _result(item_id, None, "solver_result")
                _verify_task(self.root, self.tasks[item_id])
                validate_skill(candidate)
                result = _result(item_id, score)
                if "failure" in solved:
                    result["failure"] = solved["failure"]
                if "evidence_dir" in solved:
                    result["evidence_dir"] = solved["evidence_dir"]
                return result
            if not prediction.is_file() or prediction.is_symlink():
                return _result(item_id, None, "missing_prediction")
            try:
                json.loads(prediction.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                return _result(item_id, None, "json")
            _verify_task(self.root, self.tasks[item_id])
            validate_skill(candidate)
            return self._grade(item_id, directory, prediction)

    def _grade(self, item_id: str, directory: Path, prediction: Path) -> dict:
        try:
            completed = subprocess.run(
                ["/bin/sh", str(directory / "eval/eval.sh"), str(prediction)],
                cwd=directory, env={"PATH": os.defpath, "TASK_ENV_ENABLE_JUDGE": "0"},
                timeout=self.evaluator_timeout, check=True, capture_output=True,
            )
        except subprocess.TimeoutExpired:
            return _result(item_id, None, "timeout")
        except (subprocess.CalledProcessError, OSError):
            return _result(item_id, None, "exit")
        try:
            stdout = completed.stdout.decode("utf-8")
            completed.stderr.decode("utf-8")
            payload = json.loads(stdout, parse_constant=_reject_constant)
            _check_finite(payload)
        except (ValueError, RecursionError):
            return _result(item_id, None, "json")
        try:
            score = score_from_evaluator(payload)
        except (OverflowError, ValueError):
            score = None
        return _result(item_id, score, "score" if score is None else None)
