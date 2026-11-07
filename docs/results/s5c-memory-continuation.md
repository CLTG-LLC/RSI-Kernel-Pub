# S5c: a second memory-library campaign from the approved S5b library

Slice S5c, issue #108. One campaign under the frozen pre-registration
`docs/prereg-gdpevo-pilot.md` as amended by `docs/prereg-s5c-addendum.md`
(continuation from the approved S5b memory library), which adopts
`docs/prereg-s5-addendum.md` (memory artifact), `docs/prereg-s5b-addendum.md`
(evaluate before admission) and `docs/prereg-s4-addendum.md` (trimmed final phase)
by reference. The campaign starts from the approved S5b candidate of
`task_group_001` only — lineage parent → child — with `task_group_002` and
`task_group_003` excluded (addendum §2.2). This is a diagnostic feasibility and
cost run, not a statistical claim and not an efficacy comparison.

Status: **terminal (run directory `pilot-006`).** The group campaign closed
`selected`, and the final phase completed with 42 graded solves and 0 failure rows.
The group ended `failed_gate` (adjudication retention not met), so no approval
request was written. The pre-registered status is **continuation tested**: the
campaign started from the verified approved S5b library (champion id,
champion-file sha256, reconstructed id, prior approval), and the selected
candidate's `parent_ids` is that approved library (`db7af325…`). This is a factual
status, not an outcome. Per `docs/prereg-s5c-addendum.md` §5 the terminal outcome
for `task_group_001` is **no second retained update**. A retained second update is
**not** demonstrated.

## Diagnostic only

The frozen pre-registration fixes the scope at 3 read-only groups, and the S5c
addendum §2.2 excludes `task_group_002` and `task_group_003`, so at most **one**
group can carry a candidate. The existing "at least two groups" pooled reporting
rule cannot be reached: pooled comparisons and group-clustered uncertainty are
**`"unavailable"`**, and no replacement estimator, interval or threshold is added.
No significance or power claim is made.

## What changed in this campaign (S5c addendum §2)

| Item | S5b (`pilot-003`) | S5c (`pilot-006`) |
|---|---|---|
| Starting champion | the empty library, in all three groups | `task_group_001`'s **approved S5b candidate**, loaded through the existing hash-checked loader `gdpevo_memory.pilot._champion` |
| Groups with a campaign | `task_group_001`, `task_group_002`, `task_group_003` | `task_group_001` only; 002 (`no_improvement` in S5b) and 003 (operational STOP in S5b) **excluded** |
| Lineage | empty library → S5b candidate | every S5c candidate carries the approved S5b id in `parent_ids`; the campaign's frozen `champion_id` is that id |
| Admission | add-only (`admit_draft` always selects `"add"`) | unchanged; merge and revise stay unexercised live; no D4 call |
| Spend cap per campaign | 45 (`36 solver + 3 proposer + 3 D2`, 3 unused former D4 slots) | 45, unchanged |
| Final phase | adjudication + holdout × 3 runs × champion/candidate = 42 solves; no control arm; no dev re-run | unchanged |
| Retention, selection, metric, estimator, isolation | zero margin, ties pass, retention on adjudication only | unchanged |

The addendum changes no acceptance rule. It adds no threshold, significance test or
per-item gate; the holdout comparison is report-only and blocks only on invalid or
incomplete evidence.

## Scope and frozen inputs

