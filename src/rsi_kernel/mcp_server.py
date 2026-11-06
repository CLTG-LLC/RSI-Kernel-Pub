"""MCP stdio server over the B1 control functions (issue #50, design §4.1).

Optional extra: `pip install 'rsi-kernel[mcp]'` installs the official Python SDK
(https://github.com/modelcontextprotocol/python-sdk); the console script
`rsi-kernel-mcp` exits 1 with a clear message without it. The core package never
imports `mcp`, so this module keeps every SDK import inside `main()` and
`_tool_error()`.

Tools are the B1 functions unchanged — `run_campaign`, `accept`, `status` — each
taking the same `--config` path (and `accept` the approval path) and returning the
same JSON object as the console entry. There is no approval-creation tool and no
shell or filesystem tool. Transport is stdio, so stdout carries protocol messages
only and logs go to stderr:
https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
Evaluator callbacks stay on the B1 HTTP bridge; this server only starts a session.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Callable

from . import cli


def _log(message: str) -> None:
    print(f"rsi-kernel-mcp {message}", file=sys.stderr, flush=True)


def _tool_error(message: str) -> Exception:
    from mcp.server.mcpserver.exceptions import ToolError

    return ToolError(message)


def _call(name: str, operation: Callable[[], dict]) -> dict:
    """Run one B1 operation; report an expected failure as an MCP tool error."""
    try:
        return operation()
    except Exception as error:  # malformed config, host failure, stale state
        _log(f"{name} failed: {type(error).__name__}: {error}")
        raise _tool_error(f"{type(error).__name__}: {error}") from error


def _config(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def run_campaign(config: str) -> dict:
    """Run one campaign from the config file at `config` and return its result JSON."""
    return _call("run_campaign", lambda: cli.cmd_run_campaign(_config(config)))


def accept(config: str, approval: str | None = None) -> dict:
    """Apply the campaign's selected candidate if the approval record at `approval` matches."""
    return _call("accept", lambda: cli.cmd_accept(_config(config), approval))


def status(config: str) -> dict:
    """Read the campaign state file named by the config at `config` and return it."""
    return _call("status", lambda: cli.cmd_status(_config(config)))


TOOLS = (run_campaign, accept, status)


def main() -> int:
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError as error:
        _log(f"the MCP SDK is not installed: pip install 'rsi-kernel[mcp]' ({error})")
        return 1
    server = MCPServer("rsi-kernel")
    for tool in TOOLS:
        server.add_tool(tool, name=tool.__name__)
    _log("serving run_campaign, accept and status over stdio")
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
