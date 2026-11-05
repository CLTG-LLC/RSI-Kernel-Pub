"""Ordered fallback logging, private invariance, and network-free replay."""

from dataclasses import dataclass
import http.client
import io
import json
import urllib.request

import pytest

from rsi_kernel.decision.backends import DeterministicBackend, JevBackend
from rsi_kernel.decision.envelope import DevPublicView, EnvelopeBuilder
from rsi_kernel.decision.log import Decider, ReplayBackend


URL = "https://api.experientiallabs.ai/v1/systemone"
CANARY = "RSI_CANARY_4f162_private_candidate"


def envelope(attempt=1):
    return EnvelopeBuilder(("c3", "c8"), ("e17",)).build(
        DevPublicView({"attempt_count": attempt, "budget_used": 0.5}, traces=CANARY,
                      candidate_text=CANARY, component_descriptions={"c3": CANARY}),
        decisions=("D2", "D4", "D5"),
    )


def records(log):
    return [json.loads(line) for line in log.getvalue().splitlines()]


@pytest.mark.parametrize("payload, reason", [
    (json.dumps({"answers": {"D2": {"choice": CANARY}, "D4": {"choice": "discard"},
                             "D5": {"choice": "strong"}}}).encode(), "off-list"),
    (CANARY.encode(), "malformed"),
    pytest.param(http.client.IncompleteRead(b"truncated"), "malformed", id="incomplete-read"),
    pytest.param(b"[" * 20_000 + b"0" + b"]" * 20_000, "malformed", id="nested-json"),
    (TimeoutError(CANARY), "timeout"),
])
def test_bad_response_uses_logged_fallback_without_content(monkeypatch, payload, reason):
    requests = []

    def open_request(self, request, timeout):
        requests.append(request.data)
        if isinstance(payload, Exception):
            raise payload
        return io.BytesIO(payload)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", open_request)
    log = io.StringIO()
    decider = Decider(JevBackend(URL), log)
    expected = {"D2": "c3", "D4": "discard", "D5": "strong"}
    assert decider.decide(envelope()) == expected
    assert records(log) == [{
        "seq": 1, "backend": "jev", "model": "jev-latest", "envelope": envelope(),
        "answer": expected, "baseline_answer": expected, "fallback_reason": reason,
        "fallback_backend": "deterministic", "fallback_model": "deterministic",
    }]
    assert CANARY not in log.getvalue()
    assert CANARY not in b"".join(requests).decode()
    assert "synthetic-test-key" not in log.getvalue()
    # Replay the actual Jev failure record, not only the baseline's successful calls.
    def no_network(*args, **kwargs):
        pytest.fail("fallback replay attempted a network call")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", no_network)
    assert ReplayBackend(log).decide(envelope()) == expected


def test_log_replay_reproduces_sequence_with_network_disabled(monkeypatch):
    log = io.StringIO()
    decider = Decider(DeterministicBackend(), log)
    requests = [envelope(attempt) for attempt in range(1, 4)]
    answers = [decider.decide(request) for request in requests]
    assert [record["seq"] for record in records(log)] == [1, 2, 3]

    def no_network(*args, **kwargs):
        pytest.fail("replay attempted a network call")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", no_network)
    monkeypatch.setattr(urllib.request, "urlopen", no_network)
    replay = ReplayBackend(log)
    assert [replay.decide(request) for request in requests] == answers
    with pytest.raises(StopIteration):
        replay.decide(envelope())


def test_log_and_backend_get_separate_immutable_snapshots():
    class MutatingBackend:
        name = "synthetic"
        model = "synthetic"

        def decide(self, request):
            request["state"]["attempt_count"] = 99
            return {"D2": "c8", "D4": "discard", "D5": "strong"}

    log = io.StringIO()
    request = envelope()
    answer = Decider(MutatingBackend(), log).decide(request)
    assert request == envelope()
    request["state"]["attempt_count"] = 88
    answer["D2"] = "c3"
    assert records(log)[0]["envelope"] == envelope()
    assert records(log)[0]["answer"]["D2"] == "c8"


@dataclass(frozen=True)
class PrivateResults:
    adjudication: float
    holdout: float


def test_private_outcomes_cannot_change_outbound_bytes_or_later_decisions(monkeypatch):
    outbound = []

    def open_request(self, request, timeout):
        outbound.append(request.data)
        attempt = json.loads(request.data)["state"]["attempt_count"]
        if attempt == 2:
            raise TimeoutError(CANARY)
        answers = {"D2": {"choice": "c8"}, "D4": {"choice": "add"}, "D5": {"choice": "cheap"}}
        return io.BytesIO(json.dumps({"answers": answers}).encode())

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", open_request)

    def run(public, private):
        # The caller holds private results separately; the port has no private input.
        assert isinstance(private, PrivateResults)
        log = io.StringIO()
        decider = Decider(JevBackend(URL), log)
        builder = EnvelopeBuilder(("c3", "c8"), ("e17",))
        decisions = [decider.decide(builder.build(
            DevPublicView({**public.state, "attempt_count": attempt}, traces=public.traces,
                          candidate_text=public.candidate_text,
                          component_descriptions=public.component_descriptions),
            decisions=("D2", "D4", "D5"),
        )) for attempt in range(1, 4)]
        return decisions, log.getvalue()

    public = DevPublicView({"budget_used": 0.5}, traces=CANARY, candidate_text=CANARY)
    first = run(public, PrivateResults(adjudication=1.0, holdout=0.0))
    first_requests = list(outbound)
    outbound.clear()
    second = run(public, PrivateResults(adjudication=-1.0, holdout=1.0))
    assert first_requests == outbound
    assert first == second
    assert CANARY not in first[1]


