"""Pilot driver wiring (issue #27) on a synthetic GDPevo-shaped tree.

Fakes only: no Docker, network, live model or GDPevo data. Group/task ids
mirror the prereg carving map; the toy wrapper is the existing fixture.
"""

import email.utils
import hashlib
import json
import math
import shutil
from pathlib import Path

import pytest

from rsi_kernel.adapters.gdpevo import pilot
from rsi_kernel.adapters.gdpevo.solver_docker import DockerSolver
from rsi_kernel.candidate import Candidate

TOY = Path(__file__).parent / "fixtures" / "toy"


@pytest.fixture
def tree(tmp_path, monkeypatch):
    root = tmp_path / "gdpevo"
    for group in pilot.GROUPS:
        for subset, ids in (("train", pilot.TRAIN_IDS), ("test", pilot.TEST_IDS)):
            for task_id in ids:
                shutil.copytree(TOY, root / "data/task_groups" / group / f"{subset}_tasks" / task_id)
    champions = {}
    for group in pilot.GROUPS:
        path = tmp_path / f"{group}-SKILL.md"
        path.write_text(f"# {group} skill\n")
        champions[group] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    answer = tmp_path / "calibration-answer.json"
    answer.write_bytes(b"recorded")
    monkeypatch.setattr(pilot, "CALIBRATION_ANSWER_SHA256", hashlib.sha256(b"recorded").hexdigest())
    monkeypatch.setattr(pilot, "CALIBRATION_OUTPUT_SHA256", hashlib.sha256(b"graded").hexdigest())
    monkeypatch.setattr(pilot, "_git_head", lambda root: pilot.UPSTREAM_COMMIT)
    return root, tmp_path / "run", champions, answer


class Fakes:
    """Solver, proposer model and Jev with a shared call log."""

    def __init__(self, candidate_score=1.0, champion_score=1.0):
        self.solver_calls, self.model_calls, self.jev_calls = [], [], []
        self.scores = {"champion": champion_score, "candidate": candidate_score}
        self.replays = []
        self.overrides = {}  # 1-based solver call index -> replacement result

    def solver(self, candidate, item_id, input_dir, prediction, env):
        self.solver_calls.append((candidate.id, item_id))
        if len(self.solver_calls) in self.overrides:
            return {"item_id": item_id, **self.overrides[len(self.solver_calls)]}
        out = prediction.parent.parent / f"evidence-{len(self.solver_calls)}"
        (out / "work").mkdir(parents=True)
        (out / "work/answer.json").write_text('{"answer": "x"}')
        (out / "measurement.json").write_text(json.dumps({"token_usage": {"total_tokens": 3}}))
        arm = "candidate" if "Improved" in candidate.components["SKILL.md"] else "champion"
        return {"item_id": item_id, "score": self.scores[arm], "evidence_dir": str(out)}

    def model(self, prompt):
        self.model_calls.append(prompt)
        return f"```markdown\n# Improved skill {len(self.model_calls)}\n```"

    def replay(self, answer):
        self.replays.append(answer)
        return b"graded"

    @property
    def jev(self):
        fakes = self

        class Jev:
            name, model = "jev", "jev-latest"

            def decide(self, envelope):
                fakes.jev_calls.append(envelope)
                return {"D2": "c1"}
        return Jev()


def optimise(tree, fakes, group):
    root, run_dir, champions, answer = tree
    return pilot.optimise_group(root=root, run_dir=run_dir, group=group, champion=champions[group],
                                solver=fakes.solver, proposer=pilot.in_process_proposer(fakes.model), jev=fakes.jev,
                                calibration_answer=answer, calibration_replay=fakes.replay)


def approve_matching(path):
    request = json.loads(path.read_text())
    (path.parent / "approval.json").write_text(json.dumps({
        "candidate_hash": request["candidate_hash"], "evaluator_hash": request["evaluator_hash"],
        "data_hash": request["data_hash"], "code_hash": request["code_hash"], "approver": "Billy"}))


def final(tree, fakes, group, wait=approve_matching):
    root, run_dir, champions, answer = tree
    return pilot.final_phase(root=root, run_dir=run_dir, group=group, champions=champions,
                             solver=fakes.solver, calibration_answer=answer,
                             calibration_replay=fakes.replay, wait=wait)


def final_all(tree, fakes, wait=approve_matching):
    return {group: final(tree, fakes, group, wait) for group in pilot.GROUPS}


