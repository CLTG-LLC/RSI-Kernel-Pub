"""Ordered JSONL decisions and recorded-prediction replay (design.md section 3).

Logs are caller-owned seekable text streams, opened in a+ for persistence.
Every record carries a shadow ``baseline_answer`` from a Decider-owned
DeterministicBackend, separate from the fallback so its D2 round-robin is untouched.
Records without ``baseline_answer`` are rejected (no log predates the field).
# ponytail: one writer per campaign log; add locking only for concurrent writers.
"""

import json

from .backends import DecisionError, DeterministicBackend, validate_answers
from .envelope import validate_envelope


FALLBACK_REASONS = ("timeout", "malformed", "off-list")


def _json(value):
    return json.dumps(value, allow_nan=False, separators=(",", ":"))


def _snapshot(value):
    return json.loads(_json(value))


def _read_records(log):
    log.seek(0)
    records = []
    try:
        for seq, line in enumerate(log, start=1):
            record = json.loads(line)
            if type(record) is not dict or record["seq"] != seq:
                raise ValueError
            validate_envelope(record["envelope"])
            validate_answers(record["envelope"], record["answer"])
            validate_answers(record["envelope"], record["baseline_answer"])
            if (type(record["backend"]) is not str or type(record["model"]) is not str
                    or ("fallback_reason" in record
                        and record["fallback_reason"] not in FALLBACK_REASONS)):
                raise ValueError
            records.append(record)
    except (ValueError, TypeError, KeyError):
        raise ValueError("invalid decision log") from None
    return records


class Decider:
    """Snapshot every call and record the decision actually used, including fallback."""

    def __init__(self, primary, log, fallback=None):
        self.primary = primary
        self.fallback = fallback if fallback is not None else DeterministicBackend()
        self.baseline = DeterministicBackend()
        self.log = log
        history = _read_records(log)
        for record in history:
            # Replay history so a resumed shadow continues its D2 round-robin.
            self.baseline.decide(record["envelope"])
        self._seq = len(history)

    def decide(self, envelope):
        validate_envelope(envelope)
        snapshot = _snapshot(envelope)
        record = {"seq": self._seq + 1, "backend": self.primary.name,
                  "model": self.primary.model, "envelope": snapshot}
        try:
            answers = validate_answers(snapshot, self.primary.decide(_snapshot(snapshot)))
        except (DecisionError, TimeoutError, ValueError) as error:
            reason = error.reason if isinstance(error, DecisionError) else (
                "timeout" if isinstance(error, TimeoutError) else "malformed")
            if reason not in FALLBACK_REASONS:
                reason = "malformed"
            answers = validate_answers(snapshot, self.fallback.decide(_snapshot(snapshot)))
            record = {**record, "fallback_reason": reason,
                      "fallback_backend": self.fallback.name, "fallback_model": self.fallback.model}
        baseline = validate_answers(snapshot, self.baseline.decide(_snapshot(snapshot)))
        record = {**record, "answer": answers, "baseline_answer": baseline}
        self.log.seek(0, 2)
        self.log.write(_json(record) + "\n")
        self.log.flush()
        self._seq += 1
        return dict(answers)


class ReplayBackend:
    """No backend reference: recorded decisions are the only source of answers."""

    name = "replay"
    model = "recorded"

    def __init__(self, log):
        self._records = _read_records(log)
        self._position = 0

    def decide(self, envelope):
        validate_envelope(envelope)
        if self._position == len(self._records):
            raise StopIteration("decision log exhausted")
        record = self._records[self._position]
        if _json(record["envelope"]) != _json(envelope):
            raise ValueError("request differs from recorded envelope")
        self._position += 1
        return dict(record["answer"])
