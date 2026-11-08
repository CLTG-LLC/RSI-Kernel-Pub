#!/usr/bin/env bash
# Exercise the real smoke driver without a Docker daemon or the real harness.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
DRIVER="$ROOT/tools/fd2/gold_smoke.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
REAL_PYTHON="$(command -v python3)"
export REAL_PYTHON
# Run the driver with the interpreter running this test unless BASH_BIN says
# otherwise, so macOS /bin/bash 3.2 and a newer bash are both exercised.
BASH_BIN="${BASH_BIN:-$BASH}"

mkdir -p "$TMP/bin" "$TMP/harness" "$TMP/output"
cat > "$TMP/frozen.jsonl" <<'EOF'
{"instance_id":"demo-1","split":"python","docker_image":"registry.invalid/demo:tag"}
EOF
cat > "$TMP/selection.json" <<'EOF'
{"instances":[{"instance_id":"demo-1","split":"python","docker_image":"registry.invalid/demo:tag"},{"instance_id":"demo-2","split":"python","docker_image":"registry.invalid/demo:tag2"}]}
EOF
cat > "$TMP/bin/docker" <<'STUB'
#!/usr/bin/env bash
set -u
printf 'docker %s\n' "$*" >> "$ORDER"
if [ "${1:-}" = "--context" ]; then shift 2; fi
case "${1:-}" in
  version) printf 'linux/arm64\n' ;;
  info) printf '%s\n' "${FAKE_DOCKER_ROOT:-/}" ;;
  system) [ "${FAIL_DOCKER_DF:-0}" != 1 ] || exit 9; printf '{"Type":"Images","TotalCount":"1","Size":"1B"}\n' ;;
  context) printf 'unix:///nonexistent-test-docker.sock\n' ;;
  pull)
    if [ "${WATCH_ABORT_PULL:-0}" = 1 ] && [[ "${*: -1}" = *:tag ]]; then
      if [ -n "${DISK_PHASE_FILE:-}" ]; then touch "$DISK_PHASE_FILE/low"; fi
      sleep 10
    fi
    # Only a completed pull registers the image; a killed pull leaves none.
    : > "$ORDER.image"
    ;;
  image)
    if [ "$2" = rm ]; then ref="${4:-}"; else ref="${3:-}"; fi
    if [ "$2" = inspect ] && [ "${FAIL_INSPECT:-0}" = 1 ]; then
      printf 'Cannot connect to the Docker daemon\n' >&2; exit 1
    fi
    if [ ! -e "$ORDER.image" ]; then
      printf 'Error response from daemon: No such image: %s\n' "$ref" >&2; exit 1
    fi
    case "$2 ${5:-}" in
      "inspect {{index .RepoDigests 0}}") printf '%s@sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef\n' "${3%%@*}" ;;
      "inspect {{.Size}}") printf '123\n' ;;
      "inspect {{.Id}}") printf 'sha256:image-id\n' ;;
      "rm ")
        [ "${FAIL_REMOVE:-0}" != 1 ] || { printf 'Error response from daemon: conflict\n' >&2; exit 1; }
        # A forced removal by ID or tag deletes the image and all its tags.
        rm -f "$ORDER.image"
        ;;
      *) exit 1 ;;
    esac
    ;;
  ps)
    # Instance cleanup starts here; RECOVER_DISK models it freeing the disk.
    if [ "${RECOVER_DISK:-0}" = 1 ] && [ -n "${DISK_PHASE_FILE:-}" ]; then rm -f "$DISK_PHASE_FILE/low"; fi
    # A persistent container survives the killed harness until removed.
    if [ -n "${FAKE_CONTAINER:-}" ] && [[ "$*" = *'name=^git-launch-demo-1-'* ]]; then
      printf '%s\n' "$FAKE_CONTAINER"
    fi
    ;;
  rm) [ "${2:-}" = -f ] || exit 1 ;;
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
  if [ "${WATCH_ABORT_HARNESS:-0}" = 1 ] && [ "$instance_id" = demo-1 ]; then
    if [ -n "${DISK_PHASE_FILE:-}" ]; then touch "$DISK_PHASE_FILE/low"; fi
    sleep 10
  fi
  if [ "${WATCH_MEASURE_FAIL_HARNESS:-0}" = 1 ] && [ "$instance_id" = demo-1 ]; then
    touch "$DISK_PHASE_FILE/measure-fail"
    sleep 10
  fi
  mkdir -p "$output/$instance_id"
  printf 'DOCKER_HOST=%s\n' "${DOCKER_HOST:-}" > "$output/docker-host.txt"
  printf '{"resolved":true}\n' > "$output/$instance_id/report.json"
  exit "${FAIL_HARNESS:-0}"
