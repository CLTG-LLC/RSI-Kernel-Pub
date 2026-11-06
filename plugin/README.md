# rsi-kernel Claude Code plugin

Registers the kernel's MCP server, the `rsi-kernel-mcp` console script, over
stdio. The plugin adds no skills, commands, agents or hooks; it only connects
three tools — `run_campaign`, `accept`, `status` — each taking the same config
file as the `rsi-kernel` console entry.

Layout follows the [plugin manifest reference](https://code.claude.com/docs/en/plugins/manifest-reference#standard-layout):
`.claude-plugin/plugin.json` holds the metadata, `.mcp.json` at the plugin root
holds the server entry.

## Install

The server needs the optional extra, so install the package into the same
environment Claude Code runs in:

```sh
pip install 'rsi-kernel[mcp]'
```

Then load the plugin. From a checkout, one session without installing it:

```sh
claude --plugin-dir ./plugin
```

Anything else (a marketplace, a `.zip`, `claude plugin install`) installs it the
same way; `claude plugin validate ./plugin` checks the package before you try.

## What it does not do

- **No approval-writing tool.** `accept` reads an `ApprovalRecord` JSON that the
  host or the owner wrote, and the plugin supplies no tool that writes one. That
  is the whole of what the plugin can say: `cli.py` reads whatever approval file
  it is handed, and hash matching shows the record is internally consistent, not
  who authored it. Keeping approval files where the agent cannot write them is an
  operational requirement on the host or owner, not a guarantee of this plugin.
- **State belongs outside the plugin root, by setup.** Put the config file outside
  the plugin directory and point its `store` outside as well; campaign state and
  the archive then land there, not next to the manifests. `${CLAUDE_PLUGIN_ROOT}`
  changes when the plugin updates, so nothing durable belongs in it. This is a
  setup requirement: the CLI does not enforce plugin-root exclusion, and a config
  naming a store inside the plugin root still runs.
- **No credentials.** The manifest and `.mcp.json` declare no `env` and no
  secrets.

## Manual check

`claude plugin validate ./plugin` is the vendor check. It runs when Claude Code
is installed on the machine; the test skips when `claude` is not on `PATH`, so a
CI job runs it only if it installs the CLI. To confirm
the server actually starts, use a throwaway config directory so the plugin is
never added to a real configuration:

```sh
CLAUDE_CONFIG_DIR=$(mktemp -d) claude --plugin-dir ./plugin mcp list
```

which prints `plugin:rsi-kernel:rsi-kernel: rsi-kernel-mcp - ✔ Connected` when
`rsi-kernel-mcp` is on `PATH` (install the extra into that environment first).
Session-only loading writes nothing to the user's settings
([flags that load a plugin for one session](https://code.claude.com/docs/en/plugins/cli-reference#flags-that-load-a-plugin-for-one-session)).
In an interactive session, the same check is `/mcp`.
