# MIT License
# Copyright (c) 2026 Jason Lee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Data-only briefs, deterministic rendering, and noop write-guard port.

Ported logic: huacnlee/noop@246561d04d444f90ed634af5cede9f2fd682a22a,
cloud/src/tools.ts:43,47–56,344–357 and src/brain.ts:75–97.
https://github.com/huacnlee/noop/blob/246561d04d444f90ed634af5cede9f2fd682a22a/cloud/src/tools.ts#L43-L56
At this SHA, src/tools.ts has moved to cloud/src/tools.ts.
The target regex is adapted to opaque entry JSON components (design §3).
Brief fields: https://arxiv.org/html/2611.05306v1#A1 (Appendix A).
The JSON field names and rendering are a named local adapter template, not a
paper-defined wire format. Hashing uses the unchanged kernel Candidate.
"""

import json
import re
from typing import Mapping, Sequence

from ...candidate import Candidate, content_id


ENTRY_TARGET = re.compile(r"entries/(e[1-9][0-9]*)\.json", re.ASCII)
BRIEF_FIELDS = frozenset({"task_pattern", "action", "completion_criteria", "pointers"})


def validate_entry(entry: object) -> dict:
    if type(entry) is not dict or set(entry) != BRIEF_FIELDS:
        raise ValueError("entry must contain exactly the brief fields")
    if any(type(entry[key]) is not str or not entry[key].strip()
           for key in BRIEF_FIELDS - {"pointers"}):
        raise ValueError("brief text fields must be non-empty strings")
    if type(entry["pointers"]) is not list or any(
        type(pointer) is not str or not pointer.strip() for pointer in entry["pointers"]
    ):
        raise ValueError("brief pointers must be a list of non-empty strings")
    return {**entry, "pointers": list(entry["pointers"])}


def _unique_object(pairs):
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate JSON field")
    return dict(pairs)


def parse_entry(text: str | bytes) -> dict:
    try:
        return validate_entry(json.loads(text, object_pairs_hook=_unique_object))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ValueError("invalid entry JSON brief") from None


def read_library(candidate: Candidate) -> dict[str, dict]:
    if candidate.media_type != "application/json":
        raise ValueError("library must be JSON data")
    if content_id(candidate.components) != candidate.id:
        raise ValueError("library candidate hash mismatch")
    entries = {}
    for target, payload in candidate.components.items():
        match = ENTRY_TARGET.fullmatch(target)
        if match is None:
            raise ValueError("writes are limited to library entry targets")
        entries[match[1]] = parse_entry(payload)
    return {eid: entries[eid] for eid in sorted(entries, key=lambda value: int(value[1:]))}


def _candidate(entries: Mapping[str, dict], parent_ids=()) -> Candidate:
    components = {f"entries/{eid}.json": json.dumps(validate_entry(entry), sort_keys=True,
                  ensure_ascii=False, allow_nan=False, separators=(",", ":"))
                  for eid, entry in entries.items()}
    candidate = Candidate(components, "application/json", parent_ids=parent_ids)
    read_library(candidate)
    return candidate


def library_candidate(entries: Sequence[dict]) -> Candidate:
    """The adapter, never the proposer, issues ids from the kernel registry namespace."""
    return _candidate({f"e{index}": entry for index, entry in enumerate(entries, start=1)})


def admit(champion: Candidate, draft: dict, choice: str) -> Candidate | None:
    """Exactly one existing id for replacement; exact-duplicate add is skipped.

    Merge and revise use the LLM's complete replacement brief, retaining the
    selected id. D4 advises the target, never generates or combines entry text.
    """
    entries, draft = read_library(champion), validate_entry(draft)
    if choice == "discard":
        return None
    if choice == "add":
        if draft in entries.values():
            return None
        eid = f"e{max((int(eid[1:]) for eid in entries), default=0) + 1}"
    else:
        if type(choice) is not str or ":" not in choice:
            raise ValueError("invalid library operation")
        operation, eid = choice.split(":", 1)
        if operation not in {"merge", "revise"} or ENTRY_TARGET.fullmatch(f"entries/{eid}.json") is None:
            raise ValueError("invalid library operation target")
        # Validated unique ids make membership an exactly-one-entry match.
        if eid not in entries:
            raise ValueError("replacement must match exactly one existing entry")
        if entries[eid] == draft:
            return None
    return _candidate({**entries, eid: draft}, parent_ids=(champion.id,))


def render_skill(candidate: Candidate) -> Candidate:
    entries = read_library(candidate)
    sections = ["# Memory / skill library\n"]
    for eid in sorted(entries, key=lambda value: int(value[1:])):
        entry = entries[eid]
        sections.append(f"\n## {eid}\nTask pattern: {entry['task_pattern']}\n"
                        f"Action / intent: {entry['action']}\n"
                        f"Completion criteria: {entry['completion_criteria']}\nPointers:\n"
                        + "".join(f"- {pointer}\n" for pointer in entry["pointers"]))
    return Candidate({"SKILL.md": "".join(sections)}, "text/plain", parent_ids=(candidate.id,))