| Item | Frozen value |
|---|---|
| Run commit | `e7087c144033e0468cce1081c2d690739717c2ca` (clean detached checkout; the first `main` commit containing the S5c addendum, addendum §3) |
| Group in this campaign | `task_group_001` |
| Dev / adjudication / holdout tasks | 3 (`train/001`–`003`) / 2 (`train/004`–`005`) / 5 (`test/001`–`005`) |
| Attempts per task | 3 runs (`RUNS = 3`) |
| Arms in the final phase | champion and candidate only |
| Champion artifact | approved S5b candidate `db7af32578f5bcd75114309a0088988bb23e4dcfa4b38a2cca4e314ecd508144`; champion-file sha256 `4ab85f4b37a1a5729a1b24e10e6142c78b3380bbee4ca50b031f41a52b6a6670` |
| Champion parent | the empty library `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Rendered champion `SKILL.md` (via `render_skill`) | sha256 `ce5e8470beb7d7afefafcc36e5692c63223a113221c6ee3a15975225bfd70e51` |
| Prior approval | S5b acceptance `updated` on the owner's four-hash approval (`docs/results/e1a-s5b-evaluate-first.md`, "Acceptance outcome") |
| Manifest hash (`shasum -a 256` of `manifest.json`) | `9ca0e700bba654aaffe37bcef7adb1f2d5b61d34b920f37e3aca0085f627a37a` — all 10 carved tasks, 60 hashed files; byte-identical to S4b's `task_group_001` manifest |
| Bootstrap RNG entropy | `174709475050119758070513037539850574770`, `pilot-006/entropy.json` (written 2026-11-07 18:27:52 CST, after the campaign record closed at 18:26:47 and before the first final solve at 18:28:23) |

Source: `docs/prereg-s5c-addendum.md` §2–§3; `pilot-config/config-s5c.json`;
`pilot-006-logs/code-identity.txt`; `pilot-006/task_group_001/manifest.json`.

## Pre-run STOP evidence

Per the S5c addendum §3, in its stated order, enforced by `launch-s5c.sh`. Any miss
is a STOP before the first campaign solve.

| Pre-run STOP | Status | Evidence |
|---|---|---|
| (a) Identity frozen; champion reconstruction and prior approval | Held | `code-identity.txt`: loading the champion through `_champion` (sha256-checked) reconstructs id `db7af325…` = the approved S5b `candidate_hash`, parent the empty library; `render_skill(champion)` equals the frozen rendered file byte-for-byte; line `reconstruction verified db7af325…` |
| (b) Lead-only live smoke at the pin, outside CI, exactly one executed and passing test | Held | `tests/adapters/test_gdpevo_solver_live.py` with `RSI_LIVE_GDPEVO=1`, the rendered approved library and its sha256: **1 passed in 170.02 s**, `task_group_001/train/001`, evidence `s5c-smoke/attempts/gdp-63ac7b38`. A skip would have been a STOP |
| (c) Exposure reconciled across S4, S5, S5b, S4b, E1c and all smokes | Held | `pilot-config/s5c/s5c-exposure-reconciliation.md` (recorded 16:40 CST before the campaign; the fixed smoke row confirmed by the actual line appended after the smoke). See "Exposure log" |
| (d) First campaign solve | Held | first attempt start 16:44:20 CST (2026-11-07), after (a)–(c), from `attempt-timing.json` |
| Calibration replay reproduces byte-identically | Held: 2 replays — campaign start `gdp-982e6d5f`, final-phase initialisation `gdp-1c4ad9c4`; both `calibration-answer.json` hash to the frozen `5eb5cc63…ae96b` and both `calibration-score.json` to the frozen `12308ca2…6205e` | prereg calibration task `task_group_001/train/001` |

Smoke detail: 1 solve, no operational failure (`container_exit_code` 0,
`docker_attach_exit_code` 0), 130.2 s solver elapsed, started 16:41:27 CST; tokens
167,385 input / 147,840 cached / 5,115 output (1,658 reasoning), model
`gpt-6.1-sol` via `proxy`, `cost_usd` null. Recorded outside the campaign caps.

## Code identity

Two hashes, one formula (`gdpevo.pilot._code_hash`), recorded before the first solve
and recomputed on the run tree.

| Identity | Recorded | Recomputed | Compared with |
|---|---|---|---|
| full code hash | `5aa9150d652138a624729b629a03a3a8aacd8790b3e7f117d23e75637cfba63c` | equal | `campaign.json` `code_hash`: equal; differs from S5b's `021c1bb3…0d006e` and S4b's `8758f567…173e25` |
| kernel-only hash (`exclude=("adapters",)`) | `8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc` | equal | **equal to S4b and E1c** (`s4b-continuation.md`, `e1c-harness-code.md`); differs from S5b's `2781ad32…99f3e8` |
| campaign git SHA | `e7087c144033e0468cce1081c2d690739717c2ca` | equal; worktree clean | the final launcher ran at the same pin; no `rebind.json` |
| `evaluator_hash` | — | `8e8845dd4030d1c08ff4ed4675866e1ba93da0bf37e37f0f968b4a0c248a0fd4` | `campaign.json` and every `outcomes.jsonl` row agree; differs from S5b's group-001 `d5c1546c…59e57` |

Recompute command, run inside the run tree at `e7087c1`:

```
uv run python -c "from rsi_kernel.adapters.gdpevo.pilot import _code_hash; print(_code_hash()); print(_code_hash(exclude=('adapters',)))"
```

**Exit criterion 3.** With this campaign, the same kernel-only bytes `8ea2ae0a…`
have closed a campaign on the skill tier (S4b), the harness-code tier (E1c) and now
the memory tier (S5c). That completes exit criterion 3 ("same kernel bytes close
campaigns on skill, memory and harness-code tiers", `docs/results/plug-and-play-exit.md`
§3). It is an execution fact about kernel identity, not an efficacy result.

Descriptive differences from the S5b run commit `f67a45a` (`git diff --numstat`):

| Path set | Changed files | Insertions | Deletions |
|---|---|---|---|
| `src/rsi_kernel/` excluding `adapters/` | 3 | 427 | 0 |
| `src/rsi_kernel/adapters/gdpevo_memory/` (5 files, 339 lines at the pin) | 0 | 0 | 0 |
| `src/rsi_kernel/adapters/gdpevo/` | 3 | 220 | 39 |
| `uv.lock` | 1 | 1,061 | 4 |

Mid-run drift remains a STOP. None was found.

Source: `pilot-006-logs/code-identity.txt`; `pilot-006/task_group_001/campaign.json`,
`outcomes.jsonl`; recompute and `git diff --numstat` in the run tree.

## Runtime pins

| Pin | Frozen value | Verified at run |
|---|---|---|
| Solver image base digest | `python:3.12-slim@sha256:b224e2fe…f5f5b` | present in all 80 staged `Dockerfile` files (36 campaign + 42 final + 2 calibration replays) |
| Solver CLI | Codex CLI 0.166.0 and the three frozen asset hashes | present in all 80 `Dockerfile` files; all 78 solver traces report `cli_version` 0.166.0 |
| Served model | `gpt-6.1-sol` via the local model proxy | all 78 `measurement.json` files: `gpt-6.1-sol`, provider `proxy`, token source `codex_session_trace` |
| Reasoning effort | `xhigh` | every solver trace carries `"reasoning_effort":"xhigh"` |
| Solver wall-time limit | 3600 s | elapsed campaign 78.8 s min / 236.6 s max; final 95.9 s / 269.0 s |
| Spend cap (calls per campaign) | 45 | **42 / 45** (`calls.jsonl`: 36 `solver`, 3 `proposer`, 3 `jev`; D4 0) |
| Evaluator cap | 36 | 36 / 36 (`evaluator_items_used`) |
| Retry accounting | logical calls; retries logged as `retry` rows, not metered again | 0 `retry` rows |
| Docker | — | `29.5.2` in all 80 evidence directories |

## Dev campaign

Only dev scores guided proposals and selection. Dev is not re-run in the final
phase; every row below is read from the optimise archive. The campaign is closed
(`status: "closed"`, `outcome: "selected"`, `stop_reason: "attempts"`).

### Champion dev rows

All 9 champion rows carry the approved S5b id `db7af325…`. Aggregation: mean over
the 3 runs per task, then the equal-task mean.

| Task | Runs 0 / 1 / 2 | Mean | `std@3` |
|---|---|---|---|
| `train/001` | 0.733333 / 0.733333 / 0.733333 | 0.733333 | 0 |
| `train/002` | 1.000000 / 1.000000 / 1.000000 | 1.000000 | 0 |
| `train/003` | 0.857143 / 1.000000 / 1.000000 | 0.952381 | 0.067343 |
| **Macro-mean** | | **0.895238** | mean per-task 0.022448 |

`std@3` is the population standard deviation over the three runs (ddof = 0), the
upstream statistic (`docs/prereg-gdpevo-pilot.md:105`, `metric_and_scoring.md:115–139`).
The spread of the three run-level champion means (0.863492, 0.911111, 0.911111) is
also 0.022448. Champion pass counts (score exactly 1.0): 5 of 9 (`c1.dev_pass_count`
5, `c1.dev_fail_count` 4 in every D2 state below). The noise statistic is not used as
a threshold, and no inference is drawn from comparing it with the deltas.

Source: `pilot-006/task_group_001/public/results.jsonl` (`score` fields).

### Per attempt: evaluated, paired dev delta, selection

`yes` means a valid, non-duplicate draft was admitted add-only as an isolated
candidate and 9 dev solves were run against it. The delta is exactly the
`mean_delta` in `outcomes.jsonl`.

| Attempt | Candidate | Evaluated | `train/001` | `train/002` | `train/003` | Macro mean | Paired dev delta | Outcome |
|---|---|---|---|---|---|---|---|---|
| a1 | `16a53c7e…` | yes | 0.733333 / 0.666667 / 0.666667 → 0.688889 (`std@3` 0.031427) | 1.000000 | 1.000000 | 0.896296 | **+0.001058** | `dev_pass`, **selected** |
| a2 | `da7f0a66…` | yes | 0.666667 ×3 | 1.000000 | 1.000000 | 0.888889 | −0.006349 | `dev_regression` |
| a3 | `0e8cc1d8…` | yes | 0.666667 ×3 | 1.000000 | 1.000000 | 0.888889 | −0.006349 | `dev_regression` |

- 3 of 3 attempts were evaluated; none was rejected for an invalid brief, a
  duplicate, a hash mismatch or a cap, and no call failed.
- a1's delta is the mean of −0.044444 (`train/001`), 0 (`train/002`) and +0.047619
  (`train/003`): a loss on one task offset by the champion's single 0.857143 run on
  `train/003`. It is reported as measured; it is not read as a dev gain beyond noise.
- Selected: `16a53c7e35e8fa51ff98f907f90ab1b87bb558d4d81c4a6bfe072ec0cbca5b86`.
  Lineage, recorded not asserted: empty library `e3b0c442…` → approved S5b
  `db7af325…` → S5c candidate `16a53c7e…`; every row of `public/candidates.jsonl`
  and `campaign.json` `selected` carry `parent_ids = [db7af325…]`.

### Dev split table

| Split | Outcome | Champion | Candidate | Estimate | CI | Retention passed |
|---|---|---|---|---|---|---|
| dev, `task_group_001` | `failed_gate` | 0.895238 | 0.896296 | +0.001058 | `unavailable` | Yes (≥ 0; dev is selection, not the gate) |
| dev, pooled | — | `unavailable` | `unavailable` | `unavailable` | `unavailable` | — |

The pooled row is `"unavailable"` because fewer than two groups have a candidate
(addendum §2.2, §5); no bootstrap or interval is fabricated.

Source: `pilot-006/task_group_001/public/results.jsonl`, `campaign.json`,
`outcomes.jsonl`.

## Adjudication

| Task | Champion runs | Candidate runs | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|---|
| `train/004` | 0.692308 ×3 | 0.538462 / 0.692308 / 0.538462 | 0.692308 | 0.589744 | −0.102564 |
| `train/005` | 1.000000 ×3 | 1.000000 ×3 | 1.000000 | 1.000000 | 0.000000 |
| **Group mean (6 v 6)** | | | **0.846154** | **0.794872** | **−0.051282** |

- 42 graded solves (`train/004`–`005`, `test/001`–`005`; 3 runs; two arms), in the
  order run → task id → arm, 21 per arm, all 42 `(item_id, run, arm)` keys unique,
  **0 failure rows**, every solve `container_exit_code` 0. 12 of the 42 are
  adjudication.
- Zero-margin retention on adjudication: −0.051282 < 0, so retention failed and
  `acceptance.json` records `{"outcome": "failed_gate"}`. Pooled: `unavailable`.

## Holdout

| Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|
| `test/001` | 0.687500 | 0.687500 | 0.000000 |
| `test/002` | 0.590909 | 0.590909 | 0.000000 |
| `test/003` | 0.794872 | 0.794872 | 0.000000 |
| `test/004` | 0.738095 | 0.690476 | −0.047619 |
| `test/005` | 0.714286 | 0.571429 | −0.142857 |
| **Group mean (15 v 15)** | **0.705132** | **0.667037** | **−0.038095** |

Holdout is **report-only**, not a gate (addendum §2.3, §5): its evidence was
complete and valid (30 / 30, 0 failures), and its score did not decide the outcome.
No holdout score was used to choose anything; the candidate was frozen at campaign
close. Pooled: `unavailable`.

Source: `pilot-006/final/task_group_001/observations.jsonl`,
`task_group_001/acceptance.json`; `pilot-006-logs/final-task_group_001.out`
(`{"task_group_001": "failed_gate"}`, empty stderr).

## D2: which component to change (Jev vs the deterministic baseline)

Advisory only. D4 is not on this path (addendum §2.1: no D4 call is restored).

| Quantity | Value |
|---|---|
| D2 records | 3, backend `jev`, model `jev-latest` |
| Jev choice / baseline choice | `c1`, `c1`, `c1` / `c1`, `c1`, `c1`; agree 3 of 3 |
| Fallbacks, `none` answers | 0 / 0 |
| States asked | `attempt_count` 0/1/2, `budget_used` 9/18/27, `c1.dev_pass_count` 5, `c1.dev_fail_count` 4, plus `c1.dev_paired_score_delta` +0.001058 and −0.006349 from attempt 2 on |

The memory library is registered as a single component `c1`, so the D2 choice is
trivial: the only alternative is `none`. Agreement here says nothing about Jev's
selection quality. No selection depended on D2.

Source: `pilot-006/task_group_001/decisions.jsonl`.

## Terminal outcome (S5c addendum §5)

| Part | Value | Basis |
|---|---|---|
| Status | **continuation tested** (continuation from an approved memory artifact demonstrated, as an execution fact) | champion id, file sha256, reconstructed id, prior approval and lineage recorded (§2.1) |
| Terminal outcome, `task_group_001` | **no second retained update** | `acceptance.json` `failed_gate`: adjudication retention not met (−0.051282); no approval request written |
| `task_group_002`, `task_group_003` | no S5c outcome | excluded (addendum §2.2); not pooled, not re-run |

"Retained second update" would require `accept()` to return `updated`: dev
selection under the zero-margin rule, adjudication retention, complete final
evidence, and a matching four-hash approval. The chain stopped at adjudication
retention, so no approval was requested and no second update was retained. No
operational STOP occurred before, during or after the final phase.

## Cost

Provider-metered token buckets as measured; no modelled price.

| Stage | Solver attempts | Proposer | D2 | Calls against the 45 cap | Evaluator items | Input tokens | Cached input | Output tokens | Wall time |
|---|---|---|---|---|---|---|---|---|---|
| Campaign | 36 | 3 | 3 | **42 of 45** | 36 / 36 | 5,412,604 | 4,674,816 | 196,887 | 1.71 h (1.24 h solver time) |
| Final phase | 42 | 0 | 0 | outside the campaign cap | 42 | 8,171,320 | 7,166,976 | 284,868 | 2.42 h (2.01 h solver time) |

- Solver campaign tokens: 5,380,333 input / 4,674,816 cached / 177,193 output
  (64,966 reasoning) / 5,557,526 total; summed from `calls.jsonl` and equal, in
  every bucket, to the sum over the 36 `measurement.json` files.
- Proposer tokens: 32,271 input (0 cached) / 19,694 output (10,182 reasoning) over
  3 calls, every call with a recorded `token_usage`.
- Jev tokens: not recorded (`token_usage: null` on all 3 records).
- Final-phase tokens: sum over the 42 `observations.jsonl` rows, equal to the 42
  `measurement.json` files in every bucket; 124,732 reasoning, 8,456,188 total.
- Logical model calls: 36 + 42 solver + 3 proposer + 3 D2 = **84**, plus the 1 smoke
  solve outside the cap. The same count as S5b group 001's planning figure, which was
  not a prediction.
- Wall time: campaign 16:44:20–18:26:45 CST, final 18:28:23–20:53:20 CST
  (2026-11-07), from `attempt-timing.json`; the second figure is summed per-attempt
  solver seconds.
- Billed cost: not available (`cost_usd: null` on all 78 attempts). Failed calls: 0.

Source: `pilot-006/task_group_001/calls.jsonl`, `evidence/<id>/measurement.json`,
`evidence/<id>/attempt-timing.json`; `final/task_group_001/observations.jsonl`.

## Acceptance outcome

| Outcome | Reported | Reason |
|---|---|---|
| `updated` | No | no approval request: the gate failed first |
| `no_improvement` | No | a candidate was selected |
| Operational STOP | No | 0 failure rows; no STOP |
| `not_updated` | No | no approval was sought |
| `failed_gate` | **Yes** | adjudication retention not met (−0.051282); final evidence complete and valid |

No `approval-request.json` or `approval.json` exists; `apply(hash)` was not run.
Keeping the champion is not counted as success.

## Exposure log

Every screen used is already **adaptive**; no split is fresh. Prior exposure is the
actual per-split, per-group reconciliation recorded before the first campaign solve
at `pilot-config/s5c/s5c-exposure-reconciliation.md` (pre-append sha256
`79cf0c56…`; post-smoke snapshot, before the appended correction, `30d64aaa…`;
current, including the correction, `bdfd14bc…`), read from the
records of S4, S5, S5b, S4b, E1c and every smoke.

### Prior exposure before the S5c campaign (from the reconciliation, incl. the S5c smoke)

| Group | dev campaign | dev smoke / feasibility | adjudication | holdout | In S5c |
|---|---|---|---|---|---|
| `task_group_001` | 153 | 17 | 48 | 120 | yes |
| `task_group_002` | 117 | 1 | 0 | 0 | excluded |
| `task_group_003` | 126 | 2 | 36 | 90 | excluded |

Group 001's adjudication and holdout screens had been solved in four campaigns (S4,
S5b, S4b, E1c) before S5c. Of the 20 reported smoke/feasibility attempts, the reconciliation identifies one
E1c smoke operational failure. Its failure summary omits the seven S4 feasibility
operational STOPs recorded in `docs/prereg-gdpevo-pilot.md:4–7`. The historical
reported total is therefore eight operational STOPs/failures (derived: seven S4 +
one E1c), not a fresh reconstruction from the remaining directories. Separate disclosures (not solves), carried from the reconciliation:
the S5b holdout grader-output disclosure; proposer inputs carried dev text only.
The reconciliation also discloses that the S4 feasibility count of 8 comes from
report text while 7 attempt directories exist on disk.

### S5c exposure added by this run

| Split | What was exposed | When | Effect on independence |
|---|---|---|---|
| pre-run smoke | 1 dev solve of `train/001` with the approved library (`gdp-63ac7b38`, passed) | 16:41:27 CST | already exposed dev task; outside campaign caps |
| dev | 36 solves: 9 champion + 27 candidate (3 × 9); each proposal received the champion's 9 dev records | 16:44:20–18:26:45 CST | further reuse of an adaptive split |
| adjudication | `train/004`–`005`, 3 runs × 2 arms = 12 solves, 0 failures | 18:28:23–20:53:20 CST | fifth read of this pair; no independence |
| holdout | `test/001`–`005`, 3 runs × 2 arms = 30 solves, 0 failures | same | fifth read; no independence |

Group 001 after S5c (derived: reconciliation + this run): dev campaign 189, dev
smoke/feasibility 17, adjudication 60, holdout 150. These are within the registered
bounds (≤ 36 dev solver attempts; 42 final solves only because a candidate was
selected). D2 received numeric state only; no adjudication or holdout material
reached the proposer.

**No independence, replication or compounding-efficacy claim is made.** S5c does
not recover a fresh split, does not replicate S5b, and its result does not show
that continuation compounds.

## Named local exceptions (carried, not re-derived)

| Exception | Where frozen | Effect on this report |
|---|---|---|
| Complete first-run scope (3 read-only groups, 3 runs per task), diagnostic only | `docs/prereg-gdpevo-pilot.md` | no significance or power claim |
| Groups 002 and 003 excluded: no approved library | `docs/prereg-s5c-addendum.md` §2.2 | one group; pooled rows `unavailable` |
| Carving map (no seed): dev `train/001`–`003`, adjudication `train/004`–`005`, holdout `test/001`–`005` | `docs/prereg-gdpevo-pilot.md` | 3 / 2 / 5 tasks in the one campaign group |
| Model `gpt-6.1-sol` at `xhigh` instead of upstream | same | served identity recorded from the trace |
| Evaluator timeout 3600 s (upstream gives none) | same | not hit |
| Spend metered as logical model calls, cap 45 | `docs/prereg-s5b-addendum.md` §2.2 | cost is calls and tokens; no billed cost |
| Dev re-run and control arm dropped; noise is the champion's `std@3` | `docs/prereg-s4-addendum.md` | dev from the optimise archive |

## Limitations

Stated as limitations, not results (addendum §2.1, §5):

- **Admission is add-only.** The live path wires `admit_draft`, which always
  selects `"add"`; existing entries were neither merged nor revised.
- **Live merge and revise remain unexercised**, even though the champion now has an
  entry; their write-guard tests are not live evidence.
- The kernel passes the same original champion to every proposal: inter-campaign
  continuation, not cumulative incumbent updates within a campaign.
- The champion is a previously approved artifact selected on screens already read;
  the recorded lineage is a fact, not evidence that continuing from it improves.
- A single group: no pooled comparison or interval exists.

## Not covered

- No improvement claim: dev +0.001058 is within the champion's own run-to-run
  spread on one task, adjudication fell by 0.051282, and holdout fell by 0.038095.
- No retained second update: `failed_gate`, so no approval, `apply(hash)` or
  champion change exists from S5c.
- No result for `task_group_002` or `task_group_003`.
- No significance, power, p-value or interval.
- No independence, replication or compounding-efficacy claim; no release to any
  product; no cross-product transfer.