fi
printf 'python %s\n' "$*" >> "$ORDER"
if [ "${FAIL_ROW_WRITE:-0}" = 1 ] && [ "$#" -eq 13 ] && [ "${3:-}" = demo-2 ]; then exit 9; fi
if [ "${FAIL_DISK_MEASURE:-0}" = 1 ] && [ "${1:-}" = -c ]; then exit 9; fi
# One transient measurement failure, consumed by the first / measurement.
if [ -n "${DISK_PHASE_FILE:-}" ] && [ -e "$DISK_PHASE_FILE/measure-fail" ] &&
    [ "${1:-}" = -c ] && [[ "${2:-}" = *'shutil.disk_usage("/")'* ]]; then
  rm -f "$DISK_PHASE_FILE/measure-fail"
  exit 9
fi
if [ "${1:-}" = -c ] && [[ "${2:-}" = *'shutil.disk_usage(sys.argv[1])'* ]]; then
  printf '%s\n' "${MOCK_DOCKER_FREE:-1000000000}"
  exit 0
fi
if [ "${1:-}" = -c ] && [[ "${2:-}" = *'shutil.disk_usage("/")'* ]]; then
  if [ -n "${DISK_PHASE_FILE:-}" ] && [ -e "$DISK_PHASE_FILE/low" ]; then
    printf '100\n'
  else
    printf '%s\n' "${MOCK_ROOT_FREE:-1000000000}"
  fi
  exit 0
fi
if [ "${FAIL_SUMMARY_WRITE:-0}" = 1 ] && [ "$#" -eq 6 ] && [ -n "$ORDER" ]; then
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
  if ORDER="$TMP/$name/order" PATH="$TMP/bin:$PATH" DOCKER_CONTEXT=smoke-test LOW_DISK_BYTES=0 WATCHDOG_INTERVAL=0.01 \
      "$@" "$BASH_BIN" "$DRIVER" --harness-dir "$TMP/harness" --frozen-jsonl "$TMP/frozen.jsonl" \
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
inspect
remove
inspect
pull
pin
harness run
harness run
harness run
inspect
remove
inspect'
  local actual
  # One sequential pass: separate greps would hide reordering.
  actual="$(sed -n \
    -e 's/^docker .* pull .*/pull/p' \
    -e 's/^python .*prepare_frozen.py --pin-image .*/pin/p' \
    -e 's/^harness run.*/harness run/p' \
    -e 's/^docker .* image rm .*/remove/p' \
    -e 's/^docker .* image inspect sha256:image-id.*/inspect/p' "$1")"
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
assert summary["stop_reason"] is None
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
mkdir -p "$TMP/workflow/SWE-bench-Live" "$TMP/workflow/smoke" "$TMP/workflow/docker-root"
cp "$TMP/frozen.jsonl" "$TMP/workflow/smoke/frozen.jsonl"
cp "$TMP/selection.json" "$TMP/workflow/smoke/selection.json"
"$REAL_PYTHON" - "$TMP/workflow/smoke/frozen.jsonl" "$TMP/workflow/smoke/selection.json" <<'PY'
import json
import sys
with open(sys.argv[1], "a", encoding="utf-8") as stream:
    stream.write(json.dumps({"instance_id": "demo-2", "split": "python",
                             "docker_image": "registry.invalid/demo:tag2"}) + "\n")
with open(sys.argv[2], encoding="utf-8") as stream:
    selection = json.load(stream)
selection["instances"][1]["docker_image"] = "registry.invalid/demo:tag2"
with open(sys.argv[2], "w", encoding="utf-8") as stream:
    json.dump(selection, stream)
