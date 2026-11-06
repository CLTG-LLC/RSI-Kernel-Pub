# Plug-and-play exit evidence at one frozen commit

Issue #68. Every measurement below is at `main` commit `af2054c` (detached checkout, no local changes). Measured 2026-11-06 on an Apple-silicon Mac, macOS 26.6 (Darwin 25.6.0), `uv 0.13.4` (Homebrew), CPython 3.13.16 (uv-managed), OpenJDK 21.0.13 (Homebrew `openjdk@21`). There are no pass thresholds; each criterion is reported as observed. Evidence paths are relative to the run's `exit-evidence/` directory. Wall times are `/usr/bin/time -p` `real` seconds from single runs. Sections 3 and 4 cite campaign results measured at those runs' own pinned commits, each stated in the cited report.

Three claims are kept separate throughout:

| Claim | Status in this report |
|---|---|
| Capability demonstrated (the kernel runs a campaign and an approval-gated accept through the plug-in surfaces) | criteria 1, 2, 5, 6, 7 below |
| Continuation demonstrated (the same kernel bytes close campaigns on further tiers) | "continuation tested" in S4b (`docs/results/s4b-continuation.md`), which is a factual status, not a demonstrated claim; the cross-tier claim stays pending, criterion 3 |
| Retained second update demonstrated (a ratchet from an approved champion, parent → child) | not demonstrated (S4b: no second retained update), §4 |

## 1. Wheel in a clean venv, campaign plus accept from the console entry, no checkout present

Commands (wheel built from the pinned checkout; everything after runs from a directory with no source checkout, `git rev-parse` there fails with `not a git repository`):

```sh
uv build --out-dir exit-evidence/w1/dist                # in the pinned checkout
uv venv --seed --python 3.13 venv
venv/bin/pip install dist/rsi_kernel-0.1.0-py3-none-any.whl
venv/bin/python -c 'import rsi_kernel; print(rsi_kernel.__file__)'
./run.sh                                                # quickstart (a), verbatim, in run-a/
```

`run.sh` activates the venv, starts a stdlib loopback host, writes the quickstart (a) config with that host's port, then runs `status`, `run-campaign`, `status`, `accept --approval approval.json` in the background, waits for `store/approval-request.json`, writes `approval.json` with the quickstart's one-line `os.replace` publish, waits for `accept`, and runs `status` again. The host (`w1/py_host.py`) is evidence-only, not repository code: the `FakeHost` handler of `tests/test_cli.py` at this commit as a standalone script (champion `Use alpha.`, score 1.0 when the text contains `beta`, else 0.5, `/apply` record-only).

| Observation | Value | Evidence |
|---|---|---|
| Wheel | `rsi_kernel-0.1.0-py3-none-any.whl`, SHA-256 `56ae8dcad1d5d77b6bd24f944ecff2cf5398097068a08431b6a5a84cab164c16` | `w1/c1-build.log`, `w1/dist/` |
| `rsi_kernel.__file__` | `<venv>/lib/python3.13/site-packages/rsi_kernel/__init__.py` | `w1/run-a/rsi_kernel_file.txt` |
| `which rsi-kernel` | `<venv>/bin/rsi-kernel` | `w1/run-a/run.log` |
| `status` (before) | exit 0, `{"acceptance": null, "approval_request": null, "campaign": null}` | `w1/run-a/run.log` |
| `run-campaign` | exit 0, `{"outcome": "selected", "stop_reason": "attempts", "attempts": 1, "evaluator_items_used": 4, ...}` | `w1/run-a/run.log` |
| `status` (after campaign) | exit 0, carries `approval_request` with `candidate_hash` `489e4f3f…9ebc39` | `w1/run-a/run.log` |
| `accept` | exit 0, `{"outcome": "updated", "candidate_id": "489e4f3f…9ebc39"}` | `w1/run-a/run.log` |
| `status` (after accept) | exit 0, `acceptance.outcome` `updated` | `w1/run-a/run.log` |
| Host `/applied` | `["489e4f3f…9ebc39"]` | `w1/run-a/run.log` |
| Store contents | `approval-request.json`, `campaign-quickstart.json`, `decisions.jsonl`, `outcomes.jsonl`, `private/`, `public/` | `w1/run-a/store/` |

## 2. Java host: get_artifact / evaluate / run_campaign / accept / apply, mismatched approval, kernel hashes

Commands:

```sh
export PATH=/opt/homebrew/opt/openjdk@21/bin:$PATH
javac -d java-classes examples/java-host/EvaluatorHost.java   # from the pinned checkout
./java_run.sh run-b pos        # matching approval
./java_run.sh run-b-neg neg    # mismatched approval, fresh state dir
```

