"""Predictions file and harness-report parsing for the official resolved endpoint.

Schema source, read at harness commit ``091279261203b243386adf256b2b107656013dbf``:
https://github.com/microsoft/SWE-bench-Live/blob/091279261203b243386adf256b2b107656013dbf/evaluation/evaluation.py

- predictions are a JSON object keyed by instance id, each ``{"model_patch": str}``
  (:269-274 read the file, :314-319 take ``model_patch``);
- the per-instance report is ``report.json`` with ``instance_id``, ``resolved`` and the
  two test groups (:146-160 reuse, :176-199 write);
- the aggregate ``results.json`` carries the outcome lists that decide the category
  (:209-215 empty patches never reach a container, :234-246 success/failure/error/
  incomplete, :247-250 the counts).

Resolution itself (:188-193) is the harness's, not ours: we only read the flag. An
empty submission is a real 0.0 with its category preserved (disposition 1); anything
the harness did not account for stays unscored rather than becoming a zero.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

RESOLVED = "resolved"
UNRESOLVED = "unresolved"
EMPTY_PATCH = "empty_patch"
ERROR = "error"
INCOMPLETE = "incomplete"
MISSING = "missing"
UNACCOUNTED = "unaccounted"
CONFLICT = "conflict"

# Failure reasons reuse the missing-result vocabulary; a zero is never a failure.
HARNESS_ERROR = "harness_error"
HARNESS_REPORT_MISSING = "harness_report_missing"

_LISTS = ("submitted_ids", "empty_patch_ids", "success_ids", "failure_ids",
          "error_ids", "incomplete_ids")
# The mutually exclusive outcome lists an instance may appear in, and no more than one of.
OUTCOMES = ("success_ids", "failure_ids", "empty_patch_ids", "error_ids", "incomplete_ids")


@dataclass(frozen=True)
class Grade:
    score: float | None
    category: str
    reason: str | None = None


def predictions(patches: Mapping[str, str], instance_ids: Sequence[str]) -> dict:
    """Exactly the planned instances, each with one patch; identity mismatches stop."""
    if not isinstance(patches, Mapping) or not instance_ids:
        raise ValueError("predictions require a patch mapping and the evaluated instance ids")
    ids = list(instance_ids)
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and i for i in ids):
        raise ValueError("instance ids must be non-empty and unique")
    if set(patches) != set(ids):
        raise ValueError("predictions must cover exactly the evaluated instances")
    if not all(isinstance(patch, str) for patch in patches.values()):
        raise ValueError("every model_patch must be a string")
    return {instance_id: {"model_patch": patches[instance_id]} for instance_id in ids}


def read_report(path: Path, instance_id: str) -> dict | None:
    """The instance report, or ``None`` when it is absent, unreadable or another instance's."""
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(payload, dict) or payload.get("instance_id") != instance_id:
        return None
    return payload


def _checked_lists(results: Mapping) -> dict[str, list[str]]:
    if not isinstance(results, Mapping):
        raise ValueError("harness results must be an object")
    if not isinstance(results.get("submitted"), int):
        raise ValueError("harness results must report submissions")
    out = {}
    for key in _LISTS:
        value = results.get(key)
        if not isinstance(value, list) or not all(isinstance(i, str) for i in value):
            raise ValueError(f"harness results field {key} must be a list of instance ids")
        out[key] = value
    return out


def _from_report(report: dict | None, instance_id: str, resolved: bool) -> Grade:
    if report is None:
        return Grade(None, MISSING, HARNESS_REPORT_MISSING)
    if report["instance_id"] != instance_id or report.get("resolved") is not resolved:
        # The summary and the report disagree; never pick one side silently.
        return Grade(None, MISSING, HARNESS_ERROR)
    return Grade(1.0 if resolved else 0.0, RESOLVED if resolved else UNRESOLVED)


def score_from_report(instance_id: str, results: Mapping, report: dict | None = None) -> Grade:
    """One score per instance from the aggregate summary plus its own report.

    ``report`` is the parsed ``report.json`` for this instance (``None`` if absent).
    Explicit outcomes are adopted; error, incomplete and unaccounted stay ``None``.
    """
    if not isinstance(instance_id, str) or not instance_id:
        raise ValueError("instance_id must be a non-empty string")
    lists = _checked_lists(results)
    if instance_id not in lists["submitted_ids"]:
        return Grade(None, MISSING, HARNESS_REPORT_MISSING)
    # The harness itself writes one outcome per instance (:234-246); two lists means a
    # corrupted or hand-edited summary. First-match would let success_ids win over
    # error_ids and score a failure as 1.0, so a conflict is never resolved by order.
    categories = [key for key in OUTCOMES if instance_id in lists[key]]
    if len(categories) > 1:
        return Grade(None, CONFLICT, HARNESS_ERROR)
    if instance_id in lists["success_ids"]:
        return _from_report(report, instance_id, True)
    if instance_id in lists["failure_ids"]:
        return _from_report(report, instance_id, False)
    if instance_id in lists["empty_patch_ids"]:
        # evaluation.py:209-215: an empty patch is submitted but never graded.
        return Grade(0.0, EMPTY_PATCH)
    if instance_id in lists["error_ids"]:
        return Grade(None, ERROR, HARNESS_ERROR)
    if instance_id in lists["incomplete_ids"]:
        return Grade(None, INCOMPLETE, HARNESS_ERROR)
    # Listed as submitted but in no outcome list: no score, never an imputed zero.
    return Grade(None, UNACCOUNTED, HARNESS_ERROR)


def score_all(instance_ids: Iterable[str], results: Mapping,
              reports: Mapping[str, dict] | None = None) -> dict[str, Grade]:
    reports = reports or {}
    return {instance_id: score_from_report(instance_id, results, reports.get(instance_id))
            for instance_id in instance_ids}


def summary_counts(grades: Iterable[Grade]) -> dict[str, int]:
    """Per-category counts, reporting operational STOPs separately from quality FAILs."""
    counts: dict[str, int] = {}
    for grade in grades:
        counts[grade.category] = counts.get(grade.category, 0) + 1
    return dict(sorted(counts.items()))
