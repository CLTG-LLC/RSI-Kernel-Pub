"""Decision backends behind the SystemOne contract."""

import http.client
import json
import os
import urllib.error
import urllib.request
from typing import Protocol

from .envelope import validate_envelope


class DecisionError(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


def validate_answers(envelope, answers):
    if (type(answers) is not dict or set(answers) != set(envelope["questions"])
            or any(type(choice) is not str for choice in answers.values())):
        raise DecisionError("malformed")
    if any(choice not in envelope["questions"][name]["criteria"]
           for name, choice in answers.items()):
        raise DecisionError("off-list")
    return dict(answers)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    # Same credential-preserving no-redirect behavior as the existing jev_decide.
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class JevBackend:
    name = "jev"

    def __init__(self, url, model="jev-latest", timeout=120):
        # 120 seconds is the existing jev_decide default, not a tuned limit.
        self.url, self.model, self.timeout = url, model, timeout
        self.last_usage = None  # provider-reported usage of the last call, None if absent

    def decide(self, envelope):
        self.last_usage = None
        validate_envelope(envelope)
        key = os.environ.get("EXPERIENTIAL_API_KEY")
        if not key:
            raise DecisionError("malformed")
        request = urllib.request.Request(
            self.url, data=json.dumps({"model": self.model, **envelope},
                                      allow_nan=False, separators=(",", ":")).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key},
        )
        del key
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        try:
            with opener.open(request, timeout=self.timeout) as stream:
                response = json.loads(stream.read())
            usage = response.get("usage")
            self.last_usage = usage if isinstance(usage, dict) else None
            answers = {name: answer["choice"] for name, answer in response["answers"].items()}
        except TimeoutError:
            raise DecisionError("timeout") from None
        except urllib.error.URLError as error:
            reason = "timeout" if isinstance(error.reason, TimeoutError) else "malformed"
            raise DecisionError(reason) from None
        except (ValueError, KeyError, TypeError, AttributeError, OSError,
                http.client.HTTPException, RecursionError):
            raise DecisionError("malformed") from None
        return validate_answers(envelope, answers)


class Backend(Protocol):
    def decide(self, envelope: dict) -> dict[str, str]: ...


class DeterministicBackend:
    name = "deterministic"
    model = "deterministic"

    def __init__(self):
        self._turn = 0

    def decide(self, envelope):
        validate_envelope(envelope)
        answers = {}
        for name, question in envelope["questions"].items():
            choices = question["criteria"]
            if name == "D2":
                components = [choice for choice in choices if choice != "none"]
                answers[name] = components[self._turn % len(components)] if components else "none"
                self._turn += 1
            else:
                answers[name] = "discard" if name == "D4" else "strong"
            if answers[name] not in choices:
                raise ValueError("deterministic default not among asked choices")
        return answers
