"""Shared supplemental publication-marker guard; not a confidentiality proof."""

import glob
import json
import re
import sys
from pathlib import Path

# Built from fragments so this file never matches itself; no file is exempt.
# Private host/repo names are deliberately not listed: naming them here would publish them.
MARKERS = {
    "lane decision id": r"\bR-\d{3,}\b",
    "lane research id": r"\bR-[A-Z]\b",
    "build memo": "BUILD" + "-MEMO",
    "decision log": "DECISIONS" + "-RSI",
    "local home path": "/" + "Users/",
    "local temp path": "/private" + "/tmp",
    "grant requirement ids": r"\bB1\s*[–-]\s*B13\b",
    "local proxy": r"\b" + "o" + "cx" + r"\b",
    "model gateway": "Smart" + "TiTu",
    "lane workspace": "tg" + "-work",
    "other product": "Trust" + " Gateway",
    "other product repo": "TG" + "-Java",
    "grant spec item": r"\b" + "SP" + r"EC B\d+\b",
    "internal plan section": r"\b" + "PL" + r"AN §",
    "internal review rule": "RULE" + "-1",
}
# Case-insensitive so env-style spellings (e.g. NAME_API_KEY) are caught too.
# https://docs.python.org/3/library/re.html#re.IGNORECASE
PATTERN = re.compile("|".join(f"(?:{p})" for p in MARKERS.values()), re.IGNORECASE)



def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield key
            yield from _strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from _strings(child)


def scan_json_files(patterns):
    """Fail closed on unreadable/non-JSON files or markers in decoded strings.

    Patterns are the upload allowlist, not an output directory. Optional missing
    reports are allowed on aborted jobs; an empty artifact is never allowed.
    """
    paths = sorted({Path(name) for pattern in patterns for name in glob.glob(pattern)})
    if not paths:
        raise ValueError("no publication artifact files")
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError("publication artifacts must be regular JSON files")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if any(PATTERN.search(text) for text in _strings(payload)):
            raise ValueError("publication marker in artifact")
    return paths


if __name__ == "__main__":
    scan_json_files(sys.argv[1:])
