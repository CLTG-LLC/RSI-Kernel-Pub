"""Upstream judge normalization, ported without changed precedence.

Source: Prism-Shadow/GDPevo@5082a777379156a048881e94940d640702e5e09a,
data/task_groups/task_group_001/env/judge_api.py:30–62 (lead-supplied excerpt).
https://github.com/Prism-Shadow/GDPevo/blob/5082a777379156a048881e94940d640702e5e09a/data/task_groups/task_group_001/env/judge_api.py#L30-L62
"""


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def score_from_evaluator(payload):
    if not isinstance(payload, dict):
        return None
    for key in ("normalized_score", "total_score"):
        value = _number(payload.get(key))
        if value is not None and 0.0 <= value <= 1.0:
            return value
    for earned_key, total_key in (
        ("earned_score", "max_score"), ("earned_weight", "total_weight"),
        ("earned_points", "total_points"), ("earned", "total"),
        ("raw_score", "raw_total"), ("score", "max_score"),
    ):
        earned = _number(payload.get(earned_key)); total = _number(payload.get(total_key))
        if earned is not None and total is not None and total > 0:
            return max(0.0, min(1.0, earned / total))
    value = _number(payload.get("score"))
    if value is not None and 0.0 <= value <= 1.0:
        return value
    return None
