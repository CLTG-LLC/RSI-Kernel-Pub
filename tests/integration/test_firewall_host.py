"""Offline loader feasibility: synthetic bytes, unchanged kernel, no product fixtures."""

import base64
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from rsi_kernel.candidate import Candidate
from rsi_kernel.cli import HttpHost
from test_java_host import READY_TIMEOUT, _java_ready, _kernel_hashes, _start, _stop

ROOT = Path(__file__).resolve().parents[2]
HOST_DIR = ROOT / "examples" / "firewall-host"
_reason = _java_ready()
pytestmark = pytest.mark.skipif(
    _reason is not None and not os.environ.get("CI"),
    reason=f"Firewall host needs javac (JDK 21) on PATH: {_reason}",
)

# The loader class and load method are deliberately package-private. The public
# record exposes the native predicate, just as a host rule object does.
STUB = """
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.function.Predicate;
import java.util.regex.Pattern;

public final class SyntheticCatalog {
    public static List<String> defaults() { return List.of("synthetic-marker"); }
    public record Rule(Predicate<String> matcher) { }
}
final class SyntheticLoader {
    static List<SyntheticCatalog.Rule> load(InputStream input, List<?> matchers) throws IOException {
        if (!matchers.equals(List.of("synthetic-marker"))) throw new IOException("factory not called");
        String text = new String(input.readAllBytes(), StandardCharsets.UTF_8);
        if (text.equals("BROKEN")) throw new IllegalStateException("invalid synthetic schema");
        if (text.equals("OPERATIONAL")) throw new IOException("synthetic infrastructure fault");
        if (text.equals("MATCHER_FAULT"))
            return List.of(new SyntheticCatalog.Rule(s -> { throw new IllegalStateException("matcher fault"); }));
        if (!text.startsWith("regex:")) throw new IllegalStateException("missing prefix");
        Pattern pattern = Pattern.compile(text.substring("regex:".length()));
        return List.of(new SyntheticCatalog.Rule(s -> pattern.matcher(s).find()));
    }
}
"""

CHAMPION = b"regex:synthetic-guard"
VALID = b"regex:synthetic-guard|synthetic-alpha"
GUARD_FAIL = b"regex:synthetic-alpha"
CASES = {
    "d0": {"text": "synthetic-alpha", "expectation": "must_match"},
    "d1": {"text": "synthetic-beta", "expectation": "must_match"},
    "d2": {"text": "synthetic-ordinary", "expectation": "must_not_match"},
}
GUARDS = {"g0": {"text": "synthetic-guard", "expectation": "must_match"}}


def _write(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")
    return str(path)


def _request(url, path, body=None, method=None):
    req = urllib.request.Request(
        url + path, data=None if body is None else json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}, method=method,
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=READY_TIMEOUT) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def _candidate_body(data, ids=("d0", "d1", "d2")):
    candidate = Candidate({"rules.yml": data}, "application/yaml")
    return {"candidate_id": candidate.id, "item_ids": list(ids),
            "components": {"rules.yml": base64.b64encode(data).decode()}}


def test_offline_host_implementation_exists():
    assert (HOST_DIR / "FirewallHost.java").is_file(), "offline firewall host implementation is missing"


@pytest.fixture(scope="module")
def firewall_classes(tmp_path_factory):
    out = tmp_path_factory.mktemp("firewall-classes")
    stub = out / "SyntheticCatalog.java"
    stub.write_text(STUB, encoding="utf-8")
    source = HOST_DIR / "FirewallHost.java"
    # A missing implementation is an assertion RED, never a javac error.
    assert source.is_file(), "offline firewall host implementation is missing"
    subprocess.run(["javac", "-d", str(out), str(source), str(stub)], check=True,
                   capture_output=True, text=True, timeout=READY_TIMEOUT)
    return out


@pytest.fixture
def firewall_host(firewall_classes, tmp_path):
    processes = []

    def make(champion=CHAMPION, cases=CASES, guards=GUARDS, start=True, **overrides):
        work = tmp_path / str(len(processes))
        work.mkdir()
        champion_path = work / "champion.yml"
        champion_path.write_bytes(champion)
        cases_path = _write(work / "cases.json", cases)
        guard_path = _write(work / "guards.json", guards)
        log = work / "evidence.jsonl"
        config = {"classpath": str(firewall_classes), "loader_class": "SyntheticLoader",
                  "matcher_factory": "SyntheticCatalog#defaults", "champion_path": str(champion_path),
                  "cases_path": cases_path, "guard_cases_path": guard_path, "evidence_path": str(log)}
        config.update(overrides)
        properties = work / "host.properties"
        # java.util.Properties consumes backslashes before the JSON argv parser.
        properties.write_text("".join(f"{key}={str(value).replace(chr(92), chr(92) * 2)}\n"
                                      for key, value in config.items()), encoding="utf-8")
        command = ["java", "-cp", str(firewall_classes), "FirewallHost", str(properties), "0"]
        if not start:
            return command
        proc, url = _start(command)
        processes.append(proc)
        return url, log, champion_path

    yield make
    for proc in processes:
        _stop(proc)