def drift_package(tmp_path, monkeypatch):
    """Copy the package and lock so a test can change the code hash after optimisation."""
    package, lock = tmp_path / "src/rsi_kernel", tmp_path / "uv.lock"
    shutil.copytree(pilot.PACKAGE_DIR, package, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copyfile(pilot.LOCK_FILE, lock)
    monkeypatch.setattr(pilot, "PACKAGE_DIR", package)
    monkeypatch.setattr(pilot, "LOCK_FILE", lock)
    return package


def addendum(tmp_path):
    path = tmp_path / "prereg-s4-addendum.md"
    path.write_text("# Trim the pilot final phase\n")
    return path


def rebind(tree, group, path):
    root, run_dir, champions, _ = tree
    return pilot.rebind(root=root, run_dir=run_dir, group=group, champion=champions[group], addendum=path)


def test_optimise_caps_per_group_and_wiring(tree):
    fakes = Fakes()
    result = optimise(tree, fakes, "task_group_001")
    assert result.evaluator_items_used <= pilot.EVAL_CAP == 36
    calls = [json.loads(line) for line in (tree[1] / "task_group_001/calls.jsonl").read_text().splitlines()]
    assert len(calls) <= pilot.SPEND_CAP == 42
    assert len(calls) == len(fakes.solver_calls) + len(fakes.model_calls) + len(fakes.jev_calls)
    assert {c["kind"] for c in calls} == {"solver", "proposer", "jev"}
    assert all(c["token_usage"] == {"total_tokens": 3} for c in calls if c["kind"] == "solver")
    assert {item for _, item in fakes.solver_calls} == {f"task_group_001/train/{i}" for i in pilot.DEV_IDS}
    assert result.selected is not None and result.attempts == pilot.MAX_ATTEMPTS
    decisions = [json.loads(line) for line in (tree[1] / "task_group_001/decisions.jsonl").read_text().splitlines()]
    assert decisions and all("baseline_answer" in d and d["backend"] == "jev" for d in decisions)
    state = json.loads((tree[1] / "task_group_001/campaign.json").read_text())
    assert state["status"] == "closed" and state["selected"]["components"] == dict(result.selected.components)


def test_optimise_spend_cap_counts_failed_calls(tree):
    fakes = Fakes()
    def failing(prompt):
        fakes.model_calls.append(prompt)
        raise RuntimeError("model down")
    root, run_dir, champions, answer = tree
    with pytest.raises(RuntimeError):
        pilot.optimise_group(root=root, run_dir=run_dir, group="task_group_001", champion=champions["task_group_001"],
                             solver=fakes.solver, proposer=pilot.in_process_proposer(failing), jev=fakes.jev,
                             calibration_answer=answer, calibration_replay=fakes.replay)
    kinds = [json.loads(line)["kind"] for line in (run_dir / "task_group_001/calls.jsonl").read_text().splitlines()]
    assert kinds.count("proposer") == 1


def group_items(group):
    """Adjudication + holdout item ids of one group (prereg carving map)."""
    return sorted([f"{group}/test/{i}" for i in pilot.TEST_IDS] + [f"{group}/train/{i}" for i in pilot.ADJ_IDS])


def test_group_with_candidate_has_42_final_observations(tree):
    """Issue #36 bullet 1: run -> task id -> arm, no dev or control rows."""
    fakes = Fakes()
    group = "task_group_001"
    optimise(tree, fakes, group)
    fakes.solver_calls.clear()
    result = final(tree, fakes, group)
    rows = [json.loads(line) for line in
            (tree[1] / f"final/{group}/observations.jsonl").read_text().splitlines()]
    expected = [(run, item, arm) for run in range(pilot.RUNS) for item in group_items(group) for arm in pilot.ARMS]
    assert len(rows) == len(fakes.solver_calls) == 42
    assert [(r["run"], r["item_id"], r["arm"]) for r in rows] == expected
    assert {r["arm"] for r in rows} == {"champion", "candidate"}
    dev = {f"{group}/train/{i}" for i in pilot.DEV_IDS}
    assert not dev & {r["item_id"] for r in rows}
    assert result.outcome == "updated"


def test_group_without_candidate_gets_no_solves_and_no_improvement(tree):
    """Issue #36 bullet 1: an unselected campaign solves nothing and is not an update."""
    fakes = Fakes(candidate_score=0.0)  # dev regression every attempt: nothing selected
    group = "task_group_001"
    optimise(tree, fakes, group)
    assert json.loads((tree[1] / group / "campaign.json").read_text())["selected"] is None
    fakes.solver_calls.clear()
    result = final(tree, fakes, group)
    assert result.outcome == "no_improvement"
    assert not fakes.solver_calls
    assert (tree[1] / f"final/{group}/observations.jsonl").read_text() == ""
    assert json.loads((tree[1] / group / "acceptance.json").read_text()) == {"outcome": "no_improvement"}


def test_final_runs_one_group_and_a_second_run_of_it_stops(tree):
    """Issue #36 bullet 2: one group per process; the holdout is reported once."""
    fakes = Fakes()
    optimise_all(tree, fakes)
    assert final(tree, fakes, "task_group_001").outcome == "updated"
    assert not (tree[1] / "final/task_group_002").exists()
    entropy = (tree[1] / "entropy.json").read_text()
    calls = len(fakes.solver_calls)
    with pytest.raises(pilot.PilotStop, match="already ran"):
        final(tree, fakes, "task_group_001")
    assert len(fakes.solver_calls) == calls  # the STOP is before any solve
    assert final(tree, fakes, "task_group_002").outcome == "updated"
    assert (tree[1] / "entropy.json").read_text() == entropy  # created exclusively once


def test_accept_consumes_each_record_exactly_once(tree):
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    champ = Candidate({"SKILL.md": "c"}, "text/plain")
    row = {"arm": "champion", "item_id": "a", "run": 0, "score": 1.0}
    with pytest.raises(ValueError, match="duplicate"):
        pilot._Replay([row, row], champ.id, None)
    replay = pilot._Replay([row], champ.id, None)
    assert replay.evaluate(champ, ["a"]) == [row]
    with pytest.raises(KeyError):  # a second request for the same key is never served
        replay.evaluate(champ, ["a"])
    replay.check_consumed()
    with pytest.raises(pilot.PilotStop):
        pilot._Replay([row], champ.id, None).check_consumed()
    results = final_all(tree, fakes)
    for group in pilot.GROUPS:
        private = [json.loads(line) for line in (tree[1] / group / "private/results.jsonl").read_text().splitlines()]
        keys = [(r["candidate_id"], r["item_id"], r["run"]) for r in private]
        assert len(keys) == len(set(keys)) == 2 * 7 * pilot.RUNS
        assert results[group].holdout_results is not None


def test_final_refuses_while_a_campaign_is_open(tree):
    fakes = Fakes()
    optimise(tree, fakes, "task_group_001")
    optimise(tree, fakes, "task_group_002")
    (tree[1] / "task_group_003").mkdir(parents=True)
    (tree[1] / "task_group_003/campaign.json").write_text(json.dumps({"status": "open"}))
    fakes.solver_calls.clear()
    with pytest.raises(pilot.PilotStop, match="open"):
        final(tree, fakes, "task_group_003")
    assert not fakes.solver_calls


def test_optimise_solver_still_rejects_test_tasks_acceptance_admits_them(tree):
    root = tree[0]
    tasks = pilot.frozen_tasks(root, "task_group_001")
    test_task = next(t for t in tasks if t.subset == "test")
    with pytest.raises(ValueError, match="dev train"):
        DockerSolver(root=root, tasks=[test_task], evidence_dir=tree[1] / "e", timeout=1)
    assert DockerSolver(root=root, tasks=tasks, evidence_dir=tree[1] / "e", timeout=1, stage="acceptance").tasks
    with pytest.raises(ValueError):
        DockerSolver(root=root, tasks=tasks, evidence_dir=tree[1] / "e", timeout=1, stage="other")


@pytest.mark.parametrize("approval", [None, "mismatch", "malformed"])
def test_missing_or_mismatched_approval_is_not_updated(tree, approval):
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)

    def wait(path):
        assert json.loads(path.read_text())["candidate_hash"]
        if approval == "mismatch":
            approve_matching(path)
            record = json.loads((path.parent / "approval.json").read_text())
            (path.parent / "approval.json").write_text(json.dumps({**record, "data_hash": "other"}))
        elif approval == "malformed":
            (path.parent / "approval.json").write_text("{")
    results = final_all(tree, fakes, wait)
    assert {r.outcome for r in results.values()} == {"not_updated"}
    decisions = [json.loads(line) for line in (tree[1] / "task_group_001/private/decisions.jsonl").read_text().splitlines()]
    assert not any(d.get("mode") == "record-only" for d in decisions)


def test_matching_approval_is_updated_record_only(tree):
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    group = "task_group_001"
    results = {group: final(tree, fakes, group)}
    assert results[group].outcome == "updated"
    decisions = [json.loads(line) for line in (tree[1] / group / "private/decisions.jsonl").read_text().splitlines()]
    assert {"candidate_id": results[group].request.candidate_hash, "mode": "record-only"} in decisions
    # Issue #42: the approval request binds the campaign's frozen full-code hash.
    request = json.loads((tree[1] / group / "approval-request.json").read_text())
    assert request["code_hash"] == json.loads((tree[1] / group / "campaign.json").read_text())["code_hash"]
    champion = Path(tree[2][group]["path"]).read_text()
    assert champion == f"# {group} skill\n"


@pytest.mark.parametrize("drift", ["replay", "answer", "pin"])
def test_prerun_drift_stops_before_any_solver_call(tree, monkeypatch, drift):
    fakes = Fakes()
    if drift == "replay":
        fakes.replay = lambda answer: b"different"
    elif drift == "answer":
        tree[3].write_bytes(b"changed")
    else:
        monkeypatch.setattr(pilot, "_git_head", lambda root: "0" * 40)
    with pytest.raises(pilot.PilotStop):
        optimise(tree, fakes, "task_group_001")
    assert not fakes.solver_calls and not fakes.model_calls and not fakes.jev_calls
    assert not (tree[1] / "task_group_001/campaign.json").exists()


def test_report_inputs_use_analysis(tree):
    """Issue #36: dev from the optimise archive, then adjudication and holdout."""
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    final_all(tree, fakes)
    rows = pilot.report(tree[1], tree[0], "updated")
    assert [r["split"] for r in rows] == ["dev", "adjudication", "holdout"]
    assert all(r["retention_passed"] for r in rows)
    # Noise is the champion's dev run-to-run spread; the fake scores never vary.
    assert {r["champion_run_spread"] for r in rows} == {0.0}
    assert pilot._run_spread([{"item_id": "a", "score": s} for s in (0.0, 1.0)]) == 0.5


def test_proposer_runtime_network_defaults_to_none(tmp_path):
    from rsi_kernel.adapters.gdpevo.runtime import GDPevoProposerRuntime
    (tmp_path / "dev").mkdir()
    (tmp_path / "out").mkdir()
    default = GDPevoProposerRuntime("img", tmp_path / "dev", tmp_path / "out").docker_argv(["true"])
    assert default[default.index("--network") + 1] == "none"
    live = GDPevoProposerRuntime("img", tmp_path / "dev", tmp_path / "out", network="gdp-x-pnet").docker_argv(["true"])
    assert live[live.index("--network") + 1] == "gdp-x-pnet" and live.count("--network") == 1


def test_http_model_posts_without_credentials_and_records_usage(tmp_path, monkeypatch):
    sent = []

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"usage": {"total_tokens": 9}, "output": [
                {"type": "reasoning"},
                {"type": "message", "content": [{"type": "output_text", "text": "```\n# New\n```"}]}]}).encode()

    class Opener:
        def open(self, request, timeout):
            sent.append((request, timeout))
            return Response()
    monkeypatch.setattr(pilot.urllib.request, "build_opener", lambda *handlers: Opener())
    log = tmp_path / "calls.jsonl"
    assert pilot.http_model(log)("prompt") == "```\n# New\n```"
    request, timeout = sent[0]
    assert request.full_url == "http://model-fwd:8080/v1/responses" and timeout == pilot.TIMEOUT
    assert {k.lower() for k in request.headers} == {"content-type"}
    body = json.loads(request.data)
    assert body["model"] == "gpt-6.1-sol" and body["input"] == [{"role": "user", "content": [{"type": "input_text", "text": "prompt"}]}]
    calls = pilot._Calls(tmp_path / "metered.jsonl")
    pilot.ContainerProposer._meter(log, calls)
    assert calls.count == 1
    assert json.loads((tmp_path / "metered.jsonl").read_text()) == {"kind": "proposer", "token_usage": {"total_tokens": 9}}


