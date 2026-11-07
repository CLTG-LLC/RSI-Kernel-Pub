#!/usr/bin/env bash
# Exercise the real smoke driver without a Docker daemon or the real harness.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DRIVER="$ROOT/tools/fd2/gold_smoke.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
REAL_PYTHON="$(command -v python3)"
export REAL_PYTHON

mkdir -p "$TMP/bin" "$TMP/harness" "$TMP/output"
cat > "$TMP/frozen.jsonl" <<'EOF'
{"instance_id":"demo-1","split":"python","docker_image":"registry.invalid/demo:tag"}
EOF
cat > "$TMP/selection.json" <<'EOF'
{"instances":[{"instance_id":"demo-1","split":"python","docker_image":"registry.invalid/demo:tag"},{"instance_id":"demo-2","split":"python","docker_image":"registry.invalid/demo:tag"}]}
EOF
cat > "$TMP/bin/docker" <<'STUB'
#!/usr/bin/env bash
set -u
printf 'docker %s\n' "$*" >> "$ORDER"
if [ "${1:-}" = "--context" ]; then shift 2; fi
case "${1:-}" in
  version) printf 'linux/arm64\n' ;;
  context) printf 'unix:///nonexistent-test-docker.sock\n' ;;
  pull) ;;
  image)
    case "$2 ${5:-}" in
      "inspect {{index .RepoDigests 0}}") printf 'registry.invalid/demo@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n' ;;
      "inspect {{.Size}}") printf '123\n' ;;
      "inspect {{.Id}}") printf 'sha256:image-id\n' ;;
      "rm ") [ "${FAIL_REMOVE:-0}" != 1 ] ;;
      "inspect sha256:image-id") exit 1 ;;
      *) exit 1 ;;
    esac
    ;;
  ps) : ;;
  *) printf 'Unexpected docker call: %s\n' "$*" >&2; exit 1 ;;
esac
STUB
cat > "$TMP/bin/python" <<'STUB'
#!/usr/bin/env bash
if [ "${1:-}" = -m ] && [ "${2:-}" = evaluation.evaluation ]; then
  shift 2
  output=
  instance_id=
  while [ "$#" -gt 0 ]; do
    if [ "$1" = --output_dir ]; then output="$2"; shift 2
    elif [ "$1" = --instance_ids ]; then instance_id="$2"; shift 2
    else shift; fi
  done
  printf 'harness run %s\n' "$instance_id" >> "$ORDER"
  mkdir -p "$output/$instance_id"
  printf 'DOCKER_HOST=%s\n' "${DOCKER_HOST:-}" > "$output/docker-host.txt"
  printf '{"resolved":true}\n' > "$output/$instance_id/report.json"
  exit "${FAIL_HARNESS:-0}"
fi
printf 'python %s\n' "$*" >> "$ORDER"
if [ "${FAIL_ROW_WRITE:-0}" = 1 ] && [ "$#" -eq 12 ] && [ "${3:-}" = demo-2 ]; then exit 9; fi
if [ "${FAIL_DISK_MEASURE:-0}" = 1 ] && [ "${1:-}" = -c ]; then exit 9; fi
if [ "${FAIL_SUMMARY_WRITE:-0}" = 1 ] && [ "$#" -eq 5 ] && [ -n "$ORDER" ]; then
  case "$ORDER" in *summary-failure*) exit 9 ;; esac
fi
exec "$REAL_PYTHON" "$@"
STUB
chmod +x "$TMP/bin/docker" "$TMP/bin/python"
ln -s "$TMP/bin/python" "$TMP/bin/python3"

run_smoke() {
  local name="$1"
  shift
  mkdir -p "$TMP/$name"
  : > "$TMP/$name/order"
  if ORDER="$TMP/$name/order" PATH="$TMP/bin:$PATH" DOCKER_CONTEXT=smoke-test \
      "$@" "$DRIVER" --harness-dir "$TMP/harness" --frozen-jsonl "$TMP/frozen.jsonl" \
      --selection "$TMP/selection.json" --output-dir "$TMP/$name/output" \
      > "$TMP/$name/stdout" 2> "$TMP/$name/stderr"; then
    return 0
  else
    return $?
  fi
}

assert_order() {
  local expected='pull
pin
harness run
harness run
harness run
remove
verify
pull
pin
harness run
harness run
harness run
remove
verify'
  local actual
  # One sequential pass: separate greps would hide reordering.
  actual="$(sed -n \
    -e 's/^docker .* pull .*/pull/p' \
    -e 's/^python .*prepare_frozen.py --pin-image .*/pin/p' \
    -e 's/^harness run.*/harness run/p' \
    -e 's/^docker .* image rm .*/remove/p' \
    -e 's/^docker .* image inspect sha256:image-id.*/verify/p' "$1")"
  [ "$actual" = "$expected" ] || { printf 'Bad operation order:\n%s\n' "$actual" >&2; return 1; }
}

run_smoke success
assert_order "$TMP/success/order"
# The pin-after-runs mutation must fail the same ordering assertion.
{ grep '^docker ' "$TMP/success/order"
  grep '^harness run' "$TMP/success/order"
  grep 'prepare_frozen.py --pin-image' "$TMP/success/order"
} > "$TMP/reordered.log"
if assert_order "$TMP/reordered.log" 2>/dev/null; then
  printf 'Pin-after-runs mutation unexpectedly passed\n' >&2
  exit 1
