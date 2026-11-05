"""Review PR9 S2: the Java host tests must fail, not skip, in CI when javac is missing."""

import os
import subprocess
import sys
from pathlib import Path

MODULE = Path(__file__).with_name("test_java_host.py")


def _run(tmp_path, ci, javac=None):
    env = {k: v for k, v in os.environ.items() if k != "CI"}
    # javac=None: empty dir, so no javac and no java are found at all. Otherwise prepend
    # the given dir so its (fake) javac wins over anything else on PATH.
    env["PATH"] = str(tmp_path) if javac is None else os.pathsep.join([str(javac), env.get("PATH", "")])
    if ci:
        env["CI"] = "true"
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", str(MODULE)],
        env=env, capture_output=True, text=True, timeout=120,
    )


def _fake_javac(tmp_path, exit_code=1):
    """A javac that exists but does not work: macOS /usr/bin/javac without a JDK."""
    d = tmp_path / "fakejava"
    d.mkdir()
    script = d / "javac"
    script.write_text(f"#!/bin/sh\necho 'Unable to locate a Java Runtime.' >&2\nexit {exit_code}\n")
    script.chmod(0o755)
    return d


def test_ci_without_javac_fails(tmp_path):
    r = _run(tmp_path, ci=True)
    assert r.returncode != 0, r.stdout[-2000:]


def test_local_without_javac_skips_with_reason(tmp_path):
    r = _run(tmp_path, ci=False)
    assert r.returncode == 0, r.stdout[-2000:]
    assert "Java host needs javac" in r.stdout and "skipped" in r.stdout


def test_local_with_broken_javac_skips_with_reason(tmp_path):
    # issue #10: a javac stub that exits non-zero is not a usable JDK
    r = _run(tmp_path, ci=False, javac=_fake_javac(tmp_path))
    assert r.returncode == 0, r.stdout[-2000:]
    assert "Java host needs javac" in r.stdout and "skipped" in r.stdout


def test_ci_with_broken_javac_fails(tmp_path):
    r = _run(tmp_path, ci=True, javac=_fake_javac(tmp_path))
    assert r.returncode != 0, r.stdout[-2000:]
