"""Issue #50: MCP stdio server over the B1 control functions (design §4.1).

A real MCP client from the official SDK (stdio_client + ClientSession) drives the
server as a subprocess: initialize, discovery, then the same operations and the
same JSON as the `rsi-kernel` console entry. The server is an optional extra, so
the module skips when `mcp` is not installed.
"""

import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

import pytest

from test_java_host import _applied, _cli, _config, _reason, _write, java_classes, java_host  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]

try:
    import mcp  # noqa: F401  (the optional extra, name it before its dependencies)
    import anyio
    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    MCP_ERROR = None
except ImportError as error:  # the [mcp] extra is not installed
    MCP_ERROR = str(error)

pytestmark = pytest.mark.skipif(MCP_ERROR is not None, reason=f"MCP tests need the [mcp] extra: {MCP_ERROR}")

# Only the scenarios that drive the Java host need a JDK; the rest run everywhere.
needs_java = pytest.mark.skipif(
    _reason is not None and not os.environ.get("CI"),
    reason=f"MCP tests drive the Java host (JDK 21): {_reason}",
)

SERVER = [sys.executable, "-m", "rsi_kernel.mcp_server"]


def _count(url):
    with urllib.request.urlopen(url + "/count", timeout=10) as r:
        return json.loads(r.read())["items"]


def _mcp(scenario):
    """Run one client session against the server subprocess and return its result."""

    async def run():
        params = StdioServerParameters(command=SERVER[0], args=SERVER[1:])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                init = await session.initialize()
                return await scenario(session, init)

    return anyio.run(run)


def _json(result):
    assert result.is_error is False, result
    return json.loads(result.content[0].text)


@needs_java
def test_client_lists_exactly_the_three_control_tools(java_host):
    async def scenario(session, init):
        return init, await session.list_tools()

    init, tools = _mcp(scenario)
    assert init.server_info is not None and init.protocol_version
    assert sorted(t.name for t in tools.tools) == ["accept", "run_campaign", "status"]


@needs_java
def test_client_campaign_and_status_equal_the_cli(java_host, tmp_path):
    cli_cfg = _write(tmp_path / "cli.json", _config(java_host, tmp_path / "store-cli"))
    cli_result = json.loads(_cli(["run-campaign", "--config", cli_cfg], tmp_path).stdout)
    cli_status = json.loads(_cli(["status", "--config", cli_cfg], tmp_path).stdout)
    mcp_cfg = _write(tmp_path / "mcp.json", _config(java_host, tmp_path / "store-mcp"))

    async def scenario(session, init):
        before = await session.call_tool("status", {"config": mcp_cfg})
        campaign = await session.call_tool("run_campaign", {"config": mcp_cfg})
        after = await session.call_tool("status", {"config": mcp_cfg})
        return before, campaign, after

    before, campaign, after = _mcp(scenario)
    assert _json(before) == {"campaign": None, "acceptance": None, "approval_request": None}
    assert _json(campaign) == cli_result
    assert _json(after) == cli_status


@needs_java
def test_malformed_arguments_error_and_start_no_evaluation(java_host, tmp_path):
    cfg = _write(tmp_path / "cfg.json", _config(java_host, tmp_path / "store"))
    start = _count(java_host)

    async def scenario(session, init):
        missing_arg = await session.call_tool("run_campaign", {})
        missing_file = await session.call_tool("status", {"config": str(tmp_path / "absent.json")})
        wrong_type = await session.call_tool("accept", {"config": cfg, "approval": 7})
        good = await session.call_tool("status", {"config": cfg})
        return missing_arg, missing_file, wrong_type, good

    missing_arg, missing_file, wrong_type, good = _mcp(scenario)
    for result in (missing_arg, missing_file, wrong_type):
        assert result.is_error is True, result
        assert result.content and result.content[0].text
    assert _json(good) == {"campaign": None, "acceptance": None, "approval_request": None}
    assert _count(java_host) == start  # nothing was evaluated


BAD_BOUNDS = {
    # Review S2: these used to fail only after the champion evaluation had run.
    "wrong type": {"max_attempts": "invalid", "spend_cap": 10, "eval_cap": 100, "runs": 1},
    "negative cap": {"max_attempts": 2, "spend_cap": 10, "eval_cap": -1, "runs": 1},
    "non-positive runs": {"max_attempts": 2, "spend_cap": 10, "eval_cap": 100, "runs": 0},
    "missing key": {"spend_cap": 10, "eval_cap": 100, "runs": 1},
}


@needs_java
@pytest.mark.parametrize("case,bounds", sorted(BAD_BOUNDS.items()))
def test_malformed_bounds_error_and_start_no_evaluation(java_host, tmp_path, case, bounds):
    cfg = _write(tmp_path / "bounds.json",
                 _config(java_host, tmp_path / f"store-{case.replace(' ', '-')}", bounds=bounds))
    start = _count(java_host)

    async def scenario(session, init):
        return await session.call_tool("run_campaign", {"config": cfg})

    result = _mcp(scenario)
    assert result.is_error is True, result
    assert result.content and "bounds" in result.content[0].text
    assert _count(java_host) == start  # rejected input evaluated nothing


