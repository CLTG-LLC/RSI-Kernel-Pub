"""SystemOne HTTP contract, with the entire HTTP layer mocked."""

import io
import json
import urllib.error
import urllib.request

import pytest

from rsi_kernel.decision.backends import DecisionError, JevBackend
from rsi_kernel.decision.envelope import DevPublicView, EnvelopeBuilder


URL = "https://api.experientiallabs.ai/v1/systemone"
CANARY = "RSI_CANARY_4f162_private_candidate"


def envelope():
    return EnvelopeBuilder(("c3",), ("e17",)).build(
        DevPublicView({"attempt_count": 1}, traces=CANARY, candidate_text=CANARY,
                      component_descriptions={"c3": CANARY}),
        decisions=("D2", "D4", "D5"),
    )


def mock_http(monkeypatch, payload, captured):
    def open_request(self, request, timeout):
        captured.append((request, timeout))
        if isinstance(payload, Exception):
            raise payload
        return io.BytesIO(payload)

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", open_request)


def response(answers):
    return json.dumps({"answers": answers}).encode()


def test_jev_posts_native_contract_and_reads_environment_at_call_time(monkeypatch):
    backend = JevBackend(URL, timeout=120)
    monkeypatch.setenv("EXPERIENTIAL_API_KEY", "synthetic-key-set-after-construction")
    captured = []
    mock_http(monkeypatch, response({"D2": {"choice": "c3"}, "D4": {"choice": "discard"},
                                    "D5": {"choice": "cheap"}}), captured)
    assert backend.decide(envelope()) == {"D2": "c3", "D4": "discard", "D5": "cheap"}
    request, timeout = captured[0]
    assert request.full_url == URL
    assert request.get_method() == "POST"
    assert timeout == 120
    assert request.get_header("Authorization") == "Bearer synthetic-key-set-after-construction"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(request.data) == {"model": "jev-latest", **envelope()}
    assert CANARY not in request.data.decode()
    assert "synthetic-key" not in request.data.decode()
    assert "synthetic-key" not in repr(backend)


@pytest.mark.parametrize("payload, reason", [
    (response({"D2": {"choice": CANARY}, "D4": {"choice": "discard"},
               "D5": {"choice": "strong"}}), "off-list"),
    (response({"D2": {"choice": "c3"}}), "malformed"),
    (response({"D2": {"choice": "c3"}, "D4": {"choice": "discard"},
               "D5": {"choice": "strong"}, "accept": {"choice": "yes"}}), "malformed"),
    (response({"D2": "c3", "D4": {"choice": "discard"}, "D5": {"choice": "strong"}}), "malformed"),
    (response({"D2": {"choice": []}, "D4": {"choice": "discard"},
               "D5": {"choice": "strong"}}), "malformed"),
    (CANARY.encode(), "malformed"),
    (b"[]", "malformed"),
    (b'{"answers": null}', "malformed"),
    (TimeoutError(CANARY), "timeout"),
    (urllib.error.URLError(TimeoutError(CANARY)), "timeout"),
    (urllib.error.HTTPError(URL, 500, CANARY, {}, None), "malformed"),
])
def test_jev_rejects_bad_answers_with_closed_failure_codes(monkeypatch, payload, reason):
    captured = []
    mock_http(monkeypatch, payload, captured)
    with pytest.raises(DecisionError) as error:
        JevBackend(URL).decide(envelope())
    assert error.value.reason == reason
    assert CANARY not in str(error.value)
    assert CANARY not in captured[0][0].data.decode()


def test_missing_key_fails_before_http(monkeypatch):
    monkeypatch.delenv("EXPERIENTIAL_API_KEY")
    with pytest.raises(DecisionError) as error:
        JevBackend(URL).decide(envelope())
    assert error.value.reason == "malformed"


@pytest.mark.parametrize("part", ["state", "instructions", "criteria", "top"])
def test_edited_envelope_is_rejected_before_http_and_without_echo(part):
    request = envelope()
    if part == "state":
        request["state"]["trace_text"] = CANARY
    elif part == "instructions":
        request["questions"]["D2"]["instructions"] = CANARY
    elif part == "criteria":
        request["questions"]["D2"]["criteria"]["c3"] = CANARY
    else:
        request["candidate_text"] = CANARY
    with pytest.raises(ValueError) as error:
        JevBackend(URL).decide(request)
    assert CANARY not in str(error.value)
