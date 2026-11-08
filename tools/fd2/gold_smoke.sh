#!/usr/bin/env bash
# Run the frozen FD2 gold-only smoke locally or from its GitHub Actions workflow.
set -u

usage() {
  printf 'Usage: %s --harness-dir DIR --frozen-jsonl FILE --selection FILE --output-dir DIR\n' "$0" >&2
  exit 2
}

HARNESS_DIR=
FROZEN_JSONL=
SELECTION=
OUTPUT_DIR=
# NAMED LOCAL EXCEPTION: operational guard so the runner survives to upload
# the summary; not a quality gate. Override with LOW_DISK_BYTES.
LOW_DISK_BYTES="${LOW_DISK_BYTES:-2147483648}"
# NAMED LOCAL EXCEPTION: polling cadence for the operational watchdog only.
WATCHDOG_INTERVAL="${WATCHDOG_INTERVAL:-5}"
case "$LOW_DISK_BYTES" in ''|*[!0-9]*) printf 'LOW_DISK_BYTES must be a nonnegative integer\n' >&2; exit 2 ;; esac
case "$WATCHDOG_INTERVAL" in ''|*[!0-9.]*) printf 'WATCHDOG_INTERVAL must be a nonnegative number\n' >&2; exit 2 ;; esac
while [ "$#" -gt 0 ]; do
  case "$1" in
    --harness-dir) HARNESS_DIR="${2:?}" ;;
    --frozen-jsonl) FROZEN_JSONL="${2:?}" ;;
    --selection) SELECTION="${2:?}" ;;
    --output-dir) OUTPUT_DIR="${2:?}" ;;
    *) usage ;;
  esac
  shift 2
done
if [ -z "$HARNESS_DIR" ] || [ -z "$FROZEN_JSONL" ] || [ -z "$SELECTION" ] || [ -z "$OUTPUT_DIR" ]; then
  usage
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)" || exit 1
ORIGINAL_CWD="$PWD"
HARNESS_DIR="$(cd "$HARNESS_DIR" && pwd)" || exit 1
FROZEN_JSONL="$(cd "$(dirname "$FROZEN_JSONL")" && pwd)/$(basename "$FROZEN_JSONL")" || exit 1
SELECTION="$(cd "$(dirname "$SELECTION")" && pwd)/$(basename "$SELECTION")" || exit 1
mkdir -p "$OUTPUT_DIR" || exit 1
OUTPUT_DIR="$(cd "$OUTPUT_DIR" && pwd)" || exit 1
cd "$ORIGINAL_CWD" || exit 1
DATASET_PATH_FILE="$OUTPUT_DIR/pinned.jsonl"
ROWS="$OUTPUT_DIR/runs.ndjson"
HARNESS_LOGS="$OUTPUT_DIR/harness-logs"
SUMMARY="$OUTPUT_DIR/summary.json"
mkdir -p "$OUTPUT_DIR" "$HARNESS_LOGS"
cp "$FROZEN_JSONL" "$DATASET_PATH_FILE" || exit 1
: > "$ROWS" || exit 1

# All Docker CLI calls use this context without changing the user's default.
# https://docs.docker.com/engine/manage-resources/contexts/
# The array is empty without a context; bash before 4.4 treats an empty
# "${a[@]}" as unbound under set -u, so every use is ${a[@]+"${a[@]}"}.
DOCKER_CONTEXT_ARGS=()
if [ -n "${DOCKER_CONTEXT:-}" ]; then
  DOCKER_CONTEXT_ARGS=(--context "$DOCKER_CONTEXT")
  DOCKER_HOST="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} context inspect \
    "$DOCKER_CONTEXT" --format '{{(index .Endpoints "docker").Host}}')" || exit 1
  export DOCKER_HOST
fi
DOCKER_PLATFORM="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} version --format '{{.Server.Os}}/{{.Server.Arch}}')" || exit 1
DOCKER_ROOT="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} info -f '{{.DockerRootDir}}')" || exit 1

