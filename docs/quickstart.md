# Adopter quickstart

Three ways to drive the kernel, each run end to end. **All numbers: measured on
2026-11-06, macOS arm64, this machine.** No targets, no thresholds. CPython
3.13.16 (uv-managed), `uv 0.13.4`, OpenJDK 21.0.13 (Homebrew `openjdk@21`),
macOS Darwin 25.6.0. The artifact throughout is one `SKILL.md` text component;
the host scores a dev item by whether the text contains its keyword.

## (a) Python / CLI host

Five setup steps, then four commands; the core package has no runtime
dependencies.

```sh
uv build --wheel         # -> dist/rsi_kernel-0.1.0-py3-none-any.whl
uv venv --seed --python 3.13 "$TMPDIR/rsi-venv"   # --seed puts pip in the venv
. "$TMPDIR/rsi-venv/bin/activate"
pip install dist/rsi_kernel-0.1.0-py3-none-any.whl
rsi-kernel --help
```

`uv venv --python 3.13` downloads a managed interpreter when none is installed
(`uv python install 3.13` does it explicitly if downloads are disabled). Keep
the venv active for the commands below: activation puts that venv first on
`PATH`, which is how the bare `rsi-kernel` and `pip` calls resolve.

The host supplies design §4's three callbacks — `get_artifact`, `evaluate`,
`apply` — over loopback HTTP (numbers only: `127.0.0.1`; names such as
`localhost` go to the resolver and are rejected). Any local process speaking
those routes is enough; the tests' `FakeHost` (`tests/test_cli.py`, about 50
lines of stdlib `http.server`) is the shortest example.

```json
{
  "campaign_id": "quickstart", "host_url": "http://127.0.0.1:<port>", "store": "store",
  "component_ids": ["c1"], "evaluator_hash": "e", "code_hash": "k",
  "splits": {"splits": [
    {"name": "dev", "purpose": "dev", "selection_eligible": true, "item_ids": ["d0", "d1"]},
    {"name": "adjudication", "purpose": "adjudication", "selection_eligible": false, "item_ids": ["a0", "a1"]}]},
  "bounds": {"max_attempts": 1, "spend_cap": 1, "eval_cap": 100, "runs": 1},
  "proposals": [{"media_type": "text/plain", "components": {"SKILL.md": "<base64 'Use beta.'>"}}]
}
```

`selection_eligible` must be a boolean on every split and `true` only on a `dev`
split (`src/rsi_kernel/splits.py`); `item_ids` must be disjoint across splits.

```sh
rsi-kernel status       --config campaign.json   # -> {"campaign": null, ...} before any run
rsi-kernel run-campaign --config campaign.json   # -> {"outcome": "selected", ...}
rsi-kernel status       --config campaign.json   # now carries "approval_request"
rsi-kernel accept       --config campaign.json --approval approval.json &   # files the request, then waits
until [ -f store/approval-request.json ]; do sleep 1; done
python -c 'import json, os; r = json.load(open("store/approval-request.json")); f = open("approval.json.tmp", "w"); json.dump({**{k: r[k] for k in ("candidate_hash", "evaluator_hash", "data_hash", "code_hash")}, "approver": "owner"}, f); f.close(); os.replace("approval.json.tmp", "approval.json")'   # the owner's step
wait                                             # accept continues -> {"outcome": "updated", ...}
```

Same shell as above: with the venv active, `rsi-kernel` and `python` are on
`PATH`. `store` is relative to the working directory.

