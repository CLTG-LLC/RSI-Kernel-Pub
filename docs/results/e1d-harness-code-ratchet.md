# E1d: a second harness-code (T3) campaign from the approved E1c champions

Issue #119. One campaign per group under the frozen pre-registration
`docs/prereg-gdpevo-pilot.md` as amended by `docs/prereg-e1d-addendum.md`, which
adopts `docs/prereg-s4-addendum.md` (trimmed final phase) and the E1c T3 contract
(`docs/prereg-e1c-harness-code-addendum.md` with `docs/prereg-e1c-amendment-1.md`
and `docs/prereg-e1c-amendment-2.md`) by reference. The champion of each group is
its approved E1c `solver.py` (addendum §2.1), so the lineage seed → approved E1c
candidate → E1d candidate is recorded in the run records. This is a diagnostic
feasibility and cost run, not a statistical claim and not an efficacy comparison.

Status: **terminal for both groups.** `task_group_003` closed at optimise
(`no_improvement`, no candidate); `task_group_001` ran its final phase and closed
`failed_gate` (`pilot-007-logs/final-task_group_001.out`
`{"task_group_001": "failed_gate"}`, empty stderr) on the zero-margin adjudication
rule. Optimise values are filled from the terminal optimise records and final
values from the final phase's observation and attempt records, each with its
source. No value in this report is left as a marker.

Pre-registered status lines (addendum §5):

| Status | Value |
|---|---|
| "continuation tested" (harness-code) | **yes** for `task_group_001` and `task_group_003`: the campaign started from the verified approved E1c champion — champion id, champion-file sha256, reconstructed id, prior acceptance `updated` and prior approval binding recorded in `pilot-007-logs/code-identity.txt` before the first solve (below). Factual, not an outcome. |
| Retained second update, `task_group_001` | **no second retained update**: final-phase adjudication `failed_gate` (acceptance outcome `failed_gate`; champion `0.6153845`, candidate `0.5897435`, Δ −0.025641, below the zero margin), no candidate retained, no approval request written (`pilot-007/final/task_group_001/observations.jsonl`, `pilot-007/task_group_001/acceptance.json`) |
| Retained second update, `task_group_003` | **no second retained update**: optimise outcome `no_improvement`, stop reason `attempts`, no candidate selected, so no final phase and no `acceptance.json` (`pilot-007/task_group_003/campaign.json`) |
| `task_group_002` | **excluded** (addendum §2.1: E1c selected no approved candidate; not restarted from the seed) |

A retained second update, if any, is `accept()` outcome `updated` in
`<group>/acceptance.json`; any other completed outcome is "no second retained
update" with the record's reason; an operational STOP is reported as a STOP, never
as a negative outcome. **A tie retained under the zero-margin rule is not an
improvement**, and no cumulative-improvement or compounding claim is made from a
second retained update (addendum §5).

### Evidence references

Run evidence paths are relative to the external run-evidence root, not this
repository. Fixed pre-run facts come from `pilot-config/config-e1d.json`,
`pilot-config/launch-e1d.sh`, `pilot-config/launch-e1d-final.sh`,
`pilot-config/e1d/`, `pilot-007-logs/code-identity.txt` and
`pilot-007-logs/smoke.log`. Result sections will cite
`pilot-007/<group>/{campaign.json,outcomes.jsonl,calls.jsonl,decisions.jsonl,public/results.jsonl}`,
`pilot-007/final/<group>/observations.jsonl`, `pilot-007/entropy.json` and
`pilot-007/<group>/{acceptance.json,approval-request.json,approval.json}`.
Optimise values below cite the first five; per-attempt timing, exit codes,
`failure.json` reasons and `measurement.json` usage come from
`pilot-007/<group>/evidence/<attempt>/` metadata files only. Final-phase and
acceptance references for `task_group_001`: `pilot-007/final/task_group_001/`
(`observations.jsonl`, `evidence/gdp-*/{attempt.json,attempt-timing.json,measurement.json}`)
and `pilot-007/task_group_001/acceptance.json`; there is no `approval-request.json`
or `approval.json` because no approval was requested. No private archive, score
file, task prompt, answer, evaluator, notes or candidate-source content was opened.

## Diagnostic only

At most two groups can have a candidate (addendum §2.1), so the paired tables can
reach the existing "at least two groups" reporting rule only at its lower bound;
with two groups the registered group bootstrap has only 4 ordered group draws. No
significance, power, independence or replication claim is made; a degenerate
estimator result is reported as-is, with no method switching. E1d rows are a
separate campaign record, not pooled with S4, S4b, S5b, S5c or E1c.

## What changed in this campaign (E1d addendum §2)

