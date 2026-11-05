#!/bin/sh
# Entirely synthetic official-wrapper-shaped fixture; no public GDPevo material.
set -eu
exec python3 - "$1" <<'PY'
import json
import os
import sys

assert os.path.isabs(sys.argv[1])
assert os.environ.get("TASK_ENV_ENABLE_JUDGE") == "0"
with open(sys.argv[1], encoding="utf-8") as stream:
    prediction = json.load(stream)
print(json.dumps({
    "earned_points": int(prediction.get("answer") == "toy-ok"),
    "total_points": 1,
    "details": {"expected": "SYNTHETIC_GOLD_MUST_NOT_ENTER_REFLECTION"},
}))
PY