def _log_rows(log):
    return [json.loads(line) for line in log.read_text().splitlines()]


def test_valid_candidate_native_predicates_scores_and_exact_bytes(firewall_host):
    url, log, champion_path = firewall_host()
    before = champion_path.read_bytes()
    # Trailing spaces are significant regex bytes: an ignored normalization
    # would change d0 from a miss to a hit.
    for data, scores in ((VALID, [1, 0, 1]),
                         (b"regex:synthetic-guard|synthetic-alpha ", [0, 0, 1])):
        body = _candidate_body(data)
        status, result = _request(url, "/evaluate", body)
        assert status == 200
        assert result["results"] == [
            {"item_id": item_id, "score": score, "feedback": "correct" if score else "incorrect"}
            for item_id, score in zip(body["item_ids"], scores)
        ]
        assert _log_rows(log)[-1] == {"content_id": body["candidate_id"], "status": "ok",
                                     "reason_class": "none"}
    assert len(_log_rows(log)) == 2
    assert champion_path.read_bytes() == before
    assert all(case["text"] not in log.read_text() for case in GUARDS.values())


@pytest.mark.parametrize("data,reason", [(b"BROKEN", "IllegalStateException"),
                                           (b"regex:[", "PatternSyntaxException")])
def test_loader_and_compile_failure_are_hard_ineligible(firewall_host, data, reason):
    url, log, _ = firewall_host()
    body = _candidate_body(data)
    status, reply = _request(url, "/evaluate", body)
    assert status == 422
    assert reply == {"error": "ineligible", "reason_class": reason}
    assert _log_rows(log) == [{"content_id": body["candidate_id"], "status": "ineligible",
                              "reason_class": reason}]


@pytest.mark.parametrize("data,reason", [(b"OPERATIONAL", "IOException"),
                                          (b"MATCHER_FAULT", "IllegalStateException")])
def test_operational_failure_is_not_schema_failure(firewall_host, data, reason):
    url, log, _ = firewall_host()
    body = _candidate_body(data)
    status, reply = _request(url, "/evaluate", body)
    assert status == 500
    assert reply == {"error": "operational", "reason_class": reason}
    assert _log_rows(log) == [{"content_id": body["candidate_id"], "status": "operational",
                              "reason_class": reason}]


