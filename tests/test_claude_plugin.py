"""Issue #51: the Claude Code plugin that registers the MCP server (design §4.1).

The plugin is data only: a manifest and `.mcp.json`, no hooks, commands, agents,
credentials or env. The checks below pin the exact key set, so a later edit that
smuggles in a component fails here rather than silently widening the plugin.
The vendor validator runs when the `claude` CLI is on PATH and skips when it is
not, so a CI job without the CLI covers the key sets only.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugin"

MANIFEST_KEYS = {"name", "description", "version"}
MCP_ENTRY_KEYS = {"command"}


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def check_plugin(root):
    """Assert the plugin at `root` is exactly one MCP server and no other component."""
    manifest = _json(root / ".claude-plugin" / "plugin.json")
    assert set(manifest) == MANIFEST_KEYS
    assert manifest["name"] == "rsi-kernel"
    assert manifest["description"]
    # Version tracks the package, so a release bump cannot leave the plugin stale.
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert f'version = "{manifest["version"]}"' in pyproject

    servers = _json(root / ".mcp.json")["mcpServers"]
    assert list(servers) == ["rsi-kernel"]
    entry = servers["rsi-kernel"]
    # The installed console script (pyproject [project.scripts]), not a bundled
    # script: the plugin ships no code and no paths into a checkout. `command`
    # alone means no args, no env, no type and no relative path.
    assert set(entry) == MCP_ENTRY_KEYS
    assert entry["command"] == "rsi-kernel-mcp"


def test_manifest_and_server_entry():
    check_plugin(PLUGIN)


def test_no_components_beyond_the_mcp_server():
    # Anything here would be a second capability the issue did not ask for.
    assert sorted(p.name for p in PLUGIN.iterdir()) == [".claude-plugin", ".mcp.json", "README.md"]


@pytest.mark.parametrize(
    "injection",
    [
        # An inline component the manifest would otherwise load as a capability.
        ("plugin.json", {"hooks": {"PostToolUse": []}}),
        # A second channel for a secret or an environment override.
        (".mcp.json", None),
    ],
)
def test_check_plugin_fails_on_an_injected_key(tmp_path, injection):
    """The key-set assertions can fail; a copy that gains a key is rejected."""
    target, extra = injection
    root = tmp_path / "plugin"
    shutil.copytree(PLUGIN, root)
    path = root / ".claude-plugin" / "plugin.json" if target == "plugin.json" else root / ".mcp.json"
    data = _json(path)
    if extra is None:
        data["mcpServers"]["rsi-kernel"]["env"] = {"EXTRA": "1"}
    else:
        data.update(extra)
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(AssertionError):
        check_plugin(root)


@pytest.mark.skipif(shutil.which("claude") is None, reason="the claude CLI is not on PATH")
def test_vendor_validator_passes():
    # https://code.claude.com/docs/en/plugins/cli-reference#plugin-validate
    result = subprocess.run(
        ["claude", "plugin", "validate", str(PLUGIN)],
        capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Validation passed" in result.stdout