fi
printf 'Pin-after-runs mutation rejected as expected\n'
[ "$(find "$TMP/success/output" -name report.json | wc -l | tr -d ' ')" = 6 ]
"$REAL_PYTHON" - "$TMP/success/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
assert summary["docker_platform"] == "linux/arm64"
assert summary["docker_context"] == "smoke-test"
assert len(summary["instances"]) == 2
assert [run["resolved"] for run in summary["instances"][0]["runs"]] == [True] * 3
PY
[ "$(cat "$TMP/success/output/python/run-1/docker-host.txt")" = \
  'DOCKER_HOST=unix:///nonexistent-test-docker.sock' ]

# A failing harness still records all three outcomes and writes the summary.
if ! FAIL_HARNESS=1 run_smoke harness-failure env FAIL_HARNESS=1; then
  printf 'Harness failure unexpectedly stopped the driver\n' >&2
  exit 1
fi
assert_order "$TMP/harness-failure/order"
"$REAL_PYTHON" - "$TMP/harness-failure/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
runs = summary["instances"][0]["runs"]
assert len(runs) == 3
assert [run["command_status"] for run in runs] == [1, 1, 1]
PY

# Exact-image removal failure is a STOP, but the partial summary remains available.
if FAIL_REMOVE=1 run_smoke removal-failure env FAIL_REMOVE=1; then
  printf 'Removal failure did not stop the driver\n' >&2
  exit 1
fi
grep -q 'Exact instance cleanup failed; stopping: demo-1' "$TMP/removal-failure/stdout"
test -f "$TMP/removal-failure/output/summary.json"

# Use the workflow's literal relative arguments and the host's real disk/python.
mkdir -p "$TMP/workflow/SWE-bench-Live" "$TMP/workflow/smoke"
cp "$TMP/frozen.jsonl" "$TMP/workflow/smoke/frozen.jsonl"
cp "$TMP/selection.json" "$TMP/workflow/smoke/selection.json"
: > "$TMP/workflow/order"
if ! (cd "$TMP/workflow" && ORDER="$TMP/workflow/order" PATH="$TMP/bin:$PATH" \
    "$DRIVER" --harness-dir SWE-bench-Live --frozen-jsonl smoke/frozen.jsonl \
    --selection smoke/selection.json --output-dir smoke/output \
    > stdout 2> stderr); then
  printf 'Workflow relative-path invocation failed\n' >&2
  exit 1
fi
"$REAL_PYTHON" - "$TMP/workflow/smoke/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
assert len(summary["instances"]) == 2
assert sum(len(item["runs"]) for item in summary["instances"]) == 6
assert all(run["disk_free_bytes_before"] > 0 for item in summary["instances"] for run in item["runs"])
assert all(run["disk_free_bytes_after"] > 0 for item in summary["instances"] for run in item["runs"])
PY
# An actually unwritable summary destination must be fatal.
mkdir -p "$TMP/unwritable/output/summary.json"
if ORDER="$TMP/unwritable-order" PATH="$TMP/bin:$PATH" \
    "$DRIVER" --harness-dir "$TMP/harness" --frozen-jsonl "$TMP/frozen.jsonl" \
    --selection "$TMP/selection.json" --output-dir "$TMP/unwritable/output" \
    > "$TMP/unwritable/stdout" 2> "$TMP/unwritable/stderr"; then
  printf 'Unwritable summary destination did not stop\n' >&2
  exit 1
fi
grep -q 'Summary write failed; stopping' "$TMP/unwritable/stderr"

# A measurement failure stops before the harness and still writes the summary.
if ! run_smoke disk-failure env PATH="$TMP/bin:$PATH" FAIL_DISK_MEASURE=1; then
  grep -q 'Disk measurement failed; stopping' "$TMP/disk-failure/stderr"
else
  printf 'Disk measurement failure did not stop\n' >&2
  exit 1
fi
! grep -q '^harness run' "$TMP/disk-failure/order"
test -f "$TMP/disk-failure/output/summary.json"

# A row-write failure stops before the second instance and preserves the first.
if ! run_smoke row-failure env FAIL_ROW_WRITE=1; then
  grep -q 'Run record write failed; stopping' "$TMP/row-failure/stderr"
else
  printf 'Row write failure did not stop\n' >&2
  exit 1
fi
! grep -q '^harness run demo-2' "$TMP/row-failure/order"
"$REAL_PYTHON" - "$TMP/row-failure/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
assert [item["instance_id"] for item in summary["instances"]] == ["demo-1"]
assert len(summary["instances"][0]["runs"]) == 3
PY

# A summary writer failure must be fatal rather than silently discarded.
if ! run_smoke summary-failure env FAIL_SUMMARY_WRITE=1; then
  grep -q 'Summary write failed; stopping' "$TMP/summary-failure/stderr"
else
  printf 'Summary writer failure did not stop\n' >&2
  exit 1
fi

printf 'FD2 gold smoke fake-docker tests PASS\n'