def test_failed_http_call_is_still_metered(tmp_path, monkeypatch):
    class Opener:
        def open(self, request, timeout):
            raise OSError("down")
    monkeypatch.setattr(pilot.urllib.request, "build_opener", lambda *handlers: Opener())
    log = tmp_path / "calls.jsonl"
    with pytest.raises(OSError):
        pilot.http_model(log)("prompt")
    calls = pilot._Calls(tmp_path / "metered.jsonl")
    pilot.ContainerProposer._meter(log, calls)
    assert calls.count == 1


class _ScriptedServer:
    """Real local HTTP server: each request pops one scripted response.

    Script entries are ``(status, headers, body)``; a ``(status, headers, body)`` with
    status 0 means "drop the connection" so urllib raises a genuine connection error.
    """

    def __init__(self, script):
        import http.server
        import threading
        self.script, self.requests = list(script), []
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                server.requests.append(self.path)
                status, headers, body = server.script.pop(0)
                if status == 0:  # close without a response -> connection error
                    self.close_connection = True
                    self.wfile.close()
                    return
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1/responses"
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.httpd.shutdown()
        self.httpd.server_close()


OK_BODY = json.dumps({"usage": {"total_tokens": 3}, "output": [
    {"type": "message", "content": [{"type": "output_text", "text": "ok"}]}]}).encode()


def test_http_model_retries_502_then_succeeds(tmp_path, monkeypatch):
    """Acceptance 1: transient 502 then 200 -> success on the second attempt."""
    slept = []
    monkeypatch.setattr(pilot, "_retry_sleep", slept.append)
    monkeypatch.setattr(pilot, "_retry_random", lambda: 0.0)  # jitter 1 - 0.25*0 = 1
    with _ScriptedServer([(502, {}, b""), (200, {}, OK_BODY)]) as server:
        log = tmp_path / "calls.jsonl"
        assert pilot.http_model(log, url=server.url)("prompt") == "ok"
        assert len(server.requests) == 2
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert [r["call"] for r in rows] == ["started", "retry", "usage"]
    assert rows[1]["status"] == 502 and rows[1]["attempt"] == 1
    assert slept == [pilot.INITIAL_RETRY_DELAY]


def test_http_model_gives_up_after_three_attempts(tmp_path, monkeypatch):
    """Acceptance 2: three 502s -> the same operational failure as today, 3 attempts."""
    monkeypatch.setattr(pilot, "_retry_sleep", lambda seconds: None)
    with _ScriptedServer([(502, {}, b"")] * 3) as server:
        log = tmp_path / "calls.jsonl"
        with pytest.raises(pilot.urllib.error.HTTPError) as caught:
            pilot.http_model(log, url=server.url)("prompt")
        assert caught.value.code == 502
        assert len(server.requests) == 3
    calls = pilot._Calls(tmp_path / "metered.jsonl")
    pilot.ContainerProposer._meter(log, calls)
    # One logical proposer call against the spend cap; retries are logged, not metered again.
    assert calls.count == 1
    rows = [json.loads(line) for line in log.read_text().splitlines()]
    assert [r["call"] for r in rows] == ["started", "retry", "retry"]


@pytest.mark.parametrize("status", [400, 401, 404])
def test_http_model_does_not_retry_client_errors(tmp_path, monkeypatch, status):
    """Acceptance 3: 400/401/404 are permanent -> exactly one attempt."""
    slept = []
    monkeypatch.setattr(pilot, "_retry_sleep", slept.append)
    with _ScriptedServer([(status, {}, b"")] * 2) as server:
        with pytest.raises(pilot.urllib.error.HTTPError) as caught:
            pilot.http_model(tmp_path / "calls.jsonl", url=server.url)("prompt")
        assert caught.value.code == status
        assert len(server.requests) == 1
    assert slept == []


def test_http_model_honours_retry_after(tmp_path, monkeypatch):
    """Acceptance 4: 429 with Retry-After: 0 is retried (SDK honours only 0 < value)."""
    slept = []
    monkeypatch.setattr(pilot, "_retry_sleep", slept.append)
    # Draw 1.0 -> jitter factor 0.75. If the Retry-After path were jittered, 7 would
    # come back as 5.25 and this assertion fails, proving _base_client.py:802 returns
    # before the jitter block at :811-813.
    monkeypatch.setattr(pilot, "_retry_random", lambda: 1.0)
    with _ScriptedServer([(429, {"Retry-After": "0"}, b""),
                          (429, {"Retry-After": "7"}, b""),
                          (200, {}, OK_BODY)]) as server:
        assert pilot.http_model(tmp_path / "calls.jsonl", url=server.url)("prompt") == "ok"
        assert len(server.requests) == 3
    # Retry-After 0 is not honoured as a server delay (SDK requires 0 < value), so that
    # attempt uses the jittered backoff; Retry-After 7 is returned unjittered.
    assert slept == [pytest.approx(pilot.INITIAL_RETRY_DELAY * 0.75), 7]


def test_http_model_retries_connection_errors_with_exponential_backoff(tmp_path, monkeypatch):
    """Connection errors retry too; backoff is INITIAL_RETRY_DELAY * 2**n, capped."""
    slept = []
    monkeypatch.setattr(pilot, "_retry_sleep", slept.append)
    monkeypatch.setattr(pilot, "_retry_random", lambda: 0.0)
    with _ScriptedServer([(0, {}, b""), (0, {}, b"")]) as server:
        with pytest.raises(OSError):
            pilot.http_model(tmp_path / "calls.jsonl", url=server.url)("prompt")
        assert len(server.requests) == 3
    assert slept == [pilot.INITIAL_RETRY_DELAY, pilot.INITIAL_RETRY_DELAY * 2]


@pytest.mark.parametrize("draw, expected", [
    (0.0, 1.0),     # jitter 1 - 0.25*0.0  = 1.00
    (0.5, 0.875),   # jitter 1 - 0.25*0.5  = 0.875
    (1.0, 0.75),    # jitter 1 - 0.25*1.0  = 0.75
])
def test_retry_delay_applies_sdk_jitter(monkeypatch, draw, expected):
    """_base_client.py:811-813: ``sleep_seconds * (1 - 0.25 * random())``, clamped at 0."""
    monkeypatch.setattr(pilot, "_retry_random", lambda: draw)
    assert pilot._retry_delay(OSError("down"), 0) == pilot.INITIAL_RETRY_DELAY * expected


def test_retry_delay_jitter_is_bounded_and_capped(monkeypatch):
    """Jitter spans [0.75, 1.0] of the backoff; the 8 s cap applies before scaling."""
    monkeypatch.setattr(pilot, "_retry_random", lambda: 0.0)
    assert pilot._retry_delay(OSError("down"), 10) == pilot.MAX_RETRY_DELAY
    # Attempts 0 and 1 stay under the cap, so they scale the raw backoff.
    assert pilot._retry_delay(OSError("down"), 0) == pilot.INITIAL_RETRY_DELAY
    assert pilot._retry_delay(OSError("down"), 1) == pilot.INITIAL_RETRY_DELAY * 2
    monkeypatch.setattr(pilot, "_retry_random", lambda: 1.0)
    assert pilot._retry_delay(OSError("down"), 10) == pytest.approx(pilot.MAX_RETRY_DELAY * 0.75)


# --- SDK parity round (PR #62 review): parser, excessive delay, x-should-retry ---

def _http_error(status, headers=None):
    """urllib HTTPError carrying real response headers, for the decision-level tests."""
    return pilot.urllib.error.HTTPError(
        "http://model-fwd:8080/v1/responses", status, "err", _headers(headers or {}), None)


def _headers(mapping):
    message = email.message.Message()
    for name, value in mapping.items():
        message[name] = value
    return message


def test_parse_retry_after_prefers_milliseconds_then_seconds(monkeypatch):
    """_base_client.py:762-776: retry-after-ms (ms -> s) wins over retry-after."""
    assert pilot._parse_retry_after({"retry-after-ms": "1500"}) == 1.5
    assert pilot._parse_retry_after({"retry-after-ms": "1500", "retry-after": "9"}) == 1.5
    assert pilot._parse_retry_after({"retry-after": "9"}) == 9.0
    assert pilot._parse_retry_after({"retry-after": "2.5"}) == 2.5  # nonstandard float allowed
    assert pilot._parse_retry_after({}) is None