PY
: > "$TMP/workflow/order"
if ! (cd "$TMP/workflow" && ORDER="$TMP/workflow/order" PATH="$TMP/bin:$PATH" LOW_DISK_BYTES=0 WATCHDOG_INTERVAL=0.01 \
    FAKE_DOCKER_ROOT="$TMP/workflow/docker-root" \
    "$BASH_BIN" "$DRIVER" --harness-dir SWE-bench-Live --frozen-jsonl smoke/frozen.jsonl \
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
assert summary["stop_reason"] is None
assert len(summary["instances"]) == 2
assert sum(len(item["runs"]) for item in summary["instances"]) == 6
assert all(run["disk_free_bytes_before"] > 0 for item in summary["instances"] for run in item["runs"])
assert all(run["disk_free_bytes_after"] > 0 for item in summary["instances"] for run in item["runs"])
PY
# An actually unwritable summary destination must be fatal.
mkdir -p "$TMP/unwritable/output/summary.json"
if ORDER="$TMP/unwritable-order" PATH="$TMP/bin:$PATH" \
    "$BASH_BIN" "$DRIVER" --harness-dir "$TMP/harness" --frozen-jsonl "$TMP/frozen.jsonl" \
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
if grep -q '^harness run' "$TMP/disk-failure/order"; then printf 'Unexpected match %s in %s\n' '^harness run' "$TMP/disk-failure/order" >&2; exit 1; fi
test -f "$TMP/disk-failure/output/summary.json"

# A row-write failure stops before the second instance and preserves the first.
if ! run_smoke row-failure env FAIL_ROW_WRITE=1; then
  grep -q 'Run record write failed; stopping' "$TMP/row-failure/stderr"
else
  printf 'Row write failure did not stop\n' >&2
  exit 1
fi
# The injected failure is demo-2's first row write, which follows its first harness
# run: exactly one demo-2 run, then STOP (no second or third run).
[ "$(grep -c '^harness run demo-2' "$TMP/row-failure/order")" = 1 ] || { printf 'Row-write failure did not stop after one demo-2 run\n' >&2; exit 1; }
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

# The operational low-disk guard stops before pulling and records its reason.
if ! run_smoke low-disk env MOCK_ROOT_FREE=100 LOW_DISK_BYTES=200; then
  grep -q 'STOP reason=low_disk phase=before-instance root_free_bytes=100 docker_root_free_bytes=null' "$TMP/low-disk/stdout"
else
  printf 'Low disk did not stop the driver\n' >&2
  exit 1
fi
if grep -q '^docker .* pull' "$TMP/low-disk/order"; then printf 'Unexpected match %s in %s\n' '^docker .* pull' "$TMP/low-disk/order" >&2; exit 1; fi
"$REAL_PYTHON" - "$TMP/low-disk/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
assert summary["stop_reason"] == "low_disk"
assert summary["instances"] == []
PY
[ "$(grep -c '^Disk diagnostics:' "$TMP/success/stdout")" = 8 ]

# Without a named context, a low Docker root must stop even when / is healthy.
mkdir -p "$TMP/docker-low"
: > "$TMP/docker-low/order"
if ORDER="$TMP/docker-low/order" PATH="$TMP/bin:$PATH" MOCK_ROOT_FREE=1000000000 MOCK_DOCKER_FREE=100 LOW_DISK_BYTES=200 \
    "$BASH_BIN" "$DRIVER" --harness-dir "$TMP/harness" --frozen-jsonl "$TMP/frozen.jsonl" \
    --selection "$TMP/selection.json" --output-dir "$TMP/docker-low/output" \
    > "$TMP/docker-low/stdout" 2> "$TMP/docker-low/stderr"; then
  printf 'Low Docker root did not stop the driver\n' >&2
  exit 1
fi
grep -q 'STOP reason=low_disk phase=before-instance root_free_bytes=1000000000' "$TMP/docker-low/stdout"
grep -q 'docker_root_free_bytes=100 threshold_bytes=200' "$TMP/docker-low/stdout"

# Check the diagnostic command separately; do not mistake its failure for empty data.
if ! run_smoke docker-df-failure env FAIL_DOCKER_DF=1; then
  grep -q 'Docker disk diagnostic failed; stopping' "$TMP/docker-df-failure/stderr"
else
  printf 'Docker diagnostic failure did not stop\n' >&2
  exit 1
fi
test -f "$TMP/docker-df-failure/output/summary.json"
if grep -q '^harness run' "$TMP/docker-df-failure/order"; then printf 'Unexpected match %s in %s\n' '^harness run' "$TMP/docker-df-failure/order" >&2; exit 1; fi

# A mid-pull abort records all three runs, cleans up, and continues after recovery.
mkdir -p "$TMP/pull-abort"
if ! run_smoke pull-abort env WATCH_ABORT_PULL=1 RECOVER_DISK=1 DISK_PHASE_FILE="$TMP/pull-abort" \
    LOW_DISK_BYTES=200 WATCHDOG_INTERVAL=0.05; then
  printf 'Recovered pull watchdog abort failed\n' >&2
  exit 1
fi
"$REAL_PYTHON" - "$TMP/pull-abort/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
assert summary["stop_reason"] is None
first, second = summary["instances"]
assert [r["reason"] for r in first["runs"]] == ["low_disk"] * 3
assert all(not r["resolved"] for r in first["runs"])
assert all(r["resolved"] for r in second["runs"])
PY
# The killed pull never registered an image: confirmed absence is clean.
if grep -q '^docker .* image rm .*:tag$' "$TMP/pull-abort/order"; then
  printf 'Missing image was removed by tag\n' >&2
  exit 1
fi
grep -q '^docker .* image rm -f sha256:image-id' "$TMP/pull-abort/order"
grep -q '^harness run demo-2' "$TMP/pull-abort/order"

# A daemon error while checking the image is not absence: cleanup STOPs.
mkdir -p "$TMP/inspect-failure"
if run_smoke inspect-failure env WATCH_ABORT_PULL=1 RECOVER_DISK=1 DISK_PHASE_FILE="$TMP/inspect-failure" \
    FAIL_INSPECT=1 LOW_DISK_BYTES=200 WATCHDOG_INTERVAL=0.05; then
  printf 'Image inspect daemon error did not stop the driver\n' >&2
  exit 1
fi
grep -q 'Exact instance cleanup failed; stopping: demo-1' "$TMP/inspect-failure/stdout"

# A harness abort suppresses remaining executions but records all three outcomes.
mkdir -p "$TMP/harness-abort"
if ! run_smoke harness-abort env WATCH_ABORT_HARNESS=1 RECOVER_DISK=1 DISK_PHASE_FILE="$TMP/harness-abort" \
    FAKE_CONTAINER=fake-ctr-1 LOW_DISK_BYTES=200 WATCHDOG_INTERVAL=0.05; then
  printf 'Recovered harness watchdog abort failed\n' >&2
  exit 1
fi
[ "$(grep -c '^harness run demo-1' "$TMP/harness-abort/order")" = 1 ]
grep -q '^docker --context smoke-test rm -f fake-ctr-1$' "$TMP/harness-abort/order"
# The pulled image goes once, by ID; a second removal by tag would fail.
[ "$(grep -c '^docker .* image rm ' "$TMP/harness-abort/order")" = 2 ]
"$REAL_PYTHON" - "$TMP/harness-abort/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
first, second = summary["instances"]
assert [r["reason"] for r in first["runs"]] == ["low_disk"] * 3
assert [r["run"] for r in first["runs"]] == [1, 2, 3]
assert all(r["resolved"] for r in second["runs"])
PY

# If disk does not recover after cleanup, stop nonzero and preserve the summary.
mkdir -p "$TMP/not-recovered"
if ! run_smoke not-recovered env WATCH_ABORT_PULL=1 DISK_PHASE_FILE="$TMP/not-recovered" \
    LOW_DISK_BYTES=200 WATCHDOG_INTERVAL=0.05; then
  test -f "$TMP/not-recovered/output/summary.json"
else
  printf 'Unrecovered watchdog abort did not stop\n' >&2
  exit 1
fi
if grep -q '^harness run demo-2' "$TMP/not-recovered/order"; then printf 'Unexpected match %s in %s\n' '^harness run demo-2' "$TMP/not-recovered/order" >&2; exit 1; fi
"$REAL_PYTHON" - "$TMP/not-recovered/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
assert summary["stop_reason"] == "low_disk"
assert len(summary["instances"]) == 1
assert [r["reason"] for r in summary["instances"][0]["runs"]] == ["low_disk"] * 3
PY

# A transient watchdog measurement failure is not low disk: STOP with its
# reason after removing the instance's containers.
mkdir -p "$TMP/measure-abort"
if run_smoke measure-abort env WATCH_MEASURE_FAIL_HARNESS=1 DISK_PHASE_FILE="$TMP/measure-abort" \
    FAKE_CONTAINER=fake-ctr-1 WATCHDOG_INTERVAL=0.05; then
  printf 'Watchdog measurement failure did not stop\n' >&2
  exit 1
fi
grep -q 'STOP reason=disk_measurement_failed phase=run-1 instance=demo-1' "$TMP/measure-abort/stdout"
grep -q '^docker --context smoke-test rm -f fake-ctr-1$' "$TMP/measure-abort/order"
[ "$(grep -c '^harness run demo-1' "$TMP/measure-abort/order")" = 1 ]
if grep -q '^harness run demo-2' "$TMP/measure-abort/order"; then
  printf 'Measurement failure did not stop before demo-2\n' >&2
  exit 1
fi
"$REAL_PYTHON" - "$TMP/measure-abort/output/summary.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    summary = json.load(stream)
assert summary["stop_reason"] == "disk_measurement_failed"
# The STOP precedes any row for the killed run, so no null-reason row exists.
assert summary["instances"] == []
PY

printf 'FD2 gold smoke fake-docker tests PASS\n'