def test_guard_failure_blocks_selection_despite_zero_champion(firewall_host, tmp_path):
    zero_cases = {key: {"text": f"synthetic-unmatched-{key}", "expectation": "must_match"}
                  for key in ("d0", "d1")}
    url, log, _ = firewall_host(cases=zero_cases)
    before = _kernel_hashes()
    host = HttpHost(url)
    champion = host.get_artifact()
    assert [row["score"] for row in host.evaluate(champion, ["d0", "d1"])] == [0, 0]
    status, reply = _request(url, "/evaluate", _candidate_body(GUARD_FAIL, ["d0", "d1"]))
    assert status == 422 and reply["reason_class"] == "GoldenGuardFailure"
    config = {
        "campaign_id": "synthetic-guard-rejection", "host_url": url, "store": str(tmp_path / "store"),
        "component_ids": ["c1"], "evaluator_hash": "synthetic-native-predicate-v1", "code_hash": "frozen",
        "splits": {"splits": [{"name": "dev", "purpose": "dev", "selection_eligible": True,
                               "item_ids": ["d0", "d1"]}]},
        "bounds": {"max_attempts": 2, "spend_cap": 10, "eval_cap": 100, "runs": 1},
        "proposals": [{"media_type": "application/yaml", "components":
                       _candidate_body(GUARD_FAIL)["components"]}],
    }
    result = subprocess.run([sys.executable, "-m", "rsi_kernel.cli", "run-campaign", "--config",
                             _write(tmp_path / "campaign.json", config)], capture_output=True,
                            text=True, timeout=60, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    output = json.loads(result.stdout)
    assert output["outcome"] == "no_improvement"
    assert output["selected_id"] is None
    rejected = [row for row in _log_rows(log) if row["content_id"] == _candidate_body(GUARD_FAIL)["candidate_id"]]
    assert rejected and all(row["status"] == "ineligible" for row in rejected)
    assert _kernel_hashes() == before


def test_legitimate_zero_score_tie_is_not_rejected(firewall_host, tmp_path):
    cases = {"d0": {"text": "synthetic-unmatched", "expectation": "must_match"}}
    url, _, _ = firewall_host(cases=cases)
    status, result = _request(url, "/evaluate", _candidate_body(VALID, ["d0"]))
    assert status == 200 and result["results"][0]["score"] == 0


def test_artifact_and_record_only_apply_do_not_change_champion(firewall_host):
    url, _, champion_path = firewall_host()
    before = hashlib.sha256(champion_path.read_bytes()).hexdigest()
    host = HttpHost(url)
    original = host.get_artifact()
    assert original.components == {"rules.yml": CHAMPION}
    candidate_id = _candidate_body(VALID)["candidate_id"]
    assert _request(url, "/apply", {"candidate_id": candidate_id}) == (200, {"applied": [candidate_id]})
    assert host.get_artifact().id == original.id
    assert hashlib.sha256(champion_path.read_bytes()).hexdigest() == before


@pytest.mark.parametrize("change", ["hash", "missing", "extra", "unknown_item", "type"])
def test_invalid_request_is_rejected_and_logged_once(firewall_host, change):
    url, log, _ = firewall_host()
    body = _candidate_body(VALID)
    if change == "hash":
        body = {**body, "candidate_id": "0" * 64}
    elif change == "missing":
        body = {key: value for key, value in body.items() if key != "components"}
    elif change == "extra":
        body = {**body, "components": {**body["components"], "other.yml": "eA=="}}
    elif change == "unknown_item":
        body = {**body, "item_ids": ["unknown"]}
    else:
        body = {**body, "item_ids": "d0"}
    assert _request(url, "/evaluate", body)[0] == 400
    rows = _log_rows(log)
    assert len(rows) == 1 and rows[0]["status"] == "operational"
    if change == "hash":
        assert rows[0]["content_id"] == _candidate_body(VALID)["candidate_id"]


def test_routes_enforce_exact_path_and_method(firewall_host):
    url, log, _ = firewall_host()
    assert _request(url, "/artifact", {}, "POST")[0] == 405
    assert _request(url, "/evaluate")[0] == 405
    assert _request(url, "/apply")[0] == 405
    assert _request(url, "/artifact/extra")[0] == 404
    assert len(_log_rows(log)) == 1


@pytest.fixture
def guard_setup(tmp_path):
    offline = tmp_path / "synthetic offline copy"
    offline.mkdir()
    resource = offline / "rules.yml"
    resource.write_bytes(CHAMPION)
    counter = offline / "runs"
    seen = offline / "seen.bytes"
    script = offline / 'guard "quoted".py'
    script.write_text(
        "import os, pathlib, subprocess, sys, time\n"
        "assert pathlib.Path.cwd() == pathlib.Path(sys.argv[1])\n"
        "counter = pathlib.Path('runs')\n"
        "counter.write_text(str(int(counter.read_text()) + 1) if counter.exists() else '1')\n"
        "data = pathlib.Path('rules.yml').read_bytes()\n"
        "pathlib.Path('seen.bytes').write_bytes(data)\n"
        "print('synthetic-private-guard-output', flush=True)\n"
        "print('synthetic-private-guard-error', file=sys.stderr, flush=True)\n"
        "if b'synthetic-child-timeout' in data:\n"
        "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "    pathlib.Path('guard.pids').write_text(str(os.getpid()) + ' ' + str(child.pid))\n"
        "    time.sleep(60)\n"
        "if b'synthetic-timeout' in data: time.sleep(60)\n"
        "if b'synthetic-delete' in data: pathlib.Path('rules.yml').unlink()\n"
        "sys.exit(1 if b'synthetic-reject' in data else 0)\n", encoding="utf-8",
    )
    config = {"guard_command": json.dumps([sys.executable, str(script), str(offline)]),
              "guard_working_directory": str(offline), "guard_resource_path": str(resource),
              "guard_timeout_seconds": READY_TIMEOUT}
    return config, resource, counter, seen


@pytest.mark.parametrize("data,code,guard_status", [
    (VALID + b" ", 200, "passed"),
    (VALID + b"|synthetic-reject", 422, "guard_failed"),
])
def test_guard_command_exact_bytes_restoration_and_cache(firewall_host, guard_setup,
                                                       data, code, guard_status):
    config, resource, counter, seen = guard_setup
    url, log, champion_path = firewall_host(**config)
    for ids in (("d0",), ("d1",)):
        status, reply = _request(url, "/evaluate", _candidate_body(data, ids))
        assert resource.read_bytes() == champion_path.read_bytes() == CHAMPION
        assert status == code
        if code == 422:
            assert reply == {"error": "ineligible", "reason_class": "guard_failed"}
        else:
            assert reply["results"][0]["item_id"] == ids[0]
        row = _log_rows(log)[-1]
        assert "guard_status" in row, "guard command result is missing from evidence"
        assert row["guard_status"] == guard_status
        assert row["skipped_tests"] == "unknown"
        assert row["reason_class"] == ("none" if code == 200 else "guard_failed")
        assert "synthetic-private" not in log.read_text() + json.dumps(reply)
        assert seen.read_bytes() == data
        assert counter.read_text() == "1"
    # A distinct content ID needs its own guard result, even in the same host.
    assert _request(url, "/evaluate", _candidate_body(VALID + b"|synthetic-next"))[0] == 200
    assert counter.read_text() == "2"
    assert resource.read_bytes() == CHAMPION


@pytest.mark.parametrize("failure", ["launch", "timeout"])
def test_guard_command_unavailable_is_operational_and_restored(firewall_host, guard_setup, failure):
    config, resource, counter, _ = guard_setup
    data = VALID
    if failure == "launch":
        config = {**config, "guard_command": json.dumps([str(resource.parent / "missing")])}
    else:
        # 0.5s is the existing bounded-startup test's timeout precedent.
        config = {**config, "guard_timeout_seconds": 0.5}
        data += b"|synthetic-timeout"
    url, log, champion_path = firewall_host(**config)
    started = time.monotonic()
    for _ in range(2):
        status, reply = _request(url, "/evaluate", _candidate_body(data))
        assert resource.read_bytes() == champion_path.read_bytes() == CHAMPION
        assert status == 500
        assert reply == {"error": "operational", "reason_class": "guard_unavailable"}
        assert _log_rows(log)[-1]["guard_status"] == "guard_unavailable"
        assert "synthetic-private" not in log.read_text() + json.dumps(reply)
    assert time.monotonic() - started < READY_TIMEOUT
    if failure == "timeout":
        assert counter.read_text() == "1"
    else:
        assert not counter.exists()


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


def test_guard_command_timeout_terminates_descendants_before_response(firewall_host, guard_setup):
    config, resource, _, _ = guard_setup
    config = {**config, "guard_timeout_seconds": 0.5}
    url, log, _ = firewall_host(**config)
    pids_path = resource.parent / "guard.pids"
    try:
        status, reply = _request(url, "/evaluate", _candidate_body(VALID + b"|synthetic-child-timeout"))
        assert status == 500 and reply["reason_class"] == "guard_unavailable"
        assert pids_path.exists(), "guard did not record its owned parent and child PIDs"
        pids = [int(value) for value in pids_path.read_text().split()]
        assert len(pids) == 2
        assert not any(_pid_alive(pid) for pid in pids), "guard descendants survived the timeout response"
        assert resource.read_bytes() == CHAMPION
        assert _log_rows(log)[-1]["guard_status"] == "guard_unavailable"
    finally:
        # Only the PIDs created and recorded by this synthetic guard are ours.
        if pids_path.exists():
            for pid in [int(value) for value in pids_path.read_text().split()]:
                try:
                    os.kill(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass


def test_guard_command_resource_directory_contains_only_candidate(firewall_host, tmp_path):
    offline = tmp_path / "offline"
    resource_dir = offline / "resources"
    resource_dir.mkdir(parents=True)
    resource = resource_dir / "rules.yml"
    resource.write_bytes(CHAMPION)
    listing = offline / "resource-listing.json"
    script = offline / "guard.py"
    script.write_text(
        "import json, pathlib, sys\n"
        "names = sorted(path.name for path in pathlib.Path('resources').iterdir())\n"
        "pathlib.Path('resource-listing.json').write_text(json.dumps(names))\n"
        "sys.exit(0 if names == ['rules.yml'] else 1)\n", encoding="utf-8")
    url, log, _ = firewall_host(
        guard_command=json.dumps([sys.executable, str(script)]),
        guard_working_directory=str(offline), guard_resource_path=str(resource),
        guard_timeout_seconds=READY_TIMEOUT,
    )
    status, reply = _request(url, "/evaluate", _candidate_body(VALID))
    assert status == 200, f"guard saw unexpected resource files: {listing.read_text()} ({reply})"
    assert json.loads(listing.read_text()) == ["rules.yml"]
    assert sorted(path.name for path in resource_dir.iterdir()) == ["rules.yml"]
    assert resource.read_bytes() == CHAMPION
    assert _log_rows(log)[-1]["guard_status"] == "passed"


def test_guard_command_restores_deleted_resource_before_response(firewall_host, guard_setup):
    config, resource, _, seen = guard_setup
    original = resource.stat()
    url, log, _ = firewall_host(**config)
    data = VALID + b"|synthetic-delete"
    status, reply = _request(url, "/evaluate", _candidate_body(data))
    assert resource.exists(), "guard deletion prevented restoration of the champion"
    assert resource.read_bytes() == CHAMPION
    restored = resource.stat()
    assert restored.st_mode == original.st_mode
    assert restored.st_mtime_ns == original.st_mtime_ns
    assert status == 200 and "results" in reply
    assert seen.read_bytes() == data
    assert _log_rows(log)[-1]["guard_status"] == "passed"


def test_guard_command_incremental_build_sees_candidate_not_stale_champion(firewall_host, guard_setup):
    # Timestamp-based build tools (GNU Make, incremental resource copies) rebuild
    # only when the source is newer than the built copy; candidate install must
    # therefore carry a fresh mtime, while restoration keeps the original one.
    config, resource, _, _ = guard_setup
    offline = resource.parent
    built = offline / "built.yml"
    script = offline / "incremental.py"
    script.write_text(
        "import pathlib, shutil, sys\n"
        "src, out = pathlib.Path('rules.yml'), pathlib.Path('built.yml')\n"
        "if not out.exists() or src.stat().st_mtime_ns > out.stat().st_mtime_ns:\n"
        "    shutil.copyfile(src, out)\n"
        "sys.exit(1 if b'synthetic-reject' in out.read_bytes() else 0)\n", encoding="utf-8")
    past = resource.stat().st_mtime - 100
    os.utime(resource, (past, past))
    built.write_bytes(CHAMPION)  # prebuilt, newer than the source
    original = resource.stat()
    config = {**config, "guard_command": json.dumps([sys.executable, str(script)])}
    url, log, _ = firewall_host(**config)
    status, reply = _request(url, "/evaluate", _candidate_body(VALID + b"|synthetic-reject"))
    assert status == 422, "incremental guard built stale champion bytes"
    assert reply == {"error": "ineligible", "reason_class": "guard_failed"}
    assert resource.read_bytes() == CHAMPION
    assert resource.stat().st_mtime_ns == original.st_mtime_ns


@pytest.mark.parametrize("change", ["missing_timeout", "zero_timeout", "negative_timeout",
                                    "nan_timeout", "infinite_timeout", "shell_string",
                                    "empty_argv", "blank_executable", "missing_workdir",
                                    "missing_resource", "outside_resource"])
def test_guard_command_invalid_config_fails_before_listening(firewall_host, guard_setup, tmp_path, change):
    config, resource, _, _ = guard_setup
    if change == "missing_timeout":
        config = {key: value for key, value in config.items() if key != "guard_timeout_seconds"}
    elif change in ("zero_timeout", "negative_timeout", "nan_timeout", "infinite_timeout"):
        config = {**config, "guard_timeout_seconds": {
            "zero_timeout": 0, "negative_timeout": -1, "nan_timeout": "NaN",
            "infinite_timeout": "Infinity"}[change]}
    elif change in ("shell_string", "empty_argv", "blank_executable"):
        config = {**config, "guard_command": {"shell_string": "python guard.py",
                  "empty_argv": "[]", "blank_executable": '[""]'}[change]}
    elif change == "outside_resource":
        outside = tmp_path / "outside.yml"
        outside.write_bytes(CHAMPION)
        config = {**config, "guard_resource_path": str(outside)}
    else:
        key = "guard_working_directory" if change == "missing_workdir" else "guard_resource_path"
        config = {name: value for name, value in config.items() if name != key}
    command = firewall_host(start=False, **config)
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        try:
            stdout, _ = proc.communicate(timeout=0.5)
        except subprocess.TimeoutExpired:
            pytest.fail("invalid guard configuration started the server")
        assert proc.returncode != 0
        assert "LISTENING" not in stdout
        assert resource.read_bytes() == CHAMPION
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=READY_TIMEOUT)
        proc.stdout.close()
        proc.stderr.close()
