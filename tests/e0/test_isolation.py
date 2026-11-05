"""E0: a hostile proposer inside the container is denied protected state.

Docker none network driver: https://docs.docker.com/engine/network/drivers/none/
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from rsi_kernel.isolation import ProposerRuntime

IMAGE = "python:3.12-slim"
SECRET_VAR = "RSI_E0_SECRET"
SECRET = "e0-canary-7f3c"


def _docker_ready() -> str | None:
    if shutil.which("docker") is None:
        return "docker CLI not found"
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        return "docker daemon not reachable"
    if subprocess.run(["docker", "image", "inspect", IMAGE], capture_output=True).returncode != 0:
        if subprocess.run(["docker", "pull", IMAGE], capture_output=True).returncode != 0:
            return f"cannot pull {IMAGE}"
    return None


_reason = _docker_ready()
# Locally, skip with the reason if Docker is missing. In CI (GitHub sets CI=true)
# E0 must run, so the tests fail instead of skipping.
pytestmark = pytest.mark.skipif(
    _reason is not None and not os.environ.get("CI"), reason=f"E0 needs Docker: {_reason}"
)


def _sha(path: Path) -> dict[str, str]:
    files = [path] if path.is_file() else sorted(p for p in path.rglob("*") if p.is_file())
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


HOSTILE = r"""
import json, os, socket, sys
targets = json.loads(sys.argv[1])
out = []

def attempt(kind, target, fn):
    try:
        got = fn()
        out.append({"kind": kind, "target": target, "denied": False, "detail": repr(got)[:200]})
    except Exception as e:
        out.append({"kind": kind, "target": target, "denied": True, "detail": f"{type(e).__name__}: {e}"[:200]})

def read(p):
    if os.path.isdir(p):
        return os.listdir(p)
    with open(p, "rb") as f:
        return f.read()

def write(p):
    with open(p, "w") as f:
        f.write("tampered")
    return "written"

for t in targets["read"]:
    attempt("read", t, lambda t=t: read(t))
for t in targets["write"]:
    attempt("write", t, lambda t=t: write(t))

def env():
    v = os.environ[targets["env"]]
    return v
attempt("env", targets["env"], env)

def net(host, port):
    s = socket.create_connection((host, port), timeout=3)
    s.close()
    return "connected"
for host, port in targets["net"]:
    attempt("net", f"{host}:{port}", lambda h=host, p=port: net(h, p))

with open("/out/denials.json", "w") as f:
    json.dump(out, f)
"""


@pytest.fixture
def layout():
    # Under $HOME, not the system temp dir: VM-backed Docker on macOS (Colima's
    # default config) shares only the home directory with the daemon.
    root = Path(tempfile.mkdtemp(prefix=".rsi-e0-", dir=Path.home()))
    dev = root / "dev"
    dev.mkdir()
    (dev / "items.jsonl").write_text('{"item_id": "d0"}\n')
    adj = root / "adjudication"
    adj.mkdir()
    (adj / "items.jsonl").write_text('{"item_id": "a0", "label": "sealed"}\n')
    ho = root / "holdout"
    ho.mkdir()
    (ho / "items.jsonl").write_text('{"item_id": "h0", "label": "sealed"}\n')
    priv = root / "private"
    priv.mkdir()
    (priv / "results.jsonl").write_text('{"item_id": "a0", "score": 1}\n')
    approvals = root / "approvals"
    approvals.mkdir()
    (approvals / "approval.json").write_text('{"candidate": "abc", "approved": true}\n')
    out = root / "out"
    out.mkdir()
    yield {"root": root, "dev": dev, "adj": adj, "ho": ho, "priv": priv, "approvals": approvals, "out": out}
    shutil.rmtree(root, ignore_errors=True)


def test_hostile_proposer_is_denied_and_protected_state_unchanged(layout, monkeypatch):
    if _reason:
        pytest.fail(f"E0 must run in CI but Docker is unavailable: {_reason}")
    monkeypatch.setenv(SECRET_VAR, SECRET)  # present on the host, must not reach the container
    protected = [layout["adj"], layout["ho"], layout["priv"], layout["approvals"], layout["dev"]]
    before = {k: v for p in protected for k, v in _sha(p).items()}

    protected_paths = [str(layout[k]) for k in ("adj", "ho", "priv", "approvals")] + [
        str(layout["approvals"] / "approval.json"),
        str(layout["priv"] / "results.jsonl"),
        "/data/adjudication",
        "/data/holdout",
        "/data/private",
        "/data/approvals",
    ]
    targets = {
        "read": protected_paths,
        "write": [
            "/data/dev/items.jsonl",
            str(layout["approvals"] / "approval.json"),
            str(layout["priv"] / "results.jsonl"),
        ],
        "env": SECRET_VAR,
        "net": [["1.1.1.1", 53], ["8.8.8.8", 443], ["host.docker.internal", 80]],
    }
    rt = ProposerRuntime(IMAGE, layout["dev"], layout["out"])
    argv = rt.docker_argv(["python", "-c", HOSTILE, json.dumps(targets)], env={"RSI_RUN_ID": "e0"})
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr

    evidence = json.loads((layout["out"] / "denials.json").read_text())
    expected = len(targets["read"]) + len(targets["write"]) + 1 + len(targets["net"])
    assert len(evidence) == expected
    allowed = [e for e in evidence if not e["denied"]]
    assert allowed == [], allowed
    # sanity: the container could see its own dev data (mount works) but not change it
    assert SECRET not in proc.stdout + proc.stderr + json.dumps(evidence)

    after = {k: v for p in protected for k, v in _sha(p).items()}
    assert after == before
    # keep denial evidence for the report
    sys.stdout.write(json.dumps(evidence, indent=1) + "\n")


def test_dev_data_is_readable_inside_container(layout):
    if _reason:
        pytest.fail(f"E0 must run in CI but Docker is unavailable: {_reason}")
    rt = ProposerRuntime(IMAGE, layout["dev"], layout["out"])
    script = "import shutil; shutil.copy('/data/dev/items.jsonl', '/out/copy.jsonl')"
    proc = subprocess.run(rt.docker_argv(["python", "-c", script]), capture_output=True, text=True, timeout=120)
    assert proc.returncode == 0, proc.stderr
    assert (layout["out"] / "copy.jsonl").read_text() == (layout["dev"] / "items.jsonl").read_text()