def test_parse_retry_after_malformed_is_none(monkeypatch):
    """_base_client.py:767-770,786-787: unparseable numerics fall through; bad dates -> None."""
    assert pilot._parse_retry_after({"retry-after-ms": "soon"}) is None
    assert pilot._parse_retry_after({"retry-after": "later"}) is None
    assert pilot._parse_retry_after({"retry-after": ""}) is None


def test_parse_retry_after_excessive_numeric_overflow(monkeypatch):
    """_base_client.py:771-775: numeric overflow is an excessive delay sentinel, not None."""
    # 1e309 parses to inf but is not the literal infinity spelling -> sentinel.
    assert pilot._parse_retry_after({"retry-after": "1e309"}) == pilot.MAX_RETRY_AFTER_DELAY + 1
    assert pilot._parse_retry_after({"retry-after-ms": "1e400"}) == pilot.MAX_RETRY_AFTER_DELAY + 1


def test_parse_retry_after_literal_infinity_follows_sdk(monkeypatch):
    """_base_client.py:771 exempts the literal spellings from the overflow sentinel, so
    they return the parsed double (inf). :817 requires isfinite to refuse a retry, so an
    infinity is NOT treated as excessive: the call is retried, and :801's isfinite guard
    makes the delay fall back to exponential backoff. Only numeric overflow is refused."""
    for literal in ("inf", "infinity", "+inf", "+Infinity", " INF "):
        parsed = pilot._parse_retry_after({"retry-after": literal})
        assert parsed == float("inf") and not math.isfinite(parsed)
    inf_error = _http_error(502, {"retry-after": "inf"})
    assert pilot._retryable(inf_error) is True
    # The delay ignores the non-finite value and uses the backoff (:801 isfinite guard).
    monkeypatch.setattr(pilot, "_retry_random", lambda: 0.0)
    assert pilot._retry_delay(inf_error, 0) == pilot.INITIAL_RETRY_DELAY


def test_parse_retry_after_http_date_is_relative_to_now(monkeypatch):
    """_base_client.py:778-789: HTTP-date becomes seconds from now."""
    monkeypatch.setattr(pilot, "_retry_now", lambda: 1_800_000_000.0)
    future = email.utils.formatdate(1_800_000_030, usegmt=True)
    assert pilot._parse_retry_after({"retry-after": future}) == pytest.approx(30, abs=1)
    past = email.utils.formatdate(1_799_999_970, usegmt=True)
    assert pilot._parse_retry_after({"retry-after": past}) == pytest.approx(-30, abs=1)


def test_retry_after_boundary_120_is_retried_and_121_is_not(monkeypatch):
    """_base_client.py:817-823: >120 s (inclusive at 120) refuses retry; 120 is allowed."""
    slept = []
    monkeypatch.setattr(pilot, "_retry_sleep", slept.append)
    monkeypatch.setattr(pilot, "_retry_random", lambda: 0.0)
    assert pilot._retryable(_http_error(502, {"retry-after": "120"})) is True
    assert pilot._retryable(_http_error(502, {"retry-after": "121"})) is False
    assert pilot._retryable(_http_error(502, {"retry-after": "1e309"})) is False
    assert pilot._retry_delay(_http_error(502, {"retry-after": "120"}), 0) == 120


def test_excessive_retry_after_body_returns_no_retry(tmp_path, monkeypatch):
    """End to end: a 502 with Retry-After 121 makes exactly one attempt, no sleep."""
    slept = []
    monkeypatch.setattr(pilot, "_retry_sleep", slept.append)
    with _ScriptedServer([(502, {"Retry-After": "121"}, b"")] * 2) as server:
        with pytest.raises(pilot.urllib.error.HTTPError):
            pilot.http_model(tmp_path / "calls.jsonl", url=server.url)("prompt")
        assert len(server.requests) == 1
    assert slept == []


def test_x_should_retry_header_overrides_status(monkeypatch):
    """_base_client.py:825-834: true -> retry, false -> no retry, checked before status."""
    assert pilot._retryable(_http_error(502, {"x-should-retry": "false"})) is False
    assert pilot._retryable(_http_error(400, {"x-should-retry": "true"})) is True
    # Unrecognised values fall through to the status rules.
    assert pilot._retryable(_http_error(502, {"x-should-retry": "maybe"})) is True
    assert pilot._retryable(_http_error(400, {"x-should-retry": "maybe"})) is False


def test_x_should_retry_true_retries_a_400_end_to_end(tmp_path, monkeypatch):
    """A 400 that the server marks retryable is retried on the wire."""
    slept = []
    monkeypatch.setattr(pilot, "_retry_sleep", slept.append)
    monkeypatch.setattr(pilot, "_retry_random", lambda: 0.0)
    with _ScriptedServer([(400, {"x-should-retry": "true"}, b""), (200, {}, OK_BODY)]) as server:
        assert pilot.http_model(tmp_path / "calls.jsonl", url=server.url)("prompt") == "ok"
        assert len(server.requests) == 2
    assert slept == [pilot.INITIAL_RETRY_DELAY]


def test_meter_counts_successful_retry_as_one_entry(tmp_path, monkeypatch):
    """Accounting: a retried-then-successful call is ONE proposer entry with its usage."""
    monkeypatch.setattr(pilot, "_retry_sleep", lambda seconds: None)
    monkeypatch.setattr(pilot, "_retry_random", lambda: 0.0)
    log = tmp_path / "calls.jsonl"
    with _ScriptedServer([(502, {}, b""), (200, {}, OK_BODY)]) as server:
        assert pilot.http_model(log, url=server.url)("prompt") == "ok"
    calls = pilot._Calls(tmp_path / "metered.jsonl")
    pilot.ContainerProposer._meter(log, calls)
    assert calls.count == 1
    assert json.loads((tmp_path / "metered.jsonl").read_text()) == {
        "kind": "proposer", "token_usage": {"total_tokens": 3}}


def test_meter_does_not_leak_usage_across_a_failed_call(tmp_path, monkeypatch):
    """Accounting: a failed call must not take the NEXT call's usage."""
    monkeypatch.setattr(pilot, "_retry_sleep", lambda seconds: None)
    monkeypatch.setattr(pilot, "_retry_random", lambda: 0.0)
    log = tmp_path / "calls.jsonl"
    with _ScriptedServer([(502, {}, b"")] * 3) as server:
        with pytest.raises(pilot.urllib.error.HTTPError):
            pilot.http_model(log, url=server.url)("first")
    with _ScriptedServer([(200, {}, OK_BODY)]) as server:
        assert pilot.http_model(log, url=server.url)("second") == "ok"
    calls = pilot._Calls(tmp_path / "metered.jsonl")
    pilot.ContainerProposer._meter(log, calls)
    rows = [json.loads(line) for line in (tmp_path / "metered.jsonl").read_text().splitlines()]
    assert calls.count == 2
    assert rows[0] == {"kind": "proposer", "token_usage": None}  # failed call: no usage
    assert rows[1] == {"kind": "proposer", "token_usage": {"total_tokens": 3}}


def test_container_proposer_uses_internal_network_and_shared_forwarder(tree, monkeypatch):
    from rsi_kernel.adapters.gdpevo import solver_docker
    root, run_dir, champions, _ = tree
    tasks = pilot.frozen_tasks(root, "task_group_001")
    solver = DockerSolver(root=root, tasks=[t for t in tasks if t.subset == "train"],
                          evidence_dir=run_dir / "evidence", timeout=1)
    adapter = pilot._adapter(root, run_dir / "task_group_001", tasks, pilot._champion(champions["task_group_001"]),
                             solver, "stages")
    argvs = []

    def fake_run(argv, output=None, *, check=True):
        argvs.append(list(argv))
        if "propose-in-container" in argv:
            out = Path(argv[argv.index("--mount") + 3].split(",")[1].split("=", 1)[1])
            (out / "calls.jsonl").write_text('{"call": "started"}\n{"call": "usage", "token_usage": null}\n')
            (out / "result.json").write_text(json.dumps({"skill": "# Proposed\n"}))
        import subprocess
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    monkeypatch.setattr(solver, "_run", fake_run)
    envs = []
    def environment(out):  # the real one creates out/docker-config, so twice per attempt fails
        envs.append(out)
        solver_docker._DOCKER_ENV.set({"PATH": ""})
    monkeypatch.setattr(solver, "_docker_environment", environment)
    calls = pilot._Calls(run_dir / "calls.jsonl")
    proposer = pilot.ContainerProposer(adapter, solver, run_dir / "proposer", "img")
    champion = adapter.get_artifact()
    candidate = proposer(champion, [], adapter.splits, calls)
    assert candidate.components == {"SKILL.md": "# Proposed\n"} and candidate.parent_ids == (champion.id,)
    assert calls.count == 1
    internal = next(a for a in argvs if a[:4] == ["docker", "network", "create", "--internal"])[-1]
    run = next(a for a in argvs if "propose-in-container" in a)
    assert run[run.index("--network") + 1] == internal and "-e" in run
    assert not any("KEY" in arg or "TOKEN" in arg for arg in run)
    assert ["docker", "network", "connect", "--alias", "model-fwd", internal] == next(
        a for a in argvs if a[:3] == ["docker", "network", "connect"])[:6]
    assert any(solver_docker.NGINX_IMAGE in a for a in argvs)
    assert len(envs) == 1
    removed = next(a for a in argvs if a[:3] == ["docker", "rm", "-f"])
    assert {name.rsplit("-", 1)[1] for name in removed[3:]} == {"proposer", "fwd"}
    assert "--rm" not in run and run[run.index("--name") + 1].endswith("-proposer")


