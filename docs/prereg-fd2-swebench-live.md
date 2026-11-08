# FD2 prereg addendum — the skill tier on SWE-bench-Live MultiLang, post-cutoff cohort (issue #139)

Amendment to `docs/prereg-gdpevo-pilot.md` for the skill tier on a second stream.
The frozen pre-registration is untouched; this file records the change under the
COS "Transparent Changes" rule for preregistration amendments
(https://www.cos.io/initiatives/prereg). Forward-only: it governs FD2 only.

Scope convention: as in `docs/prereg-e2-skill-groups.md`, only what differs from
the frozen `docs/prereg-gdpevo-pilot.md` and `docs/prereg-s4-addendum.md` (the
trimmed final phase) is stated here; the estimator, retention, approval, isolation
and the skill artifact are adopted by reference.

Timing: written before any FD2 solver smoke, campaign solve, observation or
acceptance record exists. The carve in §3 was computed from metadata only
(`instance_id`, `repo`, `created_at`); no problem statement, gold patch, test patch
or test list has been read by the lead or any worker. Every value not yet measured
is `PENDING-<source>`; a PENDING value still open at the first campaign solve is a
STOP (§8). Planning numbers are not guarantees.

## 1. Why

E2 measures the skill tier on GDPevo groups whose answers are public. FD2 asks the
same question on a stream whose labels are executable tests and whose instances
post-date the bound solver's documented knowledge cutoff: **one tier, one stream,
one cohort**. It narrows uncertainty; it does not give a universal yes/no, and it is
not an E2 replication (different adapter, different outcome type: binary resolved).

## 2. Frozen identity

| Item | Value | Source |
|---|---|---|
| Dataset | `SWE-bench-Live/MultiLang`, revision `eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3`, MIT; 1,077 instances, 431 repos, 0 missing/unparseable `created_at` | metadata freeze receipt, bound by sha256 in this file and the sidecar; the receipt itself is held in the project's private evidence store. Receipt sha256 `cc3915da36260889b8d8f933cf3cbc69adf39ba0df520db19821348924ba436e` (freeze script sha256 `5cba71121f3a863b5a12fa56cb68cc17fb34305dc393c101de9dbe745684b61f`) |
| Parquet hashes | c `a4c382c1…541de`, cpp `8448db88…768ae`, cs `29ffe16d…37c1f`, go `76d2b5df…756e2`, java `00387685…68ee8`, js `bc6ec49c…55a7a`, rust `02ac78e2…074ebc`, ts `7e23783e…c32714`; full digests in `docs/prereg-fd2-items.json` `files_sha256` (copied from the receipt). A mismatch at load is a STOP before any row is parsed | `adapters/swebench_live/tasks.py` `load_tasks`; `tools/fd2/prepare_frozen.py` `EXPECTED_SHA256` |
| Harness | `microsoft/SWE-bench-Live` `091279261203b243386adf256b2b107656013dbf`; RepoLaunch submodule `c4b623d930f3728e5338664bb634021b98492cbf` (pinned by that tree); dependency lock hash: PENDING-adapter-pin | https://github.com/microsoft/SWE-bench-Live/tree/091279261203b243386adf256b2b107656013dbf |
| Grading data | a local frozen copy built from the verified revision inside the private grading boundary, `docker_image` replaced by its frozen digest (the harness has no revision argument) | `tools/fd2/prepare_frozen.py` (`pin_image`); measurement plan's lead disposition (kept outside the published tree) |
| Per-instance image digests | `linux/amd64` registry manifest digests resolved once at freeze: PENDING-freeze. A mismatch or non-amd64 image at any solve or grade is a STOP. The pinned harness maps `--platform linux` to `x86_64` images only (`evaluation/evaluation.py` lines 75–82 at the harness commit) | `tasks.py` `_DIGEST`; `solver.py` `_verify_image` |
| `evaluator_hash` | `content_id` over {dataset revision, 8 parquet hashes, harness + submodule commits, lock hash, image digests, grading argv template, parser file hashes}: PENDING-adapter-pin | `rsi_kernel.candidate.content_id` |
| Solver model | `gpt-6.1-sol`, reasoning effort `xhigh`, via the local model proxy and per-run forwarder; served identity trace-verified; **documented knowledge cutoff Apr 30, 2026** | `docs/prereg-gdpevo-pilot.md` lines 59–65; provider model page (https://developers.openai.com/api/docs/models/gpt-6.1-sol) |
| Agent runtime | Codex CLI 0.166.0 `x86_64-unknown-linux-musl` static assets bind-mounted read-only into the instance image; release-API `asset.digest` values: `codex` `a0bf572d2f93f056c6712a6da348e96078dc84f3885fd7be67807ef389cb3978`, `bwrap` `a37212d853eec479c6ad4f0852ccf857dec422b76747f0349c70a382954be56f`, `codex-code-mode-host` `7588334fd47bc4003d970b70dfd4d1e4578491b1e9baa72976a4c2d7e97590da` | `adapters/swebench_live/solver.py` `CODEX_ASSETS` (from https://api.github.com/repos/openai/codex/releases/tags/rust-v0.166.0) |
| Task prompt template | OpenHands multilingual fix template `benchmarks/swebenchmultilingual/prompts/default.j2` at `701700e6cad1f6309f456213a974544644bda0f4` (upstream sha256 `b9e8b36d19f670f9eae26dc4f2322a1aef6309e7f0110b4c654c80aee4af2053`), taken verbatim with placeholders substituted and exactly two NAMED LOCAL EXCEPTIONS (§2.1). Frozen template-with-deviations sha256 `64bae603f032d401a3b140b11e1df7ba4e1bb4d7376310e1d2d0ea96b845b6c4`; rendered per-instance prompt sha256: PENDING-adapter-pin | https://github.com/OpenHands/benchmarks/blob/701700e6cad1f6309f456213a974544644bda0f4/benchmarks/swebenchmultilingual/prompts/default.j2; `adapters/gdpevo/solver_docker.py` `_prompt` (verbatim-with-placeholders precedent) |
| Seed skill (champion) | E2 seed, unchanged: candidate id `4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e`, file sha256 `b0fe3906ded74360a0c639093f11128a851aada57d12cfa48ce235195c657283` | `docs/prereg-e2-skill-groups.md` §2.2 |
| Proposer | GEPA standalone proposer at commit `3d34469165f0d604df3b48f1d5c776e9080f3da0`; feedback projected to `{item_id, score, correct}` only | `docs/prereg-gdpevo-pilot.md` lines 211–216; `adapters/swebench_live/feedback.py` |
| Code pin | first `main` commit containing this file and the merged solver slice; git SHA, full and kernel-only code hashes logged before the first solve (smoke included); drift = STOP | `docs/prereg-e2-skill-groups.md` §3 |
| Run directory | **`fd2-001`** (new name; no earlier run directory is reused or edited) | `docs/prereg-e2-skill-groups.md` §3 |

**Cohort definition and claim wording (verbatim, for this file and the report):**
`created_at` is the fix pull request's GitHub creation time (UTC), the SWE-bench
convention (harness `curation/swe_task_crawling/get_pull_request_content.py`
lines 75–78 at the pinned commit). Pool rule: `created_at >= 2026-05-01T00:00:00Z`
(`splits.py` `CUTOFF`). Claim: "instances whose fix pull request was opened on or
after 2026-05-01T00:00:00Z, after the bound gpt-6.1-sol's documented Apr 30, 2026
knowledge cutoff. Contamination-controlled for the fix by the timestamp rule, not
proven contamination-free. The linked issue text may predate the cutoff."
Precedent: LiveCodeBench (problems released after the model's cutoff). If the
served model or its documented cutoff changes, the pool is re-derived in a NEW
registration.

### 2.1 Prompt template

- **Choice.** The OpenHands multilingual fix template,
  [`benchmarks/swebenchmultilingual/prompts/default.j2`](https://github.com/OpenHands/benchmarks/blob/701700e6cad1f6309f456213a974544644bda0f4/benchmarks/swebenchmultilingual/prompts/default.j2)
  at commit `701700e6cad1f6309f456213a974544644bda0f4`, sha256
  `b9e8b36d19f670f9eae26dc4f2322a1aef6309e7f0110b4c654c80aee4af2053` (63 lines;
  byte-identical to `benchmarks/swebench/prompts/default.j2` at the same commit).
  The dataset card (README.md line 145 at the pinned revision) names OpenHands as a
  compliant baseline but mislinks `benchmarks/swtbench/prompts/default.j2` (sha256
  `efd5d4c28a3e4495e222d848e28c8ecf010861bc826091d19928153f7c447071`), the
  SWT-bench **test-writing** template, which asks the agent to change only tests and
  submit failing tests. It is not used. The card's other link, SWE-agent
  `config/default.yaml` at `a1193dd8fd84eb3e2cd6b0ecbd0bed1cdbb84993` (sha256
  `96aeb863cbfaa768044527155f8555c9b401c6644e937b5b6b0bba5538b6eee4`), is not used.
- **Verbatim, placeholders only.** The template text is used as published; only
  its own placeholders are substituted: `{{ instance.problem_statement }}` (the
  problem statement, inline), `{{ instance.repo_path }}` (the repository root found
  in the instance image) and `{{ instance.base_commit }}` (that repository's frozen
  `HEAD`). Precedent: GDPevo, where the upstream prompt text is used verbatim with
  placeholders substituted (`adapters/gdpevo/solver_docker.py` `_prompt`).
- **Exactly two NAMED LOCAL EXCEPTIONS:**
  - (a) **Skill sentence appended.** After the final line, one blank line and the
    sentence `Read /work/skill/SKILL.md and follow its instructions while you
    resolve the issue.` are appended (one line, newline-terminated). Reason: the
    skill is the artifact being optimised, and the upstream template has no skill
    reference.
  - (b) **Python/conda-specific environment lines removed** (upstream lines 9 and
    22–23): line 9 (`Also the development Python environment is already set up
    for you …`) and step 2.1 (`Activate the environment by running` and the
    `source /opt/miniconda3/etc/profile.d/conda.sh ; conda activate testbed`
    command) are deleted; no other line is changed or renumbered. Reason: line 9 is
    false for FD2's c, cpp, cs, java, js and rust instances, and the conda
    `testbed` step does not apply; all use per-language RepoLaunch images.
- **Hashes.** Frozen template-with-deviations text (the upstream file with (b)
  applied, then (a)): 62 lines, 3,686 bytes, sha256
  **`64bae603f032d401a3b140b11e1df7ba4e1bb4d7376310e1d2d0ea96b845b6c4`**. The
  rendered per-instance prompt sha256 is PENDING-adapter-pin: the current adapter
  passes one caller-supplied constant string to `codex exec` and stages the
  statement as a file (`solver.py` `_solve`, `_stage`), so per-instance rendering
  needs an adapter change, tracked as a separate issue. Each rendered prompt's
  sha256 is logged per attempt once wired.

## 3. Pool, carve and exclusions

- **Pool (metadata only):** 331 instances in 70 repository clusters; 2026-05: 22,
  2026-06: 78, 2026-07: 231. Languages present: c 74, cpp 65, cs 49, java 51, js 15,
  rust 77; go and ts have no post-cutoff instance and are absent from FD2, which
  claims nothing about them.
- **Cluster = repository** (an independent group); a repository lives in exactly
  one split (sklearn `GroupShuffleSplit` semantics, cited in `splits.py`).
- **Holdout = the 34 July-only repositories, 122 instances.** This is a
  chronological cohort (newest finite month).
- **Dev / adjudication = a seeded repository-group split of the 36 May–June
  repositories.** July rows of those repositories are excluded
  (`july_outside_holdout`). Dev and adjudication are group-disjoint, **not
  chronological**; disclosed as such.
  - `adjudication_fraction = 0.2` of repository groups, rounded up (8 adjudication
    repos, 28 dev repos). Source: sklearn `GroupShuffleSplit` default
    `test_size=0.2` (scikit-learn 1.5.2 `_split.py`, class at line 1994,
    `_default_test_size = 0.2` at line 2091). The GDPevo 3:2 task map is not a
    ratio rule (`docs/prereg-gdpevo-pilot.md` line 40: "no ratio, seed or ordinal
    default in code") and is not used as one.
  - **`seed = 101368004346016732645078248396961554525`**, drawn by the lead from
    `numpy.random.SeedSequence().entropy` and recorded before any FD2 outcome
    existed. Precedent: the registered bootstrap is seeded the same way, recorded
    before execution (`docs/prereg-gdpevo-pilot.md` line 156). The carve permutation
    uses stdlib `random.Random(seed)`; fold membership is a frozen function of the
    seed, not claimed to reproduce sklearn indices (`splits.py` docstring).
- **Reproducing the carve without task-content exposure.** Verify all eight
  parquet SHA-256 values before decoding any column. Read only `instance_id`, `repo`
  and `created_at`; derive the language from each parquet filename and `item_id` as
  `<language>/<instance_id>`, and parse timestamps with `tasks.py` `_utc`. Pass
  metadata records exposing `item_id`, `repo` and `created_at` directly to
  `splits.py` `carve`, using the recorded seed and `adjudication_fraction=0.2`. Do
  not call `load_tasks` for this metadata-only reproduction: it additionally
  requires statement and image-digest inputs. The
  full item lists, repositories per split and every exclusion with its reason are in
  the sidecar **`docs/prereg-fd2-items.json`, sha256
  `5ad4c899e96a85cc83d28030829e4faba720a50fdbd8a53767af2d0304abfff9`**. The run
  config's `CarvedSplits.to_config()` record at `fd2-001` must equal the sidecar's
  item lists and counts exactly; any difference is a STOP.

**Carve result** (before gold-validity exclusions):

| Split | Instances | Repositories | Languages (instances) |
|---|---|---|---|
| dev | 70 | 28 | c 9, cpp 31, cs 23, js 2, rust 5 |
| adjudication | 30 | 8 | c 22, cs 4, rust 4 |
| holdout | 122 | 34 | c 4, cpp 6, cs 5, java 51, js 10, rust 46 |
| **Included** | **222** | **70** | |

| Exclusion reason | Instances |
|---|---|
| `before_cutoff` | 746 |
| `unparseable_created_at` | 0 (receipt `missing_or_unparseable_created_at.count`) |
| `july_outside_holdout` | 109 (from 23 of the 36 May–June repositories) |
| `outside_cohorts` | 0 (receipt `max_valid_created_at` 2026-07-31T05:37:17Z) |

Totals: 222 + 109 = 331 pool instances; 331 + 746 = 1,077. Disclosure: the group
split is neither chronological nor language-stratified. Adjudication is 22/30 `c`
instances, and all 51 `java` instances are in holdout.

- **Exclusions, frozen, every one reported with its reason, none silent.** A newer
  monthly drop requires a NEW registration. **Gold validity:** an included instance
  must grade resolved on all three gold-validity runs on the campaign host;
  otherwise it is excluded and reported. Three runs follow the pinned upstream
  evaluation README, "Run gold patch," line 71. This repetition count and exclusion
  rule are fixed by this registration and cannot be changed by the budgets
  amendment. Gold patches never enter the optimise process.
- **Singletons are kept** (one-instance repositories are valid clusters). No
  sub-month boundary.

## 4. Host and fidelity rule

Campaign host: the Apple Silicon development host running Docker Desktop with
Rosetta amd64 emulation (Apple Virtualization backend) in its own Docker context,
separate from E2's. It may host FD2 only if all three hold: (a) the frozen
8-instance 3× gold smoke (newest instance per language split, ties → lowest
`instance_id`; `tools/fd2/select_smoke.py`), run with the identical shared script
(`tools/fd2/gold_smoke.sh`), reproduces the native x64 runner's per-instance
resolved outcomes **exactly** — any mismatch is a STOP for this host, not a
tolerance; (b) the solver smoke (§5) passes; (c) every included instance meets the
gold-validity rule of §3. Backend, Docker versions, CPU/RAM allocation and emulation
mode are recorded. The host fidelity run also records its Docker image store
(containerd or legacy) and disk allocation: the native gold smoke needed its runner
switched to the legacy store because the containerd store took a 19.7 GB image to
about 104 GB (https://docs.docker.com/engine/storage/containerd/). Recorded only;
the store is not part of the fidelity comparison. **No native-performance claim is
made.** Docker CLI and Python SDK are both bound to the intended daemon
(`DOCKER_CONTEXT` + `DOCKER_HOST`). The solver container has no dataset, cache,
grader, evidence, private-store or Docker-socket mount; its only egress is the
forwarder to the model proxy; grading runs in a fresh container on the host side
(`solver.py` module docstring). FD2 solves start only after E2's jobs leave this
host (4-job cap).

## 5. Runs, attempts, budgets

Counts below are computed on the §3 carve, **before gold-validity exclusions**; the
budgets amendment restates every formula on the post-exclusion counts.

| Item | Value | Justification |
|---|---|---|
| `runs` | 3 per (item, arm) | Carried from E2 (`docs/prereg-gdpevo-pilot.md` lines 104–113) because the registered estimator's aggregation is defined over 3 runs; SWE-bench-Live's own protocol is single-attempt pass@1, so no upstream repetition count exists — the carry-over is a NAMED LOCAL EXCEPTION (estimator continuity) |
| `max_attempts` | 3 proposals | Same proposer and loop as E2 (`docs/prereg-e2-skill-groups.md` §2.2); the count bounds proposer calls and is stream-independent |
| `eval_cap` | `|dev| × 3 × (1 + 3)` = 70 × 12 = **840** item-evaluations | pilot formula (`docs/prereg-gdpevo-pilot.md` lines 77–78) |
| Campaign spend cap | `eval_cap + 3 proposer + 3 D2` = **846** logical calls; tokens recorded, not capped | same, lines 79–90 |
| Solver wall timeout | PENDING-smoke (solver smoke) | E1c's 3600 s is not carried as a threshold |
| Grader timeout, per-instance disk | PENDING-smoke (native and host gold-smoke measurements) | same |
| Final phase | adjudication + holdout × 3 runs × {champion, candidate}; dev read from the archive; no control arm: (30 + 122) × 3 × 2 = **912** solves | `docs/prereg-s4-addendum.md` lines 49–64 |
| Solver smoke | **1 dev instance**, seed skill: the newest dev instance by `created_at`, ties to the lowest `instance_id`. On the §3 carve this is **`rust/yvgude__lean-ctx-632`** (created 2026-06-30T23:12:06Z, no tie). The rule applies to the dev list after gold-validity exclusions (§8 step 5 precedes step 6), so if that instance is excluded the same rule picks the next one, recorded before the smoke. Exercises staging, solve, patch extraction and private grading | `docs/prereg-e2-skill-groups.md` §3 STOP 5 (one smoke) |
| Noise-floor run (report-only) | champion (seed skill) on adjudication × `runs` = 3, before the first campaign solve and after the carve and gold-validity exclusions: `|adj| × 3` = 30 × 3 = **90** solves. For each run r, let M_r be the equal-repository macro-mean of the champion's scores, using an equal-instance mean within each repository. Report all three M_r values and δ = sqrt(Σ_r(M_r − mean(M))² / 3), their population standard deviation. This adopts the population-standard-deviation convention in `docs/prereg-s4-addendum.md` lines 45–47; results go to the private store, never to the proposer, and count in the §7 exposure reconciliation. **δ is descriptive only: it sets no gate, it is not a §8 STOP, and it does not change the zero-margin, ties-pass retention rule of §7.** | practice of measuring run-to-run noise from repeated base runs: RRSI arXiv 2609.24972v3 §3.3, App. E.1 (δ from repeated base-harness runs; cited for the calibration practice, not its noise-band gate); EnvHarness arXiv 2608.19880 Table 8, App. E.3 (5 baseline rollouts, "never from a single trace"); AHE arXiv 2604.25850 App. A (2 rollouts per task). `runs` = 3 is the existing value above. The spread statistic is a NAMED LOCAL EXCEPTION (the sources give the practice, not this estimator) |
| Campaign wall-clock budget | measured per-job wall (grading from the gold smokes, solving from the solver smoke) × planned job counts (`eval_cap`, final-phase solves, noise-floor solves, solver smoke, gold-validity runs) under the 4-job cap: PENDING-smoke | each FD2 run is a per-instance Docker harness job (solve container, then a fresh grading container, §4) |

Before the first noise-floor or campaign solve, the amendment fills only
smoke-measured operational budgets and the remaining identity pins, records the
deterministic gold-validity exclusions, and recomputes the registered budget
formulas on the surviving counts. It cannot change split membership except through
the registered gold-validity rule, repetition counts, selection, retention or
analysis. If the registered allocation is infeasible, FD2 stops; subsampling
requires a new registration with prior smoke exposure disclosed.

## 6. Metric, missing results, analysis

- **Metric:** "official-harness resolved" (harness `evaluation.py` lines 188–193):
  resolved → 1.0, explicit failure → 0.0, explicit empty submission → 0.0 with its
  category kept; error, incomplete, unaccounted, conflicting or missing report →
  `None` (`grading.py`). The official score is not tightened.
- **Missing-result accounting:** every `None` blocks paired comparison and
  acceptance—never a zero, a dropped observation or a retry. Preserve and report the
  frozen implementation's actual `failure.reason` verbatim, including staging,
  runtime-identity, repository-discovery, timeout, grading and adapter-validation
  failures. Retain its evidence directory when supplied; a missing reason or evidence
  directory is an additional provenance failure, not a scored result. Report
  operational STOP counts separately from quality FAIL, per arm and stage.
- **Primary estimate:** the registered **cluster-aware paired bootstrap**
  (`analysis.py` `paired_group_bootstrap`, `group_of` = repository; macro-mean of
  per-repository candidate − champion; SciPy `bootstrap(paired=True)` defaults,
  BCa, two-sided 95%, 9,999 resamples; degenerate BCa reported as-is; entropy
  recorded before the first final solve). Primary estimand: the **holdout** paired
  macro-mean difference; adjudication reported separately. Below two paired
  clusters the estimate is "unavailable". Exact McNemar is **not** used on pooled
  correlated repetitions.
- **Counted separately, never imputed:** instances attempted; paired instance and
  cluster counts entering each split; STOPs by stage and reason; excluded
  instances by reason.
- **Interpretation guard:** a retained tie is reported as "retained without
  demonstrated improvement" (ties pass under the zero-margin rule, §7). The holdout
  paired estimate stays the primary evidence and adjudication only filters
  acceptance (arXiv 2610.09239 §6); it is reported as a paired,
  repository-clustered estimate and interval (Miller, arXiv 2411.00640 §5). If a
  later registration reuses FD2 holdout instances, its result is labelled
  adaptive / reused-holdout and the reuse is disclosed (E2 exposure-disclosure
  rule).
- **Power planning (planning only, kept outside the published tree):** PASS
  ch. 150 / Machin et al. (1997) McNemar sample size with Kish DEFF = 1 + (m − 1)·ICC,
  m = 122/34 ≈ 3.6, α 0.05 two-sided, power 0.80. The 122-instance holdout reaches
  80% power **only** at discordance ψ = 0.10 with net effect δ = 0.10
  (N ≈ 86–116 for ICC 0.05–0.2); These calculations apply only to the examined
  ψ/δ/ICC scenarios; they do not establish that δ = 0.05 is unpowerable under every
  feasible discordance pattern. The planning grid is not a power calculation for the
  registered equal-repository bootstrap estimator. The ψ/δ/ICC grid is a NAMED LOCAL EXCEPTION;
  equal-cluster-size DEFF understates the real design effect. These numbers
  guarantee nothing. A nonsignificant result is reported as its estimate and
  interval, not as "no effect".

## 7. Retention, approval, isolation, exposure

- **Selection:** non-negative mean paired dev delta selects one candidate; the
  campaign closes before adjudication.
- **Retention:** zero margin on **adjudication**, ties pass — the candidate's
  adjudication macro-mean (equal-repository) ≥ the champion's; operational or data
  failures block (Growing Harness arXiv 2609.26760 §3.6;
  `docs/prereg-gdpevo-pilot.md` lines 131–139). FD2 is one campaign, so this is one
  gate, as in E2's per-campaign rule; it is not an all-repositories-pass rule,
  which would be stricter. Holdout **reported, not gated**. No new threshold,
  significance test or per-item gate.
- **Approval:** hash-bound per request to candidate, evaluator, data and code
  hashes; `apply(hash)` record-only. Under the owner's standing grant the lead may
  approve a record-only apply when retention passes; each approval logs its request
  hashes and the grant. Identical to `docs/prereg-e2-skill-groups.md` §6.
- **Isolation:** the solver receives the problem statement inline in the §2.1
  prompt, `skill/SKILL.md`, and the repository inside the instance image. The host
  adapter decodes `instance_id`, `repo`, `created_at`, `docker_image`,
  `rebuild_cmds` and `problem_statement` (`tasks.py` `ALLOWED_COLUMNS`); the dataset
  metadata fields are not supplied to the solver. The adapter does not decode gold
  patches, test patches, hints or test lists. The proposer gets
  `{item_id, score, correct}` for dev only; adjudication and holdout results go to
  the private store. Protocol-compliance wording applies to **holdout only**; dev
  is a training set by construction.
- **Exposure:** every FD2 instance has **zero prior solve exposure**: no campaign,
  final or smoke has solved any; the gold smoke ran gold patches with no model call;
  the lead and workers read metadata only (`instance_id`, `repo`, `created_at`,
  `docker_image`, `rebuild_cmds`). Reconciliation records actual counts from every
  earlier run directory and smoke before the first solve; a missing record is a
  STOP, not an assumed zero. Pretraining caveat: these repositories are public; the
  issue text may predate the cutoff (§2).

What FD2 may add: ≤ 840 solver attempts in the campaign, 912 final solves if a
candidate is selected, 90 noise-floor solves on adjudication and the one dev smoke
(carve counts; restated after gold-validity exclusions). These are registered
bounds, not predictions.

## 8. Pre-run STOPs (in order, before the first campaign solve)

1. Solver slice merged at the pin; tests pass on the run tree; identity log written.
2. Frozen inputs verified: parquet hashes = receipt, harness and submodule commits,
   lock hash, image digests resolved and `linux/amd64`.
3. Native x64 gold smoke: 8 instances × 3; non-3/3 instances excluded and reported.
4. Host fidelity: identical procedure on the campaign host, per-instance outcomes
   identical to step 3.
5. Carve frozen: seed, fraction, item lists, counts and exclusions recorded and equal
   to `docs/prereg-fd2-items.json`; gold-validity exclusions applied and reported.
6. Solver smoke on the one dev instance (§5) passes.
7. Budgets amendment filled; no PENDING remains.
8. Exposure reconciled from actual records.

## 9. Not claimed

No leaderboard submission; no contamination-free claim; no protocol-compliance
claim for dev; no claim about go/ts, pre-cutoff instances, Python `full`, other
tiers or other benchmarks; no native-performance claim; no RSI proof; no
compounding across rounds (no round 2 is registered here).

## 10. Sources

- `docs/prereg-gdpevo-pilot.md` (frozen; line citations above);
  `docs/prereg-s4-addendum.md` (trimmed final phase, lines 49–64);
  `docs/prereg-e2-skill-groups.md` (scope convention, seed skill, run identity,
  smoke, approval).
- `src/rsi_kernel/adapters/swebench_live/` (`tasks.py`, `splits.py`, `solver.py`,
  `grading.py`, `feedback.py`); `src/rsi_kernel/analysis.py`
  (`paired_group_bootstrap`); `tools/fd2/` (`select_smoke.py`, `prepare_frozen.py`,
  `gold_smoke.sh`).
- `docs/prereg-fd2-items.json` (carve sidecar, sha256 above).
- [SWE-bench-Live/MultiLang dataset card at the pinned revision](https://huggingface.co/datasets/SWE-bench-Live/MultiLang/blob/eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3/README.md).
- [SWE-bench-Live harness at the pinned commit](https://github.com/microsoft/SWE-bench-Live/tree/091279261203b243386adf256b2b107656013dbf).
- [SWE-agent `config/default.yaml`](https://github.com/SWE-agent/SWE-agent/blob/a1193dd8fd84eb3e2cd6b0ecbd0bed1cdbb84993/config/default.yaml);
  [OpenHands `swtbench/prompts/default.j2`](https://github.com/OpenHands/benchmarks/blob/701700e6cad1f6309f456213a974544644bda0f4/benchmarks/swtbench/prompts/default.j2);
  [OpenHands `swebench/prompts/default.j2`](https://github.com/OpenHands/benchmarks/blob/701700e6cad1f6309f456213a974544644bda0f4/benchmarks/swebench/prompts/default.j2).
- [scikit-learn 1.5.2 `GroupShuffleSplit`](https://github.com/scikit-learn/scikit-learn/blob/1.5.2/sklearn/model_selection/_split.py).
- [SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).
- [COS preregistration — Transparent Changes](https://www.cos.io/initiatives/prereg).
