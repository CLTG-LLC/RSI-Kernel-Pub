"""Console entry hardening (PR #54 review): store paths, frozen champion, loopback callbacks, exit codes."""

import base64
import json
import os
import re
import subprocess
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from rsi_kernel import approval as approval_module, cli
from rsi_kernel.candidate import Candidate
from rsi_kernel.loop import ApprovalRequest

DEV = ["d0", "d1"]


def _b64(text):
    return base64.b64encode(text.encode()).decode()


class FakeHost:
    """In-process Python stand-in for the Java host; champions rotate per GET /artifact."""

    def __init__(self, champions, redirect=False):
        self.champions, self.redirect = list(champions), redirect
        self.artifact_calls, self.evaluated, self.requests = 0, [], 0
        host = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _send(self, status, body, headers=()):
                data = json.dumps(body).encode()
                self.send_response(status)
                for k, v in headers:
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                host.requests += 1
                if host.redirect:
                    return self._send(302, {}, [("Location", "/elsewhere")])
                text = host.champions[host.artifact_calls % len(host.champions)]
                host.artifact_calls += 1
                self._send(200, {"media_type": "text/plain", "components": {"SKILL.md": _b64(text)}})

            def do_POST(self):
                host.requests += 1
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                if self.path == "/evaluate":
                    host.evaluated.append(body["candidate_id"])
                    text = base64.b64decode(body["components"]["SKILL.md"]).decode()
                    score = 1.0 if "beta" in text else 0.5
                    return self._send(200, {"results": [{"item_id": i, "score": score, "feedback": ""}
                                                        for i in body["item_ids"]]})
                self._send(200, {"applied": [body["candidate_id"]]})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()


@pytest.fixture
def make_host():
    hosts = []

    def make(*champions, **kw):
        h = FakeHost(champions or ["Use alpha."], **kw)
        hosts.append(h)
        return h

    yield make
    for h in hosts:
        h.close()


def _config(url, store, **over):
    return {"campaign_id": "c", "host_url": url, "store": str(store), "component_ids": ["c1"],
            "evaluator_hash": "e", "code_hash": "k",
            "splits": {"splits": [{"name": "dev", "purpose": "dev", "selection_eligible": True, "item_ids": DEV}]},
            "bounds": {"max_attempts": 1, "spend_cap": 1, "eval_cap": 100, "runs": 1},
            "proposals": [{"media_type": "text/plain", "components": {"SKILL.md": _b64("Use beta.")}}], **over}


def _main(tmp_path, cfg, *extra, capsys=None):
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(cfg))
    return cli.main(["run-campaign", "--config", str(path), *extra])


# -- 1. store path escape ------------------------------------------------------

@pytest.mark.parametrize("cid", ["x/../../evil", "..", "a/b", "a\\b", "", "."])
def test_campaign_id_must_be_one_filename_component(make_host, tmp_path, cid):
    store = tmp_path / "store"
    (store / "campaign-x").mkdir(parents=True)  # lets "x/../../evil" resolve if unchecked
    before = sorted(p for p in tmp_path.rglob("*"))
    assert _main(tmp_path, _config(make_host().url, store, campaign_id=cid)) == 1
    after = sorted(p for p in tmp_path.rglob("*") if p.name != "cfg.json")
    assert [p for p in after if p not in before and store not in p.parents] == []


def test_state_file_symlink_out_of_store_is_rejected(make_host, tmp_path):
    store, outside = tmp_path / "store", tmp_path / "outside.json"
    store.mkdir()
    outside.write_text("untouched")
    (store / "campaign-s.json").symlink_to(outside)
    assert _main(tmp_path, _config(make_host().url, store, campaign_id="s")) == 1
    assert outside.read_text() == "untouched"


# -- 2. one frozen champion per campaign --------------------------------------

def test_changing_host_champion_is_frozen_once(make_host, tmp_path, capsys):
    host = make_host("Use alpha.", "Use gamma.", "Use delta.")
    assert _main(tmp_path, _config(host.url, tmp_path / "store")) == 0
    out = json.loads(capsys.readouterr().out)
    state = json.loads((tmp_path / "store" / "campaign-c.json").read_text())
    champion = Candidate({"SKILL.md": "Use alpha."}, "text/plain").id
    assert host.artifact_calls == 1
    assert out["champion_id"] == champion == host.evaluated[0]
    assert state["selected"]["parent_ids"] == [champion]


# -- 3. loopback-only callbacks ------------------------------------------------