@pytest.mark.parametrize("phase", ["final", "rebind"])
def test_final_and_rebind_require_a_group(tmp_path, phase):
    """Issue #36: the final phase is a per-group process (the launcher parallelises groups)."""
    config = tmp_path / "config.json"
    config.write_text("{}")
    with pytest.raises(SystemExit):
        pilot.main([phase, "--config", str(config)])


def test_owner_wait_polls_until_approval_file(tmp_path, monkeypatch):
    request = tmp_path / "approval-request.json"
    sleeps = []
    def sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) == 2:
            (tmp_path / "approval.json").write_text("{}")
    monkeypatch.setattr(pilot.time, "sleep", sleep)
    pilot._wait_for_owner(request)
    assert sleeps == [1, 1]


def optimise_all(tree, fakes):
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    fakes.solver_calls.clear()
    fakes.replays.clear()


def test_champion_change_between_phases_stops_before_solver(tree):
    fakes = Fakes()
    optimise_all(tree, fakes)
    config = tree[2]["task_group_002"]
    Path(config["path"]).write_text("# swapped champion\n")
    config["sha256"] = hashlib.sha256(Path(config["path"]).read_bytes()).hexdigest()
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, "task_group_002")
    assert not fakes.solver_calls and not fakes.replays


def test_code_change_between_phases_stops_then_a_valid_rebind_proceeds(tree, tmp_path, monkeypatch):
    """Issue #36 bullet 3: code drift STOPs; one recorded rebind lets the final run."""
    package = drift_package(tmp_path, monkeypatch)
    fakes = Fakes()
    optimise_all(tree, fakes)
    (package / "loop.py").write_text((package / "loop.py").read_text() + "# drift\n")
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, "task_group_001")
    assert not fakes.solver_calls and not fakes.replays
    path = addendum(tmp_path)
    record = rebind(tree, "task_group_001", path)
    state = json.loads((tree[1] / "task_group_001/campaign.json").read_text())
    assert record["from"] == {k: state[k] for k in ("champion_id", "evaluator_hash", "code_hash")}
    assert record["to"] != record["from"] and record["champion_id"] == state["champion_id"]
    assert record["addendum"] == str(path)
    assert record["addendum_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    stored = json.loads((tree[1] / "task_group_001/rebind.json").read_text())
    assert stored == record
    result = final(tree, fakes, "task_group_001")
    assert result.outcome == "updated"
    # Issue #42: approval binds the rebound (running) code, not the original frozen one.
    assert result.request.code_hash == record["to"]["code_hash"] != record["from"]["code_hash"]


def test_rebind_with_wrong_from_or_changed_champion_stops_before_solver(tree, tmp_path, monkeypatch):
    """Issue #36 bullet 3: from must equal campaign.json; the champion may not change."""
    package = drift_package(tmp_path, monkeypatch)
    fakes = Fakes()
    optimise_all(tree, fakes)
    (package / "loop.py").write_text((package / "loop.py").read_text() + "# drift\n")
    path = addendum(tmp_path)
    group = "task_group_001"
    rebind(tree, group, path)
    record = json.loads((tree[1] / group / "rebind.json").read_text())
    for broken in ({**record, "from": {**record["from"], "code_hash": "0" * 64}},
                   {**record, "to": {**record["to"], "code_hash": "0" * 64}},
                   {**record, "champion_id": "0" * 64}):
        (tree[1] / group / "rebind.json").write_text(json.dumps(broken))
        with pytest.raises(pilot.PilotStop, match="identity drift"):
            final(tree, fakes, group)
    assert not fakes.solver_calls and not fakes.replays
    # A rebind is only accepted while its recorded addendum still hashes to itself.
    (tree[1] / group / "rebind.json").write_text(json.dumps(record))
    path.write_text("# rewritten\n")
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, group)
    with pytest.raises(pilot.PilotStop, match="malformed rebind"):
        (tree[1] / group / "rebind.json").write_text("{")
        final(tree, fakes, group)
    assert not fakes.solver_calls and not fakes.replays


def test_rebind_refuses_open_campaign_and_a_second_rebind(tree, tmp_path):
    fakes = Fakes()
    optimise(tree, fakes, "task_group_001")
    path = addendum(tmp_path)
    assert rebind(tree, "task_group_001", path)
    with pytest.raises(pilot.PilotStop, match="already recorded"):
        rebind(tree, "task_group_001", path)
    (tree[1] / "task_group_002").mkdir(parents=True, exist_ok=True)
    (tree[1] / "task_group_002/campaign.json").write_text(json.dumps({"status": "open"}))
    with pytest.raises(pilot.PilotStop, match="open or missing"):
        rebind(tree, "task_group_002", path)


def test_code_hash_covers_package_and_lock(tmp_path):
    package, lock = tmp_path / "src/rsi_kernel", tmp_path / "uv.lock"
    package.mkdir(parents=True)
    (package / "a.py").write_text("a")
    lock.write_text("lock")
    before = pilot._code_hash(package, lock)
    (package / "__pycache__").mkdir()
    (package / "__pycache__/a.pyc").write_bytes(b"cache")
    assert pilot._code_hash(package, lock) == before
    lock.write_text("lock2")
    assert pilot._code_hash(package, lock) != before


# Schedule order per group (addendum #36): run -> adjudication + holdout task id -> champion,
# candidate. Call 2 is the first champion row of run 0 (test/001), call 1 its candidate row.
FAILED = {"score": None, "failure": {"status": "STOP", "reason": "solver"}}


@pytest.mark.parametrize("call,where", [(1, "champion on holdout"), (2, "candidate on holdout")])
def test_invalid_final_row_fails_gate_without_approval(tree, call, where):
    """Issue #36 bullet 4: a failed final row still blocks acceptance (existing behaviour)."""
    fakes = Fakes()
    optimise_all(tree, fakes)
    fakes.overrides = {call: FAILED}
    approvals = []
    results = final_all(tree, fakes, lambda path: approvals.append(path))
    group = "task_group_001"
    assert results[group].outcome == "failed_gate"
    assert not (tree[1] / group / "approval-request.json").exists()
    assert all(p.parent.name != group for p in approvals)
    assert len(approvals) == 2  # the other, valid groups still reach approval
    decisions = [json.loads(line) for line in (tree[1] / group / "private/decisions.jsonl").read_text().splitlines()]
    assert not any(d.get("mode") == "record-only" for d in decisions)


def test_scheduled_valid_requires_exactly_the_trimmed_schedule(tree):
    """Issue #36 bullet 1: 7 items x 3 runs x 2 arms; a dev or control row is invalid."""
    item_ids = ["a", "b"]
    rows = [{"arm": arm, "item_id": item, "run": run, "score": 1.0}
            for run in range(pilot.RUNS) for item in item_ids for arm in pilot.ARMS]
    assert len(rows) == 2 * pilot.RUNS * 2
    assert pilot._scheduled_valid(rows, item_ids)
    assert not pilot._scheduled_valid(rows + [{"arm": "control", "item_id": "a", "run": 0, "score": 1.0}], item_ids)
    assert not pilot._scheduled_valid(rows + [{"arm": "champion", "item_id": "c", "run": 0, "score": 1.0}], item_ids)
    assert not pilot._scheduled_valid(rows[:-1], item_ids)


