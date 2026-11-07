# E1a-S5b: memory/skill library with drafts evaluated before admission

Re-run of slice S5 (`docs/results/e1a-two-artifact.md`, issue #6) on the changed
path of issue #45: the D4 pre-evaluation veto is retired, so a valid draft becomes
the candidate library and the existing paired dev evaluation decides. One campaign
per group under the frozen pre-registration `docs/prereg-gdpevo-pilot.md`, the S5
amendment `docs/prereg-s5-addendum.md` and the S5b amendment
`docs/prereg-s5b-addendum.md`. This is a diagnostic feasibility and cost run, not a
statistical claim and not an efficacy comparison.

Status: **one group closed `updated`; one group closed with no improvement; one
group is an operational STOP.** `task_group_001` selected `db7af325…` after three
evaluated attempts; its final phase completed 42 graded solves (12 adjudication + 30
holdout) with 0 failure rows, passed zero-margin retention on adjudication, and closed
`updated` after hash-bound owner approval. `task_group_002` closed `no_improvement`
after three evaluated attempts that each scored below the champion. `task_group_003`
stopped operationally when its proposer model call returned HTTP 502; it is reported
as an operational STOP, never as a negative result. The S5b addendum §5 checklist is below, filled from the
run records.

## Diagnostic only

The pre-registration ("Uncertainty and unchanged control") fixes the scope at 3
read-only groups. With 3 groups the smallest exact two-sided paired p-value is 0.25
and the bootstrap has only 27 ordered group draws, so no significance or power claim
is made. Paired tables require at least two groups with a candidate; this run has
one (`task_group_001`), so every pooled row is `unavailable` and no bootstrap is
computed.

## What changed in this re-run (S5b addendum §2)

| Item | S5 (`pilot-002`) | S5b (`pilot-003`) |
|---|---|---|
| D4 admission in PROPOSE | one call per attempt, `discard` vetoed the draft | call removed; no D4 record in this run |
| Entry measured on dev | never (0 of 3 attempts reached evaluation) | every attempt that produced a valid, non-duplicate draft |
| Decision on an attempt | `no_candidate` (D4 `discard`) | `dev_pass` or `dev_regression` from the paired dev delta |
| Spend cap per group | 45 (`36 + 3 + 3 + 3 D4`) | 45, unchanged; the 3 D4 slots are unused headroom |
| Everything else | groups, carving map, metric, retention, estimator, isolation, final phase | unchanged (S5 addendum §2a, adopted by reference) |

The retirement is the remedy the S5 addendum deferred to a later slice (§9.4,
issue #45). No acceptance rule was altered: selection is still the zero-margin
paired dev rule, and acceptance is still the trimmed final phase plus hash-bound
owner approval.

## Scope and frozen inputs

Per the pre-registration ("Objective and diagnostic scope", "Frozen inputs,
artifact and carving rule") and the S5/S5b amendments.

| Item | Frozen value |
|---|---|
| GDPevo revision | `5082a777379156a048881e94940d640702e5e09a` (pinned checkout, unchanged from S4/S5) |
| Run commit | `f67a45af3f0c34af207fd603e648bad4df655b93` (clean detached worktree, `pilot-code-f67a45a…`) |
| Groups (read-only, first three by ID) | `task_group_001`, `task_group_002`, `task_group_003` |
| Dev tasks per group | 3 (`train/001`–`003`) |
| Adjudication tasks per group | 2 (`train/004`–`005`) |
| Holdout tasks per group | 5 (`test/001`–`005`) |
| Attempts per task | 3 runs per task (`RUNS = 3`) |
| Arms in the final phase | champion and candidate only (control arm dropped by the S4 addendum) |
| Champion artifact | the empty seed library `pilot-config/s5-seed-library.json`, sha256 `9399b563f5490e626828287e2358bce8abeb4c4a19f6b9afa54a6994fe9adeee`; content `{"components": {}, "media_type": "application/json", "parent_ids": []}` |
| Champion candidate ID | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (all three groups; `content_id({})` for the empty library) |
| Rendered champion artifact staged to the solver | `# Memory / skill library\n`, 25 bytes, sha256 `04250b5d069ca2f20252345cae5a1c80a77daf6aaa76f222e5ba66331782920d` |
| Manifest hash (`shasum -a 256` of each group's `manifest.json`) | `001` `9ca0e700bba654aaffe37bcef7adb1f2d5b61d34b920f37e3aca0085f627a37a`; `002` `aedea146fc681e808548c78848266668218a75039b94f61cb8a44c1d3ff4efb3`; `003` `eac5ba2fbfee4dfae0d51a262355498141ef51e0c9907172843e000f35f0bc22` |
| Manifest coverage | `001` 60 file hashes over 10 tasks (6 each); `002` 60 over 10; `003` 82 over 10 (8–9 each) |
| Bootstrap RNG entropy | `24098377403422517637253708555914377847`, written to `pilot-003/entropy.json` at 2026-11-06 12:00:11 CST — after groups 001 and 002 closed (last `campaign.json` 11:59:35 CST) and group 003 stopped operationally with its campaign record still `open`. No bootstrap was computed. |

Source: `pilot-003/task_group_00{1,2,3}/campaign.json`, `manifest.json`,
`evidence/<id>/stage-manifest.json`; `pilot-config/config-s5b.json` and
`s5-seed-library.json` (both re-hashed); `pilot-003/entropy.json`.

## Pre-run STOP evidence

Per the pre-registration ("GEPA dependency and verification"). Any miss is a STOP.

| Pre-run STOP | Status | Evidence |
|---|---|---|
| Runner merged; repeated-run identities, reservations, aggregation and isolation verified by its tests plus one live smoke test | Tests held; live smoke not re-run for this code | Run tree at `f67a45a`, which carries #45 and the S5b addendum. 555 tests collect at that commit; `tests/adapters/test_gdpevo_memory.py` (470 lines) covers the adapter. **No live smoke solve exists for S5b**: no smoke run directory and no log records one, and the launcher script runs calibration replay then the three campaigns directly. The most recent live smoke is the S5 pre-run smoke (`s5-smoke`, 2026-11-06 00:50 CST) on the S5 code. Stated as an evidence gap, not as a pass. |
| Complete per-task manifest generated by the runner and recorded with the results | Held | `task_group_00N/manifest.json` as above; per-attempt image IDs in `evidence/<id>/image-ids.txt` |
| Calibration replay reproduces byte-identically | Held | Prereg calibration task `task_group_001/train/001`, answer sha256 `5eb5cc630e4f69d1892b2fe721a593b8eb83513c96b723ff4c0f756e518ae96b`. Replays ran once per group at campaign start (`gdp-c1c1dc1a`, `gdp-b96078de`, `gdp-ee1dd40a`, all 10:03:19 CST) and once per group at final-phase initialisation (`gdp-ca0f29e4` for 001, `gdp-dc3b0a16` for 002). All five `calibration-score.json` files hash to `12308ca22e257b47c05099acec8679a9a06f2205c99870578885098adbf6205e` — the frozen value, `earned 8 / max 15`, `total_score 0.533333`. |

Source: `pilot-003/task_group_00N/manifest.json`, `evidence/<id>/calibration-answer.json`,
`evidence/<id>/calibration-score.json`, `final/task_group_00N/evidence/<id>/calibration-score.json`;
`pilot-config/launch-s5b-optimise.sh`, `launch-s5b-final.sh`; prereg "GEPA dependency and verification".

## Code identity

Per the S5b addendum §3. Two hashes, one formula (`pilot._code_hash`), recorded in
`pilot-003-logs/code-identity.txt` before the first solve (10:03:02 CST; earliest
attempt start 10:03:52 CST) and recomputed here on the run tree
`pilot-code-f67a45af3f0c34af207fd603e648bad4df655b93` at `f67a45a`.

| Identity | Recorded | Recomputed | Compared with |
|---|---|---|---|
| full code hash | `021c1bb3364ba6b89b8598ed639dc0c236479415d29ce8742d94d647990d006e` | `021c1bb3…9006e` (equal) | every `campaign.json` `code_hash` — equal in all three groups; the S5 full hash `81e2d85d…a070f` differs |
| kernel-only hash (`exclude=("adapters",)`) | `2781ad329f787e3c2f3e2eb2e482f03b661b1413df83f4abbe389b472599f3e8` | `2781ad32…99f3e8` (equal) | S4's `e8d7b2b5…c4d209` and S5's `e8d7b2b5…c4d209` — **both differ, as §3 predicted** |
| campaign git SHA | `f67a45af3f0c34af207fd603e648bad4df655b93` | `git rev-parse HEAD` equal; worktree clean | — |
| per-group `evaluator_hash` | — | `001` `d5c1546cf93f750445d78209a3d568fb522b833dab6683ee83fce3ba74459e57`; `002` `1a60d2c36e994a210019b8644340e5d68199c8aadbfaf658eec7f5624ac2b694`; `003` not recorded (campaign left open) | `campaign.json` and `outcomes.jsonl` agree per group; both differ from S5's |

Recompute command, run inside `pilot-code-f67a45af3f0c34af207fd603e648bad4df655b93`:

```
uv run python -c "from rsi_kernel.adapters.gdpevo.pilot import _code_hash; print(_code_hash()); print(_code_hash(exclude=('adapters',)))"
```

Kernel drift is confined to the #43 change that §3 named in advance:

| Path set | diff `7919829` (S4) … `f67a45a` | diff `765f1d8` (S5) … `f67a45a` |
|---|---|---|
| `src/rsi_kernel/` excluding `adapters/` | `loop.py` only, +6 / −4 | `loop.py` only, +6 / −4 |
| `uv.lock` | empty (sha256 `5b2763277e5f320d861bc8a3f01f612a6d3f65904db1afedff321b19222c1c4a` at both commits) | empty |

The +6 / −4 in `loop.py` is the `code_hash` field on `ApprovalRequest` /
`ApprovalRecord`, the new `accept(code_hash=...)` parameter and the four-way match
in the approval comparison. No other kernel file changed during the run, so there
is no mid-run drift STOP.

**This run does not claim an unchanged kernel.** The S5 addendum §8 "empty kernel
diff" premise applied to S5 (`pilot-002`); §3 of the S5b addendum records that the
kernel-only hash must change, and it did. The E1a statement this run supports is
narrower: the memory artifact again ran on a kernel that differs from S4's only by
the approval-hash binding.

Source: `pilot-003-logs/code-identity.txt`; `pilot-003/task_group_00N/campaign.json`,
`outcomes.jsonl`; recompute and `git diff --numstat` in the run tree;
`docs/prereg-s5b-addendum.md` §3; `docs/results/gdpevo-pilot.md` "Code identity".

## Runtime pins

Per the pre-registration ("Frozen inputs, artifact and carving rule").

| Pin | Frozen value | Verified at run |
|---|---|---|
| Solver image base digest | `python:3.12-slim@sha256:b224e2fe306f9d303251ada22961635e5b52a69c0414a0050611be31c59f5f5b` | the `FROM` line carries that digest in all 84 staged `build/Dockerfile` files of the campaign tree (81 dev attempts + 3 calibration replays), and in every final-phase one staged so far |
| Solver CLI release and asset hashes | Codex CLI 0.166.0; `codex-aarch64-unknown-linux-musl.tar.gz` `94eb707605ec2646b2e05b7edf7c4e7b3ccf02b16237c34ae9beb8cfb7f810a9`; `bwrap-…` `b59c26ee2cc939a1f3df81b639fcc4fb965609bdc704ca85777c168c12cfeb26`; `codex-code-mode-host-…` `ac98d1f878e353a16cba711fd47bfef2f6c814109bdd819ee2b6b6d6a19701e7` | identical in every staged `Dockerfile`; every solver trace reports `cli_version` 0.166.0 and `model_provider` proxy |
| Served model identity (from the trace) | `gpt-6.1-sol` via the local model proxy | all 81 campaign `measurement.json` files record `model: gpt-6.1-sol`, `model_provider: proxy`; all 81 dev solver traces report provider `proxy` |
| Reasoning effort | `xhigh` | every solver trace carries `"reasoning_effort":"xhigh"` |
| Solver wall-time limit | 3600 s per attempt | observed elapsed 77.3 s min / 232.1 s max over the 81 dev attempts; none near the limit |
| Evaluator timeout | 3600 s (NAMED LOCAL EXCEPTION) | no evaluator timeout recorded |
| Spend cap (calls per group campaign) | 45 (`36 solver + 3 proposer + 3 D2 + 3 unused D4 slots`) | observed 42 / 42 / 11 per group; no group stopped on `spend_cap` |
| Evaluator cap (item-evaluations per group) | 36 | `evaluator_items_used` is 36 in both closed `campaign.json` files — the cap exactly filled, as §2.2 anticipated for the worst case. `task_group_003` stopped before writing the field; its 9 solver attempts are the 9 item-evaluations seen in its evidence |
| Docker version | — | `29.5.2` in every group; `image-platforms.txt` `linux/arm64` |

Source: `pilot-003/task_group_00N/evidence/<id>/build/Dockerfile`, `measurement.json`,
`image-ids.txt`, `image-platforms.txt`, `docker-version.txt`, `attempt-timing.json`,
solver trace `session_meta`, `campaign.json`; `docs/prereg-s5b-addendum.md` §2.2.

## Dev campaign

Only dev scores guided proposals and selection. Dev was **not** re-run in the final
phase (S4 addendum, adopted by S5 addendum §2a); every row below is read from the
optimise archive.

### Champion dev rows per group

All 9 rows per group carry the champion candidate ID; the champion is the empty
library, so its rows are the seed's. Aggregation is the pre-registration's rule:
mean over the 3 runs per task, then the equal-task mean per group.

| Group | `train/001` (runs 0/1/2) | `train/002` (runs 0/1/2) | `train/003` (runs 0/1/2) | Champion macro-mean |
|---|---|---|---|---|
| `task_group_001` | 0.533333 / 0.533333 / 0.533333 → 0.533333 | 1.000000 / 1.000000 / 1.000000 → 1.000000 | 0.857143 / 0.214286 / 0.214286 → 0.428572 | 0.653968 |
| `task_group_002` | 1.000000 / 1.000000 / 1.000000 → 1.000000 | 0.833333 / 0.833333 / 0.833333 → 0.833333 | 0.266667 / 0.266667 / 0.266667 → 0.266667 | 0.700000 |
| `task_group_003` | 0.937500 / 0.937500 / 0.937500 → 0.937500 | 1.000000 / 1.000000 / 1.000000 → 1.000000 | 0.588235 / 0.588235 / 0.588235 → 0.588235 | 0.841912 |

Equal-group macro-mean over the three groups: 0.731960.

Champion pass counts (score exactly 1.0 over 9 dev observations) are 3 / 3 / 3 —
the `c1.dev_pass_count` every D2 state carries below.

Source: `pilot-003/task_group_00N/public/results.jsonl` (9 champion records per group);
`evidence/<id>/score.json` agrees per attempt.

### Noise: the champion's dev run-to-run spread

The control arm is gone, so run-to-run noise is the champion's own dev spread — the
population standard deviation over its three runs per task, the upstream `std@3`
statistic (`metric_and_scoring.md:115–139`). The champion dev arm is the same code
as S5's `pilot-002` champion arm.

| Group | `train/001` | `train/002` | `train/003` | Mean per-task spread (`std@3`) | Spread of the three run-level group means |
|---|---|---|---|---|---|
| `task_group_001` | 0 | 0 | 0.303046 | 0.101015 | 0.101015 |
| `task_group_002` | 0 | 0 | 0 | 0 | 0 |
| `task_group_003` | 0 | 0 | 0 | 0 | 0 |

- Pooled mean per-task spread over the nine dev tasks across groups: 0.033672.
- Groups 002 and 003 are constant across runs; group 001 varies only on
  `train/003`, where run 0 scored 0.857143 and runs 1 and 2 scored 0.214286.
- The noise statistics and the candidate deltas are different quantities (per-task
  run-to-run spread versus a macro paired difference). Neither is used as a
  threshold here, and no inference is drawn from comparing them.

Source: `pilot-003/task_group_00N/public/results.jsonl`; all means and population
standard deviations computed from those scores.

### Per group, selection and stop

| Group | Champion dev mean | Selected candidate | Attempts | Attempt outcomes | Stop reason | Campaign outcome |
|---|---|---|---|---|---|---|
| `task_group_001` | 0.653968 | `db7af325…` | 3 | `dev_pass` ×3 | `attempts` | `selected` |
| `task_group_002` | 0.700000 | none | 3 | `dev_regression` ×3 | `attempts` | `no_improvement` |
| `task_group_003` | 0.841912 | none | 1 (interrupted) | none recorded | — (`status: "open"`) | operational STOP |

- `task_group_001` had three non-negative paired deltas; the zero-margin rule keeps
  the best, `db7af32578f5bcd75114309a0088988bb23e4dcfa4b38a2cca4e314ecd508144` (+0.257143).
  Its `parent_ids` is the champion ID, as stored in `campaign.json`.
- `task_group_002` had three negative deltas, so no attempt was eligible for
  selection. After exhausting the three-proposal budget, the campaign closed
  `no_improvement` and ran no final solves.
- `task_group_003` never reached an attempt outcome: the proposer call failed before
  a draft existed (section "Operational STOP").
- `stop_reason` is `attempts` (the 3-proposal budget) in both closed groups, not the
  spend or evaluation cap.

Source: `pilot-003/task_group_00N/campaign.json`, `outcomes.jsonl`;
`pilot-003-logs/task_group_00{1,2}.out`.

### Per attempt: was the candidate evaluated, and what was its paired dev delta

Required by S5b addendum §5. `yes` means a valid, non-duplicate draft became the
candidate and 9 dev solves (3 tasks × 3 runs) were run against it; the delta is the
candidate − champion mean over dev, exactly the `mean_delta` in `outcomes.jsonl`.

| Group | Attempt | Candidate | Candidate evaluated | Paired dev delta | Selection outcome |
|---|---|---|---|---|---|
| `task_group_001` | 1 | `eaea9482…` | yes | +0.226455 | `dev_pass`, superseded by attempt 3 |
| `task_group_001` | 2 | `f37f7e45…` | yes | +0.202116 | `dev_pass`, superseded by attempt 3 |
| `task_group_001` | 3 | `db7af325…` | yes | +0.257143 | `dev_pass`, **selected** |
| `task_group_002` | 1 | `2e1f3f7c…` | yes | −0.018519 | `dev_regression` |
| `task_group_002` | 2 | `0982e682…` | yes | −0.012346 | `dev_regression` |
| `task_group_002` | 3 | `bded7be2…` | yes | −0.018519 | `dev_regression` |
| `task_group_003` | 1 | — | **no** — proposer model call returned HTTP 502, no draft returned, so no candidate was built and no dev evaluation ran | not recorded | none (operational STOP) |

6 of 7 attempts were evaluated; the one that was not failed operationally, not on a
rule. No attempt was rejected for an invalid brief, a duplicate, a hash mismatch or
a cap: `calls.jsonl` records exactly 3 proposer and 3 D2 calls per closed group, and
every attempt in groups 001 and 002 produced a scored candidate.

### Per-attempt paired detail, `task_group_001`

The only group with a candidate; per-task means are over the 3 runs.

| Task | Champion mean | Candidate `db7af325…` | Difference |
|---|---|---|---|
| `train/001` | 0.533333 | 0.733333 | +0.200000 |
| `train/002` | 1.000000 | 1.000000 | 0.000000 |
| `train/003` | 0.428572 | 1.000000 | +0.571428 |
| **Macro** | **0.653968** | **0.911111** | **+0.257143** |

Two smaller deltas from the superseded attempts illustrate how little separates
them on two of the three tasks: `f37f7e45` scored 0.711111 / 1.000000 / 0.857143
(+0.202116) and `eaea9482` scored 0.688889 / 1.000000 / 0.952381 (+0.226455). The
selection is by the registered rule (highest non-negative delta), not by this
table.

### Dev split table

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| dev | `unavailable` | 0.653968 (one paired group) | unavailable (pooled) | unavailable | unavailable | unavailable | not recorded | not applicable (dev is selection, not the retention gate; group delta +0.257143) |

- `unavailable` is the pre-registered wording when fewer than two groups have a
  candidate (S5 addendum §2a; S5b addendum §5). Here exactly **one** group does, so
  no pooled macro paired difference, no bootstrap and no interval exist. The
  estimator resamples group indices, and one group gives a single draw.
- `task_group_001`'s own paired dev delta is **+0.257143** (above). It is a
  single-group descriptive statistic, not the pooled estimate.
- The champion column is the `task_group_001` champion mean, because that is the
  only group with a candidate to pair against. The S5 report's dev row averaged all
  three groups with no candidate present; the two rows therefore describe different
  group sets and are not comparable.
- Dev retention is the zero-margin rule on that delta: +0.257143 ≥ 0, so the
  candidate was retained by the campaign. Formal retention and acceptance were decided in
  the final phase (below): `task_group_001` closed `updated`.

Source: `pilot-003/task_group_00N/public/results.jsonl`, `outcomes.jsonl`,
`decisions.jsonl`.

## Adjudication

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| adjudication | `unavailable` (pooled); group outcome `updated` | 0.615385 (one paired group) | 0.818376 (one paired group) | +0.202992 (single-group difference) | unavailable | unavailable | not recorded | Yes (`task_group_001`) |

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_001` | `train/004` | 0.230769 | 0.692308 | +0.461539 |
| `task_group_001` | `train/005` | 1.000000 | 0.944444 | −0.055556 |
| `task_group_001` | group mean | 0.615385 | 0.818376 | +0.202992 |
| `task_group_002` | — | not run (no candidate) | unavailable | unavailable |
| `task_group_003` | — | not run (operational STOP) | unavailable | unavailable |

- `task_group_001`: the final phase completed at the pinned `f67a45a`: 42 graded
  solves (`train/004`, `train/005`, `test/001`–`005`; 3 runs; champion and
  candidate), in the order run → task id → arm, 21 per arm, every
  `(item_id, run, arm)` unique, 0 failure rows. 12 of the 42 are adjudication
  (2 tasks × 3 runs × 2 arms). The calibration replay ran at initialisation
  (`gdp-ca0f29e4`, hash `12308ca2…205e`).
- Zero-margin retention on adjudication: candidate group mean 0.818376 ≥ champion
  0.615385, so retention passed. The pooled row is `unavailable` because only one
  group has a candidate: the pilot's `report` returns
  `"comparison": "unavailable"`, "fewer than two groups with a selected candidate",
  for every split, and `report_table`'s bootstrap raises SciPy's two-observation
  error on one group. No interval is reported.
- The adjudication gain comes from `train/004` (+0.461539); `train/005` is below the
  champion (−0.055556), where the champion already scored 1.0 in all three runs.
- `task_group_002`: no candidate was frozen, so `final_phase` ran no solves. The
  group's final evidence directory holds only the calibration replay
  (`gdp-dc3b0a16`), `observations.jsonl` is 0 bytes, and `acceptance.json` records
  `{"outcome": "no_improvement"}`. This is the registered no-candidate path.
- `task_group_003`: no final phase was started; the campaign is `open` and the group
  has no `final/` directory.

Source: `pilot-003/final/task_group_001/observations.jsonl`, `final/task_group_002/observations.jsonl`,
`final/task_group_00N/evidence/<id>/calibration-score.json`, `task_group_00{1,2}/acceptance.json`;
`pilot-003-logs/final-task_group_00{1,2}.{out,err}` (`{"task_group_001": "updated"}`,
`{"task_group_002": "no_improvement"}`, both stderr empty). Means computed with
`rsi_kernel/analysis.py` (`aggregate`, `retention_per_group`) at `f67a45a`.

## Holdout

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| holdout | `unavailable` (pooled); group outcome `updated` | 0.448264 (one paired group) | 0.608795 (one paired group) | +0.160531 (single-group difference) | unavailable | unavailable | not recorded | Yes (`task_group_001`; reported, not a gate) |

- 30 of the 42 final solves are holdout (5 tasks × 3 runs × 2 arms), all from
  `task_group_001`. No holdout record exists for `task_group_002` or
  `task_group_003`, and none is expected.
- No holdout score has been used to choose anything: the candidate was frozen at
  campaign close, before the final phase started. Holdout remains report-only.
- The pooled row is `unavailable` for the same one-group reason as adjudication.

### Per-task holdout diagnostics

Diagnostic only. Candidate mean minus champion mean over the three holdout runs of
each task.

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_001` | `test/001` | 0.562500 | 0.687500 | +0.125000 |
| `task_group_001` | `test/002` | 0.590909 | 0.590909 | 0.000000 |
| `task_group_001` | `test/003` | 0.230769 | 0.384615 | +0.153846 |
| `task_group_001` | `test/004` | 0.142857 | 0.809524 | +0.666667 |
| `task_group_001` | `test/005` | 0.714286 | 0.571429 | −0.142857 |
| `task_group_002` | — | not run (no candidate) | unavailable | unavailable |
| `task_group_003` | — | not run (operational STOP) | unavailable | unavailable |

- The holdout gain is concentrated in one task: `test/004` contributes +0.666667 of
  the five task differences, which sum to +0.802656 (group difference +0.160531).
  Without `test/004` the other four tasks sum to +0.135989.
- `test/005` is below the champion (−0.142857); `test/002` is an exact tie.

Source: `pilot-003/final/task_group_001/observations.jsonl` (30 holdout records,
`(item_id, run, arm)` unique), `task_group_001/acceptance.json`. Means computed with
`rsi_kernel/analysis.py` (`aggregate`, `retention_per_group`) at `f67a45a`.

## D4: admission, removed on this path

The S5b addendum §5 drops the D4-versus-baseline item from the checklist because no
D4 call exists to compare. That is what the records show:

| Quantity | Value |
|---|---|
| D4 records logged | 0 (all three groups) |
| D4 calls in `calls.jsonl` | 0 |
| D2 records | 7 (3 / 3 / 1), each with only a `D2` question in its envelope |
| Admission path used | validated `add` on the candidate library, then the paired dev evaluation |

Every `decisions.jsonl` envelope asks one question, `D2`, and offers `{c1, none}`.
No envelope carries an admission question, and no decision record carries entry text.

**The §9.4 limitation is addressed, not restated as a result.** In S5 the D4
envelope described the champion only, so a `discard` said nothing measurable about
the draft and no entry was ever evaluated. Here the draft is measured: each valid
draft became the candidate library and its 9 dev solves produced a paired delta
reported in "Per attempt" above. The claim this supports is limited to that: the
entries were evaluated. It says nothing about whether the surviving entry is good
beyond its dev delta, and no evaluation-before-admission mechanism is claimed to be
superior to the retired one.

Source: `pilot-003/task_group_00N/decisions.jsonl`, `calls.jsonl`,
`proposer/<id>/out/result.json`; `docs/prereg-s5b-addendum.md` §2.1, §5.

## D2: which component to change (Jev vs the deterministic baseline)

Advisory only, as in S4 and S5. New in this run: from attempt 2 on, the D2 state
carries the previous attempt's paired dev delta (`c1.dev_paired_score_delta`), which
S5 never produced because no candidate was evaluated.

| Group | Jev D2 choice | Baseline D2 choice | Agree |
|---|---|---|---|
| `task_group_001` | `c1`, `c1`, `c1` | `c1`, `c1`, `c1` | 3 of 3 |
| `task_group_002` | `c1`, `c1`, `c1` | `c1`, `c1`, `c1` | 3 of 3 |
| `task_group_003` | `c1` | `c1` | 1 of 1 |

| Quantity | Value |
|---|---|
| D2 records logged | 7 (3 / 3 / 1) |
| Baseline decisions | 7 (one shadow `baseline_answer` per record) |
| Agreements | 7 |
| Timeouts or malformed answers falling back at D2 | 0 (no record carries `fallback_reason`) |
| `none` answers | 0 |
| States asked | `attempt_count` 0/1/2 with `budget_used` 9/18/27, `c1.dev_pass_count` 3, `c1.dev_fail_count` 6, plus `c1.dev_paired_score_delta` where a prior attempt produced one |

`task_group_001`'s attempt-2 and attempt-3 states carried +0.226455 and +0.202116;
`task_group_002`'s carried −0.018519 and −0.012346. Every D2 call chose the single
registered component `c1` regardless of the sign of that delta; the deterministic
baseline chose the same. D2 is advisory and no selection depended on it.

Source: `pilot-003/task_group_00N/decisions.jsonl`.

## Operational STOP: `task_group_003`

This group is **not** a negative result. It is an interrupted campaign.

| Fact | Record |
|---|---|
| Last champion dev solve ended | 10:28:11 CST (`train/003`), container exit 0 |
| Failing stage | proposer container, one model call |
| Error | `urllib.error.HTTPError: HTTP Error 502: Bad Gateway`, raised in the container's model client, surfacing as `RuntimeError: proposer container failed` in `gdpevo/pilot.py` |
| Consequence | no draft, no candidate, no dev evaluation, no attempt outcome |
| Campaign state | `campaign.json` == `{"status": "open"}`; `outcomes.jsonl` 0 bytes; `decisions.jsonl` holds one D2 record (seq 1) |
| Evidence retained | `task_group_003/proposer/gdp-0871e7f3/` including `proposer.log.stderr` and `dev/request.json`; 9 solver evidence dirs plus the calibration replay |
| Launcher exit | group 3 exit 1 (`pilot-003-logs/task_group_003.err`, 10:31:37 CST) |
| Spend charged | 11 calls (9 solver + 1 proposer + 1 D2); the failed proposer call is metered |

Under the frozen prereg's retention clause, "Operational or data failures block
acceptance", and the prereg has no re-run clause, the group was not re-run: no
rescue run, no added exposure. The fix went forward as a separate change, not as a
retry of this campaign: issue #57 (retry transient errors with the openai-python
default policy — 2 retries on 408/409/429/5xx), merged as PR #62. `task_group_003`
therefore has no outcome to report for this run, and its absence is not evidence
about the artifact or the group.

Source: `pilot-003/task_group_003/campaign.json`, `outcomes.jsonl`, `decisions.jsonl`,
`proposer/gdp-0871e7f3/proposer.log.stderr` (final line), `calls.jsonl`;
`pilot-003-logs/task_group_003.err`, `pilot-003-launch.log`; prereg "Retention and
acceptance".

## Comparison with S5

| Item | S5 (`pilot-002`) | S5b (`pilot-003`) |
|---|---|---|
| Attempts producing a candidate | 0 of 9 (D4 `discard` on all 9, 2 of them fallback) | 6 of 7 (the seventh failed operationally) |
| Dev evaluations of a candidate | 0 | 54 solver solves over 6 evaluated candidates |
| Groups with a selected candidate | 0 | 1 (`task_group_001`) |
| Dev deltas observed | none (all `mean_delta: null`) | +0.226455, +0.202116, +0.257143, −0.018519, −0.012346, −0.018519 |
| Final-phase solves | 0 | 42 for `task_group_001` (completed, 0 failure rows) |
| Group outcome | `no_improvement` ×3 | `updated` / `no_improvement` / operational STOP |

What this comparison supports:

- **The S5 gap is closed at the mechanism level.** S5's limitation was that D4
  admission could not see the proposed entry, so no draft was ever measured. In S5b
  every draft that reached the evaluation stage was measured, and the paired dev
  rule decided. That is #45 doing what the S5 addendum §9.4 deferred.
- **The all-discard pattern of S5 does not repeat.** Nine D4 responses in S5, of
  which seven agreed with the `discard` baseline and two were fallback discards;
  here there are no D4 responses at all, and three of six evaluated attempts cleared
  the zero-margin rule.
- **It is not a like-for-like efficacy comparison.** The two runs differ in which
  mechanism gated admission, in code hash (both identities differ), in evaluator
  hashes, in how many attempts were evaluated, and in whether a final phase ran.
  Neither run's champion changed across the two runs (the empty library), but that
  does not make the two sets of deltas comparable as an A/B of the mechanism.

Source: `pilot-003/task_group_00N/*`; `docs/results/e1a-two-artifact.md` "D4",
"Cost", "Acceptance outcome"; `docs/prereg-s5b-addendum.md` §1, §6.

## Limitation (S5 addendum §2, quoted)

Stated here as a limitation, not as a result:

> **Limitation: live D4 is add/discard only**
>
> The unchanged kernel passes the same original champion to every proposal inside
> one campaign (`loop.py:run_campaign` -> `proposer(champion, ...)`). With an empty
> seed, every live D4 call therefore offers only `add` and `discard`: `merge` and
> `revise` require an existing registered entry, and only the selected candidate —
> not the champion — could carry one. Consequences, stated up front:
>
> - the S5 run yields **no merge/revise claim** and **no cumulative-growth claim**
>   (one admitted entry per attempt, from an empty library);
> - `merge`/`revise` remain covered by the adapter's write-guard tests only.

The premise still holds for S5b: the kernel is unchanged in `run_campaign`, so each
proposal in a campaign still sees the original empty champion, and each attempt can
add at most one entry. This run therefore also yields **no merge/revise claim and no
cumulative-growth claim**. The removal of D4 does not change that: with an empty
champion there was no entry to merge or revise, and no attempt produced a library
with more than one entry.

## Cost

Provider-metered token buckets as measured. A billed cost appears only if the
provider supplies a real billing record; no modelled price is reported.

| Stage | Solver attempts | Proposer calls | D2 calls | D4 calls | Calls against the 45 cap | Evaluator item-evaluations | Input tokens | Cached input tokens | Output tokens | Wall time |
|---|---|---|---|---|---|---|---|---|---|---|
| Campaign, `task_group_001` | 36 | 3 | 3 | 0 | **42 of 45** | 36 | 5,466,233 | 4,691,968 | 178,738 | 1.93 h (1.40 h of solver time) |
| Campaign, `task_group_002` | 36 | 3 | 3 | 0 | **42 of 45** | 36 | 5,795,332 | 4,962,304 | 139,772 | 1.66 h (1.18 h of solver time) |
| Campaign, `task_group_003` | 9 | 1 (failed, still metered) | 1 | 0 | **11 of 45** | 9 | 1,563,260 | 1,330,688 | 30,791 | 0.41 h (0.33 h of solver time) |
| Final phase, `task_group_001` | 42 | 0 | 0 | 0 | outside the campaign cap | 42 | 7,231,025 | 6,407,168 | 252,890 | 2.18 h (1.78 h of solver time) |
| Final phase, `task_group_002` | 0 | 0 | 0 | 0 | — | 0 | not recorded | not recorded | not recorded | not run (calibration replay only) |

| Item | Value |
|---|---|
| Proposer tokens, per group | `001` 25,410 input (0 cached) / 21,940 output (14,498 reasoning); `002` 21,792 / 15,333 (9,058 reasoning); `003` not recorded (`token_usage: null` on the failed call) |
| Reasoning output tokens (solver) | `001` 66,656; `002` 30,348; `003` 9,516 |
| Jev tokens | not recorded: all 7 Jev records (D2) carry `token_usage: null` |
| Calls per group against the 45 cap | 42 / 42 / 11; the three former D4 slots are unused headroom in both closed groups, and the cap is unchanged at 45 |
| Evaluator item-evaluations against the 36 cap | 36 and 36 recorded in the two closed groups (9 champion + 3 × 9 candidate, the exact worst case); `task_group_003` recorded no field and ran 9 |
| Billed cost (real billing record) | Not available: `measurement.json` records `cost_usd: null` on all 81 dev attempts |
| Estimated cost (modelled price, labelled estimate) | Not reported — no modelled price is given here. |
| Failed calls charged | 1 proposer call in `task_group_003` failed at HTTP 502 and is metered; all calls per group are metered, failed calls included by rule |
| Solver attempts failed | 0 of 81 (every dev attempt has `container_exit_code` 0) |

- Solver token totals are summed from the `solver` records in each `calls.jsonl` and
  agree exactly with the sum over that group's `measurement.json` files (all five
  buckets, all three groups).
- Diagnostic model calls outside the per-group campaign: none new for S5b.
  The five calibration replays (3 at campaign start, 2 at final initialisation)
  re-grade the recorded feasibility answer without a model call. Ordinary
  final-phase grading also makes no model call, but grades each newly produced
  solver prediction. The S5 pre-run smoke and S4-era smokes are prior exposure,
  counted in the exposure log.
- Wall time is the span from the first attempt start to the last attempt end in the
  group, from `attempt-timing.json`; the second figure is the sum of per-attempt
  elapsed solver seconds. Observed solver elapsed 77.3 s min / 232.1 s max; container
  exit 0 on all 81.

Source: `pilot-003/task_group_00N/calls.jsonl`, `evidence/<id>/measurement.json`,
`evidence/<id>/attempt-timing.json`, `campaign.json`, `decisions.jsonl`.

## Acceptance outcome

| Outcome | Reported | Reason |
|---|---|---|
| `updated` (approval bound to candidate, data, evaluator and code hashes) | 1 group (`task_group_001`) | `campaign.json` records `selected.id = db7af325…`, `stop_reason: "attempts"`; the 42-solve final phase completed with 0 failure rows, adjudication retention passed, the approval matches the request on all four hashes, and `acceptance.json` records `{"outcome": "updated"}` |
| `no_improvement` (no candidate, or candidate equals champion) | 1 group (`task_group_002`) | `campaign.json` records `outcome: "no_improvement"`, `selected: null`; all three attempts `dev_regression`; `final_phase` ran no solves; `acceptance.json` == `{"outcome": "no_improvement"}` |
| Operational STOP | 1 group (`task_group_003`) | Proposer HTTP 502; campaign left `open`; no acceptance record and none due, since report and acceptance for this group are blocked by the failure, not decided by it |
| `not_updated` (approval missing or mismatched) | 0 groups | `task_group_001`'s `approval.json` matches its `approval-request.json` on candidate, data, evaluator and code hash; no other group requested approval |
| `failed_gate` (record failures on either final split, or adjudication retention not met) | 0 groups | `task_group_001`'s 42 final records are complete and unique, and adjudication retention passed (0.818376 ≥ 0.615385) |

| Item | Value |
|---|---|
| Approval record | `task_group_001` only: `approval-request.json` (mtime 2026-11-06 14:11 CST) and `approval.json` (approver `Billy`, mtime 14:40 CST, written atomically). Owner reply 2026-11-06, verbatim "Go with your recom", to the lead's explicit "yes" recommendation. The approval file holds the approver name and hashes only; the wording is from the owner's message, not the run record |
| Approval binding | candidate `db7af325…508144`, data `d4e27d11…de444`, evaluator `d5c1546c…59e57`, code `021c1bb3…0d006e`; request and approval identical on all four (prereg "Approver", issue #42). No `rebind.json`: the frozen identity held |
| `apply(hash)` record | Record-only, called with `db7af325…`; the final-phase output is `{"task_group_001": "updated"}`. Its `record-only` decision goes to the run's private decision store, which this report does not read. It never replaces the champion or starts enforcement |
| Independent review of this report | pending, before the issue PR |

Keeping the champion is not counted as success. The `task_group_002` result means
the empty library stayed; its dev scores are the seed's.

Source: `pilot-003/task_group_00N/campaign.json`, `task_group_00{1,2}/acceptance.json`,
`task_group_001/approval-request.json`, `task_group_001/approval.json`,
`outcomes.jsonl`; `pilot-003-logs/*.out`.

## Adapter diff against the kernel

Descriptive only (S5 addendum §7, carried by S5b §5): file and line counts, with no
judgement attached and no "thin" threshold.

Against the frozen S4 commit `7919829` (the two-artifact comparison):

| Path set | Files at `f67a45a` | Lines at `f67a45a` | Changed files | Insertions | Deletions |
|---|---|---|---|---|---|
| `src/rsi_kernel/` excluding `adapters/` | 12 | 1,351 | 1 (`loop.py`) | 6 | 4 |
| `uv.lock` | 1 | — | 0 | 0 | 0 |
| `src/rsi_kernel/adapters/gdpevo_memory/` | 5 (`__init__.py`, `adapter.py`, `library.py`, `pilot.py`, `proposer.py`) | 339 (8 / 61 / 135 / 60 / 75) | 4 (`library.py` unchanged) | 116 | 18 |
| `src/rsi_kernel/adapters/gdpevo/` | 9 | 1,765 | 1 (`pilot.py`) | 296 | 111 |
| Both adapter packages | 14 | 2,104 | 5 | 412 | 129 |

Against the S5 run commit `765f1d8` (what this re-run changed):

| Path set | Changed files | Insertions | Deletions |
|---|---|---|---|
| `src/rsi_kernel/loop.py` | 1 | 6 | 4 |
| `src/rsi_kernel/adapters/gdpevo/pilot.py` | 1 | 5 | 2 |
| `src/rsi_kernel/adapters/gdpevo_memory/` | 3 (`__init__.py` +1/−1, `pilot.py` +5/−4, `proposer.py` +6/−11) | 12 | 16 |

- The `loop.py` change is the `code_hash` binding of #42 (merged before this run).
- The `gdpevo_memory` changes are the #45 removal of the D4 call from PROPOSE, the
  matching cap comment, and the host-side path that admits a valid draft and hands
  it to the existing paired evaluation; `proposer.py` loses the D4 envelope
  construction that lived beside the draft call.
- The `gdpevo/pilot.py` change is in the shared `final_phase`: it resolves the
  validated `code_hash` (frozen value or a rebind's `to`) and passes it to `accept()`,
  so an approval record binds the code identity. It changes no solve, no staging and
  no scoring, and `proposer` on the S4 path is untouched; the S4 numbers in
  `docs/results/gdpevo-pilot.md` therefore describe the same S4 flow.
- Outside `src/`, the range also changes `docs/prereg-s5b-addendum.md`,
  `tests/adapters/test_gdpevo_memory.py`, `tests/adapters/test_gdpevo_pilot.py`,
  `tests/test_loop.py` and `docs/results/gdpevo-pilot.md`.

Source: `git diff --numstat`, `git diff --stat`, `git ls-tree -r` and `wc -l` at the
two commits in the run tree's repository.

## Exposure log

Per the pre-registration ("Isolation and exposure"), the S5 addendum §6 and the S5b
addendum §4. Every private-split submission or disclosure is recorded; once
disclosed, continued independence is not claimed.

### Prior exposure of the same screens before S5b

| Split | Task group | What was exposed | When | Effect on independence |
|---|---|---|---|---|
| pre-run smokes and feasibility | `task_group_001` | `train/001` in the eight recorded feasibility attempts plus three lead live smoke solves of the runner | Before S4 | A dev task; already dev exposure |
| pre-run smokes | `task_group_002` | `train/001` solved once with the seed skill | Before S4 | Dev exposure |
| pre-run smokes | `task_group_003` | `train/001` solved twice with the seed skill | Before S4 | Dev exposure |
| dev (S4 optimise) | 001, 002, 003 | every dev task (`train/001`–`003`), solved by the S4 champion and by each evaluated candidate; dev input/output text reached the S4 proposer | S4 optimise phase | Dev can no longer be treated as unseen |
| S4 final phase | `task_group_001` | 42 final solves, 0 failures: `train/004`, `train/005`, `test/001`–`005`, 6 each | S4 final phase | Adjudication and holdout for this group already read |
| S4 final phase | `task_group_002` | 0 final solves (no candidate) | S4 final phase | No final-split exposure from S4 |
| S4 final phase | `task_group_003` | 42 final solves, 0 failures: `train/004`, `train/005`, `test/001`–`005`, 6 each | S4 final phase | Adjudication and holdout for this group already read |
| S5 optimise | 001, 002, 003 | 9 champion dev solves per group = 27; 3 proposals per group; zero adjudication, zero holdout | 2026-11-06 08:47–09:13 CST | Dev only; no new split |
| S5 pre-run smoke | `task_group_001` | one solve of `train/001` with the empty library rendered (`s5-smoke`, score 0.733333) | 2026-11-06 00:50 CST | Dev task, already exposed |

### S5b exposure added by this run

| Split | Task group | What was exposed | When | Effect on independence |
|---|---|---|---|---|
| dev | `task_group_001` | 36 dev solves: 9 champion + 27 candidate (3 evaluated candidates × 9); each of the 3 proposals received the original champion's 9 dev records, including dev input/output text and projected `{score, correct}`. Candidate traces were not passed to the proposer; prior paired deltas reached D2 as numeric state | first attempt start 10:03:52, last ended 11:59:34 CST | Dev is already adaptive; 36 more solves on an exposed split, no new split |
| dev | `task_group_002` | 36 dev solves: 9 champion + 27 candidate (3 evaluated candidates); 3 proposals | 10:03:52–11:43:30 CST | As above |
| dev | `task_group_003` | 9 champion dev solves only; the one proposal call failed and carried dev records to the proposer container without returning a draft | 10:03:52–10:28:11 CST | As above; 9 solves, no candidate evaluation |
| pre-run smoke | — | **none for S5b**: no smoke run directory or log exists for this code | — | No smoke exposure added by this run |
| adjudication | `task_group_001` | `train/004`, `train/005` — 3 runs × 2 arms = 12 solves, 0 failures | 12:00:44–14:11:31 CST (whole final phase) | First read of this group's S5b adjudication pair; already read in S4 |
| adjudication | 002, 003 | none | not run | — |
| holdout | `task_group_001` | `test/001`–`005` — 3 runs × 2 arms = 30 solves, 0 failures | 12:00:44–14:11:31 CST (whole final phase) | Already read in S4; this adds another read |
| holdout | 002, 003 | none | not run | — |

- Total S5b dev exposure: **81 dev solves** (36 / 36 / 9) on already-adaptive splits,
  plus 0 smoke solves. Final-phase exposure: 42 solves for `task_group_001` only
  (12 adjudication + 30 holdout, 0 failure rows); 0 for the other two groups. This
  matches the recorded reconciliation (`pilot-config/s4b/s5b-exposure-reconciliation.md`:
  36/0/12/30, 36/0/0/0, 9/0/0/0); its evidence-dir counts exceed graded rows by one
  per phase, the grader-only calibration replay, which is not a solve.
- Additional disclosure (decision record, 2026-11-06 13:43 CST): during an operational check, the lead printed part of one holdout attempt's grader output, including rubric goal text. The decision record states that it was not used for any decision and no copy was kept. This was an additional disclosure, not an additional solve; it does not change the solve counts above. Continued independence is not claimed.
- Compared with S5, dev exposure rose from 27 to 81 solves: 27 champion solves
  plus 54 candidate solves, comprising three evaluated candidates in each of
  groups 001 and 002 and none in group 003.
- **No independence claim is made for any screen.** Every screen used here was
  already adaptive before this run. Group 001's adjudication and holdout screens
  were solved in two campaigns, S4 and S5b; S5 added no final-split solves.
- Proposer input: each proposal carries the champion text, the dev item ids and the
  9 dev records with `input`, `output` and `feedback`; never adjudication or holdout
  material — no such record exists.
- D2 received numeric state only (counts, budget and the previous paired delta); no
  entry text and no task text. There is no D4 call in this run to disclose.

Source: `pilot-003/task_group_00N/public/results.jsonl`, `evidence/<id>/attempt.json`,
`proposer/<id>/dev/request.json`, `decisions.jsonl`,
`final/task_group_001/observations.jsonl`; `docs/results/e1a-two-artifact.md`
"Exposure log"; `docs/prereg-s5b-addendum.md` §4.

## Named local exceptions (carried, not re-derived)

| Exception | Where frozen | Effect on this report |
|---|---|---|
| Complete first-run scope (3 read-only groups, 3 attempts per task), "NAMED LOCAL EXCEPTION — diagnostic only" | `docs/prereg-gdpevo-pilot.md`, "Objective and diagnostic scope" | Scope is cost-sized; no significance or power claim |
| Group selection: first three read-only IDs, "**not** representative sampling" | same | Results describe these three groups only |
| Carving map (NAMED LOCAL EXCEPTION, no seed): dev `train/001`–`003`, adjudication `train/004`–`005`, holdout `test/001`–`005` | same | 9 dev, 6 adjudication, 15 holdout tasks across the groups |
| Model `gpt-6.1-sol` at `xhigh` instead of upstream `gpt-5.5` (the hosted model has no weight hash) | same | Not the upstream model; served-model identity is recorded from the trace |
| Evaluator timeout 3600 s "(NAMED LOCAL EXCEPTION: upstream gives none)" | same | Our value; grading was not the bottleneck |
| Campaign spend metered as model calls per group campaign, cap 45, because "this route has no verified price (NAMED LOCAL EXCEPTION: accounting unit)" | same, "Caps"; `docs/prereg-s5b-addendum.md` §2.2 | Cost is calls and tokens; no billed cost. The 3 D4 slots are unused headroom, not a lower cap |
| Library size unbounded and per-entry metrics not collected: "no documented bound exists … none is invented" | `docs/prereg-s5-addendum.md` §1, §5 | No per-entry metric is reported; D2 state is artifact-level `c1` counts only |
| The four-field brief wire format is "a named local adapter template, not a paper-defined one" | `docs/prereg-s5-addendum.md` §1 | The draft schema is ours, cited to arXiv 2611.05306v1 App. A for the field set |
| D4 on the host inside PROPOSE was "a **lead implementation choice**"; the D4 call is now retired | `docs/prereg-s5-addendum.md` §3; `docs/prereg-s5b-addendum.md` §2.1 | No admission call exists in this run; admission is the validated `add` plus the paired dev rule |
| Dev re-run dropped and control arm dropped: "The report now reads dev from the optimise archive instead"; noise is the champion's spread (upstream `std@3`) | `docs/prereg-s4-addendum.md`, adopted by `docs/prereg-s5-addendum.md` §2a | Dev rows come from the optimise archive; noise is the champion's three dev runs |

## Not covered

- No merge/revise and no cumulative-growth claim: with the empty champion each
  attempt adds at most one entry, and only one group selected one (§2 limitation).
- No pooled efficacy comparison: one group has a candidate, so every pooled row is
  `unavailable`; no bootstrap, no interval, no p-value.
- No significance, power or independence claim of any kind; no screen here is
  fresh.
- No pooled adjudication or holdout estimate: `task_group_001`'s final rows are a
  single-group description, and its holdout gain is concentrated in `test/004`.
- No result for `task_group_003` in either direction: the campaign stopped
  operationally before an attempt outcome existed.
- No claim that evaluating drafts is better than admitting them: the two runs
  differ in code, evaluator hashes, evaluated attempts and final-phase coverage, and
  this report does not construct a comparison from that.
- No statistical claim of any kind, and no release to any product.