@pytest.mark.parametrize("url", ["http://10.0.0.1:9", "https://127.0.0.1:9", "http://example.com",
                                 "http://127.0.0.1.evil.test:9", "file:///etc/passwd", "http://user@127.0.0.1:9",
                                 "http://localhost:9", "http://LOCALHOST:9"])
def test_non_loopback_host_url_is_rejected_before_any_callback(monkeypatch, url):
    sent = []
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", lambda self, *a, **k: sent.append(a))
    with pytest.raises(ValueError):
        cli.HttpHost(url).get_artifact()
    assert sent == []


@pytest.mark.parametrize("url", ["http://127.0.0.1:9", "http://[::1]:9"])
def test_loopback_host_urls_are_accepted(url):
    assert cli.HttpHost(url).base_url == url


def test_redirects_are_not_followed(make_host):
    host = make_host(redirect=True)
    with pytest.raises(Exception):
        cli.HttpHost(host.url).get_artifact()
    assert host.requests == 1


def test_environment_proxy_is_ignored(make_host, monkeypatch):
    for name in ("http_proxy", "HTTP_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")  # dead proxy: used => connection refused
    for name in ("no_proxy", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
    # macOS system config bypasses loopback; force the env proxy to apply if consulted.
    monkeypatch.setattr(urllib.request, "proxy_bypass", lambda host: False)
    assert cli.HttpHost(make_host().url).get_artifact().media_type == "text/plain"


# -- 4. exit codes ---------------------------------------------------------------

@pytest.mark.parametrize("args", [[], ["run-campaign"], ["bogus", "--config", "x"]])
def test_usage_error_exits_2_with_empty_stdout(args):
    r = subprocess.run([sys.executable, "-m", "rsi_kernel.cli", *args], capture_output=True, text=True, timeout=60)
    assert (r.returncode, r.stdout) == (2, "")
    assert "usage" in r.stderr


def test_runtime_error_exits_1_with_empty_stdout(tmp_path, capsys):
    assert cli.main(["status", "--config", str(tmp_path / "missing.json")]) == 1
    assert capsys.readouterr().out == ""


# -- 5. fresh status shape -----------------------------------------------------

def test_fresh_status_has_exact_initial_shape(tmp_path, capsys):
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(_config("http://127.0.0.1:9", tmp_path / "store")))
    assert cli.main(["status", "--config", str(path)]) == 0
    assert json.loads(capsys.readouterr().out) == {"campaign": None, "acceptance": None, "approval_request": None}


# -- 6. rejected configuration evaluates nothing (review S2) -------------------

BAD_BOUNDS = {
    # Rejected only because they would raise anyway: a type the loop cannot compare
    # or index, and a cap evaluator.Budget itself refuses. Values the kernel accepts
    # (attempt counts below zero, a float attempt count) stay accepted; see below.
    "wrong type": {"max_attempts": "invalid", "spend_cap": 1, "eval_cap": 100, "runs": 1},
    "negative cap": {"max_attempts": 1, "spend_cap": 1, "eval_cap": -1, "runs": 1},
    "non-positive runs": {"max_attempts": 1, "spend_cap": 1, "eval_cap": 100, "runs": 0},
    "missing key": {"spend_cap": 1, "eval_cap": 100, "runs": 1},
}


@pytest.mark.parametrize("case,bounds", sorted(BAD_BOUNDS.items()))
def test_malformed_bounds_exit_1_and_evaluate_nothing(make_host, tmp_path, capsys, case, bounds):
    host = make_host()
    assert _main(tmp_path, _config(host.url, tmp_path / "store", bounds=bounds)) == 1
    out = capsys.readouterr()
    assert out.out == "" and "bounds" in out.err
    assert (host.artifact_calls, host.evaluated) == (0, [])


@pytest.mark.parametrize("key", ["campaign_id", "host_url", "store", "component_ids",
                                 "evaluator_hash", "code_hash", "splits", "bounds"])
def test_missing_required_config_field_exits_1_before_any_callback(make_host, tmp_path, capsys, key):
    host = make_host()
    cfg = _config(host.url, tmp_path / "store")
    del cfg[key]
    assert _main(tmp_path, cfg) == 1
    out = capsys.readouterr()
    assert out.out == "" and key in out.err
    assert (host.artifact_calls, host.evaluated) == (0, [])


# -- 7. accepted bound values keep their kernel semantics (owner: never stricter) --

