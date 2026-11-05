import json
import threading
import urllib.error
import urllib.request

import pytest

from rsi_kernel.evaluator import DevEvaluatorServer

DEV = frozenset({f"d{i}" for i in range(20)})


class CountingEvaluator:
    """Host-supplied callable; counts real invocations and items evaluated."""

    def __init__(self):
        self.calls = 0
        self.items = 0
        self._lock = threading.Lock()

    def __call__(self, candidate_id, item_ids):
        with self._lock:
            self.calls += 1
            self.items += len(item_ids)
        return [{"item_id": i, "score": 1.0, "feedback": f"ok {i}"} for i in item_ids]


def _post(url, body):
    req = urllib.request.Request(
        url + "/evaluate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


@pytest.fixture
def make_server():
    servers = []

    def make(cap, fn=None):
        fn = fn or CountingEvaluator()
        s = DevEvaluatorServer(fn, DEV, cap)
        s.start()
        servers.append(s)
        return s, fn

    yield make
    for s in servers:
        s.stop()


def test_returns_per_item_results_with_feedback(make_server):
    s, fn = make_server(cap=5)
    status, body = _post(s.url, {"candidate_id": "c1", "item_ids": ["d0", "d1"]})
    assert status == 200
    assert body["results"] == [
        {"item_id": "d0", "score": 1.0, "feedback": "ok d0"},
        {"item_id": "d1", "score": 1.0, "feedback": "ok d1"},
    ]
    assert body["budget"] == {"cap": 5, "used": 2}


@pytest.mark.parametrize("n,k", [(3, 2), (5, 7)])
def test_cap_n_with_n_plus_k_requests_runs_exactly_n(make_server, n, k):
    s, fn = make_server(cap=n)
    statuses = [_post(s.url, {"candidate_id": "c", "item_ids": [f"d{i}"]})[0] for i in range(n + k)]
    assert statuses.count(200) == n
    assert statuses.count(429) == k
    assert fn.items == n and fn.calls == n


def test_concurrent_requests_never_overshoot(make_server):
    n, k = 4, 12
    s, fn = make_server(cap=n)
    statuses = []
    lock = threading.Lock()

    def go(i):
        st, _ = _post(s.url, {"candidate_id": "c", "item_ids": [f"d{i}"]})
        with lock:
            statuses.append(st)

    threads = [threading.Thread(target=go, args=(i,)) for i in range(n + k)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert statuses.count(200) == n and statuses.count(429) == k
    assert fn.items == n


def test_batch_that_would_exceed_cap_is_refused_before_calling(make_server):
    s, fn = make_server(cap=3)
    status, _ = _post(s.url, {"candidate_id": "c", "item_ids": ["d0", "d1", "d2", "d3"]})
    assert status == 429
    assert fn.calls == 0
    # the refused batch reserved nothing; the full cap is still usable
    assert _post(s.url, {"candidate_id": "c", "item_ids": ["d0", "d1", "d2"]})[0] == 200
    assert fn.items == 3


@pytest.mark.parametrize("items", [["adj1"], ["d0", "holdout7"]])
def test_non_dev_items_rejected_without_calling(make_server, items):
    s, fn = make_server(cap=10)
    status, _ = _post(s.url, {"candidate_id": "c", "item_ids": items})
    assert status == 400
    assert fn.calls == 0


@pytest.mark.parametrize(
    "body",
    [{}, {"candidate_id": "c"}, {"candidate_id": 1, "item_ids": ["d0"]}, {"candidate_id": "c", "item_ids": []}],
)
def test_malformed_requests_rejected(make_server, body):
    s, fn = make_server(cap=10)
    assert _post(s.url, body)[0] == 400
    assert fn.calls == 0


def test_unknown_path_404(make_server):
    s, _ = make_server(cap=1)
    req = urllib.request.Request(s.url + "/other", data=b"{}")
    with pytest.raises(urllib.error.HTTPError) as e:
        urllib.request.urlopen(req, timeout=10)
    assert e.value.code == 404


def test_server_binds_loopback_only(make_server):
    s, _ = make_server(cap=1)
    assert s.url.startswith("http://127.0.0.1:")


def test_host_is_not_configurable():
    # review PR5 finding 2: a wildcard host must not be accepted at all
    with pytest.raises(TypeError):
        DevEvaluatorServer(CountingEvaluator(), DEV, 1, host="0.0.0.0")


@pytest.mark.parametrize("length", ["-1", "abc", "+5", "1.0", ""])
def test_invalid_content_length_rejected_before_evaluating(make_server, length):
    # review PR5 finding 3; RFC 9112 section 6.3: invalid Content-Length -> 400, close
    import socket

    s, fn = make_server(cap=10)
    host, port = s.url.removeprefix("http://").split(":")
    body = json.dumps({"candidate_id": "c", "item_ids": ["d0"]}).encode()
    head = f"POST /evaluate HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length:{length}\r\n\r\n"
    with socket.create_connection((host, int(port)), timeout=10) as sock:
        sock.sendall(head.encode() + body)
        sock.shutdown(socket.SHUT_WR)
        data = b""
        while chunk := sock.recv(4096):
            data += chunk
    assert data.startswith(b"HTTP/1.0 400") or data.startswith(b"HTTP/1.1 400"), data[:80]
    assert b"connection: close" in data.lower()
    assert fn.calls == 0


def test_missing_content_length_rejected(make_server):
    import socket

    s, fn = make_server(cap=10)
    host, port = s.url.removeprefix("http://").split(":")
    with socket.create_connection((host, int(port)), timeout=10) as sock:
        sock.sendall(b"POST /evaluate HTTP/1.1\r\nHost: x\r\n\r\n")
        sock.shutdown(socket.SHUT_WR)
        data = b""
        while chunk := sock.recv(4096):
            data += chunk
    assert b" 400 " in data.split(b"\r\n")[0]
    assert fn.calls == 0


def test_invalid_cap_rejected():
    with pytest.raises(ValueError):
        DevEvaluatorServer(CountingEvaluator(), DEV, -1)


def test_evaluator_results_not_matching_request_are_an_error(make_server):
    s, _ = make_server(cap=5, fn=lambda cid, ids: [{"item_id": "d9", "score": 1.0}])
    assert _post(s.url, {"candidate_id": "c", "item_ids": ["d0"]})[0] == 502
