"""Console entry hardening (PR #54 review): store paths, frozen champion, loopback callbacks, exit codes."""

import base64
import json
import subprocess
import sys
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from rsi_kernel import cli
from rsi_kernel.candidate import Candidate

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