@needs_java
@pytest.mark.parametrize("max_attempts,expected", [(-1, "no_improvement"), (1.0, "selected")])
def test_bounds_the_kernel_accepts_match_the_cli(java_host, tmp_path, max_attempts, expected):
    bounds = {"max_attempts": max_attempts, "spend_cap": 10, "eval_cap": 100, "runs": 1}
    tag = f"compat-{max_attempts}".replace(".", "-")
    cli_cfg = _write(tmp_path / "cli.json", _config(java_host, tmp_path / "store-cli", bounds=bounds))
    cli_result = json.loads(_cli(["run-campaign", "--config", cli_cfg], tmp_path).stdout)
    mcp_cfg = _write(tmp_path / "mcp.json", _config(java_host, tmp_path / "store-mcp", bounds=bounds))

    async def scenario(session, init):
        return await session.call_tool("run_campaign", {"config": mcp_cfg})

    result = _json(_mcp(scenario))
    assert cli_result["outcome"] == expected  # the parent commit's behaviour
    assert result == cli_result


@needs_java
def test_client_accept_equals_the_cli_and_needs_a_real_approval(java_host, tmp_path):
    from test_java_host import _approval

    # One campaign per accept: a completed adjudication closes the campaign (loop.CampaignClosed).
    def prepared(name):
        cfg = _write(tmp_path / f"{name}.json", _config(java_host, tmp_path / f"store-{name}", campaign_id=name))
        return cfg, json.loads(_cli(["run-campaign", "--config", cfg], tmp_path).stdout)["selected_id"]

    wrong_cfg, wrong_selected = prepared("mcp-mismatch")
    right_cfg, right_selected = prepared("mcp-match")
    unapproved = _write(tmp_path / "wrong.json", _approval(wrong_selected, code_hash="other-code"))
    approved = _write(tmp_path / "ok.json", _approval(right_selected))

    async def scenario(session, init):
        first = await session.call_tool("accept", {"config": wrong_cfg, "approval": unapproved})
        second = await session.call_tool("accept", {"config": right_cfg, "approval": approved})
        return first, second

    first, second = _mcp(scenario)
    assert _json(first) == {"outcome": "not_updated", "candidate_id": wrong_selected}
    assert _json(second) == {"outcome": "updated", "candidate_id": right_selected}
    assert right_selected in _applied(java_host)  # the mismatched call left it unapplied (not_updated)


@needs_java
def test_stdout_carries_protocol_messages_only(java_host, tmp_path):
    cfg = _write(tmp_path / "cfg.json", _config(java_host, tmp_path / "store"))
    proc = subprocess.Popen(SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, cwd=tmp_path)

    def send(message):
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
          "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                     "clientInfo": {"name": "test", "version": "0"}}})
    first = json.loads(proc.stdout.readline())
    send({"jsonrpc": "2.0", "method": "notifications/initialized"})
    send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
          "params": {"name": "run_campaign", "arguments": {"config": cfg}}})
    second = json.loads(proc.stdout.readline())
    proc.stdin.close()
    rest = proc.stdout.read()
    stderr = proc.stderr.read()
    assert proc.wait(timeout=60) == 0

    frames = [first, second] + [json.loads(line) for line in rest.splitlines() if line.strip()]
    assert all(frame["jsonrpc"] == "2.0" for frame in frames)
    assert [frame["id"] for frame in frames] == [1, 2]
    assert json.loads(second["result"]["content"][0]["text"])["outcome"] == "selected"
    # The run's own log lines went to stderr, not between the protocol frames.
    assert "rsi-kernel run-campaign" in stderr


def test_console_script_is_declared():
    from importlib.metadata import entry_points

    scripts = {e.name: e.value for e in entry_points(group="console_scripts")}
    assert scripts.get("rsi-kernel-mcp") == "rsi_kernel.mcp_server:main"


def test_console_script_without_the_extra_exits_1_with_a_clear_error(tmp_path):
    code = """
import sys

class Block:
    def find_spec(self, name, path=None, target=None):
        if name == "mcp" or name.startswith("mcp."):
            raise ModuleNotFoundError(name)
        return None

sys.meta_path.insert(0, Block())
from rsi_kernel.mcp_server import main

sys.exit(main())
"""
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=60, cwd=tmp_path)
    assert r.returncode == 1, (r.stdout, r.stderr)
    assert "rsi-kernel[mcp]" in r.stderr and "Traceback" not in r.stderr
    assert r.stdout == ""


def test_core_package_never_imports_mcp():
    code = "import sys, rsi_kernel, rsi_kernel.cli; assert not [m for m in sys.modules if m.split('.')[0] == 'mcp']"
    subprocess.run([sys.executable, "-c", code], check=True, capture_output=True, timeout=60, cwd=ROOT)


@needs_java
def test_client_accept_waits_for_the_owner_approval_file(java_host, tmp_path):
    # Issue #60: accept files approval-request.json and blocks until the approval exists.
    import threading
    import time

    store = tmp_path / "store-wait"
    cfg = _write(tmp_path / "wait.json", _config(java_host, store, campaign_id="mcp-wait"))
    selected = json.loads(_cli(["run-campaign", "--config", cfg], tmp_path).stdout)["selected_id"]
    approval = tmp_path / "owner.json"

    def owner():
        request = store / "approval-request.json"
        deadline = time.monotonic() + 60
        while not request.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        filed = json.loads(request.read_text())
        assert not approval.exists()
        temp = approval.with_name(approval.name + ".tmp")  # publish atomically, as the docs say
        temp.write_text(json.dumps({**{k: filed[k] for k in ("candidate_hash", "evaluator_hash",
                                                              "data_hash", "code_hash")}, "approver": "owner"}))
        os.replace(temp, approval)

    writer = threading.Thread(target=owner)
    writer.start()

    async def scenario(session, init):
        return await session.call_tool("accept", {"config": cfg, "approval": str(approval)})

    result = _mcp(scenario)
    writer.join(60)
    assert _json(result) == {"outcome": "updated", "candidate_id": selected}
    assert selected in _applied(java_host)