write_summary() {
  local exit_status="$1"
  local stop_reason="${2:-}"
  if [ -n "$stop_reason" ]; then
    STOP_REASON="$stop_reason"
  fi
  python - "$ROWS" "$SUMMARY" "$DOCKER_PLATFORM" "${DOCKER_CONTEXT:-}" "${STOP_REASON:-}" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    runs = [json.loads(line) for line in stream if line.strip()]
instances = []
for key in dict.fromkeys((row["instance_id"], row["split"]) for row in runs):
    matching = [row for row in runs if (row["instance_id"], row["split"]) == key]
    instances.append({"instance_id": key[0], "split": key[1], "runs": matching})
with open(sys.argv[2], "w", encoding="utf-8") as stream:
    json.dump({"instances": instances, "docker_platform": sys.argv[3],
               "docker_context": sys.argv[4], "stop_reason": sys.argv[5] or None}, stream, indent=2, sort_keys=True)
    stream.write("\n")
PY
  local summary_status=$?
  if [ "$summary_status" -ne 0 ]; then
    printf 'Summary write failed; stopping\n' >&2
    return "$summary_status"
  fi
  return "$exit_status"
}

fail_stop() {
  printf '%s; stopping\n' "$1" >&2
  write_summary 1
  exit $?
}

cd "$HARNESS_DIR" || exit 1
free_bytes() {
  if [ "$1" = / ]; then
    python3 -c 'import shutil; print(shutil.disk_usage("/").free)'
  else
    python3 -c 'import shutil,sys; print(shutil.disk_usage(sys.argv[1]).free)' "$1"
  fi
}
is_low_disk() {
  local root_free docker_free free_status
  if root_free="$(free_bytes /)"; then free_status=0; else free_status=$?; fi
  if [ "$free_status" -ne 0 ]; then return 2; fi
  if [ "$root_free" -lt "$LOW_DISK_BYTES" ]; then return 0; fi
  if [ -z "${DOCKER_CONTEXT:-}" ]; then
    if docker_free="$(free_bytes "$DOCKER_ROOT")"; then free_status=0; else free_status=$?; fi
    if [ "$free_status" -ne 0 ]; then return 2; fi
    if [ "$docker_free" -lt "$LOW_DISK_BYTES" ]; then return 0; fi
  fi
  return 1
}
WATCHDOG_ABORTED=
WATCHDOG_MEASURE_FAILED=
WATCHDOG_PGID=
# https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html
# Job control gives each child its own process group. The caller polls that
# child and reaps it before continuing; no detached watcher is created.
stop_watchdog() {
  local status="$1"
  if [ -n "$WATCHDOG_PGID" ]; then
    kill -KILL -- "-$WATCHDOG_PGID" 2>/dev/null || true
    wait "$WATCHDOG_CHILD" 2>/dev/null || true
  fi
  trap - EXIT
  trap 'stop_watchdog 0' EXIT
  set +m
  WATCHDOG_PGID=
  return "$status"
}
abort_watched_job() {
  printf 'Watchdog reason=low_disk; killing watched process group %s\n' "$WATCHDOG_PGID"
  kill -KILL -- "-$WATCHDOG_PGID" 2>/dev/null || true
  WATCHDOG_ABORTED=1
}
trap 'stop_watchdog 0' EXIT
set -m
check_disk() {
  local phase="$1"
  local root_free docker_free=null docker_usage docker_df
  if ! root_free="$(python3 -c 'import shutil; print(shutil.disk_usage("/").free)')"; then
    fail_stop 'Disk measurement failed'
  fi
  # A named context can point to a Docker Desktop VM; its daemon root is not a
  # host path, so only the host / measurement is meaningful there.
  if [ -z "${DOCKER_CONTEXT:-}" ]; then
    if ! docker_free="$(python3 -c 'import shutil,sys; print(shutil.disk_usage(sys.argv[1]).free)' "$DOCKER_ROOT")"; then
      fail_stop 'Disk measurement failed'
    fi
  fi
  if ! docker_df="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} system df --format '{{json .}}')"; then
    fail_stop 'Docker disk diagnostic failed'
  fi
  if ! docker_usage="$(python3 -c \
      'import json,sys; print(" ".join("{}={}/{}".format(r.get("Type"), r.get("TotalCount"), r.get("Size")) for line in sys.stdin if line.strip() for r in [json.loads(line)]))' \
      <<< "$docker_df")"; then
    fail_stop 'Docker disk diagnostic parse failed'
  fi
  printf 'Disk diagnostics: phase=%s root_free_bytes=%s docker_root_free_bytes=%s docker_system_df="%s"\n' \
    "$phase" "$root_free" "$docker_free" "$docker_usage"
  if [ "$root_free" -lt "$LOW_DISK_BYTES" ] ||
      { [ "$docker_free" != null ] && [ "$docker_free" -lt "$LOW_DISK_BYTES" ]; }; then
    printf 'STOP reason=low_disk phase=%s root_free_bytes=%s docker_root_free_bytes=%s threshold_bytes=%s\n' \
      "$phase" "$root_free" "$docker_free" "$LOW_DISK_BYTES"
    write_summary 1 'low_disk'
    exit $?
  fi
}
watch_job() {
  local pid status=0 low_status
  WATCHDOG_ABORTED=
  WATCHDOG_MEASURE_FAILED=
  set -m
  "$@" &
  pid=$!
  WATCHDOG_PGID="$pid"
  WATCHDOG_CHILD="$pid"
  # Poll the running job; no detached watcher survives this function.
  while [[ $(jobs -pr) == *"$pid"* ]]; do
    sleep "$WATCHDOG_INTERVAL"
    if [[ $(jobs -pr) != *"$pid"* ]]; then break; fi
    is_low_disk
    low_status=$?
    if [ "$low_status" -eq 0 ]; then
      abort_watched_job
    elif [ "$low_status" -eq 2 ]; then
      printf 'Watchdog disk measurement failed; stopping watched process group\n' >&2
      WATCHDOG_MEASURE_FAILED=1
      kill -KILL -- "-$WATCHDOG_PGID" 2>/dev/null || true
    fi
  done
  if wait "$pid"; then status=0; else status=$?; fi
  stop_watchdog "$status"
}
remove_instance_containers() {
  local containers
  containers="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} ps -aq --filter "name=^git-launch-${instance_id}-")" || return 1
  if [ -n "$containers" ]; then
    docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} rm -f $containers > /dev/null || return 1
  fi
}
# The watched job is already reaped; a failed measurement means the disk state
# is unknown, so remove this instance's containers and STOP with its reason.
stop_measurement_failed() {
  STOP_REASON=disk_measurement_failed
  printf 'STOP reason=disk_measurement_failed phase=%s instance=%s\n' "$1" "$instance_id"
  remove_instance_containers || fail_stop 'Measurement-failure container cleanup failed'
  write_summary 1
  exit $?
}
# 0 prints the image ID; 1 means the daemon confirmed absence; 2 is any other
# failure. Moby reports a missing image as "No such image: <ref>"
# (github.com/moby/moby daemon/images/image.go, ErrImageDoesNotExist).
image_state() {
  local output
  if output="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} image inspect "$1" --format '{{.Id}}' 2>&1)"; then
    printf '%s\n' "$output"
    return 0
  fi
  case "$output" in *'No such image'*) return 1 ;; esac
  printf '%s\n' "$output" >&2
  return 2
}

