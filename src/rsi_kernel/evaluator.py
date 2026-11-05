"""Budgeted dev evaluator server (design §2 step 3, §5).

Shape follows GEPA ``oa/eval_server.py`` (POST /evaluate, HTTP 429 when the
budget is exhausted). Difference (new kernel behaviour, issue #1): the budget is
reserved *before* the host evaluator runs, so no evaluation ever runs past the
cap. GEPA's ``oa/budget.py`` records after evaluation and can overshoot.

The budget unit is one item evaluation: a request for k items reserves k.
"""

from __future__ import annotations

import json
import re
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Iterable, Sequence

LOOPBACK = "127.0.0.1"
_CONTENT_LENGTH = re.compile(r"^[0-9]+$")  # RFC 9110 §8.6: Content-Length = 1*DIGIT

EvaluateFn = Callable[[str, Sequence[str]], Sequence[dict]]


class Budget:
    """Thread-safe up-front reservation of item evaluations."""

    def __init__(self, cap: int) -> None:
        if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
            raise ValueError("cap must be a non-negative int")
        self.cap = cap
        self.used = 0
        self._lock = threading.Lock()

    def reserve(self, n: int) -> bool:
        with self._lock:
            if self.used + n > self.cap:
                return False
            self.used += n
            return True


class _Handler(BaseHTTPRequestHandler):
    server: "_Server"

    def log_message(self, *args: Any) -> None:  # keep test output quiet
        pass

    def _send(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:  # noqa: N802 (stdlib name)
        if self.path != "/evaluate":
            self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        raw_length = (self.headers.get("Content-Length") or "").strip()
        if not _CONTENT_LENGTH.match(raw_length):
            # RFC 9112 §6.3: invalid Content-Length -> 400 and close the connection.
            self.close_connection = True
            self.send_response(HTTPStatus.BAD_REQUEST)
            self.send_header("Connection", "close")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        try:
            req = json.loads(self.rfile.read(int(raw_length)) or b"null")
        except (ValueError, json.JSONDecodeError):
            self._send(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON"})
            return
        owner = self.server.owner
        error = owner.validate(req)
        if error:
            self._send(HTTPStatus.BAD_REQUEST, {"error": error})
            return
        item_ids = req["item_ids"]
        if not owner.budget.reserve(len(item_ids)):
            self._send(HTTPStatus.TOO_MANY_REQUESTS, {"error": "budget exhausted", "budget": owner.budget_view()})
            return
        try:
            results = owner.run(req["candidate_id"], item_ids)
        except Exception as exc:  # host evaluator failed; reservation stays spent
            self._send(HTTPStatus.BAD_GATEWAY, {"error": f"evaluator failed: {type(exc).__name__}"})
            return
        self._send(HTTPStatus.OK, {"results": results, "budget": owner.budget_view()})


class _Server(ThreadingHTTPServer):
    daemon_threads = True
    owner: "DevEvaluatorServer"


class DevEvaluatorServer:
    """Localhost HTTP wrapper around a host-supplied dev evaluator callable."""

    def __init__(self, evaluate: EvaluateFn, dev_item_ids: Iterable[str], cap: int, port: int = 0):
        self._evaluate = evaluate
        self.dev_item_ids = frozenset(dev_item_ids)
        self.budget = Budget(cap)
        # Loopback only; the host is deliberately not configurable (no auth here).
        self._httpd = _Server((LOOPBACK, port), _Handler)
        self._httpd.owner = self
        self._thread: threading.Thread | None = None

    @property
    def url(self) -> str:
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}"

    def budget_view(self) -> dict:
        return {"cap": self.budget.cap, "used": self.budget.used}

    def validate(self, req: Any) -> str | None:
        if not isinstance(req, dict):
            return "body must be an object"
        cid, items = req.get("candidate_id"), req.get("item_ids")
        if not isinstance(cid, str) or not cid:
            return "candidate_id must be a non-empty string"
        if not isinstance(items, list) or not items or not all(isinstance(i, str) for i in items):
            return "item_ids must be a non-empty list of strings"
        if len(set(items)) != len(items):
            return "duplicate item ids"
        if not set(items) <= self.dev_item_ids:
            return "only dev-split items may be evaluated"
        return None

    def run(self, candidate_id: str, item_ids: list[str]) -> list[dict]:
        results = [
            {"item_id": r["item_id"], "score": r["score"], "feedback": r.get("feedback", "")}
            for r in self._evaluate(candidate_id, item_ids)
        ]
        if [r["item_id"] for r in results] != item_ids:
            raise ValueError("evaluator results do not match requested items")
        return results

    def start(self) -> None:
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread:
            self._thread.join()