def test_proposer_timeout_kills_and_verifies_named_container(tree, monkeypatch):
    import subprocess
    from rsi_kernel.adapters.gdpevo import solver_docker
    root, run_dir, champions, _ = tree
    tasks = pilot.frozen_tasks(root, "task_group_001")
    solver = DockerSolver(root=root, tasks=[t for t in tasks if t.subset == "train"],
                          evidence_dir=run_dir / "evidence", timeout=1)
    adapter = pilot._adapter(root, run_dir / "task_group_001", tasks, pilot._champion(champions["task_group_001"]),
                             solver, "stages")
    argvs = []

    def fake_run(argv, output=None, *, check=True):
        argvs.append(list(argv))
        if "propose-in-container" in argv:
            raise subprocess.TimeoutExpired(argv, 1)
        return subprocess.CompletedProcess(argv, 0, b"false\n" if "inspect" in argv else b"", b"")
    monkeypatch.setattr(solver, "_run", fake_run)
    monkeypatch.setattr(solver, "_docker_environment", lambda out: solver_docker._DOCKER_ENV.set({"PATH": ""}))
    calls = pilot._Calls(run_dir / "calls.jsonl")
    with pytest.raises(subprocess.TimeoutExpired):
        pilot.ContainerProposer(adapter, solver, run_dir / "proposer", "img")(
            adapter.get_artifact(), [], adapter.splits, calls)
    run = next(a for a in argvs if "propose-in-container" in a)
    name = run[run.index("--name") + 1]
    after = argvs[argvs.index(run) + 1:]
    assert after[0] == ["docker", "kill", name]
    assert after[1][:2] == ["docker", "inspect"] and after[1][-1] == name
    assert not any(a[:2] in (["docker", "rm"], ["docker", "network"]) for a in after)  # evidence kept



def test_rebind_cannot_swap_the_champion_even_if_the_record_agrees(tree, tmp_path, monkeypatch):
    """PR #37 review S1: frozen, current and recorded champion ids must all agree."""
    package = drift_package(tmp_path, monkeypatch)
    fakes = Fakes()
    optimise_all(tree, fakes)
    (package / "loop.py").write_text((package / "loop.py").read_text() + "# drift\n")
    path, group = addendum(tmp_path), "task_group_001"
    rebind(tree, group, path)
    config = tree[2][group]
    Path(config["path"]).write_text("# swapped champion\n")
    config["sha256"] = hashlib.sha256(Path(config["path"]).read_bytes()).hexdigest()
    swapped = pilot._champion(config).id
    record = json.loads((tree[1] / group / "rebind.json").read_text())
    record = {**record, "champion_id": swapped, "to": {**record["to"], "champion_id": swapped}}
    (tree[1] / group / "rebind.json").write_text(json.dumps(record))
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, group)
    assert not fakes.solver_calls and not fakes.replays


def test_existing_rebind_is_validated_even_without_drift(tree, tmp_path):
    """PR #37 review S2: a present rebind is never skipped, even when nothing drifted."""
    fakes = Fakes()
    optimise_all(tree, fakes)
    path, group = addendum(tmp_path), "task_group_001"
    rebind(tree, group, path)
    record = json.loads((tree[1] / group / "rebind.json").read_text())
    (tree[1] / group / "rebind.json").write_text(
        json.dumps({**record, "to": {**record["to"], "code_hash": "0" * 64}}))
    with pytest.raises(pilot.PilotStop, match="identity drift"):
        final(tree, fakes, group)
    assert not fakes.solver_calls and not fakes.replays


def test_report_lists_no_candidate_group_without_pairing_it(tree):
    """PR #37 review S2: a no-candidate group is reported, not fed to the paired estimator."""
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    state = tree[1] / "task_group_002/campaign.json"
    state.write_text(json.dumps({**json.loads(state.read_text()), "selected": None}))
    for group in pilot.GROUPS:
        final(tree, fakes, group)
    rows = pilot.report(tree[1], tree[0], "updated")
    assert [r["split"] for r in rows] == ["dev", "adjudication", "holdout"]
    assert all(r["no_candidate_groups"] == ["task_group_002"] for r in rows)
    assert all(r["paired_groups"] == ["task_group_001", "task_group_003"] for r in rows)


def test_report_lists_operationally_stopped_group_without_pairing_it(tree):
    """Issue #72: a campaign that stopped operationally has no ``selected`` key at all.

    The group is reported as stopped and unpaired, never as a no-candidate group and
    never fed to the paired estimator.
    """
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    # pilot-003/task_group_003 state: the campaign never closed, so the closed record
    # (outcome, stop_reason, selected) was never written.
    (tree[1] / "task_group_003/campaign.json").write_text(json.dumps({"status": "open"}))
    for group in pilot.GROUPS:
        if group != "task_group_003":
            final(tree, fakes, group)
    rows = pilot.report(tree[1], tree[0], "updated")
    assert [r["split"] for r in rows] == ["dev", "adjudication", "holdout"]
    assert all(r["stopped_groups"] == ["task_group_003"] for r in rows)
    assert all(r["no_candidate_groups"] == [] for r in rows)
    assert all(r["paired_groups"] == ["task_group_001", "task_group_002"] for r in rows)


def test_null_rebind_record_is_malformed_not_absent(tree, tmp_path):
    """PR #37 re-check: a present rebind.json holding JSON null still STOPs."""
    fakes = Fakes()
    optimise_all(tree, fakes)
    (tree[1] / "task_group_001/rebind.json").write_text("null")
    with pytest.raises(pilot.PilotStop, match="malformed rebind"):
        final(tree, fakes, "task_group_001")
    assert not fakes.solver_calls and not fakes.replays


@pytest.mark.parametrize("selected", [(), ("task_group_001",)])
def test_report_marks_comparison_unavailable_below_two_paired_groups(tree, selected):
    """PR #37 re-check: zero or one candidate group reports status, not a crash."""
    fakes = Fakes()
    for group in pilot.GROUPS:
        optimise(tree, fakes, group)
    for group in pilot.GROUPS:
        if group not in selected:
            state = tree[1] / group / "campaign.json"
            state.write_text(json.dumps({**json.loads(state.read_text()), "selected": None}))
    for group in pilot.GROUPS:
        final(tree, fakes, group)
    rows = pilot.report(tree[1], tree[0], "no_improvement")
    assert [r["split"] for r in rows] == ["dev", "adjudication", "holdout"]
    assert all(r["comparison"] == "unavailable" and r["paired_groups"] == list(selected) for r in rows)
    assert all(r["champion_run_spread"] == 0.0 for r in rows)

# S5 library artifact through the same driver (issue #35 addendum).

MEMORY = "SYNTHETIC_ENTRY_CANARY"
# Addendum §1: empty seed library, in the pilot's own candidate serialization.
EMPTY_SEED = {"components": {}, "media_type": "application/json", "parent_ids": []}


def brief(action):
    return {"task_pattern": "Toy JSON tasks", "action": action,
            "completion_criteria": "The toy answer passes", "pointers": ["toy/input/prompt.txt"]}


