# FD2 amendment 3: measured operational budgets and exposure reconciliation (pre-campaign, forward-only)

Recorded 2026-11-08 UTC, **after the one registered solver smoke and gold-validity
run, before any noise-floor or campaign solve**. This implements FD2 prereg §8
steps 7–8 under COS **Transparent Changes**
(https://www.cos.io/initiatives/prereg). The original
`docs/prereg-fd2-swebench-live.md` (**FD2 prereg**) and amendments 1–2 remain
unchanged historical records. This amendment fills operational budgets, identity
pins and deterministic gold-validity exclusions; it does not revise the experiment.

## 1. Measured evidence and scope

The lead verified the following smoke measurements, not population estimates:

- Solver: dev `rust/yvgude__lean-ctx-632`, seed skill, `gpt-6.1-sol` through the
  same local model-proxy route as E2. Solve wall **693.6 s**, concurrency **1**.
  Input **3,963,217** tokens, including **3,866,880 cached**; output **25,190**,
  including **12,166 reasoning**. These subsets are not additional tokens.
  Tokens are recorded, not capped. Score **0.0**, explicit **unresolved**: the
  smoke exercised solve, extraction and remote grading, not successful repair.
- Image pull approximately **8 minutes** for an approximately **53 GB** image.
  Docker Desktop VM `MemTotal` **8,317,267,968 bytes**, **18 CPUs**,
  `linux/amd64` via Rosetta. This is not a native-performance measurement.
- That prediction's remote grade: **2 s** job queue, **1,231 s** job duration,
  successful workflow execution at public workflow commit `e3318b7`. Workflow
  success does not mean the prediction resolved the instance.
- Gold-validity workflow **42489186173**: **170 valid / 51 invalid / 1
  incomplete** in the unmodified aggregate. Invalid causes: **30 never-resolved,
  12 flaky, 9 low_disk**. Queue median **9,858 s**, maximum **22,105 s**;
  job duration median **1,257 s**, maximum **18,545 s**. These observations are
  from the gold-validity workload, not measurements of future prediction grades.
- `c/DynamoRIO__dynamorio-7903` reached the provider's six-hour job limit. The
  lead's recorded disposition is a **documented operational capacity exclusion**
  under amendment 2 §3 item 3, not an unstarted job or missing artifact assumed
  invalid. The aggregate's `validation_incomplete=true` is preserved; it is not
  rewritten to a completed result. With this explicit disposition, the final
  accounting is **170 included, 52 excluded**, of which 10 exclusions are
  operational (9 disk, 1 job limit). No rerun or rescue was used.

Only safe identity, aggregate validity and image-size metadata were read. No
problem statement, gold patch, test patch, per-test detail, grading-data file,
solver trace or prediction content was read for this amendment. Exposure scanning
opens no artifact contents; `model_patch.diff` is handled by filename only.

## 2. Frozen identity completion

The **grading evaluator remains the public `e3318b7cb672072da49d229ffbc8aa8e7cfb15dc`
tree**. Its workflow ref remains **tag `fd2-eval-1` → `e3318b7`**, as recorded by
the lead; this amendment does not move the tag or repin grading to the current
working tree. The solver's frozen code remains `c590af80ba9d2df20ed8f802a66ddeb6eebafb02`.

| Identity | Frozen value / evidence |
|---|---|
| Solver full code hash | `a4eafc191b19007765323cfb28bd33b3d88f81378048d11d185a3b4aa7bc5abc` |
| Solver kernel-only hash | `d9b4cbf5cce03586cbadcb86e7f8054845c330b5ac7a68db33fe50cdd58966c1` |
| Smoke config / launcher SHA-256 | `3f3b0a46fac73b9d2d5b1eaa00ae736c92864625b9214b95a0671eb677ad0163` / `91464a50254e2b1b18029311276f882e6f90df423460751359b1afc6094764f7` |
| Harness / RepoLaunch | `091279261203b243386adf256b2b107656013dbf` / `c4b623d930f3728e5338664bb634021b98492cbf` |
| Harness dependency lock SHA-256 | `ffb6816eb1e167be8c70b101041c38d469e6718e6c576ac087cc333bfb90fd76` |
| Dataset revision | `eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3`; eight parquet hashes unchanged in the sidecar |
| Frozen image mapping SHA-256 | `86b1b7c8c208674746b27237f0a18d7183ffacd895d6a8a981bedb387e43d802`; mapping platform `linux/amd64`, individual digests in receipts |
| Carve sidecar SHA-256 | `5ad4c899e96a85cc83d28030829e4faba720a50fdbd8a53767af2d0304abfff9` |
| Validity aggregate SHA-256 | `e15756d3b1a27e2c2364753af79690971de76fb19a697f190eff70fa04c600e8` |
| Rendered smoke prompt SHA-256 | `5905bd635fddaa8fb1ecf9660dbb801d663ff523cf0b13960f4207fc6768effa` |
| Evaluator content ID | `f5112e72c20b7390a2fcefc7ecee3a42d4d3f31bb00479c937d9fc4bff162f63` |

The evaluator content ID uses the existing `candidate.content_id` framing: one
component named `evaluator_identity`, whose UTF-8 value is
`json.dumps({item_id: receipt.evaluator_identity for every original included item},
sort_keys=True)`. It binds the full 222-item identity map, including dataset,
parquet hashes, per-instance image digests, harness/submodule, locked files,
grading argv and parser hashes; it is not a score hash. This is reproduced by
`tools/fd2/budgets.py`, using the length-prefixed sorted-component convention in
`src/rsi_kernel/candidate.py`. Existing per-request identity/digest bindings remain
required; this aggregate identifier does not replace them.

All **16 receipt-bound file hashes** were verified against the frozen grading
Git tree, not against today's checkout. In particular, the frozen
`tools/fd2/gold_validity.py` hash is
`52696848db129b9d4b6a000ad2594ed856688cbe5914de6cf85d6eb3972b3293`.
A later report-grouping-only change selects `ImageOS` and `ImageVersion` when
aggregating runner builds. It changes neither grading nor the frozen evaluator.
Comparing that newer file to an older receipt was initially flagged and paused;
comparison with the correct frozen tree resolved the apparent discrepancy. No
frozen mismatch is waived.

The smoke prompt digest completes the historical smoke pin; every future attempt
still records its own rendered-prompt digest before use. No one shared digest is
claimed for different instances. Other solver/model, runtime asset, seed-skill,
proposer, prompt-template and isolation pins remain exactly as registered. Runner
builds remain recorded per job, not an immutable provider-image promise.

## 3. Registered counts and exclusions

The stdlib-only script joins the pinned aggregate's instance identities to the
unchanged sidecar, rejects duplicate/missing/unexpected identities, and rejects
unclassified incomplete validation. Only the specifically documented job-limit
case above receives the lead-recorded operational-exclusion disposition.

| Split | Original | Included | Excluded | Surviving repositories | Languages (included instances) |
|---|---:|---:|---:|---:|---|
| Dev | 70 | 58 | 12 | 23 | c 6, cpp 30, cs 21, rust 1 |
| Adjudication | 30 | 26 | 4 | 7 | c 20, cs 4, rust 2 |
| Holdout | 122 | 86 | 36 | 27 | c 4, cpp 6, cs 5, java 44, js 8, rust 19 |
| Total | 222 | 170 | 52 | 57 | 6 languages |

There is no reassignment across splits, backfill or replacement. The smoke item
survives, so its frozen selection rule chooses the same instance.

Registered arithmetic, unchanged except for substitution of surviving counts:

- Campaign `eval_cap = |dev| × 3 × (1 + 3) = 58 × 3 × 4 = 696` solves.
- Campaign logical-call spend cap `eval_cap + 3 proposer + 3 D2 = 702`.
  This remains the **campaign** cap, not a claim that final/noise-floor calls are
  included in 702. Tokens are recorded, not capped.
- Final `(26 + 86) × 3 × 2 = 672` solves, conditional on selection; dev read from
  archive, no control arm.
- Report-only noise floor `26 × 3 = 78` solves, before campaign.
- Smoke **1 completed**; maximum whole-plan solver count **1,447**, of which
  **1,446 remain**. Proposer/D2 calls are not solver attempts in this count.

### Reproducible budget-script output

Run `python tools/fd2/budgets.py --validity <validity.json> --frozen-ref
<frozen-grading-tree>` from the checkout. The local tree ref must resolve to the
public evaluator's exact file bytes. No dataset parquet or grading-data file is
opened. Output, including every excluded identity and reason:

```text
frozen_evaluator_file_hashes_verified=16
evaluator_hash=f5112e72c20b7390a2fcefc7ecee3a42d4d3f31bb00479c937d9fc4bff162f63
survivors: {"adjudication": 26, "dev": 58, "holdout": 86}
dev: repositories=23 distinct_images=58 languages={"c": 6, "cpp": 30, "cs": 21, "rust": 1}
adjudication: repositories=7 distinct_images=26 languages={"c": 20, "cs": 4, "rust": 2}
holdout: repositories=27 distinct_images=86 languages={"c": 4, "cpp": 6, "cs": 5, "java": 44, "js": 8, "rust": 19}
registered: {"eval_cap": 696, "final": 672, "noise_floor": 78, "smoke_done": 1, "spend_cap": 702, "total_solves": 1447}
campaign: solves=696 serial_solve_seconds=482745.6 tokens={"input": 2758399032, "cached_input": 2691348480, "output": 17532240, "reasoning_output": 8467536}
noise_floor: solves=78 serial_solve_seconds=54100.8 tokens={"input": 309130926, "cached_input": 301616640, "output": 1964820, "reasoning_output": 948948}
final: solves=672 serial_solve_seconds=466099.2 tokens={"input": 2663281824, "cached_input": 2598543360, "output": 16927680, "reasoning_output": 8175552}
smoke_done: solves=1 serial_solve_seconds=693.6 tokens={"input": 3963217, "cached_input": 3866880, "output": 25190, "reasoning_output": 12166}
total: solves=1447 serial_solve_seconds=1003639.2 tokens={"input": 5734774999, "cached_input": 5595375360, "output": 36449930, "reasoning_output": 17604202}
surviving_distinct_images=170 recorded_image_bytes=1499122542699
excluded flaky (12): c/colbymchenry__codegraph-804, c/colbymchenry__codegraph-951, cs/JasperFx__wolverine-3233, cs/tui-cs__Terminal.Gui-5487, java/floci-io__floci-1895, java/floci-io__floci-1908, js/jsonata-js__jsonata-814, rust/NVlabs__cuda-oxide-381, rust/agentgateway__agentgateway-2313, rust/nearai__ironclaw-6724, rust/prefix-dev__pixi-6335, rust/prefix-dev__pixi-6457
excluded job_limit_operational (1): c/DynamoRIO__dynamorio-7903
excluded low_disk (9): rust/biomejs__biome-10767, rust/biomejs__biome-10773, rust/lance-format__lance-7545, rust/pnpm__pnpm-12879, rust/pnpm__pnpm-12888, rust/pnpm__pnpm-12935, rust/pola-rs__polars-28484, rust/servo__servo-46309, rust/tursodatabase__turso-8102
excluded never-resolved (30): c/DynamoRIO__dynamorio-7944, c/DynamoRIO__dynamorio-7945, cpp/FastLED__FastLED-2691, java/btraceio__btrace-894, java/btraceio__btrace-895, java/btraceio__btrace-898, java/btraceio__btrace-899, java/btraceio__btrace-910, js/jsonata-js__jsonata-809, js/open-gsd__gsd-core-1794, js/open-gsd__gsd-core-1799, rust/gleam-lang__gleam-5938, rust/gleam-lang__gleam-5958, rust/gleam-lang__gleam-5971, rust/gleam-lang__gleam-5982, rust/gleam-lang__gleam-6021, rust/gleam-lang__gleam-6030, rust/gleam-lang__gleam-6049, rust/h4ckf0r0day__obscura-390, rust/h4ckf0r0day__obscura-392, rust/h4ckf0r0day__obscura-412, rust/h4ckf0r0day__obscura-413, rust/h4ckf0r0day__obscura-414, rust/h4ckf0r0day__obscura-421, rust/h4ckf0r0day__obscura-426, rust/h4ckf0r0day__obscura-440, rust/h4ckf0r0day__obscura-447, rust/h4ckf0r0day__obscura-477, rust/h4ckf0r0day__obscura-479, rust/web-infra-dev__rspack-14803
```

## 4. Operational wall, disk and token budgets

### Timeout policies and upstream research

- **Solver wall timeout: 21,600 s per attempt. NAMED LOCAL EXCEPTION.** This is
  the timeout actually used for the smoke, chosen to avoid censoring that
  measurement and anchored to GitHub's six-hour hosted-job limit, not to a
  solver-performance standard. E2's **3,600 s** came from upstream GDPevo
  (`docs/prereg-gdpevo-pilot.md` lines 69–72); FD2 prereg §5 explicitly does not
  carry that threshold. One smoke of about 694 seconds cannot justify a
  multiplier, and no multiplier is used.
- Research found **no positive documented upstream per-instance solver wall cap**
  applicable here. SWE-bench-Live's paper, [Appendix C](https://arxiv.org/html/2505.23419v1),
  gives OpenHands **60 iterations** and SWE-agent **100 LLM calls**, not elapsed
  time; its [pinned evaluation README](https://github.com/microsoft/SWE-bench-Live/blob/091279261203b243386adf256b2b107656013dbf/evaluation/README.md)
  states no solver wall limit. The official [mini-swe-agent default agent](https://github.com/SWE-agent/mini-swe-agent/blob/main/src/minisweagent/agents/default.py)
  documents `wall_time_limit_seconds = 0`, meaning no limit. SWE-agent's
  [tools configuration](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/tools/tools.py)
  distinguishes individual and cumulative command-execution timeouts; neither is
  a whole-agent elapsed-wall cap. Those moving-main sources were inspected for
  this amendment, not adopted as frozen runtime dependencies. The absence claim
  is bounded to these inspected sources, not every agent implementation.
- **Remote dispatch-to-result deadline: 43,705 s = 21,600 + 22,105. NAMED LOCAL
  EXCEPTION.** The first term is the provider's documented hosted-job maximum;
  the second is the maximum observed gold-validity queue. Source: GitHub Actions
  limits, [Existing system limits](https://docs.github.com/en/actions/reference/limits#existing-system-limits),
  row “All GitHub-hosted runners / Job execution time / 6 hours.” No separate
  standard hosted-runner queue-wait maximum is given there. This finite deadline
  is already set; retrieval must finish inside it, not receive an invented extra
  allowance. It is not a guarantee that future queueing fits. Deadline expiry,
  provider job timeout, cancellation, missing artifact and binding failure remain
  `None`/STOP, never a scored zero, redispatch or late-result substitution.

### Serial solve projection and recurring image costs

The only measured solving parallelism is **one**. At **693.6 s × planned solves**:

| Phase | Solves | Serial solve seconds | Distinct images |
|---|---:|---:|---:|
| Campaign ceiling | 696 | 482,745.6 | 58 |
| Noise floor | 78 | 54,100.8 | 26 |
| Final, if selected | 672 | 466,099.2 | 112 |
| Smoke, completed | 1 | 693.6 | 1 (already in dev) |
| Total | 1,447 | 1,003,639.2 | 170 across the union |

The total is **about 11.62 serial days**, solve time alone; remaining solve-time
projection is **1,002,945.6 s**. These are arithmetic projections from **n=1**,
not guaranteed completion times, confidence intervals or validated upper bounds.
A 21,600 s timeout is an abort boundary, not the measured per-solve wall. Proposer
and D2 wall time is not measured here and is not silently assigned zero.

The measured image pull adds approximately **480 s per cold pull**. Thus a
transparent wall expression is **693.6 s × solves + approximately 480 s × cold
pulls + eviction/staging overhead + any unhidden grading waits + proposer/D2
wall**. The last terms have no measured aggregate value yet, so no fabricated
all-in elapsed-time bound is claimed.

There are **170 distinct surviving images** in the receipt metadata, with
**1,499,122,542,699 bytes** of recorded image sizes (sum over distinct images).
The host has approximately **604 GB free**. Images cannot all remain resident;
eviction and later pulls recur. Layer sharing and on-disk representation can
change actual disk usage; the sum is not a measured simultaneous disk footprint.
A cold pass through campaign, noise floor and final comprises **58 + 26 + 112 =
196 phase-distinct image visits** (adjudication recurs in final), plus the already
completed smoke pull. At the one observed pull time, 196 cold phase visits would
add approximately **94,080 s**; pulling cold for each of the 1,447 solves would
add approximately **694,560 s**. These are explicit cache-policy scenarios,
**not measured pull counts, an upper bound, or an adopted scheduling rule**.
No eviction-time sample exists, so no invented eviction charge is added.

For per-instance disk planning, the largest recorded image among survivors is
**58,095,071,946 bytes**, for `rust/web-infra-dev__rspack-14794`; the smoke image
was approximately 53 GB. Image size is not peak build/test scratch usage. The
existing **2,147,483,648-byte** `low_disk` guard in `tools/fd2/README.txt` and
`gold_smoke.sh` is unchanged, not asserted sufficient for every remaining solve.
The 9 measured disk exclusions remain exclusions. The measurement does not
establish a new universal per-instance disk quota.

**Four local jobs is a ceiling, not measured achievable throughput.** The 18 CPUs
and roughly 8 GB of Docker VM memory do not prove that four concurrent solves
fit or scale. Achievable parallelism and actual pulls/evictions will be measured
during the already registered noise floor and restated **forward-only** before
the campaign, without changing counts, rules or rescuing failed runs. No
four-way speedup is presented as measured. If the allocation is infeasible,
FD2 stops: **no subsampling without a new registration** disclosing this exposure.

### Remote grading and historical gold work

Grading runs in parallel on hosted runners, not on the solving host. The
prediction smoke measured **1,231 s/job plus 2 s queue**; gold-validity jobs had
**1,257 s median / 18,545 s maximum job duration**, and **9,858 s median /
22,105 s maximum queue**. The remote cap remains **20 concurrent hosted jobs**,
shared across the organisation (amendment 2; [GitHub concurrency limits](https://docs.github.com/en/actions/reference/limits#job-concurrency-limits-for-github-hosted-runners)).
It is not reserved capacity or measured sustained campaign throughput. A queue
maximum and a job maximum need not belong to the same job. We therefore do not
divide aggregate grading time by 20 and label it elapsed time.

Each planned solver evaluation requires its corresponding grade; at the smoke
rate, the 1,447-solve envelope would represent **1,447 × 1,231 = 1,781,257
runner-seconds**, not local serial wall. The smoke's one grade is already done.
This n=1 projection is not extrapolation of gold-success rates. Historical
validity scheduled **222 × 3 = 666 gold repetitions**; the aggregate records
**636 completed, 4 aborted and 26 unexecuted** repetitions. Earlier gold smokes
and this gold-validity work are sunk qualification work, not future solver
calls; they are neither hidden inside the 1,447 nor scheduled for another run.
Their measured job/queue observations above inform the deadline, but are not
added serially to local solve wall when grading overlaps.

### Token projection (n=1; not a token cap or price estimate)

The pasted script output gives measured per-solve usage multiplied by each
phase's planned solves. Whole-plan projection: **5,734,774,999 input tokens**
(including **5,595,375,360 cached**) and **36,449,930 output tokens** (including
**17,604,202 reasoning**). Remaining projection excludes the completed smoke:
**5,730,811,782 input**, **5,591,508,480 cached**, **36,424,740 output**,
**17,592,036 reasoning**. Cache behavior, instance variability and future skill
length are not estimated by one smoke. No confidence interval exists. Proposer
and D2 token usage is additional and unmeasured here. The campaign's logical-call
cap remains 702; these token projections neither impose nor relax it.

## 5. Exposure reconciliation (§8 step 8)

`tools/fd2/exposure.py` scans every current `rsi-runs/fd2-*` directory, including
`fd2-smoke-prerun`, using names and filesystem metadata only. It inventories
without following symlinks, excludes installed environments/Git objects, and
recognizes solve records by the co-located `model_patch.diff`, `measurement.json`
and `result.json` filenames. A root result is not counted again. The historical
smoke evidence-directory-to-instance binding is explicit and lead-verified;
unknown solve bindings, incomplete solve records, unclassified directories and
inventory errors STOP rather than becoming zeros. This is a reconciliation of
current retained records, not proof that no deleted or unrecorded execution ever
occurred. Rerun it before the first noise-floor/campaign solve if directories change.

Five empty gold-smoke directories initially lacked local records. The lead
recorded their classification as artifact-download targets of failed/cancelled
gold workflows, not model solves. This disposition is explicit in the script;
an arbitrary empty directory is still a STOP. The structural check found **no
model, Codex, model-credential, API-key or proxy references in the workflow/action
files**, in both the frozen grading tree and current tree. Their gold entrypoints
apply gold patches only; the grade workflow grades supplied predictions and does
not generate them. The model proxy is reachable only on the solving host
(lead-recorded topology). A name or empty folder alone is not the evidence.

Lead-recorded public workflow history: gold-smoke **2 success / 5 failure /
1 cancelled**; gold-validity **1 cancelled plus the completed workflow** (the
latter still contains the per-instance job-limit operational exclusion); prediction
grading **exactly 1 run**, the smoke grade. Workflow counts and local download
directory counts are different inventories, not a one-to-one mapping claimed
here. The historical cancelled gold-validity run is separately counted as a gold
workflow with no model call, not invented as a missing local directory.

Command: `python tools/fd2/exposure.py --runs-root <rsi-runs>`. Actual output:

```text
rsi-runs/fd2-code-c590af8: code checkout, not an execution record
rsi-runs/fd2-codex-assets-0.166.0: runtime assets, not an execution record
rsi-runs/fd2-freeze: image metadata freeze, no model call
rsi-runs/fd2-gold-smoke-1: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-2: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-3: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-4: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-6: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-7: gold run, no model call; summary record present
rsi-runs/fd2-gold-smoke-8: gold run, no model call; summary record present
rsi-runs/fd2-gold-validity-1: gold validity, no model call; aggregate record present
rsi-runs/fd2-host-smoke: gold host-fidelity run, no model call; summary present; vendored result.json files are not solves
rsi-runs/fd2-smoke: solver smoke; root result.json is not a second solve
rsi-runs/fd2-smoke-prerun: preflight records (4 dry-run, 1 run launcher); solve counted at fd2-smoke, not again here
rust/yvgude__lean-ctx-632: 1
total_model_solves=1
```

Thus **one dev solve**, **zero adjudication solves**, **zero holdout solves** in
the reconciled records. Gold-only executions are separate from solver exposure.
The dev smoke is adaptive exposure, not a fresh independent test, and cannot be
relabelled unseen later.

**Separate drafting exposure, unchanged:** amendment 2 §5 records a worker's
printing of the first 1,500 bytes of a frozen grading-data file, including part of
the gold patch for `xroche__httrack-893`. That instance is outside the carve
(`july_outside_holdout`); other instances from its repository are in adjudication.
The incident is neither a model solve nor contamination-free evidence. It remains
disclosed separately; no new content from that file was read here. Candidates
still come only from the frozen proposer/solver path, never authored by these
reviewers or drafting workers.

## 6. What does not change; prospective scope

Unchanged: the dataset/cohort and original sidecar, split seed and fraction,
membership except registered gold-validity exclusions, three repetitions,
proposal count, smoke-selection rule, final-phase arms, dev selection,
zero-margin/ties-pass adjudication retention, report-only noise-floor statistic,
missing-result STOP semantics, paired repository-clustered analysis, holdout
reporting-not-gating, approval and isolation. There is no new acceptance margin,
subsampling, retry, rescue, outcome filter or extra candidate selection.

This amendment is **not outcome-independent**: the solver smoke's explicit 0.0
and the gold-validity outcomes already exist and are disclosed above. It is
prospective for noise-floor, campaign and final solves, and does not reinterpret
an observed solver result. Operational budgets use the registered amendment
permission, not a fitted success threshold. No PENDING operational value is
silently assigned a number: measured components and their unmeasured all-in
throughput/overhead limits are distinguished explicitly. This document does not
claim that all other pre-run gates have passed or authorize a campaign launch.

Verification commands for this candidate:

```sh
export PATH=/opt/homebrew/opt/openjdk@21/bin:$PATH
CI=true uv sync --locked && uv run pytest -q
uv run pytest -q tests/test_publication_markers.py
```
