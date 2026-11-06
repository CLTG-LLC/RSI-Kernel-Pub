# E1c prereg addendum — first live harness-code (T3) campaign (issue #49)

Amendment to `docs/prereg-gdpevo-pilot.md` for the first live campaign on the T3
harness-code tier. The frozen pre-registration is untouched; this file records the
change under the COS "Transparent Changes" rule for preregistration amendments
(<https://www.cos.io/initiatives/prereg>). Forward-only: it governs this campaign
only.

Amended 2026-11-06, before any T3 run directory, campaign, observation or
acceptance record exists, so it cannot be tuned to the data it will measure.

Scope convention: only what changes is stated here. Everything else — groups, the
dev / adjudication / holdout carve, schedule, arms, metric, retention rule,
estimator, isolation and the trimmed final phase — is `docs/prereg-gdpevo-pilot.md`
(frozen) and `docs/prereg-s4-addendum.md` (trimmed final phase), adopted by
reference. The T3 contract itself is `docs/design.md` §6, "T3 harness-code
contract", implemented by `src/rsi_kernel/adapters/gdpevo_code/`; this addendum
freezes the values and the order of events for the first live campaign, not the
implementation.

## 1. Why

T3 (harness code as the artifact) is implemented and covered only by synthetic
checks: exact-key/path/symlink and parent denial, non-root uid:gid, resource
flags, trusted-score authority, scoped timeout removal, and synthetic
reference/change grading. No live campaign has run on it (issues #49, #59). This
addendum authorises that first live campaign so the tier disposition can report
**"capability demonstrated (harness-code)"** separately from continuation (S4b)
and from a second retained update.

Precedent for editing code as the evolved artifact inside a sandbox, with the
trusted runner and grading fixed: SWE-bench-style editable-code-in-sandbox
evaluation (<https://github.com/SWE-bench/SWE-bench>), and whole-file rewrite
rather than diff, as already cited in `docs/design.md` §6 T3
([OpenEvolve configuration.md:74](https://github.com/algorithmicsuperintelligence/openevolve/blob/0fa8c4de9faff5d11e2f819557c6b14e0add3a23/docs/configuration.md#L74)).
Nothing here introduces a new mechanism: the campaign driver, retention rule,
spend meter and acceptance path are the S4 ones.

## 2. Scope

### 2.1 All three groups

`task_group_001`–`003`, as S4. T3 starts from a root seed (a `solver.py`, not an
approved skill), so the S4b reason for excluding group 002 ("no approved parent")
does not apply. Running all three is the cheapest route to the existing
"at least two paired groups" reporting rule
(`docs/prereg-s5b-addendum.md` §6).

### 2.2 Seed solver is an identity passthrough

The seed champion is the smallest possible `solver.py`: read stdin, return
exactly one JSON object whose `prompt` is the same text without the trailing
newline.

```python
import json, sys

print(json.dumps({"prompt": sys.stdin.read().rstrip("\n")}))
```

The `rstrip` is required, not cosmetic. The trusted path writes `prompt.txt` with
a trailing `\n` and the shared solver command strips exactly one with
`rstrip("\n")` (`src/rsi_kernel/adapters/gdpevo/solver_docker.py`, `_prompt` and
`solve`), so an identical seed reproduces the S4 trusted prompt byte-for-byte:
same prompt in, same prompt out, no behaviour change from the artifact. The file
is `tests/fixtures/t3_seed_solver.py`, added in a separate PR; this addendum
references that path rather than carrying a second copy.

Prompt identity is checked within one staged attempt, before the trusted agent
starts:

- `expected = (harness/prompt.txt).read_bytes().rstrip(b"\n")`;
- the logic container's `prompt` field must equal `expected` exactly;
- the final `out/prompt.txt` must equal `expected + b"\n"` exactly.

Any difference is a STOP for that attempt and is reported. This is the check that
makes the seed's "no change" claim measured instead of asserted.

### 2.3 Fixed trusted skill

One frozen skill per group, the same file in all three groups:

| Identity | Value |
|---|---|
| Candidate ID (as reconstructed by `Candidate({"SKILL.md": …})`) | `4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e` |
| Raw file sha256 (`pilot-config/seed-SKILL.md`) | `b0fe3906ded74360a0c639093f11128a851aada57d12cfa48ce235195c657283` |

Both identities are labelled because they are different objects: the file hash
covers the raw bytes, the candidate id covers the component serialization. The
loader hash-checks the file (`gdpevo.pilot._champion`); the adapter additionally
requires the frozen skill to be a root artifact. Not the S4 champions: starting
from them would stack two artifacts (a changed skill and changed code) and
confound which one moved the score.

### 2.4 Caps, carve and final phase unchanged

Unchanged and not restated in detail: the dev / adjudication / holdout carve
(`docs/prereg-gdpevo-pilot.md`, "Frozen inputs, artifact and carving rule"),
`max_attempts` 3, `eval_cap` 36, and the **42-call spend cap per group**
(`gdpevo.pilot.SPEND_CAP`: 36 solver + 3 proposer + 3 D2 calls), the zero-margin
non-regression rule, the trimmed final shape (adjudication + holdout × 3 runs ×
champion/candidate = **42 solves per group with a candidate**; dev read from the
optimise archive, no control arm), and hash-bound owner approval, which binds
`code_hash` in the approval record. No new threshold, significance test or
per-item gate is added.

The 42-call cap counts **logical** calls. A proposer call may make its initial
request plus up to two retries (#57, PR #62; transient errors only), logged as
`retry` rows and not metered again, exactly as `docs/prereg-s4b-addendum.md` §3
describes. 42 is therefore a campaign bound, not an HTTP-request bound.

## 3. Resource values — NAMED LOCAL EXCEPTION T3-RESOURCE-VALUES

`CodeLimits` requires frozen `cpus`, `memory_bytes` and `file_bytes` with no
defaults (`src/rsi_kernel/adapters/gdpevo_code/solver_docker.py`). This section
records how they are obtained and what the values do and do not claim.

### 3.1 The frozen rule, reproduced

The rule was frozen at **2026-11-06 13:16:18 CST, before any sample was read**.
File: `pilot-config/t3-measure/FROZEN-RULE.md`, sha256
`7dbaacadfab97eb2ed4728bb88980e7e8403a73c6569a6cdcffb06ac8e6f2eb8`. Its content, verbatim:

```text
# T3-RESOURCE-VALUES measurement rule — frozen 2026-11-06 13:16:18 CST, before any sample was read

Status: NAMED LOCAL EXCEPTION. Borrows the Kubernetes VPA recommender's upper-bound
percentile (0.95) and margin fraction (0.15) (kubernetes/autoscaler@0b9e25f
vertical-pod-autoscaler/docs/flags.md:132-134); it is NOT VPA's algorithm (no
confidence multiplier, no per-interval memory peaks). Validated only by the T3 smoke.

Population: every docker-stats sample of a container whose name ends in "-agent"
in s5b-final-agent-stats.csv (S5b final phase, group 001, pinned f67a45a), from the
sampler's first row to its last. Samples collected before this freeze are used
unread; no sample is excluded.
Parse: CPUPerc "x%" -> x/100 cores; MemUsage left side ("a MiB"/"a GiB"/"a KiB") -> bytes (1024-based).
Statistic: numpy.percentile(values, 95, method="linear").
Value: cpus = ceil_to_0.01(p95_cpu * 1.15); memory_bytes = ceil_to_MiB(p95_mem * 1.15).
file_bytes = ceil(682571 * 1.15) = 784957 (largest retained file in inspected work/session
artifacts of pilot-001..003; per-file RLIMIT_FSIZE; margin is the same local extrapolation).
Record: sample count, first/last timestamp, max gap between consecutive timestamps.
Validation: the T3 live smoke (CodeDockerSolver, seed solver, group 001 train/001) must
execute, pass and be graded under these frozen values; failure is a STOP, not a retune.
```

Values computed by that rule from `pilot-config/t3-measure/s5b-final-agent-stats.csv`
are recorded in the run config with the sample count, first/last timestamp, max
gap and the CSV's sha256, before the smoke. This addendum does not predict them.

### 3.2 What is borrowed and what is not

Borrowed: exactly two published constants from the Kubernetes Vertical Pod
Autoscaler recommender — the upper-bound percentile `0.95` and the margin
fraction `0.15`
([kubernetes/autoscaler@0b9e25f, vertical-pod-autoscaler/docs/flags.md:132–134](https://github.com/kubernetes/autoscaler/blob/0b9e25f/vertical-pod-autoscaler/docs/flags.md#L132-L134)).

Not borrowed, and not claimed: VPA's algorithm. There is no confidence
multiplier, no per-interval memory peak, no history window and no admission
controller. It is a percentile of one observed run with a fixed margin, applied
once, then frozen.

`docker stats` sampling at one-second intervals is **diagnostic telemetry**, not
a measurement instrument with a stated error bound: it can miss sub-second
spikes, and `memory.peak` from a container's cgroup would be exact but is not
read on live third-party containers. That limitation is why the values are
validated by an end-to-end smoke rather than by the sampler, and it is reported
with the measurement table.

### 3.3 `file_bytes`

`file_bytes = 784957`, i.e. `ceil(682571 × 1.15)`. The input is the largest file
retained inside any agent container across the inspected work and session
artifacts of `pilot-001`–`pilot-003`: a Codex rollout JSONL of 682,571 bytes
(`pilot-001/final/task_group_003/evidence/gdp-9ff86d9e/sessions/…`). The limit is
applied **per file** as `RLIMIT_FSIZE` hard and soft equal, so it is a per-file
bound, not a total-disk bound. The 0.15 margin is the same local extrapolation as
in §3.1, not a measured property of that distribution.

### 3.4 The limits also bind the trusted Codex agent container

`CodeDockerSolver._solver_options` returns `limits.docker_argv()`, so the same
`--cpus`, `--memory`/`--memory-swap` and `--ulimit fsize` bind **both** containers:
the untrusted logic container and the trusted Codex agent container. The values
must therefore fit the Codex workload, not just a JSON transform.

Consequence, disclosed up front: S4 ran the trusted agent with no such limits, so
**no T3-versus-S4 score comparison is made**. T3 numbers are a campaign record,
not a controlled comparison against an earlier run, and are not pooled with S4,
S4b or S5b rows. A kill inside the agent container that costs a metered call and
drives a group to `no_improvement` for operational reasons is reported as what it
is; mitigation is disclosure, not relaxation of the frozen values.

### 3.5 Validation and drift

The only validation is the T3 live smoke in §4: `CodeDockerSolver` with the seed
solver, one solve of `task_group_001/train/001`, under these frozen values, which
must execute, pass and be graded. **A failure is a STOP, not a retune.** The
limits, the fixed skill identity and the timeout are part of the frozen execution
identity (`execution_identity`), included in `code_hash`; changing any of them
mid-campaign is identity drift and a STOP, never a silent acceptance re-run. Any
OOM, `fsize` kill or timeout during the campaign is a structured failure that is
reported and blocks acceptance.

Rejected alternative, recorded: the `cure_wm.py` values used elsewhere are for a
different workload (a short CPU-bound script with a 1 GiB address-space cap
cannot run Codex) and are not transferable.

## 4. Pre-run STOPs

All must hold before the first T3 campaign solve.

1. The three frozen STOPs (`docs/prereg-gdpevo-pilot.md`): the runner's tests plus
   one lead-run live smoke; a complete per-task manifest with every staged file
   sha256 and the image IDs; and the calibration replay reproducing the recorded
   evaluator output byte-identically (sha256 `12308ca2…`, total_score 0.533333).
2. **A fresh live T3 smoke**, at the pinned commit, via
   `tests/adapters/test_gdpevo_code_live.py` (added in a separate PR): one
   `CodeDockerSolver` solve of `task_group_001/train/001` with the seed solver and
   the frozen limits, on the pinned run tree, verifying in a real container:
   non-root uid:gid, the logic container removed afterwards, the prompt-identity
   check of §2.2, and `sessions` file size below `file_bytes`. Exactly **one
   executed, passing, graded test**; a skip does not count, and the smoke is
   counted in the exposure of §6 either way.
3. Record the smoke's actual exposure and its identity, then the first campaign
   solve.

## 5. Run identity

- New run directory: **`pilot-005`**. `pilot-001` (S4), `pilot-002` (S5),
  `pilot-003` (S5b) and `pilot-004` (S4b) are separate records and are not reused
  or edited.
- Code pinned to the **first `main` commit that contains both this addendum and
  the T3 live smoke test** `tests/adapters/test_gdpevo_code_live.py`. If the two
  land separately, the pin is the later of the two, so the smoke run under the
  pre-run STOPs is the same code the campaign runs.
- The run tree is a clean detached checkout of that commit. Its git SHA and both
  identity hashes are recorded in the run's code-identity log **before the first
  solve**, and reported with the results: the **full code hash** (`_code_hash()`)
  and the **kernel-only hash** (`_code_hash(exclude=("adapters",))`), same
  formula, both recomputed on the run tree. No unchanged-kernel premise is
  claimed: #60 (PR #64) and #59 changed the tree since S4b's pin, and this
  addendum's own code is expected to differ. Drift during the run is a STOP.

## 6. Exposure

Every screen used here is already **adaptive**; no split is fresh. Counts are
taken from the actual preceding runs, per split and per group, including smokes —
never estimated.

| Prior use | Scope | Source |
|---|---|---|
| S4 optimise | dev of all three groups, champion and each candidate | `docs/prereg-s4b-addendum.md` §4 |
| S4 final | 42 / 0 / 42 graded solves over adjudication + holdout for groups 001 / 002 / 003 | `docs/results/gdpevo-pilot.md`, exposure log |
| S5 | 27 dev solves (9 per group) + 1 pre-run smoke | `docs/results/e1a-two-artifact.md` |
| S5b (`pilot-003`) | its terminal record: dev solves per group, smoke solves, and the 42 final solves for each group that selected a candidate | `pilot-003/task_group_*/` records |
| S4b (`pilot-004`) | **terminal** counts per group: dev solves, smoke solves, and the 42 final solves for each group that selected a candidate | `pilot-004/task_group_*/` records |

**Pre-start reconciliation is a STOP.** Before the first T3 solve, the campaign's
exposure table is rebuilt from the actual records: S5b's terminal counts and S4b's
counts are read from their own run directories, not predicted, and zero is not
assumed for any line. Because §9 serializes E1c behind S4b, S4b is **finished** by
then, so its row carries terminal counts only: one block, no split between
"exposure at T3 start" and later overlapping exposure, because no later overlap
exists.

What T3 adds, on the same already-exposed screens: up to 36 solver attempts per
group (3 attempts × 3 dev tasks × 3 runs, plus the champion dev reads within the
existing `eval_cap`), the 42 final solves per group that selects a candidate, and
one smoke solve. The adjudication and holdout splits of groups 001 and 003 were
each read at least once already (S4 final) and possibly again by S4b before this
campaign starts; whatever T3 reads there is further reuse, disclosed as such.

**No independence claim is made**, and no fresh-split confirmation is implied.
Because the limits also bind the trusted agent (§3.4), T3 rows are not compared
with any earlier run's scores. The frozen pre-registration's existing note stands:
GDPevo public answers could have appeared in model pretraining.

## 7. Failure semantics

Unchanged from the frozen pre-registration and `docs/prereg-s4b-addendum.md` §5.

- A **failed dev comparison** disqualifies that candidate: it is not selected, and
  the campaign continues within `max_attempts` / `eval_cap` / the 42-call cap.
- **Invalid final evidence** — missing, corrupt, duplicate or unexpected
  `(item_id, run)` records, a malformed payload or an unnormalizable score —
  blocks acceptance. It is never dropped from a mean.
- A **campaign abort** (pre-run STOP, identity drift, cap reached, spend meter
  stop) is an **operational STOP**: nothing is solved after it, and it is reported
  as a STOP, never as a negative result.
- A **resource event** (OOM kill, `fsize` kill, timeout) is classified only from
  evidence about the container we own — `docker inspect` of that container, or its
  exit state and logs. **Exit code 137 alone is never read as OOM**: it also
  follows an external `SIGKILL`, a host OOM and a timeout path. Where attribution
  is not available, the failure is reported as an **unclassified failure** with
  what is known, and is not counted as a resource event.

## 8. What is reported

**Status: "harness-code campaign tested".** A factual status, not an outcome: it
holds once the campaign started from the verified seed `solver.py` under the
frozen identity, whether or not any candidate is selected.

**"Capability demonstrated (harness-code)"** is claimed only for a successful
**end-to-end live T3 execution** — the smoke of §4 plus campaign attempts that
actually ran the candidate logic container and the trusted agent and were graded.
It is a statement that the tier executes end to end, not that the artifact
improved anything.

Per group, from the existing acceptance record (`<group>/acceptance.json`), one
mutually exclusive terminal outcome: `updated` / any other completed outcome with
the reason the record gives / operational STOP. Per attempt:

- candidate **admitted: yes / no**, with the reason when no (invalid JSON, extra
  key, parent mismatch, unchanged content, cap reached);
- **paired dev delta** (candidate − champion, mean over dev) and the selection
  outcome, or `"unavailable"` with the reason;
- resource events by kind, with their classification evidence, and unclassified
  failures separately.

Also reported: the measurement table behind §3 (sample count, first/last
timestamp, max gap, computed values, the frozen rule's sha256 and freeze time);
both identity hashes from §5; the §6 exposure disclosure, with S4b's terminal
counts as prior exposure and its own row; the adapter diff against the kernel,
descriptively (files and lines,
no "thin" threshold); and the §3.4 disclosure that the limits bind the trusted
agent, so no T3-versus-S4 comparison is made.

**Whether any changed candidate was evaluated or retained is disclosed
separately** from the status line: "campaign ran" and "an artifact changed" are
different facts, and a group that ends `no_improvement` still reports both.

Approval is unchanged: hash-bound owner approval including `code_hash`, and
`apply()` stays record-only.

## 9. Ordering against S4b

- **S4b runs to completion first.** Its two groups are ready and wait only on the
  S5b terminal record. E1c does not start until S4b's campaigns **and any S4b
  final phase** have finished, so no E1c solve overlaps any S4b solve.
- **Why serialized, and not "overlap if it fits".** A whole-VM fit test would have
  to account for every container a solve starts, and only the two solver
  containers carry the frozen limits; each solve also starts a task-env container,
  a model forwarder and a check container with no such limits
  (`src/rsi_kernel/adapters/gdpevo/solver_docker.py`, `_environment` and
  `_forwarder`). A bound that adds only the next group's `memory_bytes` therefore
  does not bound the actual footprint, so the overlap test is dropped rather than
  approximated. Serializing against S4b needs no capacity estimate at all.
- **Within E1c**, groups start in order `001 → 002 → 003` and run in parallel up to
  the existing 4-job cap, as S4 did — one job per group, and no more than four jobs
  total.
- **No invented reserve** is introduced: there is no headroom percentage, no
  capacity-derived concurrency number and no new limit. Concurrency is the
  existing 4-job cap, and the resource bounds stay exactly the frozen `CodeLimits`
  of §3.

## Sources

- Local: `docs/prereg-gdpevo-pilot.md` (frozen), "Retention and acceptance",
  "Isolation and exposure", "Pre-run STOPs"; `docs/prereg-s4-addendum.md` (trimmed
  final phase); `docs/prereg-s5b-addendum.md` §3, §4, §6;
  `docs/prereg-s4b-addendum.md` §3, §5; `docs/design.md` §6 (T3 harness-code
  contract); `src/rsi_kernel/adapters/gdpevo_code/{adapter,pilot,solver_docker}.py`;
  `src/rsi_kernel/adapters/gdpevo/{pilot,solver_docker}.py`.
- Issues #49 (T3 harness-code artifact), #59 / PR #63 (non-root uid:gid),
  #57 / PR #62 (proposer retry), #60 / PR #64 (atomic approval request),
  #42 / PR #43 (code hash bound in approval).
- [COS preregistration — Transparent Changes](https://www.cos.io/initiatives/prereg).
- [Kubernetes VPA flags, upper-bound percentile and margin fraction](https://github.com/kubernetes/autoscaler/blob/0b9e25f/vertical-pod-autoscaler/docs/flags.md#L132-L134).
- [Docker run — resource, user, ulimit and security options](https://docs.docker.com/reference/cli/docker/container/run/).
- [OpenEvolve whole-file rewrite configuration](https://github.com/algorithmicsuperintelligence/openevolve/blob/0fa8c4de9faff5d11e2f819557c6b14e0add3a23/docs/configuration.md#L74).
- [SWE-bench container-based evaluation](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/swebench/harness/run_evaluation.py#L103-L125).
- [Codex 0.166.0 exec CLI, positional prompt after `--`](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/exec/src/cli.rs#L81-L85).