while IFS=$'\t' read -r instance_id split image; do
  check_disk "before-instance"
  abort_instance=
  pinned_image="$image"
  image_size=
  image_id=
  watch_job docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} pull "$image" > "$HARNESS_LOGS/pull.log" 2>&1
  pull_status=$?
  if [ -n "$WATCHDOG_MEASURE_FAILED" ]; then
    stop_measurement_failed pull
  elif [ -n "$WATCHDOG_ABORTED" ]; then
    abort_instance=1
  elif [ "$pull_status" -ne 0 ]; then
    printf 'Image pull failed; stopping before evaluation: %s\n' "$instance_id"
    write_summary 1
    exit $?
  fi
  if [ -z "$abort_instance" ]; then
    digest="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} image inspect "$image" --format '{{index .RepoDigests 0}}' | sed 's/^.*@//')"
  case "$digest" in sha256:*) ;; *) printf 'No repository digest: %s\n' "$instance_id"; write_summary 1; exit $? ;; esac
  pinned_image="$(python - "$DATASET_PATH_FILE" "$instance_id" "$digest" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    rows = [json.loads(line) for line in stream if line.strip()]
row = next(row for row in rows if row["instance_id"] == sys.argv[2])
repository = row["docker_image"].split("@", 1)[0].rsplit(":", 1)[0]
print(f"{repository}@{sys.argv[3]}")
PY
)"
  python "$ROOT/tools/fd2/prepare_frozen.py" --pin-image "$DATASET_PATH_FILE" "$instance_id" "$digest"
  digests="[\"${pinned_image}\"]"
  image_size="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} image inspect "$pinned_image" --format '{{.Size}}')"
  image_id="$(docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} image inspect "$pinned_image" --format '{{.Id}}')"
  fi
  # Remove once by image ID: a forced ID removal also drops the original tag
  # and the pinned digest (docs.docker.com/reference/cli/docker/image/rm,
  # examples). An aborted pull may never register the image, so confirmed
  # absence is clean; other errors stay fatal. Explicit checks; never prune.
  cleanup() {
    local ref="${image_id:-$image}" id state
    remove_instance_containers || return 1
    if [ -z "$ref" ]; then return 0; fi
    if id="$(image_state "$ref")"; then state=0; else state=$?; fi
    if [ "$state" -eq 1 ]; then return 0; fi
    if [ "$state" -ne 0 ]; then return 1; fi
    docker ${DOCKER_CONTEXT_ARGS[@]+"${DOCKER_CONTEXT_ARGS[@]}"} image rm -f "$id" > /dev/null || return 1
    if image_state "$id" > /dev/null; then state=0; else state=$?; fi
    [ "$state" -eq 1 ]
  }
  for run in 1 2 3; do
    if [ -n "$abort_instance" ]; then
      resolved=false
      command_status=137
      wall_seconds=0
      before=0
      after=0
      reason=low_disk
    else
    check_disk "before-run-$run"
    output="$OUTPUT_DIR/$split/run-$run"
    if ! before="$(python3 -c 'import shutil; print(shutil.disk_usage("/").free)')"; then
      fail_stop 'Disk measurement failed'
    fi
    started="$(date +%s)"
    watch_job python -m evaluation.evaluation \
      --dataset "$DATASET_PATH_FILE" \
      --split "$split" \
      --platform linux \
      --patch_dir gold \
      --output_dir "$output" \
      --workers 1 \
      --overwrite 0 \
      --instance_ids "$instance_id" \
      > "$HARNESS_LOGS/${split}-run-${run}.log" 2>&1
    command_status=$?
    wall_seconds=$(( $(date +%s) - started ))
    if [ -n "$WATCHDOG_MEASURE_FAILED" ]; then
      stop_measurement_failed "run-$run"
    fi
    if [ -n "$WATCHDOG_ABORTED" ]; then
      abort_instance=1
      remove_instance_containers || fail_stop 'Aborted instance container cleanup failed'
    fi
    if ! after="$(python3 -c 'import shutil; print(shutil.disk_usage("/").free)')"; then
      fail_stop 'Disk measurement failed'
    fi
    resolved="$(python - "$output/$instance_id/report.json" <<'PY'
