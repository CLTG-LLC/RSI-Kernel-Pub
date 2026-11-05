# GDPevo pilot pre-registration — FROZEN (issue #4)

Issue #3 delivered the wiring and the draft. Issue #4 freezes this file and owns
the campaign. Before this freeze, live runs were limited to feasibility attempts
on dev task group 001 / train 001 (eight recorded feasibility attempts). Attempts 1–7
stopped operationally; attempts 3, 4 and 7 consumed model tokens but produced no
answer. Attempt 8 was the only successful scored attempt. These runs set the
runtime pins, timing and calibration below. No candidate was proposed or
compared. This commit precedes any pilot run.

## Objective and diagnostic scope

Prove the host contract in `design.md` §4 on GDPevo, then measure feasibility and
cost. This is a single-adapter diagnostic, not E1a, statistical proof of RSI,
cross-product transfer or a release. The first run uses **3 read-only groups**,
excluding mutable group 022, and **3 attempts per task**. The complete first-run
scope is a **NAMED LOCAL EXCEPTION — diagnostic only**: the group count comes
from issue #3, is cost-sized, and makes no statistical claim; the attempt count
has upstream precedent in `codex/guides/metric_and_scoring.md:115–139`.

**Groups: `task_group_001`, `task_group_002`, `task_group_003`.** Rule: filter
`env.state_mode == read_only` (declared at `task_group.yaml` 001:20, 002:19,
003:15), sort IDs ascending, take the first three. This is reproducible
convenience selection, **not** representative sampling (NAMED LOCAL EXCEPTION).
Declared `read_only` is not measured immutability.

## Frozen inputs, artifact and carving rule

- GDPevo revision: `5082a777379156a048881e94940d640702e5e09a`.
- Scene = **task group**; pairing unit = **task**, matched by `(item_id, run)`.
- Instantiate one adapter/champion per group; the split-carving helper may freeze
  a multi-group manifest, but one skill is never implicitly applied universally.
- Artifact = a group-specific champion/candidate containing exactly UTF-8
  `SKILL.md`. **NAMED LOCAL RESTRICTION:** upstream packages may contain support
  files; our first adapter rejects them. Do not imply one universal skill across
  groups.
- Freeze an explicit `dev_tasks_by_group: {group_id: [train_task_id, ...]}`
  assignment. `carve_splits` delegates validation to kernel `splits.py`: listed
  train tasks become dev, remaining train tasks become adjudication, all test
  tasks become holdout. There is **no ratio, seed or ordinal default in code**.
  This carving choice is a **NAMED LOCAL EXCEPTION**, because GDPevo does not
  supply a dev/adjudication partition (design §4).
- **Carving map (NAMED LOCAL EXCEPTION, no seed):** for each selected group,
  dev = `train_001`, `train_002`, `train_003`; adjudication = `train_004`,
  `train_005`; holdout = `test_001`–`test_005`. Totals: 9 dev, 6 adjudication
  and 15 holdout tasks across 3 groups. No published GDPevo split ratio exists.
  The feasibility run used group 001 / `train_001`, which is dev, so no
  adjudication or holdout task has been exposed.
- Freeze manifests containing every task-relative input/evaluator/dependency
  file SHA-256, candidate content IDs, code and evaluator hashes, solver/model
  version and identity, runtime/package versions, image digests, budgets and
  evaluator timeout. Drift is a STOP before any solver invocation.
