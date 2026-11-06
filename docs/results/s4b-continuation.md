# S4b: a second skill-artifact campaign from the approved S4 champions

Slice S4b of `docs/design.md` §7, issue #48. One campaign under the frozen
pre-registration `docs/prereg-gdpevo-pilot.md` as amended by
`docs/prereg-s4b-addendum.md` (continuation from the approved S4 champions), which
adopts `docs/prereg-s4-addendum.md` for the trimmed final phase by reference. The
campaign starts from the approved S4 candidate of each paired group — lineage
parent → child is the point of S4b, a ratchet — for `task_group_001` and
`task_group_003` only. This is a diagnostic feasibility and cost run, not a
statistical claim and not an efficacy comparison.

Status: **terminal (run directory `pilot-004`).** Both group campaigns closed
`selected`, and both final phases completed with 42 graded solves and 0 failure
rows each. Both groups ended `failed_gate` (adjudication retention not met), so no
approval request was written. The pre-registered status is **continuation
tested**: the campaign started from the verified approved artifact in both
groups (champion id, champion-file sha256, reconstructed id), and each selected
candidate's `parent_ids` is that approved S4 champion (`3ef20ac5…`, `96f5e060…`).
This is a factual status, not an outcome. Per `docs/prereg-s4b-addendum.md` §5 the
terminal outcome for **both** groups is **no second retained update**.

## Diagnostic only

The frozen pre-registration ("Uncertainty and unchanged control") fixes the scope
at 3 read-only groups, and `docs/prereg-s4b-addendum.md` §2.2 excludes
`task_group_002`, so S4b has at most **two** groups with a candidate. Its paired
tables can reach the existing "at least two groups" reporting rule at best at the
lower bound, and no third group is available to absorb a no-candidate outcome. No
significance or power claim is made; intervals and p-values are reported only if
the frozen estimator produces them, and a degenerate result is reported as-is
with no method switching.

## What changed in this campaign (S4b addendum §2)

| Item | S4 (`pilot-001`) | S4b (`pilot-004`) |
|---|---|---|
| Starting champion | the frozen seed skill, the same in all three groups | each group's **approved S4 candidate**, loaded through the existing hash-checked loader `gdpevo.pilot._champion` |
| Groups with a campaign | `task_group_001`, `task_group_002`, `task_group_003` | `task_group_001`, `task_group_003`; `task_group_002` **excluded** (no approved champion — S4 closed it `no_improvement`) |
| Lineage | none (seed) | every candidate carries the approved S4 candidate id in `parent_ids`; the campaign's frozen `champion_id` is that id |
| Lineage claim | — | recorded, not asserted: the chain seed → N → N+1 is in the run records |
| Spend cap per group | 42 (`36 solver + 3 proposer + 3 D2`) | 42, unchanged |
| Final phase | adjudication + holdout × 3 runs × champion/candidate = 42 solves per group with a candidate; no control arm; no dev re-run | unchanged (S4 addendum, adopted by reference) |
| Retention, selection, metric, estimator, isolation | zero margin, equal-task then equal-group macro-mean, group-clustered bootstrap | unchanged |
| Everything else | — | `docs/prereg-gdpevo-pilot.md` (frozen), adopted by reference |

The addendum changes no acceptance rule. It adds no threshold, significance test or
per-item gate, and the holdout comparison remains report-only: the retention rule
is applied to adjudication, and the holdout blocks only on invalid or incomplete
evidence.

## Scope and frozen inputs