@pytest.fixture
def library_tree(tree, tmp_path):
    """The skill tree plus a champion library file per group (empty seed, addendum)."""
    from rsi_kernel.adapters.gdpevo_memory import pilot as memory_pilot
    root, run_dir, champions, answer = tree
    libraries = {}
    for group in pilot.GROUPS:
        path = tmp_path / f"{group}-library.json"
        path.write_text(json.dumps(EMPTY_SEED), encoding="utf-8")
        libraries[group] = {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    return tree, libraries, memory_pilot


class LibraryFakes(Fakes):
    """Same fakes, with a library-shaped model and a D2+D4 Jev."""

    def model(self, prompt):
        self.model_calls.append(prompt)
        return "```json\n" + json.dumps(brief(f"Improved skill {len(self.model_calls)} {MEMORY}")) + "\n```"

    @property
    def jev(self):
        fakes = self

        class Jev:
            name, model = "jev", "jev-latest"

            def decide(self, envelope):
                fakes.jev_calls.append(envelope)
                return {name: ("c1" if name == "D2" else "add") for name in envelope["questions"]}
        return Jev()


def optimise_library(library_tree, fakes, group):
    (root, run_dir, _, answer), libraries, memory_pilot = library_tree
    return pilot.optimise_group(root=root, run_dir=run_dir, group=group, champion=libraries[group],
                                solver=fakes.solver, proposer=pilot.in_process_proposer(
                                    fakes.model, hooks=memory_pilot.LIBRARY),
                                jev=fakes.jev, calibration_answer=answer,
                                calibration_replay=fakes.replay, hooks=memory_pilot.LIBRARY)


def final_library(library_tree, fakes, group, wait=approve_matching):
    (root, run_dir, _, answer), libraries, memory_pilot = library_tree
    return pilot.final_phase(root=root, run_dir=run_dir, group=group, champions=libraries,
                             solver=fakes.solver, calibration_answer=answer,
                             calibration_replay=fakes.replay, wait=wait, hooks=memory_pilot.LIBRARY)


def test_library_optimise_wiring_uses_one_proposer_and_d2_per_attempt(library_tree):
    fakes = LibraryFakes()
    result = optimise_library(library_tree, fakes, "task_group_001")
    assert result.selected is not None
    calls = [json.loads(line) for line in
             (library_tree[0][1] / "task_group_001/calls.jsonl").read_text().splitlines()]
    # 4 dev evaluations x 3 tasks x 3 runs = 36 solver, plus 3 proposer and 3 D2.
    kinds = [call["kind"] for call in calls]
    assert kinds.count("solver") == 36
    assert kinds.count("proposer") == 3
    assert kinds.count("jev") == pilot.MAX_ATTEMPTS
    assert len(calls) == 42 < library_tree[2].SPEND_CAP == 45
    decisions = [json.loads(line) for line in
                 (library_tree[0][1] / "task_group_001/decisions.jsonl").read_text().splitlines()]
    assert [next(iter(d["envelope"]["questions"])) for d in decisions] == ["D2"] * pilot.MAX_ATTEMPTS
    assert all(set(envelope["questions"]) == {"D2"} for envelope in fakes.jev_calls)
    # The canary is in every admitted entry; neither D2 envelopes nor logs receive it.
    from rsi_kernel.adapters.gdpevo_memory import read_library
    assert MEMORY in json.dumps(read_library(result.selected))
    assert MEMORY not in json.dumps(fakes.jev_calls)
    assert MEMORY not in (library_tree[0][1] / "task_group_001/decisions.jsonl").read_text()
    assert MEMORY not in (library_tree[0][1] / "task_group_001/calls.jsonl").read_text()


class DiscardFakes(LibraryFakes):
    """Library fakes whose live D4 answers discard on every attempt (addendum §9)."""

    @property
    def jev(self):
        fakes = self

        class Jev:
            name, model = "jev", "jev-latest"

            def decide(self, envelope):
                fakes.jev_calls.append(envelope)
                return {name: ("c1" if name == "D2" else "discard") for name in envelope["questions"]}
        return Jev()


def test_library_discard_decider_cannot_veto_draft_evaluation(library_tree):
    fakes = DiscardFakes()
    result = optimise_library(library_tree, fakes, "task_group_001")
    assert result.selected is not None
    assert result.outcome == "selected"
    assert result.evaluator_items_used == (pilot.MAX_ATTEMPTS + 1) * len(pilot.DEV_IDS) * pilot.RUNS
    assert len(fakes.solver_calls) == result.evaluator_items_used
    assert len(fakes.jev_calls) == pilot.MAX_ATTEMPTS
    assert all(set(envelope["questions"]) == {"D2"} for envelope in fakes.jev_calls)
    assert MEMORY not in json.dumps(fakes.jev_calls)


def test_library_empty_drafts_select_nothing_and_report_unavailable(library_tree):
    """No draft still means no candidate, no final solve, and unavailable comparisons."""
    run_dir, root = library_tree[0][1], library_tree[0][0]
    fakes = LibraryFakes()
    fakes.model = lambda prompt: ""
    results = {}
    for group in pilot.GROUPS:
        results[group] = optimise_library(library_tree, fakes, group)
        assert json.loads((run_dir / group / "campaign.json").read_text())["selected"] is None
        outcomes = [json.loads(line) for line in
                    (run_dir / group / "outcomes.jsonl").read_text().splitlines()]
        assert [o["outcome"] for o in outcomes] == ["no_candidate"] * pilot.MAX_ATTEMPTS
        assert results[group].selected is None
        assert results[group].outcome == "no_improvement"
        assert results[group].evaluator_items_used == len(pilot.DEV_IDS) * pilot.RUNS == 9
        calls = [json.loads(line) for line in (run_dir / group / "calls.jsonl").read_text().splitlines()]
        kinds = [call["kind"] for call in calls]
        # Only champion dev, proposer and D2 calls; unused D4 slots remain headroom.
        assert (kinds.count("solver"), kinds.count("proposer"), kinds.count("jev")) == (9, 3, 3)
        assert len(calls) == 15 < library_tree[2].SPEND_CAP == 45
        decisions = [json.loads(line) for line in
                     (run_dir / group / "decisions.jsonl").read_text().splitlines()]
        assert [next(iter(d["envelope"]["questions"])) for d in decisions] == ["D2"] * pilot.MAX_ATTEMPTS
        assert not any("fallback_reason" in d for d in decisions)
    # No candidate anywhere: the final phase solves nothing and is not an update.
    fakes.solver_calls.clear()
    for group in pilot.GROUPS:
        result = final_library(library_tree, fakes, group)
        assert result.outcome == "no_improvement"
        assert json.loads((run_dir / group / "acceptance.json").read_text()) == {"outcome": "no_improvement"}
        assert (run_dir / f"final/{group}/observations.jsonl").read_text() == ""
    assert not fakes.solver_calls  # the final solver is never invoked
    rows = pilot.report(run_dir, root, "no_improvement")
    assert [row["split"] for row in rows] == ["dev", "adjudication", "holdout"]
    assert all(row["comparison"] == "unavailable" and row["paired_groups"] == [] for row in rows)
    assert all(row["no_candidate_groups"] == list(pilot.GROUPS) for row in rows)
    assert all(row["reason"] == "fewer than two groups with a selected candidate" for row in rows)


def test_library_final_42_observations_stage_the_rendered_skill(library_tree):
    """S5 addendum §"final phase": #36's trimmed shape, with the library rendered per solve."""
    fakes = LibraryFakes()
    group = "task_group_001"
    optimise_library(library_tree, fakes, group)
    seen = []
    solver = fakes.solver

    def staged(candidate, item_id, input_dir, prediction, env):
        staged_skill = (input_dir.parent / "SKILL.md").read_bytes()
        assert Candidate({"SKILL.md": staged_skill}, "text/plain").id == candidate.id
        seen.append(candidate.id)
        return solver(candidate, item_id, input_dir, prediction, env)

    fakes.solver, fakes.solver_calls = staged, []
    result = final_library(library_tree, fakes, group)
    rows = [json.loads(line) for line in
            (library_tree[0][1] / f"final/{group}/observations.jsonl").read_text().splitlines()]
    expected = [(run, item, arm) for run in range(pilot.RUNS)
                for item in group_items(group) for arm in pilot.ARMS]
    assert len(rows) == len(seen) == 42
    assert [(r["run"], r["item_id"], r["arm"]) for r in rows] == expected
    assert {r["arm"] for r in rows} == {"champion", "candidate"}
    # Dev is never re-run: no dev item appears in the final phase.
    assert not {f"{group}/train/{i}" for i in pilot.DEV_IDS} & {r["item_id"] for r in rows}
    # Both arms stage the render of their own host library: the empty-seed champion
    # and the selected candidate. Nothing else is ever staged.
    from rsi_kernel.adapters.gdpevo_memory import read_library, render_skill
    selected = pilot._selected(library_tree[0][1] / group)
    assert set(seen) == {render_skill(selected).id,
                         render_skill(library_tree[2]._champion(library_tree[1][group])).id}
    assert read_library(selected)  # the admitted entry is what got evaluated
    assert result.outcome == "updated"
    # accept() consumed every scheduled record: _Replay.check_consumed would raise otherwise.
    assert result.holdout_results is not None
    private = [json.loads(line) for line in
               (library_tree[0][1] / group / "private/results.jsonl").read_text().splitlines()]
    keys = [(r["candidate_id"], r["item_id"], r["run"]) for r in private]
    assert len(keys) == len(set(keys)) == 2 * 7 * pilot.RUNS


def test_library_main_requires_group_for_final_and_rebind(library_tree, tmp_path):
    """#36 bullet: one group per process; the library entrypoint keeps that contract."""
    _, libraries, memory_pilot = library_tree
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"root": str(library_tree[0][0]), "run_dir": str(library_tree[0][1]),
                                  "champions": libraries, "calibration_answer": "x", "jev_url": "u"}))
    for phase in ("final", "rebind"):
        with pytest.raises(SystemExit):
            memory_pilot.main([phase, "--config", str(config)])
    # The container entrypoint still dispatches before argparse, as in the S4 driver.
    assert memory_pilot.LIBRARY.module == "rsi_kernel.adapters.gdpevo_memory.pilot"