- **Runtime pins** (verified live in feasibility attempt 8):
  - solver image: `python:3.12-slim@sha256:b224e2fe306f9d303251ada22961635e5b52a69c0414a0050611be31c59f5f5b`
    plus Codex CLI 0.166.0 release assets (SHA-256):
    - `codex-aarch64-unknown-linux-musl.tar.gz` `94eb707605ec2646b2e05b7edf7c4e7b3ccf02b16237c34ae9beb8cfb7f810a9`;
    - `bwrap-aarch64-unknown-linux-musl.tar.gz` `b59c26ee2cc939a1f3df81b639fcc4fb965609bdc704ca85777c168c12cfeb26`;
    - `codex-code-mode-host-aarch64-unknown-linux-musl.tar.gz` `ac98d1f878e353a16cba711fd47bfef2f6c814109bdd819ee2b6b6d6a19701e7`.
  - Model: `gpt-6.1-sol`, reasoning effort `xhigh`, via a local model proxy
    reached through a per-run forwarder
    (`nginx@sha256:5616878291a2eed594aee8db4dade5878cf7edcb475e59193904b198d9b830de`).
  - The hosted model has no weight hash; record served-model identity from the
    trace. The upstream model is `gpt-5.5`, but it cannot be used through this
    proxy (the provider rejects Codex's `tool_search` tool), so this is a
    NAMED LOCAL EXCEPTION.
  - Codex runs with `--sandbox danger-full-access` inside the container, per
    upstream `CODEX_ORCHESTRATOR.md:109`, because the outer container is the
    boundary.
- **Timeouts:** solver wall time 3600 s per attempt (upstream
  `codex_skill_creator_comparison/configs/experiment.yaml:41-43`). The
  evaluator timeout reuses the same 3600 s (NAMED LOCAL EXCEPTION: upstream
  gives none; measured grading takes seconds).
- **Caps, derived from the plan and not chosen freely:**
  - `max_attempts` = **3 proposals per group campaign**. Precedent: GDPevo's
    `reflect-3` generates 3 independent skills per group
    (`codex/guides/skill_modes.md:119–121`).
  - `eval_cap` = **36 item-evaluations per group**: champion dev 3 tasks × 3 runs,
    plus 3 attempts × 3 tasks × 3 runs.
  - **Campaign spend** is metered as **model calls per group campaign**,
    covering evaluated-agent (solver) attempts, proposer calls and Jev calls,
    failed calls included (design §2; `loop.py` spend meter). The cap,
    **42 calls per group**, is derived from the plan:
    - 36 solver attempts (= `eval_cap`);
    - 3 proposer calls;
    - 3 Jev D2 calls.
    
    The campaign halts at the first check past the cap. The unit is calls rather
    than money because this route has no verified price (NAMED LOCAL EXCEPTION:
    accounting unit). Tokens are recorded per call and reported, not capped.
    Acceptance-stage solver attempts (adjudication, holdout, control) are
    bounded separately by the fixed allocation below.

## Metric and repetitions

Metric = **GDPevo official evaluator score**, normalized by the exact precedence
in `task_group_001/env/judge_api.py:30–62`: normalized/total score, recognized
`earned/total` pairs, then normalized `score`. No invented weights or fallback
zero. Invoke the complete task `eval/eval.sh <absolute prediction path>` in the
trusted evaluator runtime. A missing answer, solver failure, timeout, wrapper
failure, malformed payload or unnormalizable score is a structured failure that
blocks acceptance, following kernel `compare.py` and design §5. Raw output and
exception messages are never reflection feedback.

Run independent fresh-context solver attempts. Upstream `acc@3` is the arithmetic
mean of three attempt scores, not pass@3; `std@3` is population standard deviation,
not a confidence interval (`metric_and_scoring.md:115–139`). This pilot evaluates **one frozen candidate**
over all repetitions; upstream can use separately generated same-numbered skill
packages, so that difference is disclosed.

**Aggregation:** within each arm, take the arithmetic mean over 3 attempts per
task, then the equal-task mean within a group, then the **equal-group
macro-mean** (upstream `metric_and_scoring.md:115–139`; GDPevo §4.1). Each split
is reported separately.

**Schedule:** deterministic, in the order group → attempt 01–03 → task id →
champion, candidate, control. There is no schedule seed; this follows upstream's
fixed round-robin (`codex_skill_creator_comparison/guides/workflow.md:85–116`).
Complete `(item_id, run)` evidence is retained. Missing, corrupt, duplicate or
unexpected records block acceptance and are never dropped from the mean.

## Retention and acceptance (design §2/§5)

Only dev scores guide proposals and selection. Freeze one selected candidate and
close the optimization campaign before separate-process adjudication. Accept
only under the preregistered host rule using paired candidate/champion outcomes
per group, followed by independent review and human approval bound to candidate,
input/evaluator/code hashes. `apply(hash)` is record-only and never replaces the
champion or starts enforcement. Holdout is reported once per campaign, never
used to choose a candidate.

**Retention rule (dev non-regression and adjudication gate):** zero margin per
group. The candidate's group mean must be greater than or equal to the
champion's group mean; ties pass; any group decrease fails. Operational or data
failures block acceptance. Growing Harness, arXiv 2609.26760 §3.6 is the source
for the zero margin and for "cost cannot compensate": accept iff gate success
is no lower than the latest accepted checkpoint. Applying that rule **per group**
and requiring every group to pass is our host-rule mapping, not
something the paper itself mandates. Passing retention is **not** demonstrated improvement.
CIs are reported, not used as a gate.

**Approver:** the project owner. Approval is bound to the candidate, input,
evaluator and code hashes, after independent review. Classifier-style F1/FP/FN
thresholds do not transfer.

## Uncertainty and unchanged control

Bootstrap paired task-level differences **clustered by task group**: retain
candidate/champion pairing and all tasks/attempts belonging to a sampled group.
This maps a paired, scene-clustered uncertainty approach to GDPevo's scene definition;
see SciPy paired bootstrap documentation and Dror–Reichart (2018). Clustering by
group is the issue #3 requirement, not an implemented statistical engine here.

**Estimator:** the macro-mean paired difference of the 3 group means.
Resample group indices, keeping every task and attempt inside a sampled group
paired. Use SciPy `bootstrap(paired=True)` with its documented defaults: BCa,
two-sided 95%, 9,999 resamples. The RNG is seeded from `SeedSequence().entropy`,
recorded before execution. A degenerate BCa is reported as-is, with no method
switching.

**Diagnostic only:** with 3 groups, the smallest exact two-sided paired p-value
is 0.25 (2³ sign assignments), and the bootstrap has only 27 ordered group
draws. No significance or power claim is made.

Measure an **unchanged champion control** under the same task identities,
matched attempt schedule, solver/runtime/evaluator hashes and reserved budget.
Use independent fresh contexts and do not reuse a cached response as a repetition.
It estimates measurement noise; it does not veto a round by itself
(Phantom Gains, arXiv 2608.20290). Freeze arm order and reporting before execution.
**Control:** an independently executed unchanged-champion arm with the same
3 runs per task (NAMED LOCAL EXCEPTION: equal allocation). Each attempt gets a
fresh agent container, work directory and Codex home. Read-only task envs may be
shared within a stage, never across protected stages (upstream
`CODEX_ORCHESTRATOR.md:38–46`). Final frozen comparison: 30 tasks × 3 runs =
90 observations per arm, 270 in total; optimisation evaluations come on top.

**Cost reporting:** report provider-metered token buckets as measured. Billed
cost is reported only if the provider supplies a real billing record; any
modelled price is labelled as an estimate (arXiv 2611.05306 App. B).
Feasibility measurement, one dev attempt: 89,927 tokens (85,331 input, of which
72,320 cached; 4,596 output), 119 s wall time.

## Isolation and exposure

Proposer runs via kernel `ProposerRuntime`: no network in the wiring tests,
allowlisted environment, staged dev data read-only and separate writable output.
It cannot mount the GDPevo source root, any ancestor, protected child or a symlink
alias. That includes every issue #3 exclusion: test tasks; train output/eval/notes;
group env/judge assets; experiments, data_construction, site; workspace
 task_group/runs/original_traces/scratch/report/skills; adjudication-selected inputs.
The private archive is also denied. Only selected dev input/output traces and
projected `{score, correct}` reach GEPA. No raw grader `details`, rubrics, judge
specs, answer stores or protected inputs enter reflection.

`TASK_ENV_ENABLE_JUDGE=0` is required for proposer and injected solver config;
upstream's train-only judge does not enforce our adjudication carve.
The host adapter rejects a mixed/non-dev batch before any solver runs. The host
supplies and owns solver isolation; an injected Python callable is not itself a
sandbox. Runtime checks run on every task-env start: Docker health `healthy`,
`/health` ok and judge POST returning 404. The solver container carries no
credentials and mounts only the staged input, candidate and access note (read-only)
plus a writable `/work`. Grading runs with `--network none`. All of these were
verified live in feasibility attempt 8. Known limit: solver egress is not
allowlisted; a sandbox comparison is pending.

Tests contain only a synthetic GDPevo-shaped group and a toy wrapper; no tests or
CI call a live LLM or require the real task dataset. Record every private-split
submission/disclosure and prior exposure; once disclosed, do not claim continued
independence. GDPevo shares the index's organization and its public answers could
have appeared in model pretraining (issue #3). No sealed set is opened here.

## GEPA dependency and verification

Use standalone `InstructionProposalSignature` + `run_proposal` from exact Git
commit `3d34469165f0d604df3b48f1d5c776e9080f3da0` (lines 147 and 138 respectively).
It declares **0.1.4**, but published PyPI/GitHub **v0.1.4 lacks `run_proposal`**;
therefore the PEP 508 Git pin, not `gepa==0.1.4`, defines reproducible code.
GEPA is an optional runtime extra and also a dev dependency so existing
`uv sync --locked` CI exercises real upstream code with an injected fake model.
The production adapter imports GEPA lazily; no optimizer loop, live SDK or full
GEPA extras are installed. Hatch's documented direct-reference setting is needed
for editable/wheel builds.

Before any pilot measurement, reproduce a recorded known result exactly with the
same harness and hash-bound inputs (replay/repeatability; reproduce-first rule); freeze success/failure rules
and control protocol before fitting.

**Calibration (reproduced):** feasibility attempt 8 recorded answer sha256
`5eb5cc630e4f69d1892b2fe721a593b8eb83513c96b723ff4c0f756e518ae96b`. The official
evaluator output sha256
`12308ca22e257b47c05099acec8679a9a06f2205c99870578885098adbf6205e`
(total_score 0.533333) was byte-identical across the original run and two
re-runs with `--network none`. Re-run this exact check before the pilot; any
difference is a STOP.

**Pre-run STOPs. All must hold before the first pilot solve:**
1. The issue #18 runner is merged, and its repeated-run identities,
   reservations, aggregation and isolation are verified by its tests plus one
   lead-run live smoke test.
2. A complete per-task manifest is generated by the runner and recorded with
   the results: full SHA-256 of every staged input, wrapper and evaluator file,
   plus the image IDs.
3. The calibration replay above reproduces byte-identically.

## Sources

- Local: `design.md` §2, §4, §5, §7; issue #3.
- [GDPevo pinned layout and wrapper documentation](https://github.com/Prism-Shadow/GDPevo/tree/5082a777379156a048881e94940d640702e5e09a); exact path/line citations above.
- [GDPevo metric/score/failure protocol](https://github.com/Prism-Shadow/GDPevo/blob/5082a777379156a048881e94940d640702e5e09a/evaluation/eval_workspace/codex/guides/metric_and_scoring.md).
- [GEPA pinned standalone proposer](https://github.com/gepa-ai/gepa/blob/3d34469165f0d604df3b48f1d5c776e9080f3da0/src/gepa/strategies/instruction_proposal.py#L138-L147).
- [Published v0.1.4 proposer](https://github.com/gepa-ai/gepa/blob/v0.1.4/src/gepa/strategies/instruction_proposal.py); [PyPI metadata](https://pypi.org/pypi/gepa/0.1.4/json).
- [uv Git dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/#git); [Hatch direct references](https://hatch.pypa.io/latest/config/metadata/#allowing-direct-references).
- [SciPy paired bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html); [Dror–Reichart](https://arxiv.org/abs/1809.01448).
- [Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/); [none network](https://docs.docker.com/engine/network/drivers/none/).