Per the pre-registration ("Objective and diagnostic scope", "Frozen inputs,
artifact and carving rule") and the S4b addendum §2–§3.

| Item | Frozen value |
|---|---|
| GDPevo revision | `5082a777379156a048881e94940d640702e5e09a` |
| Run commit | `16ac7fe7d110623ae7a990d6e96a235aca516c97` (clean detached checkout; pin recorded in the S4b addendum §3) |
| Groups in this campaign | `task_group_001`, `task_group_003` |
| Dev tasks per group | 3 (`train/001`–`003`) |
| Adjudication tasks per group | 2 (`train/004`–`005`) |
| Holdout tasks per group | 5 (`test/001`–`005`) |
| Attempts per task | 3 runs per task (`RUNS = 3`) |
| Arms in the final phase | champion and candidate only (control arm dropped by the S4 addendum) |
| Champion artifact, `task_group_001` | approved S4 candidate `3ef20ac564f77e7276361ac1305b3dbded320e6df258326f4102d59d3bc1688c`; champion-file sha256 `bea09d29f38484f2616a98a8de631e5b1e18530ddfa54500f868041955c80be3` |
| Champion artifact, `task_group_003` | approved S4 candidate `96f5e060365012822c6914bdddfdd7b45922d41b6e49c85d16408ecb5e2dfc10`; champion-file sha256 `1d1065e73893ffbc5a0b99e572ff6f03cab7040cfdaf43b1f5e22b0f130258c0` |
| Champion pre-check (addendum §2.1) | loading the champion file reconstructs a `Candidate` whose content id equals the recorded `selected.id`; recorded as passed for both groups when the files were written, before the run |
| Manifest hash (`shasum -a 256` of each group's `manifest.json`) | `task_group_001` `9ca0e700bba654aaffe37bcef7adb1f2d5b61d34b920f37e3aca0085f627a37a`; `task_group_003` `eac5ba2fbfee4dfae0d51a262355498141ef51e0c9907172843e000f35f0bc22` |
| Manifest coverage | all 10 carved tasks per group (`train/001`–`005`, `test/001`–`005`); 60 hashed files for `task_group_001`, 82 for `task_group_003` |
| Bootstrap RNG entropy | `278213805438244147502827861937816741049`, `pilot-004/entropy.json` (written 2026-11-06 16:36:33 CST, at the first final-phase initialisation, after both campaigns closed and before any final solve) |

The champion file holds the candidate serialization from S4's `<group>/campaign.json`
`selected` — the `SKILL.md` component bytes exactly as that record stores them — and
its sha256 is recorded in the run config, so the loader's hash check covers the file.

Source: `docs/prereg-s4b-addendum.md` §2.1–§2.3, §3; `pilot-004/task_group_00N/manifest.json`
(when written); `docs/results/gdpevo-pilot.md` ("Scope and frozen inputs").

## Pre-run STOP evidence

Per the S4b addendum §3, in its stated order. Any miss is a STOP before the first
campaign solve.

| Pre-run STOP | Status | Evidence |
|---|---|---|
| (a) Identity frozen and the S5b exposure reconciled before any solve | Held | `pilot-004-logs/code-identity.txt`; the S5b reconciliation recorded at `pilot-config/s4b/s5b-exposure-reconciliation.md` (36/0/12/30 for `task_group_001`; 9/0/0/0 for `task_group_003`), restated in "Exposure log" below |
| (b) Lead-only live smoke at the pinned commit, outside CI, one executed and passing test | Held | `tests/adapters/test_gdpevo_solver_live.py` with `RSI_LIVE_GDPEVO=1`: **1 passed in 170.29 s**, one dev solve of `task_group_001/train/001` using the approved group-001 champion; evidence directory `s4b-smoke/attempts/gdp-356804be`. A skip would not have counted |
| (c) The smoke's actual exposure recorded, including any operational failure | Held | `s4b-smoke/attempts/gdp-356804be`: 1 solve, no operational failure (`container_exit_code` 0, `docker_attach_exit_code` 0), 131.7 s solver elapsed, started 14:42:14 CST; tokens 145,917 input / 120,960 cached / 5,217 output (924 reasoning), model `gpt-6.1-sol` via `proxy`, `cost_usd` null. Recorded separately from campaign attempts, outside the campaign caps |
| (d) First campaign solve | Held | first attempt start 14:45:03 CST (2026-11-06), after (a)–(c), from `attempt-timing.json` |
| Complete per-task manifest generated by the runner and recorded with the results | Held (10 tasks per group; hashes above) | `pilot-004/task_group_00N/manifest.json`; per-attempt image IDs in `evidence/<id>/image-ids.txt` |
| Calibration replay reproduces byte-identically | Held: 4 replays — campaign start `gdp-8dc050d1` (001), `gdp-1bf2a030` (003); final-phase initialisation `gdp-aadb070e` (001), `gdp-4de90bdc` (003). Every `calibration-answer.json` hashes to the frozen answer sha256 and every `calibration-score.json` to the frozen score sha256 | Prereg calibration task `task_group_001/train/001`, frozen answer sha256 `5eb5cc630e4f69d1892b2fe721a593b8eb83513c96b723ff4c0f756e518ae96b`; frozen score sha256 `12308ca22e257b47c05099acec8679a9a06f2205c99870578885098adbf6205e` (`earned 8 / max 15`, `total_score 0.533333`). Any difference is a STOP |

Source: `docs/prereg-gdpevo-pilot.md` ("GEPA dependency and verification");
`docs/prereg-s4b-addendum.md` §3; `pilot-004-logs/`; `s4b-smoke/attempts/gdp-356804be`.

## Code identity

Per the S4b addendum §3. Two hashes, one formula (`gdpevo.pilot._code_hash`),
recorded in the run's code-identity log before the first solve and recomputed on the
run tree. The addendum predicts both values differ from the S4 and S5b values; no
unchanged-kernel premise is claimed.

| Identity | Recorded | Recomputed | Compared with |
|---|---|---|---|
| full code hash | `8758f56738add8fdda337e96da52ef8f647487887dc92d3e09f1a91355173e25` | `8758f56738add8fdda337e96da52ef8f647487887dc92d3e09f1a91355173e25` (equal) | every `campaign.json` `code_hash` (both groups): equal; S4's `ad9447f6154165298314283ccec2610aec41d0d1a0c6eb1bf880adeb402ad082` and S5b's `021c1bb3364ba6b89b8598ed639dc0c236479415d29ce8742d94d647990d006e`: differ, as the addendum predicted |
| kernel-only hash (`exclude=("adapters",)`) | `8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc` | `8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc` (equal) | S4's and S5b's `e8d7b2b5d14018ab0ff68ee5b811aa133f07f60b0843638fb395c12ee6c4d209` and `2781ad329f787e3c2f3e2eb2e482f03b661b1413df83f4abbe389b472599f3e8`: differ, as the addendum predicted |
| campaign git SHA | `16ac7fe7d110623ae7a990d6e96a235aca516c97` | `16ac7fe7d110623ae7a990d6e96a235aca516c97` (equal) | `git rev-parse HEAD` equals the pin; `git status --porcelain` empty (clean worktree). The final launcher ran at the same pin with no rebind (no `rebind.json` in either group), as in S5b |
| per-group `evaluator_hash` | — | `001` `2aa5258f7def0c2256c336c51e64b2faaa5dfc1ed2372273c1f07b4f082274b5`; `003` `36aa11d143c486c10640d0ba44778ad0d869492aa9245104f9e8cbf5750667fb` | `campaign.json` and every `outcomes.jsonl` row agree per group; `001` differs from S5b's `d5c1546c…` (S5b recorded none for `003`) |

Recompute command, run inside the run tree at `16ac7fe`:

```
uv run python -c "from rsi_kernel.adapters.gdpevo.pilot import _code_hash; print(_code_hash()); print(_code_hash(exclude=('adapters',)))"
```

What the pin changes, as recorded in the addendum before the run: grading,
selection, retention and approval-matching criteria are unchanged (`loop.py`,
`analysis.py` and `gdpevo/scoring.py` are byte-identical between `6f04c52` and the
pin); the proposer model call retries transient errors (#57, PR #62), the approval
request is published atomically (#60, PR #64), and the candidate is validated before
staging (#49, PR #55). `code_hash` and `evaluator_hash` differ since both include
adapter source bytes.

| Path set | diff from the S5b run commit `f67a45a` | diff from the S4 run commit `7919829` |
|---|---|---|
| `src/rsi_kernel/` excluding `adapters/` | 3 files, +427 / −0 (`approval.py` +42, `cli.py` +297, `mcp_server.py` +88) | 4 files, +433 / −4 (the same three plus `loop.py` +6 / −4) |
| `uv.lock` | 1 file, +1061 / −4 | 1 file, +1061 / −4 |

Mid-run drift remains a STOP. No drift was found: the final phase ran at the same
pin, the identity check passed in both groups, and no rebind was recorded.

Source: `pilot-004-logs/code-identity.txt`; `pilot-004/task_group_00N/campaign.json`,
`outcomes.jsonl`; recompute and `git diff --numstat` in the run tree;
`docs/prereg-s4b-addendum.md` §3.

## Runtime pins

Per the pre-registration ("Frozen inputs, artifact and carving rule").

| Pin | Frozen value | Verified at run |
|---|---|---|
| Solver image base digest | `python:3.12-slim@sha256:b224e2fe306f9d303251ada22961635e5b52a69c0414a0050611be31c59f5f5b` | the `FROM` line carries that digest in all 160 staged `build/Dockerfile` files of `pilot-004` (72 campaign dev + 84 final + 4 calibration replays) |
| Solver CLI release and asset hashes | Codex CLI 0.166.0; `codex-aarch64-unknown-linux-musl.tar.gz` `94eb707605ec2646b2e05b7edf7c4e7b3ccf02b16237c34ae9beb8cfb7f810a9`; `bwrap-aarch64-unknown-linux-musl.tar.gz` `b59c26ee2cc939a1f3df81b639fcc4fb965609bdc704ca85777c168c12cfeb26`; `codex-code-mode-host-aarch64-unknown-linux-musl.tar.gz` `ac98d1f878e353a16cba711fd47bfef2f6c814109bdd819ee2b6b6d6a19701e7` | Codex 0.166.0 and all three asset hashes present in all 160 staged `Dockerfile` files; every final-phase solver trace reports `cli_version` 0.166.0 |
| Served model identity (from the trace) | `gpt-6.1-sol` via the local model proxy | all 84 final-phase `measurement.json` files record `model: gpt-6.1-sol`, `model_provider: proxy`, token source `codex_session_trace`; every trace reports provider `proxy` |
| Reasoning effort | `xhigh` | every final-phase solver trace carries `"reasoning_effort":"xhigh"` |
| Solver wall-time limit | 3600 s per attempt | observed final-phase elapsed 102.2 s min / 297.9 s max (`001`), 114.2 s / 353.5 s (`003`); campaign 80.0 s / 213.5 s; none near the limit |
| Evaluator timeout | 3600 s (NAMED LOCAL EXCEPTION: upstream gives none) | no evaluator timeout recorded |
| Spend cap (calls per group campaign) | 42 (`36 solver + 3 proposer + 3 D2`) | 42 / 42 per group (`calls.jsonl`: 36 `solver`, 3 `proposer`, 3 `jev`) |
| Evaluator cap (item-evaluations per group) | 36 | 36 / 36 per group (`evaluator_items_used`) |
| Retry accounting | the 42-call cap counts **logical** calls; a proposer call may make its initial request plus up to two retries, logged as `retry` rows but not metered again; 42 is not an HTTP bound | 0 `retry` rows in either `calls.jsonl` |
| Docker version | — | `29.5.2` in all 160 evidence directories; `image-platforms.txt` `linux/arm64` |

Source: `pilot-004/task_group_00N/evidence/<id>/build/Dockerfile`, `measurement.json`,
`image-ids.txt`, `image-platforms.txt`, `docker-version.txt`, `attempt-timing.json`,
solver trace `session_meta`, `campaign.json`; `docs/prereg-s4b-addendum.md` §3.

## Dev campaign

Only dev scores guided proposals and selection. Dev is **not** re-run in the final
phase (S4 addendum, adopted by reference); every row below is read from the
optimise archive. Both group campaigns are closed (`status: "closed"`,
`outcome: "selected"`, `stop_reason: "attempts"`); this section reads no
final-phase record.

### Champion dev rows per group

All 9 champion rows per group carry the group's approved S4 candidate id
(`3ef20ac5…` for `task_group_001`, `96f5e060…` for `task_group_003`), so these are
continuation rows, not seed rows. Aggregation is the pre-registration's rule: mean
over the 3 runs per task, then the equal-task mean per group.

| Group | `train/001` (runs 0/1/2) | `train/002` (runs 0/1/2) | `train/003` (runs 0/1/2) | Champion macro-mean |
|---|---|---|---|---|
| `task_group_001` | 0.733333 / 0.733333 / 0.733333 → 0.733333 | 1.000000 / 1.000000 / 1.000000 → 1.000000 | 1.000000 / 1.000000 / 1.000000 → 1.000000 | 0.911111 |
| `task_group_003` | 1.000000 / 1.000000 / 1.000000 → 1.000000 | 1.000000 / 1.000000 / 1.000000 → 1.000000 | 0.588235 / 0.529412 / 0.529412 → 0.549020 | 0.849673 |

Equal-group macro-mean over the two groups: 0.880392.

Champion pass counts (score exactly 1.0 over 9 dev observations) are 6 / 6 — the
`c1.dev_pass_count` every D2 state carries below (`c1.dev_fail_count` 3).

Source: `pilot-004/task_group_00N/public/results.jsonl` (9 champion records per group).
Means computed with `rsi_kernel/analysis.py` (`aggregate`) at the pinned commit.

### Noise: the champion's dev run-to-run spread

The control arm is not run (S4 addendum), so run-to-run noise is the champion's own
dev spread — the population standard deviation over its three runs per task, the
upstream `std@3` statistic (`metric_and_scoring.md:115–139`).

| Group | `train/001` | `train/002` | `train/003` | Mean per-task spread (`std@3`) | Spread of the three run-level group means |
|---|---|---|---|---|---|
| `task_group_001` | 0 | 0 | 0 | 0 | 0 |
| `task_group_003` | 0 | 0 | 0.027730 | 0.009243 | 0.009243 |

- Pooled mean per-task spread over the six dev tasks across the two groups: 0.004622
  (the pilot's `_run_spread` over the champion dev rows returns 0.004621613).
- `task_group_001` is constant across runs on all three tasks; `task_group_003`
  varies only on `train/003`, where run 0 scored 0.588235 and runs 1 and 2 scored
  0.529412.
- The noise statistic and the candidate deltas are different quantities (per-task
  run-to-run spread versus a macro paired difference); neither is used as a
  threshold, and no inference is drawn from comparing them.

Source: `pilot-004/task_group_00N/public/results.jsonl`; means and population
standard deviations computed from those scores.

### Per group, selection and stop

| Group | Champion dev mean | Selected candidate | Attempts | Attempt outcomes | Stop reason | Campaign outcome |
|---|---|---|---|---|---|---|
| `task_group_001` | 0.911111 | `2355a7c6…` | 3 | `dev_pass`, `dev_regression`, `dev_pass` | `attempts` | `selected` |
| `task_group_003` | 0.849673 | `f024f7f6…` | 3 | `dev_pass` ×3 | `attempts` | `selected` |

- Selection is the zero-margin paired dev rule; ties are eligible. The loop keeps
  a later attempt only if its delta is strictly greater than the best so far
  (`loop.py`, `comparison.mean_delta > best[0]`), so among equal deltas the first
  eligible attempt is kept.
- `task_group_001`: attempts 1 and 3 both had a paired delta of exactly 0.000000
  and attempt 2 was negative; the rule keeps attempt 1,
  `2355a7c6ae69c14c00d738a8990932f61c1912aa49df4cd2720fcdd886c3e22d`. Its dev rows
  equal the champion's on every task and run, so the selection is a tie, not a dev
  gain.
- `task_group_003`: all three attempts had the same paired delta, +0.013072; the rule
  keeps attempt 1, `f024f7f63a632c8b59a2b3968cc8035c41682521ba0e3137d4c119ec224bd2f8`.
- Lineage: each selected candidate's `parent_ids` is exactly the group's approved S4
  candidate id (`3ef20ac5…` and `96f5e060…`), as stored in `campaign.json`
  `selected` and in every `public/candidates.jsonl` row; the campaign's frozen
  `champion_id` is the same id.
- `stop_reason` is `attempts` (the 3-proposal budget) in both groups, not the spend
  or evaluation cap. Both campaign logs end `{"outcome": "selected", "stop_reason": "attempts"}`
  with empty stderr.

Source: `pilot-004/task_group_00N/campaign.json`, `outcomes.jsonl`,
`public/candidates.jsonl`; `pilot-004-logs/task_group_00{1,3}.{out,err}`; `loop.py` at
the pinned commit.

### Per attempt: was the candidate evaluated, and what was its paired dev delta

`yes` means a valid, non-duplicate draft became the candidate and 9 dev solves
(3 tasks × 3 runs) were run against it. The delta is the candidate − champion mean
over dev, exactly the `mean_delta` in `outcomes.jsonl` (recomputed with `aggregate`
and identical to six decimals).

| Group | Attempt | Candidate | Candidate evaluated | Paired dev delta | Selection outcome |
|---|---|---|---|---|---|
| `task_group_001` | 1 | `2355a7c6…` | yes | 0.000000 | `dev_pass`, **selected** |
| `task_group_001` | 2 | `59cb1559…` | yes | −0.022222 | `dev_regression` |
| `task_group_001` | 3 | `958c360f…` | yes | 0.000000 | `dev_pass`, tie with attempt 1, not kept |
| `task_group_003` | 1 | `f024f7f6…` | yes | +0.013072 | `dev_pass`, **selected** |
| `task_group_003` | 2 | `ad3a8541…` | yes | +0.013072 | `dev_pass`, tie with attempt 1, not kept |
| `task_group_003` | 3 | `0934f071…` | yes | +0.013072 | `dev_pass`, tie with attempt 1, not kept |

6 of 6 attempts were evaluated. No attempt was rejected for an invalid brief, a
duplicate, a hash mismatch or a cap, and no operational failure occurred:
`calls.jsonl` records exactly 36 solver, 3 proposer and 3 D2 calls per group, with
no `retry` row, and every attempt produced a scored candidate.

### Per-attempt paired detail

Per-task means over the 3 runs. Every candidate's three runs per task were equal,
so each mean is also each run's score.

| Group | Attempt | Candidate | `train/001` (champion → candidate, difference) | `train/002` | `train/003` | Macro difference |
|---|---|---|---|---|---|---|
| `task_group_001` | 1 | `2355a7c6…` | 0.733333 → 0.733333, 0.000000 | 1.000000 → 1.000000, 0.000000 | 1.000000 → 1.000000, 0.000000 | 0.000000 |
| `task_group_001` | 2 | `59cb1559…` | 0.733333 → 0.666667, −0.066666 | 1.000000 → 1.000000, 0.000000 | 1.000000 → 1.000000, 0.000000 | −0.022222 |
| `task_group_001` | 3 | `958c360f…` | 0.733333 → 0.733333, 0.000000 | 1.000000 → 1.000000, 0.000000 | 1.000000 → 1.000000, 0.000000 | 0.000000 |
| `task_group_003` | 1 | `f024f7f6…` | 1.000000 → 1.000000, 0.000000 | 1.000000 → 1.000000, 0.000000 | 0.549020 → 0.588235, +0.039216 | +0.013072 |
| `task_group_003` | 2 | `ad3a8541…` | 1.000000 → 1.000000, 0.000000 | 1.000000 → 1.000000, 0.000000 | 0.549020 → 0.588235, +0.039216 | +0.013072 |
| `task_group_003` | 3 | `0934f071…` | 1.000000 → 1.000000, 0.000000 | 1.000000 → 1.000000, 0.000000 | 0.549020 → 0.588235, +0.039216 | +0.013072 |

- In `task_group_001`, the only task with room to move on dev is `train/001`
  (the champion already scores 1.0 on `train/002` and `train/003` in every run);
  two candidates matched the champion there and one scored lower.
- In `task_group_003`, all three candidates scored 0.588235 on `train/003` in every
  run, the value the champion reached in its run 0; the +0.039216 per-task difference
  equals the gap between the champion's run-0 score and its runs 1–2 score, averaged
  over three runs. It is reported as measured; no inference about whether it
  exceeds run-to-run noise is drawn.

### Dev split table

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| dev | `failed_gate` | 0.880392 | 0.886928 | +0.006536 | 0.000000 | 0.013072 | False | Yes (both groups) |

- Two groups have a candidate, so the pooled row is computed rather than
  `unavailable`. With two groups the paired group bootstrap resamples group indices
  from a sample of two: there are only 4 ordered group draws, so the interval is
  reported as the frozen estimator returned it (SciPy defaults, not passed) and no
  significance or power claim is made.
- Bootstrap RNG entropy `278213805438244147502827861937816741049`, read from
  `pilot-004/entropy.json` (file time 2026-11-06 16:36:33 CST, after both campaign
  records closed at 16:32:48 and 16:35:29 CST).
- Per-group dev deltas: `task_group_001` 0.000000 (0.911111 → 0.911111),
  `task_group_003` +0.013072 (0.849673 → 0.862745). The pooled estimate is their mean.
- The `Outcome` column is the acceptance outcome the pilot's `report` passes to every
  split row: `failed_gate` in both groups.
- Dev retention is the zero-margin rule on each group's own delta: 0.000000 ≥ 0
  (a tie, which passes) and +0.013072 ≥ 0. Dev is selection, not the retention
  gate; formal retention is decided on adjudication (below), where it failed.
- Method: the row was computed with the pinned tree's `aggregate`,
  `paired_group_bootstrap` and `retention_per_group`, on dev rows built by the
  pilot's own `_dev_rows` (champion and selected candidate only). The pilot's
  `report` itself was not called, because it also iterates `task_group_002`, which
  has no run directory in `pilot-004`; the inputs passed are the ones `report`
  builds for the two paired groups.

Source: `pilot-004/task_group_00N/public/results.jsonl`, `campaign.json`,
`outcomes.jsonl`, `decisions.jsonl`; `pilot-004/entropy.json`.

## Adjudication

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| adjudication | `failed_gate` | 0.838047 | 0.810269 | −0.027778 | −0.027778 | −0.027778 | False | No (both groups) |

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_001` | `train/004` | 0.538462 | 0.538462 | 0.000000 |
| `task_group_001` | `train/005` | 1.000000 | 0.944444 | −0.055556 |
| `task_group_001` | group mean | 0.769231 | 0.741453 | −0.027778 |
| `task_group_003` | `train/004` | 0.833333 | 0.777778 | −0.055556 |
| `task_group_003` | `train/005` | 0.980392 | 0.980392 | 0.000000 |
| `task_group_003` | group mean | 0.906863 | 0.879085 | −0.027778 |

- Each group with a candidate runs the trimmed final phase at the pinned commit: 42
  graded solves (`train/004`, `train/005`, `test/001`–`005`; 3 runs; champion and
  candidate), in the order run → task id → arm, 21 per arm, every
  `(item_id, run, arm)` unique, with 0 failure rows for acceptance. 12 of the 42
  are adjudication. Measured: 42 / 42 per group, 21 per arm, all 42
  `(item_id, run, arm)` keys unique, the stated order, 0 failure rows, every solve
  `container_exit_code` 0.
- Zero-margin retention on adjudication is decided per group by the existing rule;
  ties pass, any group decrease fails. Both groups decreased by −0.027778
  (`001` 0.769231 → 0.741453, from `train/005`; `003` 0.906863 → 0.879085, from
  `train/004`), so retention failed in both and `acceptance.json` records
  `failed_gate` for both.
- A pooled row is reported only if both groups have a candidate. Both do, so the
  pooled row is computed. The group differences are −0.02777783333333339 (001)
  and −0.02777777777777790 (003), not identical. The frozen estimator returns
  CI [−0.02777783333333339, −0.02777777777777790] and `degenerate: False`;
  both endpoints round to −0.027778 at the table's six-decimal precision.
  With two groups there are only 4 ordered group draws, and no significance
  or power claim is made.
- The calibration replay runs at final-phase initialisation and must reproduce the
  frozen values byte-identically. Held in both groups (`gdp-aadb070e`,
  `gdp-4de90bdc`).

Source: `pilot-004/final/task_group_00N/observations.jsonl`,
`final/task_group_00N/evidence/<id>/calibration-score.json`,
`task_group_00N/acceptance.json`; `pilot-004-logs/final-task_group_00{1,3}.{out,err}`.
Means computed with `rsi_kernel/analysis.py` (`aggregate`, `retention_per_group`) at
the pinned commit.

## Holdout

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| holdout | `failed_gate` | 0.664091 | 0.680696 | +0.016604 | 0.000000 | 0.033209 | False | Yes (both groups; reported, not a gate) |

- 30 of each group's 42 final solves are holdout (5 tasks × 3 runs × 2 arms).
  Measured: 30 / 30 per group, 0 failure rows.
- Per group: `task_group_001` 0.712825 → 0.712825 (0.000000, a tie on every task);
  `task_group_003` 0.615358 → 0.648567 (+0.033209). The pooled estimate is their
  mean; the interval is the frozen estimator's output over 4 ordered group draws,
  with no significance or power claim. The holdout tie or gain does not change the
  outcome: retention is applied to adjudication only.
- No holdout score is used to choose anything: the candidate is frozen at campaign
  close, before the final phase starts. Holdout is report-only and is not a gate;
  it blocks only on invalid or incomplete evidence (S4b addendum §5).

### Per-task holdout diagnostics

Diagnostic only. Candidate mean minus champion mean over the three holdout runs of
each task.

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_001` | `test/001` | 0.687500 | 0.687500 | 0.000000 |
| `task_group_001` | `test/002` | 0.590909 | 0.590909 | 0.000000 |
| `task_group_001` | `test/003` | 1.000000 | 1.000000 | 0.000000 |
| `task_group_001` | `test/004` | 0.642857 | 0.642857 | 0.000000 |
| `task_group_001` | `test/005` | 0.642857 | 0.642857 | 0.000000 |
| `task_group_003` | `test/001` | 0.941176 | 0.941176 | 0.000000 |
| `task_group_003` | `test/002` | 0.296296 | 0.425926 | +0.129630 |
| `task_group_003` | `test/003` | 0.588235 | 0.529412 | −0.058824 |
| `task_group_003` | `test/004` | 0.727273 | 0.727273 | 0.000000 |
| `task_group_003` | `test/005` | 0.523810 | 0.619048 | +0.095238 |

Source: `pilot-004/final/task_group_00N/observations.jsonl`, `task_group_00N/acceptance.json`.
Means computed with `rsi_kernel/analysis.py` (`aggregate`, `retention_per_group`) at
the pinned commit.

## D2: which component to change (Jev vs the deterministic baseline)

Advisory only, as in S4. D4 is not on this path: the `gdpevo` skill adapter makes no
D4 call, and the S4 report does not report D4.

| Group | Jev D2 choice | Baseline D2 choice | Agree |
|---|---|---|---|
| `task_group_001` | `c1`, `c1`, `c1` | `c1`, `c1`, `c1` | 3 of 3 |
| `task_group_003` | `c1`, `c1`, `c1` | `c1`, `c1`, `c1` | 3 of 3 |

| Quantity | Value |
|---|---|
| D2 records logged | 6 (3 / 3), backend `jev`, model `jev-latest` |
| Baseline decisions | 6 (one shadow `baseline_answer` per record) |
| Agreements | 6 |
| Timeouts or malformed answers falling back at D2 | 0 (no record carries `fallback_reason`) |
| `none` answers | 0 |
| States asked | `attempt_count` 0/1/2 with `budget_used` 9/18/27, `c1.dev_pass_count` 6, `c1.dev_fail_count` 3, plus `c1.dev_paired_score_delta` from attempt 2 on |

`task_group_001`'s attempt-2 and attempt-3 states carried 0.0 and −0.022222;
`task_group_003`'s carried +0.013072 and +0.013072. Every D2 call chose the single
registered component `c1` regardless of the sign of that delta; the deterministic
baseline chose the same. D2 is advisory: no selection depended on it.

Source: `pilot-004/task_group_00N/decisions.jsonl`.

## Terminal outcome per group (S4b addendum §5)

Exactly one terminal outcome applies per group, and the two are mutually exclusive.

| Group | Status | Terminal outcome | Reason the record gives |
|---|---|---|---|
| `task_group_001` | completed; continuation tested | **no second retained update** | `failed_gate`: adjudication retention not met (−0.027778); no approval request written |
| `task_group_003` | completed; continuation tested | **no second retained update** | `failed_gate`: adjudication retention not met (−0.027778); no approval request written |

- "retained second update" means the existing `accept()` path completed in full: a
  candidate selected on dev under the zero-margin rule, adjudication retention
  passed by the existing rule, valid and complete evidence on both final splits, and
  a matching hash-bound owner approval.
- "no second retained update" covers every other completed outcome, with the reason
  the acceptance record gives.
- An operational STOP stays distinct from a completed negative outcome: it is
  reported as a STOP, with nothing solved after it, and never as "no second
  retained update". A partial result is reported per group, never pooled.

## Cost

Provider-metered token buckets as measured. A billed cost appears only if the
provider supplies a real billing record; no modelled price is reported.

| Stage | Solver attempts | Proposer calls | D2 calls | Calls against the 42 cap | Evaluator item-evaluations | Input tokens | Cached input tokens | Output tokens | Wall time |
|---|---|---|---|---|---|---|---|---|---|
| Campaign, `task_group_001` | 36 | 3 | 3 | **42 of 42** | 36 | 5,660,126 | 4,616,960 | 197,812 | 1.84 h (1.30 h of solver time) |
| Campaign, `task_group_003` | 36 | 3 | 3 | **42 of 42** | 36 | 7,762,916 | 6,651,648 | 157,439 | 1.80 h (1.26 h of solver time) |
| Final phase, `task_group_001` | 42 | 0 | 0 | outside the campaign cap | 42 | 8,077,753 | 7,000,064 | 273,341 | 2.58 h (2.18 h of solver time) |
| Final phase, `task_group_003` | 42 | 0 | 0 | outside the campaign cap | 42 | 13,853,274 | 11,857,152 | 301,945 | 2.76 h (2.35 h of solver time) |

| Item | Value |
|---|---|
| Proposer tokens, per group | `001` 38,121 input (0 cached) / 26,903 output (9,317 reasoning); `003` 22,743 / 21,677 (7,764 reasoning); 3 calls each, every call with a recorded `token_usage` |
| Reasoning output tokens (solver) | `001` 40,565; `003` 44,278 (campaign only) |
| Jev tokens | not recorded: all 6 Jev records (D2) carry `token_usage: null` |
| Calls per group against the 42 cap | 42 / 42 (36 solver + 3 proposer + 3 D2); 0 `retry` rows in either `calls.jsonl` |
| Evaluator item-evaluations against the 36 cap | 36 / 36 (`evaluator_items_used` in `campaign.json`; 9 champion + 3 × 9 candidate) |
| Billed cost (real billing record) | Not available: `measurement.json` records `cost_usd: null` on all 72 campaign dev attempts and all 84 final-phase attempts |
| Estimated cost (modelled price, labelled estimate) | Not reported — no modelled price is given here |
| Failed calls charged | 0 in the campaign: no proposer, D2 or solver call failed; 0 in the final phase (0 failure rows, every attempt exit 0) |
| Solver attempts failed | 0 of 72 campaign dev attempts (every attempt has `container_exit_code` 0 and `docker_attach_exit_code` 0); 0 of 84 final-phase attempts (same check) |

- Campaign input, cached and output tokens are the sum over the `solver` and
  `proposer` records in each `calls.jsonl` (Jev records carry no usage). Cached input
  is solver-only; the proposer reports 0 cached tokens.
- Solver token totals summed from the `solver` records in each `calls.jsonl` agree
  exactly with the sum over that group's 36 `measurement.json` files, in all five
  buckets: `001` 5,622,005 input / 4,616,960 cached / 170,909 output / 40,565
  reasoning / 5,792,914 total; `003` 7,740,173 / 6,651,648 / 135,762 / 44,278 /
  7,875,935. Every measurement names model `gpt-6.1-sol`, token source
  `codex_session_trace`.
- Campaign wall time is the span from the first attempt start to the last attempt
  end in the group, from `attempt-timing.json`: `001` 14:45:03–16:35:28 CST,
  `003` 14:45:03–16:32:47 CST (2026-11-06); the second figure is the sum of
  per-attempt elapsed solver seconds. Observed solver elapsed: `001` 92.7 s min /
  183.2 s max, `003` 80.0 s min / 213.5 s max. Each group's evidence directory also
  holds one grader-only calibration replay (`gdp-8dc050d1`, `gdp-1bf2a030`), which is
  not a solve and makes no model call.
- Final-phase tokens are the sum of the `token_usage` on each group's 42 rows in
  `final/task_group_00N/observations.jsonl`, and agree exactly with the sum over the
  42 matching `measurement.json` files in every bucket: `001` 8,077,753 input /
  7,000,064 cached / 273,341 output / 105,791 reasoning / 8,351,094 total; `003`
  13,853,274 / 11,857,152 / 301,945 / 112,270 / 14,155,219. Final-phase wall time is
  first attempt start to last attempt end from `attempt-timing.json`: `001`
  16:37:06–19:11:55 CST, `003` 16:37:01–19:22:26 CST (2026-11-06); the two groups
  ran concurrently. Each final evidence directory holds 43 entries: the 42 solves
  plus the grader-only calibration replay.
- The 42-call cap counts logical calls per group campaign (36 solver + 3 proposer +
  3 D2); retries are logged as `retry` rows and not metered again, so 42 is not an
  HTTP bound. Failed calls are metered, included by rule.
- Diagnostic model calls outside the per-group campaign: the pre-run live smoke is
  recorded separately under the exposure log, not as a campaign call.

Source: `pilot-004/task_group_00N/calls.jsonl`, `evidence/<id>/measurement.json`,
`evidence/<id>/attempt-timing.json`, `campaign.json`, `decisions.jsonl`;
`docs/prereg-s4b-addendum.md` §3.

## Acceptance outcome

| Outcome | Reported | Reason |
|---|---|---|
| `updated` (approval bound to candidate, data, evaluator and code hashes) | No (neither group) | no approval request was written: the gate failed first |
| `no_improvement` (no candidate, or candidate equals champion) | No (neither group) | both groups selected a candidate |
| Operational STOP | No (neither group) | no STOP before, during or after the final phase; 0 failure rows |
| `not_updated` (approval missing or mismatched) | No (neither group) | no approval was sought |
| `failed_gate` (record failures on either final split, or adjudication retention not met) | **Yes, both groups** | adjudication retention not met in both (−0.027778 each); evidence on both final splits was complete and valid |

| Item | Value |
|---|---|
| Approval record | none: no `approval-request.json` or `approval.json` in either group |
| Approval binding (candidate, data, evaluator, code) | not applicable: no approval was requested |
| `apply(hash)` record | not applicable: not run, since nothing was approved (record-only when it runs: it never replaces the champion or starts enforcement) |
| Independent review of this report | pending, before the issue PR |

Keeping the champion is not counted as success.

Source: `pilot-004/task_group_00N/campaign.json`, `task_group_00N/acceptance.json`,
`task_group_00N/approval-request.json`, `task_group_00N/approval.json`,
`outcomes.jsonl`; `pilot-004-logs/*.out`.

## Adapter diff against the kernel

Descriptive only: file and line counts, with no judgement attached and no "thin"
threshold. The S4b campaign uses the `gdpevo` skill adapter; the `gdpevo_memory`
adapter (S5/S5b) is not on this path.

Against the S5b run commit `f67a45a` (what this pin changed):

| Path set | Files at the pin | Lines at the pin | Changed files | Insertions | Deletions |
|---|---|---|---|---|---|
| `src/rsi_kernel/` excluding `adapters/` | 15 | 1,778 | 3 | 427 | 0 |
| `uv.lock` | 1 | 1,702 | 1 | 1,061 | 4 |
| `src/rsi_kernel/adapters/gdpevo/` | 9 | 1,925 | 3 | 193 | 33 |

Source: `git diff --numstat`, `git diff --stat`, `git ls-tree -r` and `wc -l` at the
two commits in the run tree's repository.

## Exposure log

Per the pre-registration ("Isolation and exposure") and the S4b addendum §4. Every
private-split submission or disclosure is recorded; once disclosed, continued
independence is not claimed.

### Prior exposure of the same screens before S4b (addendum §4, restated)

| Split | Group | Prior solves | Source |
|---|---|---|---|
| dev | `task_group_001` | 36 (S4 optimise: 3 tasks × 3 runs × 4 artifacts) + 8 feasibility attempts of `train/001`, of which 1 was scored and 7 stopped operationally (3 of those consumed tokens with no answer) + 3 runner smoke solves | `docs/prereg-gdpevo-pilot.md`, exposure log of `docs/results/gdpevo-pilot.md` |
| dev | `task_group_002` | 36 (S4 optimise) + 1 pre-run smoke solve | `docs/results/gdpevo-pilot.md`, exposure log |
| dev | `task_group_003` | 36 (S4 optimise) + 2 pre-run smoke solves | same |
| dev | 001 / 002 / 003 | + 9 each from S5 (champion dev, 3 attempts), + 1 S5 pre-run smoke solve (001) | `docs/results/e1a-two-artifact.md`, "S5 exposure added by this run" |
| adjudication | `task_group_001` | 12 graded solves (S4 final) | `docs/results/gdpevo-pilot.md`, exposure log |
| adjudication | `task_group_003` | 12 graded solves (S4 final) | same |
| adjudication | `task_group_002` | 0 (no candidate) | same |
| holdout | `task_group_001` | 30 graded solves (S4 final) | same |
| holdout | `task_group_003` | 30 graded solves (S4 final) | same |
| holdout | `task_group_002` | 0 (no candidate) | same |

### S5b reconciliation (addendum §4) — actual solves added before this campaign

Read from S5b's own record before the first S4b solve; the addendum makes this a
STOP condition, not an estimate.

| Split | Group | S5b solves | Notes |
|---|---|---|---|
| dev | `task_group_001` | 36 | 9 champion + 27 candidate |
| dev | `task_group_003` | 9 | 9 champion; no candidate evaluated |
| pre-run smoke | all groups | 0 | S5b ran no live smoke for its code |
| adjudication | `task_group_001` | 12 | first S5b read of this group's adjudication pair |
| adjudication | `task_group_003` | 0 | campaign stopped operationally |
| holdout | `task_group_001` | 30 | another read of an already-read split |
| holdout | `task_group_003` | 0 | campaign stopped operationally |

`task_group_002` is excluded from S4b and its S5b row is not needed for this
campaign; S5b recorded 36 dev solves and no final solves for that group.

Source: `docs/results/e1a-s5b-evaluate-first.md`, "Exposure log"; the reconciliation
recorded at `pilot-config/s4b/s5b-exposure-reconciliation.md`.

### S4b exposure added by this run

| Split | Group | What was exposed | When | Effect on independence |
|---|---|---|---|---|
| pre-run smoke | `task_group_001` | one dev solve of `train/001` with the approved group-001 champion (live smoke, `1 passed in 170.29 s`, evidence `s4b-smoke/attempts/gdp-356804be`) | before the first campaign solve | A dev task, already exposed; recorded separately from campaign attempts, outside the campaign caps |
| dev | `task_group_001` | 36 dev solves: 9 champion + 27 candidate (3 evaluated candidates × 9); each of the 3 proposals received the champion's 9 dev records with `input`, `output` and `feedback`. Candidate traces were not passed to the proposer; prior paired deltas reached D2 as numeric state | first attempt start 14:45:03, last ended 16:35:28 CST (2026-11-06) | Dev is already adaptive; 36 more solves on an exposed split, no new split |
| dev | `task_group_003` | 36 dev solves: 9 champion + 27 candidate (3 evaluated candidates × 9); 3 proposals, each with the champion's 9 dev records | 14:45:03–16:32:47 CST (2026-11-06) | As above |
| adjudication | `task_group_001` | `train/004`, `train/005` — 3 runs × 2 arms = 12 solves, 0 failures | 16:37:06–19:11:55 CST (whole final phase) | Third read of this group's adjudication pair (S4 final, S5b final, now S4b); further reuse, no independence |
| adjudication | `task_group_003` | `train/004`, `train/005` — 3 runs × 2 arms = 12 solves, 0 failures | 16:37:01–19:22:26 CST (whole final phase) | Second read (S4 final, now S4b); further reuse, no independence |
| holdout | `task_group_001` | `test/001`–`005` — 3 runs × 2 arms = 30 solves, 0 failures | 16:37:06–19:11:55 CST (whole final phase) | Third read of this group's holdout (S4, S5b, now S4b); further reuse, no independence |
| holdout | `task_group_003` | `test/001`–`005` — 3 runs × 2 arms = 30 solves, 0 failures | 16:37:01–19:22:26 CST (whole final phase) | Second read (S4, now S4b); further reuse, no independence |

- At most 9 champion dev solves plus 9 candidate dev solves per attempt per group
  (≤ 36 solver attempts per group), and — only if a group selects a candidate — the
  42 final solves. Dev, as measured: 36 / 36 solver attempts per group, 72 dev
  solves in total, plus the 1 pre-run smoke solve. Both groups selected a
  candidate, so each ran the 42 final solves: 12 adjudication + 30 holdout per
  group, 84 in total, 0 failure rows. Terminal reconciliation, recorded before the
  next run: `pilot-config/e1c/s4b-exposure-reconciliation.md` — `task_group_001`
  36 dev / 1 smoke / 12 adjudication / 30 holdout; `task_group_003` 36 / 0 / 12 / 30;
  both `failed_gate`. It matches the counts above.
- The smoke solver attempt is recorded separately from campaign attempts, outside
  the campaign caps. Model-request retries are recorded separately and are not
  additional solver attempts.
- Proposer input is the champion text, the dev item ids and the dev records with
  `input`, `output` and `feedback`; never adjudication or holdout material.
- D2 receives numeric state only (counts, budget and any prior paired delta); no
  entry text and no task text.

**No independence, replication or compounding-efficacy claim is made.** Every screen
used here is already adaptive; no split is fresh. The adjudication and holdout
splits of groups 001 and 003 were read once in the S4 final and again by S5b for
group 001 before this campaign started. Whatever S4b reads there is **further
reuse**, disclosed as such: it cannot make those screens unseen, and it cannot turn
a retention pass into an independent confirmation. S4b does not recover a fresh
split, does not replicate S4 or S5b, and its result — positive or negative — does
not show that continuation compounds.

Source: `pilot-004/task_group_00N/public/results.jsonl`, `evidence/<id>/attempt.json`,
`proposer/<id>/dev/request.json`, `decisions.jsonl`,
`final/task_group_00N/observations.jsonl`, `s4b-smoke/attempts/gdp-356804be`;
`docs/prereg-s4b-addendum.md` §4; `docs/results/e1a-s5b-evaluate-first.md`.

## Named local exceptions (carried, not re-derived)

| Exception | Where frozen | Effect on this report |
|---|---|---|
| Complete first-run scope (3 read-only groups, 3 attempts per task), "NAMED LOCAL EXCEPTION — diagnostic only" | `docs/prereg-gdpevo-pilot.md`, "Objective and diagnostic scope" | Scope is cost-sized; no significance or power claim. S4b runs two of the three, so pooled tables reach the "at least two groups" rule at best at its lower bound |
| Group selection: first three read-only IDs, "**not** representative sampling" | same | Results describe these groups only |
| Group 002 excluded from this campaign: no approved champion | `docs/prereg-s4b-addendum.md` §2.2 | Two groups, one exclusion; its outcome is not part of this campaign |
| Continuation champion = the approved S4 candidate, loaded through the existing hash-checked loader | `docs/prereg-s4b-addendum.md` §2.1 | No new loader, format or validation is introduced |
| Carving map (NAMED LOCAL EXCEPTION, no seed): dev `train/001`–`003`, adjudication `train/004`–`005`, holdout `test/001`–`005` | `docs/prereg-gdpevo-pilot.md` | 9 dev, 6 adjudication, 15 holdout tasks across the three groups; 6 / 4 / 10 across the two campaign groups |
| Model `gpt-6.1-sol` at `xhigh` instead of upstream `gpt-5.5` (the hosted model has no weight hash) | same | Not the upstream model; served-model identity is recorded from the trace |
| Evaluator timeout 3600 s "(NAMED LOCAL EXCEPTION: upstream gives none)" | same | Our value; grading was not the bottleneck in prior runs |
| Campaign spend metered as model calls per group campaign, cap 42, because "this route has no verified price (NAMED LOCAL EXCEPTION: accounting unit)" | same, "Caps"; `docs/prereg-s4b-addendum.md` §2.3 | Cost is calls and tokens; no billed cost |
| Proposer transient-error retries (2 retries on 408/409/429/≥500) count as one logical call; failed attempts' tokens may be unknown, so 42 is not an HTTP bound | `docs/prereg-s4b-addendum.md` §3 | Cost is logical calls, not requests |
| Dev re-run dropped and control arm dropped: "The report now reads dev from the optimise archive instead"; noise is the champion's spread (upstream `std@3`) | `docs/prereg-s4-addendum.md`, adopted by reference | Dev rows come from the optimise archive; noise is the champion's three dev runs |
| Artifact is exactly UTF-8 `SKILL.md`; support files are rejected (NAMED LOCAL RESTRICTION) | `docs/prereg-gdpevo-pilot.md` | No universal skill is implied across groups |

## Limitation (continuation)

Stated here as a limitation, not as a result:

- **The champion is a previously approved artifact, not a frozen seed.** Every
  screen it was selected on is already adaptive, and S4b reads the same screens
  again. The chain seed → N → N+1 is recorded in the run records; that is a lineage
  fact, not evidence that continuing from N improves on N.
- At most two groups can carry a candidate, so no third group is available to
  absorb a no-candidate outcome, and a pooled comparison can only reach the lower
  bound of the reporting rule.
- **No independence, replication or compounding-efficacy claim is made.** The S4b
  result — positive or negative — does not show that continuation compounds, and it
  is not a replication of S4 or S5b.

## Not covered

- No independence, replication or compounding-efficacy claim: every screen used
  here was already adaptive before this campaign.
- No significance, power or p-value: the pooled rows use two groups (4 ordered
  group draws), reported only as the frozen estimator returned them.
- No second retained update in either group: both ended `failed_gate`, so no
  approval, `apply(hash)` or champion change exists from S4b.
- No result for `task_group_002`: it has no approved champion and is excluded from
  this campaign, not tested and not re-run from the seed.
- No statistical claim of any kind, and no release to any product.
- No cross-product transfer and no second host: single adapter on one test bed.
- No merge/revise or cumulative-growth claim: the artifact is exactly `SKILL.md`,
  one candidate per campaign.