**Order: request, approval, then accept continues** (#60). `accept` adjudicates,
writes the `ApprovalRequest` to `store/approval-request.json` (the same hashes
`status.approval_request` reports) and waits, polling once a second with no
timeout, until the approval file exists. The owner writes `approval.json` from
that request — its `candidate_hash`, `evaluator_hash`, `data_hash` and
`code_hash` plus an `approver` — and `accept` continues: matching hashes give
`updated`, a malformed or mismatched file gives `not_updated`. Without
`--approval` it waits for `store/approval.json`. Publish the file atomically, a
sibling temp file then
[`os.replace`](https://docs.python.org/3/library/os.html#os.replace): `accept`
reads it as soon as the name appears, so a half-written file gives `not_updated`.
The campaign is closed when
adjudication runs, before the wait: stopping `accept` during the wait leaves it
closed with no outcome, and a later `accept` raises `CampaignClosed`, so write
the approval rather than restarting.

**Approvals are written by the host or owner and kept out of agent reach.** The
kernel only reads the record: matching hashes prove it is internally consistent,
not who wrote it, so keeping the file where the agent cannot write it is an
operational duty on the host.

| Measured step (one fresh venv) | Observed |
|---|---|
| `uv build --wheel` | 2.05 s real (4.50 s including a cold build env) |
| `uv venv --seed --python 3.13` | 0.02 s real; seeds `pip` 26.3 |
| `pip install <wheel>`, core | 1.02 s real; 0 runtime dependencies |
| `pip list` after core install | 2 packages (`pip`, `rsi-kernel`) |
| `rsi-kernel status` / `run-campaign` / `accept` | 0.06–0.10 s / 0.05–0.52 s / 0.05–0.09 s real (`accept` measured before #60; it now also includes the owner's approval time) |

The first `run-campaign` includes cache warm-up. It returned `{"outcome":
"selected", "stop_reason": "attempts", "attempts": 1, "evaluator_items_used": 4}`
(2 dev items x champion + candidate); `accept` returned `{"outcome": "updated"}`.
State lands in `store/`: the campaign file, `outcomes.jsonl`, `decisions.jsonl`,
`public/`, `private/`.

## (b) A Java or other-language host

Point the same CLI at your host; the kernel is unchanged and only `host_url`
differs. Two setup steps, then the same four commands.

```sh
javac -d "$TMPDIR/java-classes" examples/java-host/EvaluatorHost.java   # 0.33 s real, javac 21.0.13
java -cp "$TMPDIR/java-classes" EvaluatorHost 0                        # prints "LISTENING <port>"
```

The worked example and the frozen contract — routes, bodies, reply shapes,
error codes, the `content_id` hash over decoded component bytes, and the
loopback/no-redirect rules — are [`examples/java-host/`](../examples/java-host/)
and [design §4.1](design.md#41-frozen-host-contract-for-non-python-hosts-issue-52);
the bridge callable is [`http_evaluator.py`](../examples/java-host/http_evaluator.py).
Measured: `run-campaign` 0.10 s, `accept` 0.06 s (before #60, excluding the owner's approval time), `/count` 4 items after the
campaign and 8 after acceptance (the adjudication split), `/applied` holding the
approved hash. Apply is record-only; the champion bytes are not swapped.

## (c) MCP and the Claude Code plugin

```sh
pip install 'rsi-kernel[mcp]'    # adds the official MCP SDK
rsi-kernel-mcp                   # stdio server; tools: run_campaign, accept, status
claude --plugin-dir ./plugin     # one session, from a checkout
```

The plugin launches `rsi-kernel-mcp` by name, so **start Claude from a shell
where the venv is active** (`. "$TMPDIR/rsi-venv/bin/activate"`) — without it
the server is not on `PATH` and the plugin connection fails. Without the extra,
`rsi-kernel-mcp` prints how to install it and exits 1. The three tools take the
same `config` path as the console entry, and `accept` also takes `approval`;
values and failures match the subcommands exactly
([§4.1 MCP surface](design.md#mcp-surface-issue-50-optional-extra)).

| Measured step | Observed |
|---|---|
| `pip install '<wheel>[mcp]'` | 0.19 s real (warm cache) |
| `pip list` after the `[mcp]` extra | 30 packages (`pip list` count, core's 2 included) |
| `rsi-kernel-mcp` initialize + `tools/list` + `status` | 0.22 s, 3 responses |
| `claude plugin validate ./plugin` | passed, 1 warning (no `author` field) |
| `claude --plugin-dir ./plugin mcp list`, throwaway `CLAUDE_CONFIG_DIR` | `rsi-kernel-mcp - Connected` |

The plugin declares no skills, commands, agents or hooks, and no `env`. It has
no approval-writing tool (see the boundary above), and campaign state belongs
outside the plugin root because `${CLAUDE_PLUGIN_ROOT}` changes on update.

## Scope

Smoke paths against toy tasks, on loopback: they show the commands run and the
contract is reachable, and say nothing about evaluation quality, real hosts or
deployment beyond loopback. The Java example is a trusted local example.