| Item | E1c (`pilot-005`) | E1d (`pilot-007`) |
|---|---|---|
| Starting champion | the frozen identity-passthrough seed `b95e33ea…`, all three groups | each group's **approved E1c candidate** (table below), loaded through the existing hash-checked `gdpevo_code.pilot.load_champion` |
| Groups with a campaign | 001, 002, 003 | 001, 003; 002 **excluded** |
| Lineage | none (seed) | every admitted candidate carries the approved E1c id in `parent_ids`; recorded, not asserted |
| Caps, rules, `CodeLimits`, trusted skill, timeout | as frozen | unchanged (addendum §2.2): 3 runs per task, `max_attempts` 3, `eval_cap` 36, 42-call spend cap per group, zero margin (ties pass), retention on adjudication only, 42 final solves per group with a candidate, holdout reported not gated, hash-bound owner approval per request, record-only `apply(hash)` |

## Identity

### Pin, run directory and groups

| Item | Value | Source |
|---|---|---|
| Code pin (first `main` commit containing the E1d addendum) | `5128c1cd562286d10e9a6d24b82555fa1d15bac6` | `pilot-007-logs/code-identity.txt` (`git_sha`) |
| Full source code hash (`_code_hash()`) | `3ecd61e0d0215e69a7fb3e03b47522490c3f4190d64ff2a3d58182f61e2be36f` | same |
| Kernel-only hash (`_code_hash(exclude=("adapters",))`) | `8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc` | same; equals the value the addendum §3 requires (E1c, S4b, S5c), checked by `launch-e1d.sh` before the smoke |
| Identity log file sha256 | `06cc21dd3d94873202339dccc91dfe02532babe04430244b7e992505b2300ca7` | sha256 of `pilot-007-logs/code-identity.txt` at report time |
| Execution-bound campaign `code_hash` | g001 `c03d21d4573974a494c10221b2c0674ff31a2212eeab59441dbd75a21087708e`; g003 `3eac3e5d78d991bcb1a6d50d242d18f69b9de09fc9d2b90a0fb519ef1020b4b8` (per group: binds champion, skill, limits, timeout) | `pilot-007/<group>/campaign.json` |
| Evaluator hashes per group | g001 `35068c70ba2ba7aded9f3cb0242f655a8dbbcf419f758a57602656cc46fdbed5`; g003 `dfd6a9f6e8f5f0ceb717cf1a3830a1d6054cae5298b8f7bbc8fdaa61dfb049cf`; equal in every `outcomes.jsonl` row of the group | same; `outcomes.jsonl` |
| Run directory | `pilot-007` | `config-e1d.json` `run_dir`; addendum §3 |
| Groups | `task_group_001`, `task_group_003` | `config-e1d.json` `champions`; `launch-e1d.sh` |
| Identity drift during the run | optimise: none; both campaigns `closed` with these identities and no STOP. Final phase g001: no drift — `failed_gate` with no `rebind.json` in `pilot-007/task_group_001/`, so the frozen champion, evaluator and campaign `code_hash` are the ones the final phase ran (`final_phase` STOPs on drift before any solve, `src/rsi_kernel/adapters/gdpevo/pilot.py:591–592`) | campaign records; `pilot-007-logs/task_group_00{1,3}.out`; `pilot-007-logs/final-task_group_001.out` |

The full source hash equals the E1c attempt-3 source hash recorded in
`docs/results/e1c-harness-code.md`; this is a recorded equality, not a claim that
the execution-bound campaign hash is unchanged.

### Champions (addendum §2.1)

| Group | Approved E1c `candidate_hash` (= reconstructed id) | Champion file | Champion file sha256 | `parent_ids` of loaded champion | E1c acceptance outcome | E1c approval `candidate_hash` |
|---|---|---|---|---|---|---|
| `task_group_001` | `d65e220b04815704a16935231cb50ef71778254f368d0855a577d43f2516b60a` | `pilot-config/e1d/task_group_001-solver.py` | `5335dca5dfa63dbc8a973c6da31ea4e7b60041c994615cd160ccc98a54ad7071` | empty (root `Candidate`) | `updated` | `d65e220b04815704a16935231cb50ef71778254f368d0855a577d43f2516b60a` |
| `task_group_003` | `7ca6c7160aa9b218c2776952e88aec5a84229eb71e086248071d48df7c1bc9bd` | `pilot-config/e1d/task_group_003-solver.py` | `180ea844bf75999ed8ea2cddea8490fdebfc5ef1753caf282b126f8af11d602e` | empty (root `Candidate`) | `updated` | `7ca6c7160aa9b218c2776952e88aec5a84229eb71e086248071d48df7c1bc9bd` |
| `task_group_002` | excluded | — | — | — | E1c `no_improvement` | — |