import json
import sys
try:
    with open(sys.argv[1], encoding="utf-8") as stream:
        report = json.load(stream)
except (OSError, ValueError):
    print("false")
else:
    print("true" if report.get("resolved") is True else "false")
PY
)"
    reason=
    fi
    if [ -n "$abort_instance" ]; then
      resolved=false
      command_status=137
      reason=low_disk
    fi
    digests="[\"${pinned_image}\"]"
    python - "$ROWS" "$instance_id" "$split" "$run" "$resolved" "$wall_seconds" \
      "$command_status" "$before" "$after" "$digests" "$image_size" "$reason" <<'PY'
import json
import sys
row = {
    "instance_id": sys.argv[2], "split": sys.argv[3], "run": int(sys.argv[4]),
    "resolved": sys.argv[5] == "true", "wall_seconds": int(sys.argv[6]),
    "command_status": int(sys.argv[7]),
    "disk_free_bytes_before": int(sys.argv[8]),
    "disk_free_bytes_after": int(sys.argv[9]),
    "image_digests": json.loads(sys.argv[10]),
    "image_size_bytes": int(sys.argv[11]) if sys.argv[11] else None,
    "reason": sys.argv[12] or None,
}
with open(sys.argv[1], "a", encoding="utf-8") as stream:
    stream.write(json.dumps(row, sort_keys=True) + "\n")
PY
  record_status=$?
  if [ "$record_status" -ne 0 ]; then
    fail_stop 'Run record write failed'
  fi
  done
  if ! cleanup; then
    printf 'Exact instance cleanup failed; stopping: %s\n' "$instance_id"
    write_summary 1
    exit $?
  fi
  if [ -n "$abort_instance" ]; then
    is_low_disk
    recovery_status=$?
    if [ "$recovery_status" -eq 0 ]; then
      write_summary 1 'low_disk'
      exit $?
    elif [ "$recovery_status" -eq 2 ]; then
      fail_stop 'Disk measurement failed after watchdog abort'
    fi
    write_summary 0
  fi
done < <(python - "$SELECTION" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    selection = json.load(stream)
for row in selection["instances"]:
    print(row["instance_id"], row["split"], row["docker_image"], sep="\t")
PY
)
write_summary 0