`java_run.sh` starts `java -cp java-classes EvaluatorHost 0`, writes the same config as criterion 1 with `host_url` set to the Java port, probes `GET /artifact` and `GET /count`, runs `rsi-kernel run-campaign` and `rsi-kernel accept --approval approval.json` from the same wheel venv, publishes the approval file atomically (`neg`: `candidate_hash` replaced by the SHA-256 of `not-the-candidate`, the other three hashes copied from the request), runs `status`, probes `/count` and `/applied`, then stops the Java process by its PID.

| Observation | Matching approval (`run-b`) | Mismatched approval (`run-b-neg`) |
|---|---|---|
| `javac` | 0.40 s, exit 0 (`w1/c2-javac.log`) | same classes |
| `GET /artifact` | `{"media_type":"text/plain","components":{"SKILL.md":"VXNlIGFscGhhLg=="}}` | same |
| `run-campaign` | exit 0, `selected`, `evaluator_items_used` 4, `champion_id` `f21a1dbc…42cf448`, 0.05 s | identical output |
| `/count` after campaign | 4 | 4 |
| `accept` | exit 0, `{"outcome": "updated"}`, 1.05 s | exit 0, `{"outcome": "not_updated"}`, 1.05 s |
| `/count` after accept | 8 (adjudication split) | 8 |
| `/applied` | `["489e4f3f…9ebc39"]` | `[]` |
| Evidence | `w1/run-b/run.log` | `w1/run-b-neg/run.log` |

The mismatched approval is rejected as `not_updated` with exit code 0. Stdout contains the JSON result with `candidate_id` and `outcome: "not_updated"`; stderr reports `rsi-kernel accept quickstart: not_updated`, without a mismatch-specific diagnostic. `apply` is not called (`/applied` empty).

`champion_id` `f21a1dbc…42cf448` is the same in the Python-host and Java-host runs; both hosts serve the champion `Use alpha.`.

**Kernel file hashes.** SHA-256 of every installed `site-packages/rsi_kernel/*.py` (12 files) was taken once after install and before and after each of the three runs (`hash_kernel.sh`). All seven lists are byte-identical (`w1/hashes-initial.txt`, `w1/run-a/hashes-{before,after}.txt`, `w1/run-b/hashes-{before,after}.txt`, `w1/run-b-neg/hashes-{before,after}.txt`). The installed files also equal `src/rsi_kernel/*.py` in the pinned checkout (`w1/hashes-checkout-src.txt`).

**Operations not driven by the Java host as shipped.** `EvaluatorHost.java` serves the three callbacks (`/artifact` line 49, `/evaluate` line 48, `/apply` line 50); `main` (lines 45–56) only starts the HTTP server and contains no process launch. `run_campaign` and `accept` were invoked from the shell via the `rsi-kernel` console entry, not by Java code. Of the five operations named in the criterion, `get_artifact`, `evaluate` and `apply` were exercised against the Java host; `run_campaign` and `accept` were driven by the shell against it.

## 3. Same kernel bytes close campaigns on skill, memory and harness-code tiers

Pending (E1c running). Context and tool routing tiers: untested.

- Skill tier: S4 closed `updated` for `task_group_001` and `task_group_003` on the owner's hash-bound approval, and `no_improvement` for `task_group_002` (`docs/results/gdpevo-pilot.md`).
- Memory tier: S5b closed `updated` for `task_group_001`, `no_improvement` for `task_group_002`, and an operational STOP for `task_group_003` (`docs/results/e1a-s5b-evaluate-first.md`).

## 4. One ratchet from an approved champion