Source: `config-e1d.json` `champions[<g>]` `{path, sha256}` (file hashes recomputed
equal at report time); `pilot-007-logs/code-identity.txt` lines `champion_sha256`,
`reconstructed_id`, `champion_parent_ids`, `e1c_acceptance_outcome`,
`e1c_approval_candidate_hash` and `reconstruction verified`. The E1c parent of both
champions is the seed `b95e33ea6f9d2cc0450488afbb4fce1cd3fe65a131b781db5e4ed2ddcb41e374`
(addendum §2.1 table), retained in the E1c records rather than in the loaded object.

Campaign `champion_id`: g001 `d65e220b04815704a16935231cb50ef71778254f368d0855a577d43f2516b60a`,
g003 `7ca6c7160aa9b218c2776952e88aec5a84229eb71e086248071d48df7c1bc9bd`, each equal
to the approved E1c `candidate_hash`. Every admitted candidate (3 per group) carries
exactly that id as its only `parent_ids` entry, and g001's `selected.parent_ids` is
`[d65e220b…]`, so the records retain seed → approved E1c `solver.py` → E1d
candidate. Source: `campaign.json` (`champion_id`, `selected.parent_ids`),
`public/candidates.jsonl`, `outcomes.jsonl` `champion_id`.

### Frozen skill and limits (carried from E1c)

| Item | Value | Source |
|---|---|---|
| Trusted skill file (both groups) | `pilot-config/seed-SKILL.md`, sha256 `b0fe3906ded74360a0c639093f11128a851aada57d12cfa48ce235195c657283` | `config-e1d.json` `skills` |
| `CodeLimits` | Candidate-code container only: `cpus` 0.05, `memory_bytes` 45088768, `file_bytes` 784957. The trusted agent has no CodeLimits CPU, memory, swap or fsize limit. | `config-e1d.json` `code_limits`; E1c amendment 1 §2; `launch-e1d.sh` STOPs unless `file_bytes` is 784957 |
| Limits evidence binding | `csv_sha256` `5d349dca7d7314c06bc01c2cb321f2c7d861e5462277dd6e1c240ff8f75e6dfe`, `rule_sha256` `7dbaacadfab97eb2ed4728bb88980e7e8403a73c6569a6cdcffb06ac8e6f2eb8` | `config-e1d.json` `code_limits_evidence` |

### Launchers and configuration

| File | sha256 |
|---|---|
| `pilot-config/config-e1d.json` | `b531602d3caefab021c137f8bd1f803c088b21dec6852bc5faa76ad40a1836d4` |
| `pilot-config/launch-e1d.sh` | `51c1a7be285ac6f9cffa0e17864d437b88a983f415ff0f3a62ba6f0d5f5f50dc` |
| `pilot-config/launch-e1d-final.sh` | `5343d2c722214294b17608635201c13a3f22e9e74cdc7cccf3c570fea0764e3f` |

`launch-e1d.sh` runs the pre-run STOPs in the addendum §3 order (identity and
kernel-only hash; champion reconstruction; fresh live T3 smoke; exposure
reconciliation present) before optimising groups 001 and 003. `launch-e1d-final.sh`
runs the final phase at the same pinned checkout, with no rebind.

## Pre-run STOPs

| STOP (addendum §3) | Result | Evidence |
|---|---|---|
| (a) identity and kernel-only hash | passed: kernel-only hash `8ea2ae0a…` | `pilot-007-logs/code-identity.txt` |
| (a) champion reconstruction | passed, both groups: reconstructed id equals the approved E1c `candidate_hash`, root `Candidate`, E1c acceptance `updated`, E1c approval binds the champion | same |
| (b) fresh live T3 smoke at the pin | passed: **"1 passed in 151.93s (0:02:31)"**; `T3 agent OOM evidence: {"OOMKilled": false}`; evidence `e1d-smoke/attempts/gdp-33a8e86e`; frozen seed solver, not the champion (infrastructure check only) | `pilot-007-logs/smoke.log`, sha256 `60623f433f2429d6dd51e550ef8af37677c99b2e3c4723bd0075aedf22a073d4` |
| (c) exposure reconciliation recorded | passed: file present and non-empty | `pilot-config/e1d/e1d-exposure-reconciliation.md` (below) |
| (d) first campaign solve | started 2026-11-07 13:01:51 UTC in both groups, after (a)–(c); one calibration replay per group precedes it and is not a solve | `pilot-007/<group>/evidence/*/attempt-timing.json` |

The smoke log records "T3 memory peak: not recorded by CodeDockerSolver or Docker
inspect .State"; no peak value is claimed.

## Runtime pins

Carried unchanged from E1c (addendum §2.2). `git diff 126ba900 5128c1cd -- src uv.lock`
is empty, so the solver image Dockerfile, CLI asset pins, reasoning effort, solver
and evaluator timeouts are the E1c source unchanged. Verified in the optimise
records:

| Pin | Verified at run (optimise) |
|---|---|
| Served model identity | `gpt-6.1-sol` / `proxy` in all 72 optimise `measurement.json` receipts and the smoke receipt |
| Docker version and image platforms | `29.5.2`; task and solver images `linux/arm64` in all 74 optimise evidence directories (72 solves + 2 calibration replays) |
| Solver wall-time limit 3600 s | no attempt near it: longest optimise attempt 295.9 s (g001), 471.4 s (g003) |
| Spend cap 42 | 42/42 per group: 36 solver + 3 proposer + 3 `jev`; no retry rows |
| Evaluator cap 36 | 36/36 per group (`campaign.json` `evaluator_items_used`) |

Final-phase verification for g001, from the 43 directories under
`pilot-007/final/task_group_001/evidence/gdp-*` (42 solver attempts with an
`attempt.json`, plus one calibration replay directory `gdp-3f46903e` that holds only
`calibration-answer.json` and `calibration-score.json`): Docker `29.5.2` and image
platforms `linux/arm64` in all 43; served model `gpt-6.1-sol` / `proxy` in all 42
`measurement.json` receipts; longest attempt 319.3 s against the 3600 s solver
limit; `container_exit_code` 0 and `docker_attach_exit_code` 0 in all 42. The
calibration replay output itself was not opened (its score file is a grade
artifact); its pass is established by the control path, since `final_phase` calls
`_prerun` and STOPs unless the replay hash equals the frozen reference before any
observation is written. The final phase made 42 solver calls; the calibration replay
is a grading replay with no `measurement.json` in its directory, so it is not a
model call. There are no proposer or D2 calls, because final acceptance has no
optimiser.

## Dev campaign

Only dev scores guide proposals and selection; dev is not re-run in the final
phase. Aggregation and noise follow `docs/results/e1c-harness-code.md`: run mean
per task, equal-task group mean; `std@3` is population std (`ddof=0`) per task over
three runs, then mean across tasks. Neither noise nor dev delta is a retention
threshold.

### Champion dev rows and noise

| Group | Champion dev mean | Champion mean per-task `std@3` | Champion rows |
|---|---|---|---|
| `task_group_001` | `0.6531951111111111` | `0.05721326674452566` | 9 (3 dev tasks × runs 0/1/2) |
| `task_group_003` | `0.8419117647058824` | `0.0` | 9 (3 dev tasks × runs 0/1/2) |

Source: `public/results.jsonl` `score` fields of the champion's `candidate_id`
(per task run mean, equal-task mean; `std@3` = `statistics.pstdev` per task, then
mean). g003's champion dev mean equals the E1c dev mean recorded for the same
candidate; g001's differs from E1c's `0.6788361111111111`. Recorded, not
interpreted.

### Per group, selection and stop

| Group | Champion dev mean | Selected candidate dev mean | Selected candidate | Attempts | Attempt outcomes | Stop reason | Optimise outcome |
|---|---|---|---|---|---|---|---|
| `task_group_001` | `0.6531951111111111` | `0.7343916666666667` | `c40f1da395fe74e650f66924bb5ed466d198719c9a5f08e8a7fc2314808638ae` | 3 | a1 `dev_pass`, a2 `dev_pass`, a3 `dev_pass` | `attempts` | `selected`; status `closed` |
| `task_group_003` | `0.8419117647058824` | not applicable (no selected candidate) | none (no final phase) | 3 | a1 `dev_failure`, a2 `dev_regression`, a3 `dev_regression` | `attempts` | `no_improvement`; status `closed` |

Source: `campaign.json`, `outcomes.jsonl`, `public/results.jsonl`; both process
outputs (`pilot-007-logs/task_group_00{1,3}.out`) report the same outcome and stop
reason. These are optimise outcomes, not acceptance outcomes.

### Per attempt: admitted, evaluated, paired dev delta and lineage

| Group | Attempt | Candidate ID | `parent_ids` | Admitted | Refusal reason | Candidate evaluated | Recorded `mean_delta` | Selection |
|---|---|---|---|---|---|---|---|---|
| `task_group_001` | 1 | `8b2b053584c6dfbc966be6da417b89b723a4921aced2ef597a6213b36fa381c0` | `[d65e220b…]` | yes | not applicable | yes, 9 dev rows | `0.010826111111111116` | `dev_pass`; not selected |
| `task_group_001` | 2 | `c40f1da395fe74e650f66924bb5ed466d198719c9a5f08e8a7fc2314808638ae` | `[d65e220b…]` | yes | not applicable | yes, 9 dev rows | `0.08119655555555555` | `dev_pass`; **selected for final** (largest delta, strict `>`) |
| `task_group_001` | 3 | `8d23357638f1a430b62ef6d70184ec8f8a05ed99c5a7400dbe6986071129a626` | `[d65e220b…]` | yes | not applicable | yes, 9 dev rows | `0.025641` | `dev_pass`; not selected |
| `task_group_003` | 1 | `a70af55100272cffcd9e8c9be76ba2f5a4d6f0a8f06cf6a199a54f0075a43d0c` | `[7ca6c716…]` | yes | not applicable | 9 solves attempted; 4 valid rows, 5 failed `missing_prediction` | `null` | `dev_failure`; not selected |
| `task_group_003` | 2 | `cf252d4bb504c61c7257eb1a643c7f43104504808398ca8e2c497f9479f8e250` | `[7ca6c716…]` | yes | not applicable | yes, 9 dev rows | `-0.020016339869281047` | `dev_regression`; not selected |
| `task_group_003` | 3 | `4037e8db0a6b5f6e07309268aa8b4f454bfa4f9e645913ca7b33c1d612afeb1e` | `[7ca6c716…]` | yes | not applicable | yes, 9 dev rows | `-0.006535947712418302` | `dev_regression`; not selected |