@pytest.mark.parametrize("max_attempts,expected", [(-1, "no_improvement"), (1.0, "selected")])
def test_bound_values_the_kernel_accepts_behave_as_before(make_host, tmp_path, capsys,
                                                         max_attempts, expected):
    host = make_host()
    bounds = {"max_attempts": max_attempts, "spend_cap": 1, "eval_cap": 100, "runs": 1}
    assert _main(tmp_path, _config(host.url, tmp_path / "store", bounds=bounds)) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["outcome"] == expected
    assert host.evaluated != []  # the champion is always evaluated first


# -- 8. accept files the request, then waits for the owner's approval (#60) --------

ADJ = ["a0", "a1"]


def _accept_config(url, store):
    cfg = _config(url, store)
    cfg["splits"]["splits"].append({"name": "adj", "purpose": "adjudication", "selection_eligible": False,
                                    "item_ids": ADJ})
    return cfg


def _until(predicate, timeout=10.0):
    import time
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "timed out"
        time.sleep(0.01)


def _record(request, **over):
    return {**{k: request[k] for k in ("candidate_hash", "evaluator_hash", "data_hash", "code_hash")},
            "approver": "owner", **over}


def _publish(path, text):
    # The documented owner step: a sibling temp file, then os.replace.
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text)
    os.replace(temp, path)


def _outcomes(store):
    path = store / "private" / "decisions.jsonl"
    return [d for d in map(json.loads, path.read_text().splitlines()) if d.get("kind") == "outcome"]


@pytest.mark.parametrize("explicit", [True, False])
def test_accept_files_request_and_waits_for_matching_approval(make_host, tmp_path, monkeypatch, explicit):
    monkeypatch.setattr(cli, "POLL_INTERVAL", 0.01, raising=False)
    store = tmp_path / "store"
    cfg = _accept_config(make_host().url, store)
    selected = cli.cmd_run_campaign(cfg)["selected_id"]
    approval = tmp_path / "owner.json" if explicit else store / "approval.json"
    result = {}
    worker = threading.Thread(target=lambda: result.update(
        cli.cmd_accept(cfg, str(approval) if explicit else None)))
    worker.start()
    request_path = store / "approval-request.json"
    _until(request_path.exists)
    request = json.loads(request_path.read_text())
    assert request == cli._approval_request(cfg, selected)  # same hashes status reports, incl. code_hash
    # Waiting: nothing decided, nothing closed in the CLI state, status shows the pending request.
    assert worker.is_alive() and _outcomes(store) == []
    assert json.loads((store / "campaign-c.json").read_text())["acceptance"] is None
    assert cli.cmd_status(cfg)["approval_request"] == request
    _publish(approval, json.dumps(_record(request)))
    worker.join(10)
    assert result == {"outcome": "updated", "candidate_id": selected}


@pytest.mark.parametrize("content", ["mismatch", "malformed"])
def test_present_mismatched_or_malformed_approval_is_not_updated(make_host, tmp_path, content):
    store = tmp_path / "store"
    cfg = _accept_config(make_host().url, store)
    selected = cli.cmd_run_campaign(cfg)["selected_id"]
    approval = tmp_path / "owner.json"
    request = cli._approval_request(cfg, selected)
    approval.write_text(json.dumps(_record(request, code_hash="other")) if content == "mismatch" else "{")
    assert cli.cmd_accept(cfg, str(approval)) == {"outcome": "not_updated", "candidate_id": selected}


# -- 9. store-managed approval paths stay in the store (PR #64 review S1) ----------

@pytest.mark.parametrize("name,target_exists", [("approval-request.json", True), ("approval-request.json", False),
                                                ("approval.json", True), ("approval.json", False)])
def test_store_approval_symlink_out_of_store_is_rejected_before_any_evaluation(make_host, tmp_path, capsys,
                                                                               name, target_exists):
    store, outside = tmp_path / "store", tmp_path / "outside.json"
    host = make_host()
    cfg = _accept_config(host.url, store)
    cli.cmd_run_campaign(cfg)
    if target_exists:
        outside.write_text("untouched")
    (store / name).symlink_to(outside)
    if name == "approval-request.json":
        (store / "approval.json").write_text("{}")  # the old code must not wait forever here
    evaluated, artifact_calls = list(host.evaluated), host.artifact_calls
    path = tmp_path / "cfg.json"
    path.write_text(json.dumps(cfg))
    assert cli.main(["accept", "--config", str(path)]) == 1
    captured = capsys.readouterr()
    assert "escapes the store" in captured.err
    assert (outside.read_text() == "untouched") if target_exists else not outside.exists()
    assert (host.evaluated, host.artifact_calls) == (evaluated, artifact_calls)
    assert not (store / "private" / "decisions.jsonl").exists() or not [
        d for d in map(json.loads, (store / "private" / "decisions.jsonl").read_text().splitlines())
        if d.get("kind") == "adjudication"]  # the campaign stays open


