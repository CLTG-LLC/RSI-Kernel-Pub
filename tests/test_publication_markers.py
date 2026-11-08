"""Publication guard (issue #25): tracked files must not carry internal markers.

Internal lane ids, private notes, local paths and routing names must not reach
a published tree. Every hit fails; there is no allowlist.
"""

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
from rsi_kernel.publication import PATTERN


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
