"""Console entry point and host bridge (issue #52, docs/host-contract.md).

Three control operations for a non-Python host: ``run-campaign``, ``accept`` and
``status``. Each reads a JSON config file and prints one JSON document on stdout;
logs go to stderr. No loop logic lives here: the subcommands call
``loop.run_campaign`` and ``loop.accept`` unchanged. Approval records are only
read, never created: the host or owner writes the approval file.

Callbacks go to the host over the S6 HTTP bridge (examples/java-host): artifacts
travel as base64 component bytes next to their ``candidate.content_id``.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import ipaddress
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Sequence

from .archive import Archive
from .candidate import Candidate
from .decision.backends import DeterministicBackend
from .decision.envelope import EnvelopeBuilder
from .decision.log import Decider
from .loop import ApprovalRecord, _evaluation_hash, accept, run_campaign
from .splits import load_splits

TIMEOUT = 30.0  # same default as examples/java-host/http_evaluator.py
# Numeric only: a name such as localhost goes to the resolver unchanged. Java binds 127.0.0.1.
LOOPBACK_HOSTS = ("127.0.0.1", "::1")


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # Same no-redirect handler as decision/backends.py.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _loopback_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url)
    if (parts.scheme != "http" or parts.hostname not in LOOPBACK_HOSTS or parts.username is not None
            or parts.password is not None or parts.query or parts.fragment):
        raise ValueError("host_url must be plain loopback HTTP (127.0.0.1 or ::1)")
    parts.port  # raises ValueError on a malformed port
    return url.rstrip("/")


def _zero_margin(comparison) -> bool:
    # Same retention/non-regression rule as the GDPevo prereg (adapters/gdpevo/pilot.py).
    return comparison.mean_delta >= 0


def _log(message: str) -> None:
    print(f"rsi-kernel {message}", file=sys.stderr, flush=True)


def _encode(candidate: Candidate) -> dict:
    return {"id": candidate.id, "media_type": candidate.media_type, "parent_ids": list(candidate.parent_ids),
            "components": {k: base64.b64encode(v if isinstance(v, bytes) else v.encode()).decode()
                           for k, v in candidate.components.items()}}


def _decode(data: dict, parent_ids: Sequence[str] = ()) -> Candidate:
    components = {k: base64.b64decode(v, validate=True) for k, v in data["components"].items()}
    candidate = Candidate(components, data["media_type"], tuple(data.get("parent_ids", parent_ids)))
    if "id" in data and data["id"] != candidate.id:
        raise ValueError("artifact bytes do not match their content hash")
    return candidate


class FrozenChampion:
    """One champion snapshot per invocation; the kernel's get_artifact() sees only it."""

    def __init__(self, host) -> None:
        self.host, self.champion = host, host.get_artifact()

    def get_artifact(self) -> Candidate:
        return self.champion

    def evaluate(self, candidate, item_ids):
        return self.host.evaluate(candidate, item_ids)

    def apply(self, approved_candidate_hash):
        return self.host.apply(approved_candidate_hash)


class HttpHost:
    """Host callbacks (design §4) over the S6 HTTP bridge."""

    def __init__(self, base_url: str, timeout: float = TIMEOUT) -> None:
        self.base_url = _loopback_url(base_url)
        self.timeout = timeout
        # Proxy-disabled, no-redirect opener: same pattern as decision/backends.py.
        self._opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())

    def _call(self, path: str, body: dict | None = None) -> dict:
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.base_url + path, data=data, headers={"Content-Type": "application/json"})
        with self._opener.open(req, timeout=self.timeout) as r:  # non-2xx (incl. 3xx) raises
            return json.loads(r.read())

    def get_artifact(self) -> Candidate:
        return _decode(self._call("/artifact"))

    def evaluate(self, candidate: Candidate, item_ids: Sequence[str]) -> list[dict]:
        body = {"candidate_id": candidate.id, "item_ids": list(item_ids),
                "components": _encode(candidate)["components"]}
        return self._call("/evaluate", body)["results"]

    def apply(self, approved_candidate_hash: str) -> None:
        self._call("/apply", {"candidate_id": approved_candidate_hash})


def _store(config: dict) -> Path:
    path = Path(config["store"])
    path.mkdir(parents=True, exist_ok=True)
    return path


def _state_path(config: dict) -> Path:
    cid = config["campaign_id"]
    if (not isinstance(cid, str) or not cid or cid in (".", "..")
            or any(sep in cid for sep in ("/", "\\", "\0"))):
        raise ValueError("campaign_id must be a single filename component")
    store = _store(config).resolve()
    path = (store / f"campaign-{cid}.json").resolve()  # follows symlinks
    if path.parent != store:
        raise ValueError("campaign state path escapes the store")
    return path


def _archive(config: dict) -> Archive:
    store = _store(config)
    return Archive(store / "public", store / "private")