def test_explicit_external_approval_path_keeps_its_contract(make_host, tmp_path):
    # An explicit --approval is the caller's path: it may live anywhere, symlink included.
    store = tmp_path / "store"
    cfg = _accept_config(make_host().url, store)
    selected = cli.cmd_run_campaign(cfg)["selected_id"]
    real, link = tmp_path / "real.json", tmp_path / "link.json"
    real.write_text(json.dumps(_record(cli._approval_request(cfg, selected))))
    link.symlink_to(real)
    assert cli.cmd_accept(cfg, str(link)) == {"outcome": "updated", "candidate_id": selected}


# -- 10. approvals and requests are published atomically (PR #64 review S2) --------

def test_acceptance_stays_pending_until_the_approval_is_published(make_host, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "POLL_INTERVAL", 0.01)
    store = tmp_path / "store"
    cfg = _accept_config(make_host().url, store)
    selected = cli.cmd_run_campaign(cfg)["selected_id"]
    approval, result = tmp_path / "owner.json", {}
    worker = threading.Thread(target=lambda: result.update(cli.cmd_accept(cfg, str(approval))))
    worker.start()
    request_path = store / "approval-request.json"
    _until(request_path.exists)
    temp = tmp_path / "owner.json.tmp"
    temp.write_text("")  # the owner has started writing, under the sibling name
    worker.join(0.2)  # 20 polls
    assert worker.is_alive() and _outcomes(store) == []
    temp.write_text(json.dumps(_record(json.loads(request_path.read_text()))))
    os.replace(temp, approval)
    worker.join(10)
    assert result == {"outcome": "updated", "candidate_id": selected}


def test_request_is_published_complete_with_os_replace(tmp_path, monkeypatch):
    request = ApprovalRequest("c", "cand", "e", "d", "k")
    target, approval = tmp_path / "approval-request.json", tmp_path / "approval.json"
    published, real_replace = [], os.replace

    def replace(src, dst):
        # At publish time the target is absent and the sibling already holds the whole request.
        published.append((Path(dst), target.exists(), Path(src).parent, json.loads(Path(src).read_text())))
        real_replace(src, dst)

    monkeypatch.setattr(os, "replace", replace)
    approval.write_text("{}")
    approval_module.file_approval(target, approval, lambda: None)(request)
    assert published == [(target, False, tmp_path, request.__dict__)]
    assert json.loads(target.read_text()) == request.__dict__
    assert sorted(p.name for p in tmp_path.iterdir()) == ["approval-request.json", "approval.json"]  # no temp left


def test_request_publish_replaces_a_stale_temp_symlink_and_keeps_umask_mode(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text("untouched")
    store = tmp_path / "store"
    store.mkdir()
    (store / "approval-request.json.tmp").symlink_to(outside)
    previous = os.umask(0o022)
    try:
        approval_module._publish(store / "approval-request.json", "{}")
    finally:
        os.umask(previous)
    assert outside.read_text() == "untouched"
    assert (store / "approval-request.json").stat().st_mode & 0o777 == 0o644  # owner-readable as before
    assert [p.name for p in store.iterdir()] == ["approval-request.json"]


def test_quickstart_owner_step_publishes_with_os_replace(tmp_path):
    doc = (Path(__file__).resolve().parents[1] / "docs" / "quickstart.md").read_text(encoding="utf-8")
    code = re.search(r"^python -c '(.*?)'", doc, re.DOTALL | re.MULTILINE).group(1)
    (tmp_path / "store").mkdir()
    request = {"campaign_id": "c", "candidate_hash": "h", "evaluator_hash": "e", "data_hash": "d", "code_hash": "k"}
    (tmp_path / "store" / "approval-request.json").write_text(json.dumps(request))
    # Only the published name may be the visible approval, and it arrives by rename.
    assert 'open("approval.json", "w")' not in code and 'os.replace("approval.json.tmp", "approval.json")' in code
    subprocess.run([sys.executable, "-c", code], cwd=tmp_path, check=True)
    assert json.loads((tmp_path / "approval.json").read_text()) == {
        "candidate_hash": "h", "evaluator_hash": "e", "data_hash": "d", "code_hash": "k", "approver": "owner"}
    assert not (tmp_path / "approval.json.tmp").exists()
