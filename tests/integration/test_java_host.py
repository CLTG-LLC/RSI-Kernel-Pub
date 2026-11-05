"""S6 / issue #7: the unchanged kernel evaluates through a Java (JDK-only) host.

Integration direction: the kernel's DevEvaluatorServer wraps a host callable
(src/rsi_kernel/evaluator.py). The host-side glue
examples/java-host/http_evaluator.py is that callable; it forwards each batch
to the Java host's POST /evaluate. No kernel file changes.
"""

import hashlib
import os
import queue
import threading
import importlib.util
import json
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from rsi_kernel.evaluator import DevEvaluatorServer

ROOT = Path(__file__).resolve().parents[2]
JAVA_DIR = ROOT / "examples" / "java-host"
KERNEL = ROOT / "src" / "rsi_kernel"
DEV = [f"d{i}" for i in range(4)]

# Same pattern as tests/e0/test_isolation.py: probe that the tool actually works, not
# just that it exists (macOS ships a /usr/bin/javac stub that exits non-zero without a
# JDK). Locally skip with the reason when the JDK is missing; in CI (GitHub sets CI=true)
# these tests must run, so they fail instead.
def _java_ready() -> str | None:
    if shutil.which("javac") is None:
        return "javac not found"
    if subprocess.run(["javac", "-version"], capture_output=True).returncode != 0:
        return "javac does not run (no JDK?)"
    return None


_reason = _java_ready()
pytestmark = pytest.mark.skipif(
    _reason is not None and not os.environ.get("CI"), reason=f"Java host needs javac (JDK 21) on PATH: {_reason}"
)


def _kernel_hashes():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(KERNEL.glob("*.py"))}


def _load_adapter():
    spec = importlib.util.spec_from_file_location("http_evaluator", JAVA_DIR / "http_evaluator.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


READY_TIMEOUT = 10  # seconds; same value as this module's other process/HTTP timeouts


def _stop(proc):
    proc.terminate()
    try:
        proc.wait(timeout=READY_TIMEOUT)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    proc.stdout.close()


def _start(cmd, env=None, timeout=READY_TIMEOUT):
    """Start a host and wait (bounded) for its "LISTENING <port>" line; kill it on timeout."""
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, text=True, env=env)
    lines = queue.Queue()
    threading.Thread(target=lambda: lines.put(proc.stdout.readline()), daemon=True).start()
    try:
        line = lines.get(timeout=timeout)
    except queue.Empty:
        _stop(proc)
        raise TimeoutError(f"host not ready within {timeout}s: {cmd}")
    if not line.startswith("LISTENING "):
        _stop(proc)
        raise RuntimeError(f"unexpected host output: {line!r}")
    return proc, f"http://127.0.0.1:{int(line.split()[1])}"


@pytest.fixture(scope="module")
def java_classes(tmp_path_factory):
    out = tmp_path_factory.mktemp("java-classes")
    subprocess.run(["javac", "-d", str(out), str(JAVA_DIR / "EvaluatorHost.java")], check=True)
    return out


@pytest.fixture(scope="module")
def java_host(java_classes):
    proc, url = _start(["java", "-cp", str(java_classes), "EvaluatorHost", "0"])
    try:
        yield url
    finally:
        _stop(proc)


def _post(url, body):
    req = urllib.request.Request(
        url + "/evaluate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def _java_items(java_url):
    with urllib.request.urlopen(java_url + "/count", timeout=10) as r:
        return json.loads(r.read())["items"]


@pytest.fixture
def kernel(java_host):
    adapter = _load_adapter()
    servers = []

    def make(cap):
        s = DevEvaluatorServer(adapter.HttpEvaluator(java_host), DEV, cap)
        s.start()
        servers.append(s)
        return s

    yield make
    for s in servers:
        s.stop()


def test_kernel_runs_unchanged_against_java_host(java_host, kernel):
    before = _kernel_hashes()
    s = kernel(cap=10)
    status, body = _post(s.url, {"candidate_id": "alpha beta", "item_ids": ["d0", "d1", "d2"]})
    assert status == 200
    # toy rule (EvaluatorHost.java): item d<i> scores 1.0 if the candidate contains its keyword
    assert body["results"] == [
        {"item_id": "d0", "score": 1.0, "feedback": "found alpha"},
        {"item_id": "d1", "score": 1.0, "feedback": "found beta"},
        {"item_id": "d2", "score": 0.0, "feedback": "missing gamma"},
    ]
    assert body["budget"] == {"cap": 10, "used": 3}
    assert _kernel_hashes() == before


def test_budget_is_enforced_before_the_java_host_runs(java_host, kernel):
    s = kernel(cap=2)
    start = _java_items(java_host)
    statuses = [_post(s.url, {"candidate_id": "x", "item_ids": [i]})[0] for i in DEV]
    assert statuses == [200, 200, 429, 429]
    assert _java_items(java_host) - start == 2  # refused requests never reached Java


def test_non_dev_items_never_reach_java(java_host, kernel):
    s = kernel(cap=5)
    start = _java_items(java_host)
    assert _post(s.url, {"candidate_id": "x", "item_ids": ["holdout7"]})[0] == 400
    assert _java_items(java_host) == start


def test_java_host_parses_escaped_request_strings(java_host, kernel):
    s = kernel(cap=2)
    status, body = _post(s.url, {"candidate_id": 'a "quoted" \\ \u00e9 alpha', "item_ids": ["d0", "d1"]})
    assert status == 200
    # json.dumps (ensure_ascii) sends \", \\ and \u00e9 as escapes; exact results show Java decoded them
    assert body["results"] == [
        {"item_id": "d0", "score": 1.0, "feedback": "found alpha"},
        {"item_id": "d1", "score": 0.0, "feedback": "missing beta"},
    ]


def test_host_binds_ipv4_loopback_when_jvm_prefers_ipv6(java_classes, kernel):
    # review PR9 S2: InetAddress.getLoopbackAddress() may return ::1 under this option
    env = {**os.environ, "JAVA_TOOL_OPTIONS": "-Djava.net.preferIPv6Addresses=true"}
    proc, url = _start(["java", "-cp", str(java_classes), "EvaluatorHost", "0"], env=env)
    try:
        adapter = _load_adapter()
        s = DevEvaluatorServer(adapter.HttpEvaluator(url), DEV, 1)
        s.start()
        try:
            status, body = _post(s.url, {"candidate_id": "alpha", "item_ids": ["d0"]})
        finally:
            s.stop()
        assert status == 200 and body["results"][0]["score"] == 1.0
    finally:
        _stop(proc)


def test_startup_wait_is_bounded_and_kills_the_process():
    # review PR9 S3: a host that never prints its readiness line must not hang the suite
    cmd = [sys.executable, "-c", "import time; time.sleep(60)"]
    start = time.monotonic()
    with pytest.raises(TimeoutError):
        _start(cmd, timeout=0.5)
    assert time.monotonic() - start < READY_TIMEOUT