Measured by S4b (`docs/results/s4b-continuation.md`, issue #48) at that run's pinned commit `16ac7fe7d110623ae7a990d6e96a235aca516c97`, under the frozen pre-registration `docs/prereg-gdpevo-pilot.md` as amended by `docs/prereg-s4b-addendum.md`. S4b ran one campaign per paired group from that group's approved S4 champion, loaded through the existing hash-checked loader; `task_group_002` has no approved champion (S4 closed it `no_improvement`) and is excluded.

| Observation | Value |
|---|---|
| Starting champion, `task_group_001` | approved S4 candidate `3ef20ac564f77e7276361ac1305b3dbded320e6df258326f4102d59d3bc1688c`; champion-file sha256 `bea09d29f38484f2616a98a8de631e5b1e18530ddfa54500f868041955c80be3` |
| Starting champion, `task_group_003` | approved S4 candidate `96f5e060365012822c6914bdddfdd7b45922d41b6e49c85d16408ecb5e2dfc10`; champion-file sha256 `1d1065e73893ffbc5a0b99e572ff6f03cab7040cfdaf43b1f5e22b0f130258c0` |
| Lineage parent → child | every selected candidate's `parent_ids` equals that group's champion id (in `campaign.json` `selected` and in every `public/candidates.jsonl` row), so the chain parent → child is recorded |
| Pre-registered status | **continuation tested** (a factual status, not an outcome) |
| Terminal outcome, both groups | **no second retained update** (`failed_gate`: adjudication retention not met, −0.027778 in each group); no approval request written |
| Approval and `apply(hash)` | none: no approval was requested, so nothing was approved or applied |

Criterion 4 has two halves, reported separately: the campaign started from an approved champion with the lineage recorded, and no second update was retained. The dev selection was a tie in `task_group_001` (paired dev delta 0.000000) and +0.013072 in `task_group_003`; the holdout split moved +0.016604 overall (report-only, not a gate) and did not change the outcome. Keeping the champion is not counted as success.

## 5. E0 denial tests and T3 checks green

Command, in the pinned checkout:

```sh
CI=true uv sync --locked -q                 # 1.56 s, exit 0
CI=true uv run pytest -q -rA                # 179.47 s, exit 0
```

Result: `708 passed, 2 skipped in 178.37s`. The two skips are the opt-in live model smokes (`tests/adapters/test_gdpevo_code_live.py:44`, `tests/adapters/test_gdpevo_solver_live.py:21`, both `opt in with RSI_LIVE_GDPEVO=1; never CI`). Full output: `w1/c5-pytest.log`, sync: `w1/c5-sync.log`.

Test ids as pytest printed them (all `PASSED`), grouped by the property each test asserts in its body:

| Property | Test ids |
|---|---|
| E0: reads of adjudication, holdout, private and approval paths denied; writes to the dev file, approval file and private results file denied; secret environment variable inaccessible; all three configured network probes denied; protected hashes unchanged | `tests/e0/test_isolation.py::test_hostile_proposer_is_denied_and_protected_state_unchanged` |
| E0: dev data readable inside the container | `tests/e0/test_isolation.py::test_dev_data_is_readable_inside_container` |
| E0: proposer argv has no network, allowlisted env, two mounts | `tests/e0/test_proposer_runtime_args.py::test_argv_has_no_network_allowlisted_env_and_only_two_mounts` |
| E0: argv validation | `tests/e0/test_proposer_runtime_args.py::test_invalid_env_names_rejected[]`, `[A=B]`, `[1BAD]`, `[a b]`; `::test_mount_source_with_comma_rejected`; `::test_same_dir_for_dev_and_output_rejected`; `::test_nested_dev_and_output_dirs_rejected[root/dev-root]`, `[root-root/out]` |
| GDPevo protected mounts (answers, eval scripts, judge answers, eval workspace) denied | `tests/adapters/test_gdpevo_isolation.py::test_gdpevo_e0_protected_mounts_denied[...]`, 30 parametrized ids (`dev_data_dir-*` and `output_dir-*`), listed in `w1/c5-pytest.log` |
| T3: candidate cannot read gold/eval (`/trusted/eval`, `/trusted/output` absent), no network (public-address probe and both synthetic service-alias probes fail), non-root (`uid == host uid != 0`), input read-only | `tests/adapters/test_gdpevo_code_container.py::test_real_nonroot_reference_change_and_network_boundary` |
| T3: trusted command runs as host uid without candidate code | `tests/adapters/test_gdpevo_code_container.py::test_real_trusted_command_runs_as_host_uid_without_candidate_code[--help]`, `[--config=x]`, `[resume]` |
| T3: cannot outlive its timeout (owned container removed) | `tests/adapters/test_gdpevo_code_container.py::test_real_timeout_removes_the_owned_synthetic_container`; `tests/adapters/test_gdpevo_code.py::test_timeout_removes_only_owned_container[logic]`, `[agent]`, `[grade]`, `[sanity]` |
| T3: root host refused | `tests/adapters/test_gdpevo_code.py::test_root_host_refused_before_external_commands`; `::test_nonroot_limits_fixed_code_mapping_and_trusted_codex` |
| T3: gold not mounted for the solver | `tests/adapters/test_gdpevo_solver_docker.py::test_grader_output_mount_is_readonly_and_solver_never_sees_it`; `::test_task_without_gold_gets_no_output_mount` |

The container tests ran against Docker on this machine (`CI=true` makes a missing Docker image a failure, not a skip: `tests/adapters/test_gdpevo_code_container.py` fixture `synthetic_image`, `tests/e0/test_isolation.py` `_reason` check).

## 6. Claude plugin validator and one MCP session

Commands (from a venv with the `[mcp]` extra, wheel built from the pinned checkout):

```sh
claude plugin validate plugin
rsi-kernel run-campaign --config campaign.json          # quickstart (a) config, loopback host; no accept, no approval file
claude --plugin-dir plugin mcp list
claude -p --plugin-dir plugin --allowedTools 'mcp__plugin_rsi-kernel_rsi-kernel__status' \
  --output-format json "Call the rsi-kernel status tool with config campaign.json and print its raw result."
rsi-kernel status --config campaign.json                 # direct comparison
```

| Observation | Value | Evidence |
|---|---|---|
| Claude Code | 2.1.284 | `w2/C6.md` |
| `pip install '<wheel>[mcp]'` | exit 0, 15.81 s (cold cache), 30 packages, `mcp 2.3.0` | `w2/03-install.log` |
| `claude plugin validate` | exit 0, 0.60 s, "Validation passed with warnings", 1 warning (no `author` field) | `w2/04-plugin-validate.log` |
| `mcp list` | `plugin:rsi-kernel:rsi-kernel: rsi-kernel-mcp - Connected`, 38.05 s (includes health checks of the user's other MCP servers) | `w2/08-mcp-list.log` |
| Session | exit 0, 18.46 s, `is_error` false, 2 turns, no permission denials | `w2/09-session.json` |
| Tool calls in the session | exactly one: `mcp__plugin_rsi-kernel_rsi-kernel__status` with the config path, and its `tool_result` | `w2/10-session-transcript.jsonl` |
| Session result vs `rsi-kernel status` | equal as JSON objects (`campaign`, `approval_request` equal; `acceptance` null in both); text differs only in key order and indentation | `w2/11-status-cli-compare.json` |

The session used the user's normal Claude configuration, not a throwaway `CLAUDE_CONFIG_DIR`. The command explicitly allowed the `status` tool without prompting, and the transcript records exactly one invocation of that tool; this does not establish that other tools were unavailable or disallowed. `accept` was not run in this criterion, and no approval file was written.

## 7. Setup steps, dependencies, wall time

| Step | Command | Wall time | Evidence |
|---|---|---|---|
| 1. Build wheel | `uv build` | 0.43 s | `w1/c1-build.log` |
| 2. Create venv | `uv venv --seed --python 3.13 venv` | 0.02 s | `w1/c1-venv.log` |
| 3. Install wheel, core | `pip install <wheel>` | 2.11 s | `w1/c1-pip-install.log` |
| 4. Run quickstart (a): host start, 5 CLI calls, owner approval | `./run.sh` | 2.38 s total; `run-campaign` 0.04 s, `accept` 1.05 s (includes the one-second approval poll) | `w1/run-a/run.log` |
| Java host compile (quickstart (b)) | `javac` | 0.40 s | `w1/c2-javac.log` |
| Java host run, matching approval | `./java_run.sh run-b pos` | 3.16 s total | `w1/run-b/run.log` |
| Install wheel with `[mcp]` extra, fresh venv | `pip install '<wheel>[mcp]'` | 13.93 s (downloads included) | `w1/c7-pip-install-mcp.log` |

Steps 1–4 sum to 4.94 s.

| Dependency count | Value | Evidence |
|---|---|---|
| `pip list` packages, core venv | 2 (`pip` 26.3, `rsi-kernel` 0.1.0); 0 runtime dependencies (`dependencies = []`) | `w1/c1-pip-list.txt` |
| `pip list` packages, `[mcp]` venv | 30 (core's 2 included; `mcp` 2.3.0) | `w1/c7-pip-list-mcp.txt` |
| Java side | JDK 21 only | `examples/java-host/EvaluatorHost.java` imports |
| `rsi-kernel-mcp` without the extra | exit 1, prints `pip install 'rsi-kernel[mcp]'` | `w1/c7-mcp-without-extra.log` |

## Not covered

- Criterion 3 (pending the E1c run); the memory and skill tiers are cited from their merged reports in that section.
- Criterion 4 does not demonstrate a retained second update: S4b recorded the lineage and ended `failed_gate` in both groups, so no second approval, `apply(hash)` or champion change exists from it.
- Toy keyword task on loopback only; says nothing about evaluation quality or real hosts.
- Single runs; no repeat timings.
