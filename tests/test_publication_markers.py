"""Publication guard (issue #25): tracked files must not carry internal markers.

Internal lane ids, private notes, local paths and routing names must not reach
a published tree. Every hit fails; there is no allowlist.
"""

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def files():
    # Tracked plus untracked-but-not-ignored, so new files are checked before commit.
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT, check=True, capture_output=True,
    ).stdout.decode()
    return [f for f in out.split("\0") if f and (ROOT / f).is_file()]


def hits(paths):
    found = []
    for rel in paths:
        m = PATTERN.search(rel)
        if m:
            found.append(f"{rel}:0: {m.group(0)}")
        text = (ROOT / rel).read_text(encoding="utf-8", errors="replace")
        for n, line in enumerate(text.splitlines(), 1):
            m = PATTERN.search(line)
            if m:
                found.append(f"{rel}:{n}: {m.group(0)}")
    return found


def test_no_internal_markers_in_tracked_files():
    assert hits(files()) == []


def test_every_marker_is_detected():
    samples = ["R-0" + "15", "R-1" + "93", "R-" + "K", "BUILD" + "-MEMO", "DECISIONS" + "-RSI", "/" + "Users/x",
               "/private" + "/tmp/x", "B1" + "–B13", "o" + "cx proxy", "Smart" + "TiTu",
               "SMART" + "TITU_API_KEY", "tg" + "-work", "Trust" + " Gateway", "tg" + "-java",
               "SP" + "EC B4"]
    for s in samples:
        assert PATTERN.search(s), s
    for s in ["R-squared", "RSI-Kernel", "B1", "box", "PR #12", "GPT-6"]:
        assert not PATTERN.search(s), s