def test_library_champion_file_uses_the_pilot_candidate_shape(library_tree, tmp_path):
    _, libraries, memory_pilot = library_tree
    from rsi_kernel.adapters.gdpevo_memory import library_candidate, read_library
    assert read_library(memory_pilot._champion(libraries["task_group_001"])) == {}
    seeded = library_candidate([brief("Seeded")])
    path = tmp_path / "seeded.json"
    path.write_text(json.dumps({"components": dict(seeded.components), "media_type": seeded.media_type,
                                "parent_ids": []}), encoding="utf-8")
    loaded = memory_pilot._champion({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    assert loaded.id == seeded.id and read_library(loaded) == {"e1": brief("Seeded")}
    with pytest.raises(pilot.PilotStop):
        memory_pilot._champion({**libraries["task_group_001"], "sha256": "0" * 64})


def test_library_container_draft_with_d4_fields_is_rejected(library_tree, monkeypatch):
    tree_, libraries, memory_pilot = library_tree
    from rsi_kernel.adapters.gdpevo import solver_docker
    root, run_dir = tree_[0], tree_[1]
    tasks = pilot.frozen_tasks(root, "task_group_001")
    solver = DockerSolver(root=root, tasks=[t for t in tasks if t.subset == "train"],
                          evidence_dir=run_dir / "evidence", timeout=1)
    champion = memory_pilot._champion(libraries["task_group_001"])
    adapter = pilot._adapter(root, run_dir / "task_group_001", tasks, champion, solver, "stages",
                             adapter_class=memory_pilot.LIBRARY.adapter_class)

    def fake_run(argv, output=None, *, check=True):
        if "propose-in-container" in argv:
            out = Path(argv[argv.index("--mount") + 3].split(",")[1].split("=", 1)[1])
            (out / "calls.jsonl").write_text('{"call": "started"}\n')
            (out / "result.json").write_text(json.dumps(
                {"draft": json.dumps({**brief("Changed"), "choice": "add", "id": "e9"})}))
        import subprocess
        return subprocess.CompletedProcess(argv, 0, b"", b"")
    monkeypatch.setattr(solver, "_run", fake_run)
    monkeypatch.setattr(solver, "_docker_environment", lambda out: solver_docker._DOCKER_ENV.set({"PATH": ""}))
    calls = pilot._Calls(run_dir / "calls.jsonl")
    proposer = pilot.ContainerProposer(adapter, solver, run_dir / "proposer", "img",
                                       memory_pilot.LIBRARY)
    with pytest.raises(ValueError):
        proposer(champion, [], adapter.splits, calls, decider=None, dev_results=[{"score": 1.0}])
    assert calls.count == 1  # the call is metered before the draft is rejected


# Addendum §8: the kernel-only identity is the same `_code_hash` formula with
# `adapters/` excluded, pinned to the frozen S4 commit.
S4_COMMIT = "7919829"
S4_FULL_CODE_HASH = "ad9447f6154165298314283ccec2610aec41d0d1a0c6eb1bf880adeb402ad082"
S4_KERNEL_ONLY_HASH = "e8d7b2b5d14018ab0ff68ee5b811aa133f07f60b0843638fb395c12ee6c4d209"


def test_addendum_identities_match_the_frozen_s4_commit(tmp_path):
    import subprocess
    repo = pilot.PACKAGE_DIR.parents[1]
    tar = subprocess.run(["git", "-C", str(repo), "archive", S4_COMMIT], capture_output=True)
    if tar.returncode != 0:  # CI checks out depth 1; the pinned commit may be absent there
        pytest.skip(f"{S4_COMMIT} not in the local clone")
    archive = tmp_path / "tree"
    archive.mkdir()
    subprocess.run(["tar", "-x", "-C", str(archive)], input=tar.stdout, check=True)
    package, lock = archive / "src/rsi_kernel", archive / "uv.lock"
    assert pilot._code_hash(package, lock) == S4_FULL_CODE_HASH
    assert pilot._code_hash(package, lock, exclude=("adapters",)) == S4_KERNEL_ONLY_HASH
    # The exclusion is what separates them: the two identities are not the same number.
    assert S4_FULL_CODE_HASH != S4_KERNEL_ONLY_HASH


# Issue #113: driver support for the registered E2 group set (docs/prereg-e2-skill-groups.md §2.1, §2.3).
E2_GROUPS = tuple(f"task_group_{n:03d}" for n in range(4, 10))


def test_registered_groups_are_exactly_001_to_009():
    assert pilot.GROUPS == ("task_group_001", "task_group_002", "task_group_003")  # historical set unchanged
    assert pilot.E2_GROUPS == E2_GROUPS
    assert pilot.REGISTERED_GROUPS == pilot.GROUPS + E2_GROUPS


def test_calibration_identity_is_pinned_independent_of_group_set():
    """E2 prereg §3 STOP 4: task_group_001/train/001 with the recorded answer/output sha256."""
    assert pilot.CALIBRATION_TASK == ("task_group_001", "train", "001")
    assert pilot.CALIBRATION_ANSWER_SHA256 == "5eb5cc630e4f69d1892b2fe721a593b8eb83513c96b723ff4c0f756e518ae96b"
    assert pilot.CALIBRATION_OUTPUT_SHA256 == "12308ca22e257b47c05099acec8679a9a06f2205c99870578885098adbf6205e"
    import inspect
    assert "GROUPS[0]" not in inspect.getsource(pilot)


@pytest.mark.parametrize("group", E2_GROUPS)
def test_e2_group_optimise_and_final_run_with_the_same_calibration(tree, group):
    root, run_dir, champions, answer = tree
    for subset, ids in (("train", pilot.TRAIN_IDS), ("test", pilot.TEST_IDS)):
        for task_id in ids:
            shutil.copytree(TOY, root / "data/task_groups" / group / f"{subset}_tasks" / task_id)
    champions[group] = champions["task_group_001"]
    fakes = Fakes()
    assert optimise(tree, fakes, group).outcome == "selected"
    assert {item for _, item in fakes.solver_calls} == {f"{group}/train/{i}" for i in pilot.DEV_IDS}
    assert final(tree, fakes, group).outcome == "updated"
    assert fakes.replays == [answer, answer]  # same pinned calibration answer for both phases


@pytest.mark.parametrize("group", ["task_group_000", "task_group_010", "task_group_022", "toy"])
def test_unregistered_groups_stop_before_any_solve(tree, group):
    fakes = Fakes()
    tree[2][group] = tree[2]["task_group_001"]
    with pytest.raises(pilot.PilotStop, match="unknown group"):
        optimise(tree, fakes, group)
    assert not fakes.solver_calls


def test_cli_group_choices_are_exactly_the_registered_set(tmp_path):
    config = tmp_path / "config.json"
    config.write_text("{}")
    with pytest.raises(SystemExit):
        pilot.main(["final", "--config", str(config), "--group", "task_group_010"])
    for group in ("task_group_004", "task_group_009"):
        with pytest.raises(KeyError):  # argparse accepted the group; the empty config fails next
            pilot.main(["final", "--config", str(config), "--group", group])


def test_report_takes_the_e2_group_set_explicitly(tree):
    root, run_dir, champions, _ = tree
    for group in E2_GROUPS[:2]:
        for subset, ids in (("train", pilot.TRAIN_IDS), ("test", pilot.TEST_IDS)):
            for task_id in ids:
                shutil.copytree(TOY, root / "data/task_groups" / group / f"{subset}_tasks" / task_id)
        champions[group] = champions["task_group_001"]
        fakes = Fakes()
        optimise(tree, fakes, group)
        final(tree, fakes, group)
    rows = pilot.report(run_dir, root, "updated", groups=E2_GROUPS[:2])
    assert all(r["paired_groups"] == list(E2_GROUPS[:2]) for r in rows)


def test_d2_metering_records_provider_usage_when_present_else_null(tmp_path):
    calls = pilot._Calls(tmp_path / "calls.jsonl")

    class Backend:
        name, model = "jev", "jev-latest"
        last_usage = None

        def __init__(self, usage, fail=False):
            self.usage, self.fail = usage, fail

        def decide(self, envelope):
            self.last_usage = self.usage
            if self.fail:
                raise ValueError("synthetic failure")
            return {"D2": "c1"}

    pilot._MeteredBackend(Backend({"total_tokens": 5}), calls).decide({})
    pilot._MeteredBackend(Backend(None), calls).decide({})
    with pytest.raises(ValueError):
        pilot._MeteredBackend(Backend(None, fail=True), calls).decide({})
    rows = [json.loads(line) for line in (tmp_path / "calls.jsonl").read_text().splitlines()]
    assert rows == [{"kind": "jev", "token_usage": {"total_tokens": 5}},
                    {"kind": "jev", "token_usage": None}, {"kind": "jev", "token_usage": None}]