A `dev_pass` is eligibility/selection evidence only, not retained improvement.
Every attempt starts from the same campaign champion; this is inter-campaign
continuation, not within-campaign incumbent updates (addendum §2.1).

Source: `outcomes.jsonl` (`candidate_id`, `mean_delta`, `outcome`),
`public/candidates.jsonl` (`parent_ids`), row counts per `candidate_id` in
`public/results.jsonl`. All 6 drafts were admitted; no admission refusal occurred.

g003 attempt 1 (`dev_failure`): 5 of its 9 dev solves (`train/001` × 3,
`train/003` × 2) ended with `failure.reason` `missing_prediction`, status `STOP`.
In each, the solver container and `docker attach` exited 0 after 300–390 s, but no
`answer.json` was written, which the Docker solver raises as
`_Stop("missing_prediction")` (`src/rsi_kernel/adapters/gdpevo/solver_docker.py:588`).
The dev comparison therefore blocks acceptance and the loop logs `dev_failure`
with `mean_delta` `null` (`src/rsi_kernel/loop.py:188–189`). Only the 4 valid rows
were archived, so g003 `public/results.jsonl` has 31 rows, not 36. Not an OOM,
`fsize` kill or timeout (below). Source: the five attempts' `failure.json` and
`attempt-timing.json`. The candidate source was not opened.

D2 records: 3 per group, 6 total, backend `jev`, model `jev-latest`; every
`answer.D2` equals `baseline_answer.D2` (`c1`). Source: `decisions.jsonl`. This
single-component agreement is not evidence that D2 improved selection. All 6 `jev`
call rows have `token_usage: null`: the pin `5128c1cd` predates D2 usage metering
(its `_MeteredBackend.decide` logs the call without usage), so null is expected
and is reported as null, not zero.

### Dev split table

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Paired estimator delta | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| dev | selection only | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | not applicable: dev selects; adjudication decides retention |

Only `task_group_001` selected a candidate, so the fewer-than-two-groups rule
applies: the pooled dev row is `unavailable` and no bootstrap was computed. Single
group, descriptive only: g001 champion `0.6531951111111111`, selected candidate
`0.7343916666666667`, recorded paired `mean_delta` `0.08119655555555555`. No
group-002 or group-003 imputation.

Public payload hashes (sha256 at report time):
- g001 `public/results.jsonl`: `8944c96940c9522e690e8fee57f6a224c547ae7becf609574332dfb79f6da48d`.
- g003 `public/results.jsonl`: `d3accfea3c63c88a66ee724c7a51c7dd06ebb61a7875ae324d1a7f28a74d4e70`.

### Final estimator and evidence binding