def test_restarted_decider_appends_in_order():
    log = io.StringIO()
    Decider(DeterministicBackend(), log).decide(envelope())
    Decider(DeterministicBackend(), log).decide(envelope(2))
    assert [record["seq"] for record in records(log)] == [1, 2]


def test_unknown_envelope_is_not_sent_or_logged():
    log = io.StringIO()
    request = envelope()
    request["state"]["trace_text"] = CANARY
    with pytest.raises(ValueError):
        Decider(JevBackend(URL), log).decide(request)
    assert log.getvalue() == ""


def test_replay_rejects_changed_request_without_consuming_record():
    log = io.StringIO()
    Decider(DeterministicBackend(), log).decide(envelope())
    replay = ReplayBackend(log)
    with pytest.raises(ValueError):
        replay.decide(envelope(2))
    assert replay.decide(envelope()) == {"D2": "c3", "D4": "discard", "D5": "strong"}


@pytest.mark.parametrize("damage", ["sequence", "answer", "json", "envelope"])
def test_replay_rejects_corrupted_records(damage):
    log = io.StringIO()
    Decider(DeterministicBackend(), log).decide(envelope())
    record = records(log)[0]
    if damage == "sequence":
        record["seq"] = 2
    elif damage == "answer":
        record["answer"]["D2"] = CANARY
    elif damage == "envelope":
        record["envelope"]["state"]["trace_text"] = CANARY
    corrupted = io.StringIO(CANARY if damage == "json" else json.dumps(record) + "\n")
    with pytest.raises(ValueError) as error:
        ReplayBackend(corrupted)
    assert CANARY not in str(error.value)


class ScriptedBackend:
    """Synthetic primary: times out on the listed calls, otherwise answers c8."""

    name = "synthetic"
    model = "synthetic"

    def __init__(self, timeouts):
        self.timeouts, self.calls = set(timeouts), 0

    def decide(self, request):
        self.calls += 1
        if self.calls in self.timeouts:
            raise TimeoutError("synthetic timeout")
        return {"D2": "c8", "D4": "add", "D5": "cheap"}


def test_every_record_carries_valid_baseline_answer():
    log = io.StringIO()
    decider = Decider(ScriptedBackend(timeouts={2}), log)
    for attempt in range(1, 4):
        decider.decide(envelope(attempt))
    logged = records(log)
    assert ["fallback_reason" in record for record in logged] == [False, True, False]
    # Shadow baseline is its own round-robin, advanced on every call.
    assert [record["baseline_answer"]["D2"] for record in logged] == ["c3", "c8", "c3"]
    assert all(record["baseline_answer"]["D4"] == "discard" for record in logged)
    assert logged[0]["answer"] == {"D2": "c8", "D4": "add", "D5": "cheap"}


def test_shadow_recording_does_not_change_fallback_round_robin():
    timeouts = {1, 2, 4, 5, 6}
    log = io.StringIO()
    decider = Decider(ScriptedBackend(timeouts), log)
    answers = [decider.decide(envelope(attempt)) for attempt in range(1, 8)]
    # Old behaviour: the fallback alone is consulted, only on failed calls.
    reference = DeterministicBackend()
    expected = [reference.decide(envelope(attempt)) if attempt in timeouts
                else {"D2": "c8", "D4": "add", "D5": "cheap"} for attempt in range(1, 8)]
    assert answers == expected
    assert [a["D2"] for i, a in enumerate(answers, 1) if i in timeouts] == [
        "c3", "c8", "c3", "c8", "c3"]


def test_replay_returns_answer_never_baseline_answer():
    log = io.StringIO()
    Decider(ScriptedBackend(timeouts=()), log).decide(envelope())
    record = records(log)[0]
    assert record["answer"] != record["baseline_answer"]
    assert ReplayBackend(log).decide(envelope()) == record["answer"]


@pytest.mark.parametrize("damage", ["missing", "off-list", "wrong-keys"])
def test_replay_rejects_missing_or_invalid_baseline_answer(damage):
    log = io.StringIO()
    Decider(DeterministicBackend(), log).decide(envelope())
    record = records(log)[0]
    if damage == "missing":
        del record["baseline_answer"]
    elif damage == "off-list":
        record["baseline_answer"]["D2"] = CANARY
    else:
        del record["baseline_answer"]["D4"]
    with pytest.raises(ValueError) as error:
        ReplayBackend(io.StringIO(json.dumps(record) + "\n"))
    assert CANARY not in str(error.value)


def test_resumed_decider_continues_shadow_round_robin():
    def request(attempt):
        decisions = ("D4", "D5") if attempt % 2 == 0 else ("D2", "D4", "D5")
        return EnvelopeBuilder(("c3", "c8"), ("e17",)).build(
            DevPublicView({"attempt_count": attempt, "budget_used": 0.5}), decisions=decisions)

    requests = [request(attempt) for attempt in range(1, 7)]
    whole = io.StringIO()
    decider = Decider(DeterministicBackend(), whole)
    for item in requests:
        decider.decide(item)
    resumed = io.StringIO()
    for start, stop in ((0, 1), (1, 4), (4, 6)):
        decider = Decider(DeterministicBackend(), resumed)
        for item in requests[start:stop]:
            decider.decide(item)
    shadow = [record["baseline_answer"] for record in records(whole)]
    assert [record["baseline_answer"] for record in records(resumed)] == shadow
    assert [answer.get("D2") for answer in shadow] == ["c3", None, "c8", None, "c3", None]