def _approval_request(config: dict, candidate_id: str) -> dict:
    splits = load_splits(config["splits"])
    return {"campaign_id": config["campaign_id"], "candidate_hash": candidate_id,
            "evaluator_hash": config["evaluator_hash"], "code_hash": config["code_hash"],
            "data_hash": _evaluation_hash(sorted(splits.item_ids("adjudication")), config["bounds"]["runs"])}


def cmd_run_campaign(config: dict) -> dict:
    state_path = _state_path(config)  # validate before any callback or write
    host = FrozenChampion(HttpHost(config["host_url"]))
    store = _store(config)
    champion = host.get_artifact()
    # Proposals are host-supplied frozen candidates, offered one per proposer call.
    queue = iter([_decode(p, (champion.id,)) for p in config.get("proposals", [])])
    bounds = config["bounds"]
    _log(f"run-campaign {config['campaign_id']}: champion {champion.id}")
    with open(store / "outcomes.jsonl", "a+", encoding="utf-8") as outcomes, \
            open(store / "decisions.jsonl", "a+", encoding="utf-8") as decisions:
        result = run_campaign(
            adapter=host, proposer=lambda champ, component, rows: next(queue, None),
            decider=Decider(DeterministicBackend(), decisions),
            envelope_builder=EnvelopeBuilder(tuple(config["component_ids"])),
            dev_item_ids=sorted(load_splits(config["splits"]).dev_item_ids()),
            evaluator_hash=config["evaluator_hash"], archive=_archive(config), outcome_log=outcomes,
            non_regression=_zero_margin, spend=lambda: 0, max_attempts=bounds["max_attempts"],
            spend_cap=bounds["spend_cap"], eval_cap=bounds["eval_cap"], runs=bounds["runs"])
    out = {"outcome": result.outcome, "stop_reason": result.stop_reason, "attempts": result.attempts,
           "evaluator_items_used": result.evaluator_items_used, "champion_id": champion.id,
           "selected_id": result.selected.id if result.selected else None}
    state = {**out, "selected": _encode(result.selected) if result.selected else None, "acceptance": None}
    state_path.write_text(json.dumps(state, sort_keys=True), encoding="utf-8")
    _log(f"run-campaign {config['campaign_id']}: {result.outcome} ({result.stop_reason})")
    return out


def _read_approval(path: str | None):
    def approval(request):
        if path is None:
            return None
        try:
            return ApprovalRecord(**json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return None  # missing or malformed: accept() records not_updated
    return approval


def cmd_accept(config: dict, approval_path: str | None) -> dict:
    state_path = _state_path(config)
    state = json.loads(state_path.read_text(encoding="utf-8"))
    host = FrozenChampion(HttpHost(config["host_url"]))
    champion = host.get_artifact()
    if champion.id != state["champion_id"]:
        raise ValueError("host champion changed since the campaign")
    candidate = _decode(state["selected"]) if state["selected"] else None
    splits = load_splits(config["splits"])
    result = accept(
        campaign_id=config["campaign_id"], candidate=candidate, champion=champion, adjudicate=host.evaluate,
        adjudication_item_ids=sorted(splits.item_ids("adjudication")), evaluator_hash=config["evaluator_hash"],
        code_hash=config["code_hash"], retain=_zero_margin, approval=_read_approval(approval_path),
        adapter=host, archive=_archive(config), runs=config["bounds"]["runs"])
    out = {"outcome": result.outcome, "candidate_id": candidate.id if candidate else None}
    state_path.write_text(json.dumps({**state, "acceptance": out}, sort_keys=True), encoding="utf-8")
    _log(f"accept {config['campaign_id']}: {result.outcome}")
    return out


def cmd_status(config: dict) -> dict:
    path = _state_path(config)
    if not path.exists():
        return {"campaign": None, "acceptance": None, "approval_request": None}
    state = json.loads(path.read_text(encoding="utf-8"))
    campaign = {k: v for k, v in state.items() if k not in ("selected", "acceptance")}
    request = _approval_request(config, state["selected_id"]) if state["selected_id"] else None
    return {"campaign": campaign, "acceptance": state["acceptance"], "approval_request": request}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rsi-kernel", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("run-campaign", "accept", "status"):
        p = sub.add_parser(name)
        p.add_argument("--config", required=True, help="campaign config JSON file")
        if name == "accept":
            p.add_argument("--approval", help="approval record JSON written by the host/owner")
    args = parser.parse_args(argv)
    try:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
        if args.command == "run-campaign":
            out = cmd_run_campaign(config)
        elif args.command == "accept":
            out = cmd_accept(config, args.approval)
        else:
            out = cmd_status(config)
    except Exception as error:  # report on stderr; stdout stays JSON-only (empty on failure)
        _log(f"{args.command} failed: {type(error).__name__}: {error}")
        return 1
    print(json.dumps(out, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