Pooled two-group estimator per the pre-registration ("Uncertainty and unchanged
control"), `docs/prereg-s4-addendum.md` ("Reporting") and the E1c report: mean of
three runs per task, equal-task mean per group, equal-group paired difference;
resample the **two group indices** with all task/run pairs of a sampled group kept
together; existing `rsi_kernel/analysis.py` (SciPy `bootstrap(paired=True)`, BCa,
two-sided 95%, 9,999 resamples). If fewer than two groups select a candidate, every
pooled row is `unavailable` and no bootstrap is computed; a single-group result is
described as such. No method switching.

| Item | Value |
|---|---|
| Groups with final pairs | `task_group_001` only (g003 selected no candidate): pooled rows `unavailable` |
| RNG entropy (`pilot-007/entropy.json`) | `309657874688760956347344364474464567601` (recorded; unused, no bootstrap is computed) |
| `entropy.json` payload sha256 | `ff256a9dd7f9f5f023055d05ad16a95a6c7ef6e60ca6b4ccbb7489727612bb65` |
| Final observations sha256, g001 | `093dbfacf2bdcc57b206217bfb4bb9a3ec45e6571f8988e4a1d5ff3c41393cf3` (`pilot-007/final/task_group_001/observations.jsonl`, 42 lines) |
| Final observations sha256, g003 | not applicable (no final phase) |

## Adjudication

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| adjudication (pooled two-group BCa) | unavailable (one group); g001 per group `failed_gate` | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | per group, below |

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_001` | `train/004` | 0.230769 | 0.179487 | −0.051282 |
| `task_group_001` | `train/005` | 1.000000 | 1.000000 | 0.000000 |
| `task_group_001` | group mean | 0.615385 | 0.589744 | −0.025641 |
| `task_group_003` | `train/004` | not applicable (no final phase) | — | — |
| `task_group_003` | `train/005` | not applicable (no final phase) | — | — |

Retention per group (zero margin, ties pass, adjudication only): g001 **not retained** — the candidate is below the champion by 0.025641, which is not a tie, so `accept()` returned `failed_gate` (`pilot-007/task_group_001/acceptance.json`); g003 not tested (no candidate). A tie is
reported as a tie, not as improvement.

Exact per-task means: g001 `train/004` champion `0.230769` (three runs,
`0.230769` each), candidate `0.17948700000000004` (three runs of `0.230769`,
`0.076923`, `0.230769`); `train/005` `1.0` for both arms. Exact group means are
`0.6153845` / `0.5897435`, Δ `−0.025641000000000025`. Each task has 3
runs per arm (6 per arm over the two adjudication tasks), as the schedule requires.
Source: `pilot-007/final/task_group_001/observations.jsonl`, aggregated as the E1c
report aggregates its final phase — run mean per task, equal-task group mean, then
the equal-group paired difference.

## Holdout

Reported, not gated; invalid or incomplete evidence still blocks.

| Split | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate |
|---|---|---|---|---|---|---|
| holdout (pooled two-group BCa) | unavailable (one group); g001 report-only | unavailable | unavailable | unavailable | unavailable | unavailable |

Per-task holdout diagnostics (`test/001`–`005`): g001 below; g003 not applicable (no final phase).

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_001` | `test/001` | 0.812500 | 0.875000 | +0.062500 |
| `task_group_001` | `test/002` | 0.590909 | 0.590909 | 0.000000 |
| `task_group_001` | `test/003` | 0.230769 | 0.230769 | 0.000000 |
| `task_group_001` | `test/004` | 0.142857 | 0.142857 | 0.000000 |
| `task_group_001` | `test/005` | 0.642857 | 0.571429 | −0.071428 |
| `task_group_001` | group mean | 0.483978 | 0.482193 | −0.001786 |

Exact group means `0.48397846666666666` / `0.4821928`, Δ `−0.0017856666666666854`;
each group has 15 records per arm (5 tasks × 3 runs). Holdout is report-only: it is
not an additional gate, and the candidate was frozen at campaign close before the
final phase started. Source: `pilot-007/final/task_group_001/observations.jsonl`,
same aggregation as adjudication.

## Indirect chained estimate

If a group records a second retained update, the seed → E1c → E1d chain may be
summarised by adding E1c's generation-1 difference to E1d's generation-2
difference. Such a sum is **an indirect chained estimate using separately measured
generation-1 scores, not a direct contemporaneous comparison**. A positive
cumulative estimate does not show a positive second increment. The reused holdout
is further exposure (below), not fresh evidence.

| Group | Generation-1 (E1c) difference | Generation-2 (E1d) marginal difference | Indirect chained estimate |
|---|---|---|---|
| `task_group_001` | `0.0` (`0.6153845` / `0.6153845`, a TIE under the zero-margin rule; E1c report) | `−0.025641` (adjudication, above: `0.6153845` / `0.5897435`; holdout `−0.001786`, report-only, not gated) | not applicable: no second retained update, so this section's precondition is not met and no cumulative figure is reported for g001 |
| `task_group_003` | `0.07352941176470584` (adjudication, E1c report) | not applicable (no second update) | not applicable |

Reported per split only where both generations were measured; no interval is
claimed for the chained sum unless the registered estimator produces one.

## Structured failures: OOM, `fsize` and timeout

Optimise, both groups (72 solves): every `attempt-timing.json` records
`container_exit_code` 0 and `docker_attach_exit_code` 0; longest attempt 471.4 s
against the 3600 s limit. Final phase g001 (42 solves): all 42 `attempt-timing.json`
records `container_exit_code` 0 and `docker_attach_exit_code` 0; longest attempt
319.3 s against the same limit.

| Event kind | Smoke | Optimise | Final | Evidence / effect |
|---|---|---|---|---|
| OOM | 0: `OOMKilled: false` | no classified event; no exit 137 | no classified event: 0 of 42 attempts exit 137; container-event census unavailable (no Docker inspect `State` receipt is preserved in the final attempt directories) | `smoke.log`; `attempt-timing.json` |
| `fsize` kill | 0 reported | no classified event; container-event census unavailable | 0 reported; container-event census unavailable (same missing inspect receipt) | same |
| Timeout | 0 | 0: max 295.9 s (g001), 471.4 s (g003) | 0: max 319.3 s of the 3600 s limit; 0 timeout failures | `attempt-timing.json` `elapsed_seconds` |
| Unclassified solver failure | 0 | **5**, all g003 attempt 1, `missing_prediction` (exit 0, no `answer.json`) | 0: no `failure.json` in any of the 42 final attempt directories, and 0 of 42 exit codes non-zero | `failure.json`; blocked that candidate's dev comparison (`dev_failure`) |

The five `missing_prediction` STOPs are solver-result failures, not resource
events. No verified OOM or `fsize` count is inferred from absent inspect receipts.

## Cost

Actual logical calls and provider-metered tokens only; no verified billed price.
D2 usage null is reported as null, not zero.

| Stage | Solver attempts | Proposer calls | D2 calls | Calls against 42 cap | Evaluator items | Input tokens (solver) | Cached input (solver) | Output tokens (solver) | Wall time |
|---|---|---|---|---|---|---|---|---|---|
| Campaign, `task_group_001` | 36 | 3 | 3 | **42 of 42** | 36 | 5,744,450 | 4,936,192 | 232,295 | solves 13:01:51–15:20:04 UTC (2 h 18 m 13 s span); summed solve time 5,940 s |
| Campaign, `task_group_003` | 36 (5 failed) | 3 | 3 | **42 of 42** | 36 | 12,063,851 | 10,567,424 | 204,130 | solves 13:01:52–15:34:24 UTC (2 h 32 m 33 s span); summed solve time 6,704 s |
| Pre-run smoke, g001 `train/001` | 1 | not applicable | not applicable | outside campaign caps | 1 | 126,323 | 111,872 | 4,692 | pytest 151.93 s (`smoke.log`) |
| Final phase, g001 | 42 | 0 | 0 | outside campaign caps | 42 | 8,561,854 | 7,524,736 | 329,480 | solves 15:36:24–18:22:30 UTC (2 h 46 m 05 s span); summed solve time 8,479 s |
| Final phase, g003 | 0 (no candidate) | 0 | 0 | not applicable | 0 | not applicable | not applicable | not applicable | not run |

| Item | Value |
|---|---|
| Solver totals (optimise) | g001 5,976,745 total, reasoning output 70,342; g003 12,267,981 total, reasoning output 84,493. Cached and reasoning buckets are subsets; cache-write 0 |
| Proposer tokens | g001 41,931 input / 40,564 output / 82,495 total; g003 30,756 / 40,371 / 71,127 |
| D2 tokens | unavailable: all 6 `jev` rows `token_usage: null` (pin predates D2 usage metering); null, not zero |
| Failed solves charged | g003 a1's 5 `missing_prediction` solves: 2,707,043 tokens (2,669,760 input, 37,283 output), included in g003's solver totals |
| Smoke | 131,015 total, reasoning output 1,566 (`e1d-smoke/attempts/gdp-33a8e86e/measurement.json`) |
| Final phase, g001 tokens | 8,891,334 total (8,561,854 input, of which 7,524,736 cached; 329,480 output, of which 117,677 reasoning); 0 cache-write. Equal in the 42 `observations.jsonl` rows and in the 42 `measurement.json` receipts |

Source: each `calls.jsonl` (`kind`, `token_usage`) and the attempts'
`measurement.json`. Campaign calls total 84 (72 solver + 6 proposer + 6 D2).
Wall time is the solve-attempt span from `attempt-timing.json`, not process
runtime. Optimise and smoke solver tokens: 18,375,741 known; with proposer
usage 18,529,363; missing D2 usage prevents a complete all-call total.

Billed cost: unavailable for optimise and smoke: all 72 optimise and the smoke
`measurement.json` receipts have `cost_usd: null`, and no billing record exists.
Final phase g001: unavailable for the same reason — all 42 final `measurement.json`
receipts have `cost_usd: null`, and no billing record exists.

## Acceptance outcome

Acceptance is final-phase, hash-bound and record-only; the optimiser's `selected`
is not `updated`.

| Group | Disposition | Acceptance / reason |
|---|---|---|
| `task_group_001` | final-phase `failed_gate`; **no second retained update** | `acceptance.json` `{"outcome": "failed_gate"}`: the adjudication comparison of the frozen candidate (`c40f1da3…`) against the champion (`d65e220b…`) was below the zero margin (Δ −0.025641), so retention was not met; no update, no approval request |
| `task_group_003` | optimise `no_improvement`; no selected candidate; **no final phase** | no retention test, approval request or update possible; from `campaign.json`, not an `acceptance.json` |

Approval policy follows `docs/prereg-e1d-amendment-1.md` §1, which supersedes addendum
§2.2's no-standing-approval clause: the lead may approve record-only apply under the
owner's standing grant when retention passes, with each approval bound to the request's
candidate, data, evaluator and code hashes. Request, approval and binding hashes: g001 not applicable
(`failed_gate`; no approval request was written, so there is no request, approval
or binding hash); g003 not applicable. No `approval-request.json` or `approval.json`
exists in `pilot-007/task_group_001/`. `apply(hash)` stays record-only, not deployment.

## Adapter diff against the kernel

Descriptive only, no "thin" threshold. `git diff --numstat 126ba900 5128c1cd`
(E1c campaign pin → E1d pin) changes 8 files, none under `src/` and not
`uv.lock`: 5 docs files (the E1d addendum, one other addendum, three results
reports), 2 example files and 1 integration test. The E1c report's adapter-diff
tables against S4 `7919829` and S5b `f67a45a` therefore apply unchanged to the
E1d pin.

## Exposure log

Every screen is already adaptive; no split is fresh. Before the first campaign
solve, the actual counts were recorded in
`pilot-config/e1d/e1d-exposure-reconciliation.md` (addendum §3(c), §4), built on
the S5c reconciliation (sha256
`30d64aaa86fe59fb4e2602cc668a36bfeadd7e9728c684c9ca2d93790f2ddde2`) and S5c's
terminal record.

| Reconciliation file state | sha256 |
|---|---|
| Pre-append (before the lead appended the fresh-smoke actual line) | `3ab6a6400c05a44be87914e88c8da6a986bf5b149d28b5637a29ad092ea738d5` |
| Post-append (current: smoke-actual line and correction note appended) | `781b34c9aa76aad9b7f5f9ae5d915aa4a0a4be04ecc10a52785761c0d19b87cd` |

### Exposure before the E1d campaign (including the fresh E1d smoke)

| Group | dev campaign | dev smoke / feasibility | dev total | adjudication | holdout | In E1d |
|---|---|---|---|---|---|---|
| 001 | 189 | 18 | 207 | 60 | 150 | yes |
| 002 | 117 | 1 | 118 | 0 | 0 | excluded |
| 003 | 126 | 2 | 128 | 36 | 90 | yes |
| **All** | **432** | **21** | **453** | **96** | **240** | |

Source: the reconciliation file's totals table. Group 001's adjudication and
holdout screens had been solved in five campaigns (S4, S5b, S4b, E1c, S5c), group
003's in three (S4, S4b, E1c).

Correction note (appended to the reconciliation file by the lead): the failure
summary had counted 1 operational failure among smoke/feasibility attempts; the
frozen `docs/prereg-gdpevo-pilot.md:4–7` records seven S4 feasibility operational
STOPs as well, so the historical reported total is **eight** (seven S4 + one E1c).
Solve and exposure counts are unchanged. The S4 feasibility "8 vs 7 on disk"
disclosure is carried unresolved from that file.

### E1d exposure added by this run

| Group | dev campaign | dev smoke | adjudication | holdout | Source |
|---|---|---|---|---|---|
| 001 | 36 | 1 | 12 (6 champion + 6 candidate) | 30 (15 champion + 15 candidate) | `smoke.log`; `public/results.jsonl` and `evidence/` (36 solves); final `observations.jsonl` and `evidence/gdp-*` (42 solves, 21 per arm) |
| 003 | 36 (5 failed, counted) | 0 | 0 | 0 | 36 `evidence/` solve directories; no final phase |

Registered bounds, not predicted exposure: ≤ 36 solver attempts per group, 42 final
solves per group that selects a candidate, and the smoke. **No independence,
replication or compounding claim is made.**

## Named local exceptions (carried, not re-derived)

As listed in `docs/results/e1c-harness-code.md` ("Named local exceptions"),
unchanged by the E1d addendum: T3-RESOURCE-VALUES, the three-group diagnostic
scope, first-three read-only group selection (not representative sampling), the
carving map, the served model and reasoning effort, the 3600 s evaluator timeout,
calls-per-group spend metering (cap 42), whole-file `solver.py` rewrite, no PID
limit, and the dropped dev re-run and control arm.

## Not covered

- No improvement claim: a retained tie is not an improvement, and a `dev_pass` is
  selection only.
- No cumulative-improvement, compounding or ratchet-efficacy claim from a second
  retained update; any chained figure is an indirect estimate (above).
- No significance, power, independence or replication claim; no screen is fresh.
- No pooled estimate unless both groups select a candidate; group 002 is not
  imputed.
- No comparison or pooling with S4, S4b, S5b, S5c or E1c rows.
- No claim that the champion's execution was verified by the smoke: the smoke ran
  the frozen seed solver; the champion is first executed by the campaign's own
  champion dev evaluation.
- No acceptance or release to any product; `apply()` stays record-only.
