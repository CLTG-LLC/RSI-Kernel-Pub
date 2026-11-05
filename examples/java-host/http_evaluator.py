"""Host-side glue: a DevEvaluatorServer callable that forwards to an HTTP host.

The kernel (src/rsi_kernel/evaluator.py) wraps a host-supplied
``evaluate(candidate_id, item_ids) -> per-item results`` callable and keeps the
budget, split checks and loopback binding. This callable sends each reserved
batch to a non-Python host's POST /evaluate, so the kernel stays unchanged.
Precedent for a non-Python evaluator called over a process boundary: GEPA's
curl-based ``eval.sh`` caller (src/gepa/oa/engines/autoresearch.py).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Sequence


class HttpEvaluator:
    def __init__(self, base_url: str, timeout: float = 30.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def __call__(self, candidate_id: str, item_ids: Sequence[str]) -> list[dict]:
        body = json.dumps({"candidate_id": candidate_id, "item_ids": list(item_ids)}).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + "/evaluate", data=body, headers={"Content-Type": "application/json"}
        )
        # Non-2xx raises; the kernel turns that into 502 and keeps the reservation spent.
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            return json.loads(r.read())["results"]
