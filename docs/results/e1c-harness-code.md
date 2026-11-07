# E1c: first live harness-code (T3) campaign

Slice T3 of `docs/design.md` §6, issue #49. First live campaign in which the evolved
artifact is the candidate's `solver.py` rather than a skill document: the candidate
code transforms the trusted task prompt in a separate container, and the trusted
Codex agent, the model, the fixed `SKILL.md`, grading and metering stay outside it.
One campaign per group under the frozen pre-registration
`docs/prereg-gdpevo-pilot.md` and the E1c amendment
`docs/prereg-e1c-harness-code-addendum.md`, as superseded by
`docs/prereg-e1c-amendment-1.md` and `docs/prereg-e1c-amendment-2.md`. This is a diagnostic feasibility and cost
run, not a statistical claim and not an efficacy comparison.

Status: **TERMINAL — harness-code campaign tested; optimise closed in all three
groups.** Groups 001 and 003 completed the final phase and each records `updated`
(record-only apply, not deployment). Group 001 is a **TIE retained under the
zero-margin rule**, not demonstrated improvement; group 003 passed adjudication
with a positive measured delta. Group 002 closed optimise `no_improvement`,
selected no candidate, and has **no final phase**. A dev pass is selection only.

This is a **terminal campaign report**, not an efficacy or release claim. Values
that cannot be obtained within the authorised evidence boundary say `unavailable`,
with a reason; they are not zero or deferred measurements. No private archive,
score file, task prompt, answer, evaluator or notes content was opened for this
report. Final analysis uses only arm/item/run/score/token-usage fields and record
validity checks in the authorised observations, plus acceptance/approval records.

### Evidence references

Run evidence paths below are relative to the external run-evidence root, not this
repository. `pilot-005/<group>/{campaign.json,outcomes.jsonl,calls.jsonl,decisions.jsonl,manifest.json,public/results.jsonl}`
provides optimise identities, outcomes, numeric deltas, call accounting and counts.
Smoke references are `e1c-smoke/attempts/gdp-1f8f5581`,
`e1c-smoke-2/attempts/gdp-9839b680`, and
`e1c-smoke-3/attempts/gdp-ddbd11ca`; only measurement, timing, hash and container
metadata were used. `pilot-005-logs/attempt-{2,3}/` preserves smoke, identity and
process-exit logs. The original identity and smoke logs are in `pilot-005-logs/`.
Configuration and resource measurements are `pilot-config/config-e1c.json`,
`pilot-config/t3-measure/values.json`, and
`pilot-config/e1c/s4b-exposure-reconciliation.md`. Final records are
`pilot-005/final/task_group_00{1,3}/observations.jsonl`, `pilot-005/entropy.json`,
`pilot-005/task_group_00{1,3}/{acceptance.json,approval-request.json,approval.json}`
and `pilot-005-logs/attempt-3/final-task_group_00{1,3}.{out,err}`.

## Diagnostic only

The pre-registration ("Uncertainty and unchanged control") fixes the scope at 3
read-only groups. With 3 groups the smallest exact two-sided paired p-value is 0.25
and the bootstrap has only 27 ordered group draws, so no significance or power claim
is made. Paired tables require at least two groups with a candidate; if fewer groups
select one, every pooled row is `unavailable` and no bootstrap is computed.

T3 rows remain separate campaign records, not pooled with S4, S4b or S5b and not
an efficacy comparison (amendment 1 §6). Historically the first smoke limited both
containers and OOM-stopped. **Amendment 1 limits only candidate code**; it removes
the trusted-agent resource mismatch without converting this run into a controlled
comparison. The frozen values and diagnostic-only scope are unchanged.

## Scope and frozen inputs

Per the pre-registration ("Objective and diagnostic scope", "Frozen inputs, artifact
and carving rule") and the E1c addendum §2, §5.

| Item | Frozen value |
|---|---|
| GDPevo revision | `5082a777379156a048881e94940d640702e5e09a` (pinned checkout, unchanged from S4/S5/S5b) |
| Code pin | `126ba9000d524d053a999c0287b968f0e3d26916` — first `main` commit containing amendment 2 and the calibration-replay fix; supersedes original `af2054c0deb4fc754b2eb490b13e7c4994b3adcc` and amendment-1 `faa00e48c6bfd3b3f07adc75357d019b44a43331` |
| Run directory | `pilot-005` (new; `pilot-001`–`pilot-004` are separate records and are not reused or edited) |
| Run tree | clean detached checkout of the pin, recorded in the run's code-identity log before the first solve |
| Groups | `task_group_001`, `task_group_002`, `task_group_003` — all three, in that start order |
| Dev tasks per group | 3 (`train/001`–`003`) |
| Adjudication tasks per group | 2 (`train/004`–`005`) |
| Holdout tasks per group | 5 (`test/001`–`005`) |
| Attempts | `max_attempts` 3; 3 runs per task (`RUNS = 3`) |
| Arms in the final phase | champion and candidate only (control arm dropped by the S4 addendum) |
| Champion artifact | the identity-passthrough seed solver, `tests/fixtures/t3_seed_solver.py` (identity below) |
| Champion parent | none: a root artifact (`validate_code` rejects a frozen champion that carries `parent_ids`) |
| Fixed skill (all three groups) | `pilot-config/seed-SKILL.md` (identity below) |
| Editable artifact | exactly one `solver.py`, replaced as a whole file and staged to `/harness/solver.py` |
| Spend cap per group campaign | 42 logical calls (`36 solver + 3 proposer + 3 D2`); proposer retries are logged as `retry` rows and not metered again |
| Evaluator cap per group | 36 item-evaluations |
| Final-phase solves per group with a candidate | 42 (adjudication + holdout, 3 runs, champion and candidate) |
| Concurrency | one job per group, groups in order `001 → 002 → 003`, no more than the existing 4-job cap |

## Identity

### Pin, run directory and groups

| Identity | Value |
|---|---|
| Code pin (git SHA) | `126ba9000d524d053a999c0287b968f0e3d26916` |
| Run directory | `pilot-005` |
| Groups started | `task_group_001`, `task_group_002`, `task_group_003` |
| Run tree state at pin | clean detached checkout, enforced by `pilot-config/launch-e1c-3.sh` before smoke; recorded pin in `pilot-005-logs/attempt-3/code-identity.txt` |
| Recorded in code-identity log before the first solve | yes: launcher writes git SHA, full hash and kernel-only hash before smoke, then starts optimise only after `1 passed` |

### Seed solver identity

The seed champion is an **identity passthrough**: read stdin, return exactly one JSON
object whose `prompt` is the same text without trailing newline characters. The `rstrip` is
required, not cosmetic — the trusted path writes `prompt.txt` with a trailing `\n`
and the shared solver command strips trailing newline characters with `rstrip("\n")`, so an identical
seed reproduces the S4 trusted prompt byte-for-byte.

```python
import json, sys

print(json.dumps({"prompt": sys.stdin.read().rstrip("\n")}))
```

| Identity | Value |
|---|---|
| Path | `tests/fixtures/t3_seed_solver.py` |
| Raw file sha256 | `32d4f3d71711c376037986efefc5e981a145951524a994024df574b06b0e7de9` |
| Content identity (candidate ID, as reconstructed from the file bytes) | `b95e33ea6f9d2cc0450488afbb4fce1cd3fe65a131b781db5e4ed2ddcb41e374` — all three `campaign.json` champion IDs and smoke `attempt.json`; independently reproduced from pinned seed bytes |
| Behaviour | identity passthrough: same prompt in, same prompt out, no change from the artifact |

Prompt identity is checked within one staged attempt, before the trusted agent
starts:

- `expected = (harness/prompt.txt).read_bytes().rstrip(b"\n")`;
- the logic container's `prompt` field must equal `expected` exactly;
- the final `out/prompt.txt` must equal `expected + b"\n"` exactly.

Any difference is a STOP for that attempt and is reported. This check makes the
"no change" claim measured rather than asserted. Its outcome per attempt:

| Check | Outcome |
|---|---|
| Seed `prompt` field equals the stripped harness prompt | passed before agent execution in all three smokes; failed smoke reached agent exit 137, so the earlier assertion ran; fresh smokes each passed the unchanged test |
| `out/prompt.txt` equals `harness/prompt.txt` after stripping trailing newline bytes and appending one newline | passed in all three smokes on the same basis; prompt bytes were not opened by the report writer |

### Frozen skill

One frozen skill per group, the same file in all three groups. Two identities are
labelled because they are different objects: the raw file hash covers the bytes, the
candidate ID covers the component serialization. The loader hash-checks the file
(`gdpevo.pilot._champion`); the adapter additionally requires the frozen skill to be
a root artifact. Not the S4/S4b champions: starting from them would stack two
artifacts (a changed skill and changed code) and confound which one moved the score.

| Identity | Value |
|---|---|
| Path | `pilot-config/seed-SKILL.md` |
| Raw file sha256 | `b0fe3906ded74360a0c639093f11128a851aada57d12cfa48ce235195c657283` |
| Candidate ID (reconstructed by `Candidate({"SKILL.md": …})`) | `4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e` |
| Root artifact (no `parent_ids`) | yes: production fixed-skill loader constructs a root candidate and `validate_skill` admits it; all three campaigns passed pre-run checks |
| Same skill in all three groups | yes: identical path and raw hash in `config-e1c.json`; execution identity with skill `4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e` reproduces every campaign-bound code hash |

## Frozen resource limits — NAMED LOCAL EXCEPTION T3-RESOURCE-VALUES

`CodeLimits` requires frozen `cpus`, `memory_bytes` and `file_bytes` with no defaults
(`src/rsi_kernel/adapters/gdpevo_code/solver_docker.py`). The values were computed by
a rule frozen at **2026-11-06 13:16:18 CST, before any sample was read**
(`pilot-config/t3-measure/FROZEN-RULE.md`), and recorded in the run config before the
smoke.

### Measurement table

| Quantity | Value |
|---|---|
| Rule sha256 | `7dbaacadfab97eb2ed4728bb88980e7e8403a73c6569a6cdcffb06ac8e6f2eb8` |
| Rule freeze time | 2026-11-06 13:16:18 CST, before any sample was read |
| Sample source | `pilot-config/t3-measure/s5b-final-agent-stats.csv` (S5b final phase, group 001, pinned `f67a45a`), every `docker stats` sample of a container whose name ends in `-agent` |
| Sample CSV sha256 | `5d349dca7d7314c06bc01c2cb321f2c7d861e5462277dd6e1c240ff8f75e6dfe` |
| Samples | 956 (from the sampler's first row to its last; none excluded) |
| First timestamp | 05:09:41 UTC |
| Last timestamp | 06:11:28 UTC |
| Max gap between consecutive timestamps | 41 s |
| p95 CPU (cores) | `0.037325000000000004` (`values.json` and `config-e1c.json`) |
| p95 memory (bytes) | `38440796.16` (36.66 MiB; same records) |
| `cpus` | `0.05` (`ceil_to_0.01(p95_cpu × 1.15)`) |
| `memory_bytes` | `45088768` (`ceil_to_MiB(p95_mem × 1.15)`) |
| `file_bytes` | `784957` (`ceil(682571 × 1.15)`; per-file `RLIMIT_FSIZE`, not a total-disk bound) |
| Applied to both containers | historical first smoke only; **candidate-code container only** under amendment 1 §2 and amendment 2 §2. Trusted agent has no CodeLimits CPU, memory, swap or fsize limit; both keep non-root user, cap-drop and no-new-privileges |
| Identity recorded in `execution_identity` | yes: frozen champion, skill, limits and integer timeout 3600 reproduce the execution-bound `campaign.json` code hash in all three groups (see Code identity) |

The `file_bytes` input is the largest file retained inside any agent container across
the inspected work and session artifacts of `pilot-001`–`pilot-003`: a Codex rollout
JSONL of 682,571 bytes. Its 0.15 margin is the same local extrapolation, not a
measured property of that distribution.

### What is borrowed and what is not

Borrowed: exactly two published constants from the Kubernetes Vertical Pod Autoscaler
recommender — the upper-bound percentile `0.95` and the margin fraction `0.15`
([kubernetes/autoscaler@0b9e25f, vertical-pod-autoscaler/docs/flags.md:132–134](https://github.com/kubernetes/autoscaler/blob/0b9e25f/vertical-pod-autoscaler/docs/flags.md#L132-L134)).

Not borrowed, and not claimed: VPA's algorithm. There is no confidence multiplier, no
per-interval memory peak, no history window and no admission controller. It is a
percentile of one observed run with a fixed margin, applied once, then frozen.

`docker stats` sampling at one-second intervals is diagnostic telemetry, not a
measurement instrument with a stated error bound: it can miss sub-second spikes, and
`memory.peak` from a container's cgroup would be exact but is not read on live
third-party containers. That limitation is why the values are validated by an
end-to-end smoke rather than by the sampler.

### Historical OOM and amended resource scope

The original one-second, model-wait-dominated p95 was not a peak measurement. The
first smoke under both-container limits OOM-stopped; it did **not** validate the
allowance. Amendment 1 is explicitly **post-smoke, pre-campaign**, not pre-data:
it preserves the original rule, samples and values but moves the limits to the
lighter candidate prompt-code workload. It makes no claim about which subprocess
caused the OOM. Both subsequent end-to-end smokes passed under that amended scope.
No peak-memory measurement or GDPevo capacity claim follows from those passes.

Any OOM, `fsize` kill or timeout in a campaign remains a structured failure that is
reported and blocks acceptance; the preserved first-smoke STOP is not a failed
candidate comparison and is not erased by the later passes.

## Pre-run STOPs

All must hold before the first campaign solve (addendum §4, amendments 1–2).
The preserved run sequence is **three launch attempts, two pre-run STOPs**, then
successful optimise. The later final-launcher STOP is a separate operational event.

| Launch attempt | Code pin | Smoke | Campaign / disposition | Evidence |
|---|---|---|---|---|
| 1 | `af2054c0deb4fc754b2eb490b13e7c4994b3adcc` | `1 failed in 68.42s`; agent exit 137 at `34.85860979184508` s | **OOM operational STOP**; 0 campaign solves; 1 smoke dev exposure, 43,739 tokens | original `pilot-005-logs/smoke.log`; smoke `gdp-1f8f5581/{attempt-timing,measurement,failure}.json`; amendment 1 §1 records the owned-container Docker `oom` event |
| 2 | `faa00e48c6bfd3b3f07adc75357d019b44a43331` | `1 passed in 196.97s`; agent exit 0, `OOMKilled: false` | **calibration-replay operational STOP**, all three groups; 0 campaign model calls / solves / exposure; one calibration directory per group, no campaign or calls record | `pilot-005-logs/attempt-2/{smoke.log,task_group_001.err,task_group_002.err,task_group_003.err}`; `pilot-005-attempt-2-prerun-stop/`; amendment 2 §1 |
| 3 | `126ba9000d524d053a999c0287b968f0e3d26916` | `1 passed in 155.73s`; agent exit 0, `OOMKilled: false` | all three optimise processes exited 0; all campaigns closed, 36 dev solves each | `pilot-005-logs/attempt-3/{smoke.log,code-identity.txt,task_group_001.out,task_group_002.out,task_group_003.out}`; campaign/public records |

Attempt 2 failed because calibration replay dispatched its placeholder skill
through the code-only staging override (`ValueError: only the solver.py text
component is admitted`). Amendment 2 calls the base trusted staging path for
calibration only; candidate admission, values, metric, retention and smoke
assertions remain unchanged. Suite/publication gates before attempts 2 and 3 were
reported as 742/2 and 744/2 respectively in the recorded operational history;
these are prior gate records, not checks re-run by this report writer.

| Pre-run requirement | Attempt-3 status | Evidence |
|---|---|---|
| Pinned source, per-task manifests and byte-identical calibration replay | passed before campaign; 10 tasks per group, 60 / 60 / 82 task-file hashes; expected replay sha256 `12308ca22e257b47c05099acec8679a9a06f2205c99870578885098adbf6205e` | each `manifest.json`; production `_prerun` returns only after replay hash equality; all three closed campaigns establish this control path; no evaluator/answer content read |
| Fresh live T3 smoke, executed and graded | `1 passed`, 0 skipped | attempt-3 `smoke.log`, unchanged live-test assertions |
| Smoke exposure and identity before first campaign solve | recorded; three g001 `train/001` smoke solves in total | amendments 1 §1 / 2 §3; all three measurement/identity logs; launcher ordering |
| S4b terminal exposure reconciliation | complete at 2026-11-06 19:23 CST, before first E1c smoke | `pilot-config/e1c/s4b-exposure-reconciliation.md` |

| Smoke fact | Value |
|---|---|
| Test / task | `tests/adapters/test_gdpevo_code_live.py`; `task_group_001/train/001` |
| Invocation | `RSI_LIVE_GDPEVO=1`, CI disabled; each launcher requires literal `1 passed` before optimise |
| Executed / passed / graded | 3 executed; 2 passed and graded; first failed before result grading; 0 skipped |
| Pytest wall times | attempts 1 / 2 / 3: 68.42 / 196.97 / 155.73 s (distinct from agent elapsed times below) |
| Agent elapsed seconds | `34.85860979184508` / `159.00595108279958` / `112.39847570797428`, from `attempt-timing.json` |
| Solver identity | `gpt-6.1-sol`, provider `proxy`, from all three `measurement.json`; Codex CLI 0.166.0 is production version-checked before invocation, not inferred from a session read |
| Container uid:gid | agent `501:20` in attempts 2 and 3 (`container-checks.json`); unchanged live test verifies it equals invoking host and is non-root; logic uses same production argv; first-smoke numeric receipt unavailable |
| Logic container removed | yes for passing smokes: `logic_inspect_exit_code: 1` in both receipts; first smoke has no post-cleanup receipt |
| Max retained sessions file size | attempts 1 / 2 / 3: 122,939 / 256,852 / 233,234 bytes, all below 784,957; file-size metadata only, no session contents opened |
| Max retained work file size | 1,682 / 2,930 / 2,930 bytes; same metadata-only check |
| Peak memory | unavailable: not recorded by solver or Docker inspect `.State`; do not substitute sampled memory or `OOMKilled: false` for a peak |

### Final launcher operational STOP (not a measurement)

At 2026-11-06 22:44 CST the lead's first final launcher invoked
`rsi_kernel.adapters.gdpevo.pilot` (skill hooks) instead of
`rsi_kernel.adapters.gdpevo_code.pilot` (code hooks). The frozen-identity check
correctly stopped groups 001 and 003 **before solver invocation: 0 solves, 0 exposure**.
Both processes exited 1. Preserved tracebacks are
`pilot-005-logs/attempt-3/final-stop-1/final-task_group_{001,003}.err`, with exit
receipts in `e1c-final.log`. The operational record states no final directory,
entropy or rebind record existed at that STOP; the report does not inspect the
subsequently running final phase to re-establish a historical absence.

Original launcher hash prefix: `95a1376a…` (only prefix retained in the authorised
record). Corrected `pilot-config/launch-e1c-final.sh` sha256:
`29ad825d9c7d16287767cf172a2c3d9bc23892f0d820f04c0b9baeb6cf6a4492`.
Only the module changed; same code pin/config, no rebind. The recorded no-solve
pre-check matched champion/evaluator/code identities before relaunch. This was
not a rescue rerun after a quality failure.

## Exposure at T3 start

Every screen used here is already **adaptive**; no split is fresh. E1c exposure counts
are recomputed from the permitted run records. Prior exposure is attributed to the
historical reports and reconciliation records below, including the disclosed S4
feasibility discrepancy. The pre-start reconciliation is a STOP before the first T3 solve.

| Prior use | Scope | Source |
|---|---|---|
| S4 optimise | dev of all three groups, champion and each candidate | `docs/prereg-s4b-addendum.md` §4 |
| S4 final | 42 / 0 / 42 graded solves over adjudication + holdout for groups 001 / 002 / 003 | `docs/results/gdpevo-pilot.md`, exposure log |
| S5 | 27 dev solves (9 per group) + 1 pre-run smoke | `docs/results/e1a-two-artifact.md` |
| S5b (`pilot-003`) | its terminal record: dev solves per group, smoke solves, and the 42 final solves for each group that selected a candidate | `pilot-003/task_group_*/` records |
| S4b (`pilot-004`) | **terminal** counts per group: dev solves, smoke solves, and the 42 final solves for each group that selected a candidate | `pilot-004/task_group_*/` records |

### Counts at T3 start (from S4b's terminal record)

| Split | `task_group_001` | `task_group_002` | `task_group_003` | Source |
|---|---|---|---|---|
| dev solves | 36 | 0 | 36 | `pilot-config/e1c/s4b-exposure-reconciliation.md` (S4b terminal records) |
| smoke solves | 1 | 0 | 0 | `pilot-config/e1c/s4b-exposure-reconciliation.md` (S4b terminal records) |
| adjudication graded solves | 12 | 0 | 12 | `pilot-config/e1c/s4b-exposure-reconciliation.md` (S4b terminal records) |
| holdout graded solves | 30 | 0 | 30 | `pilot-config/e1c/s4b-exposure-reconciliation.md` (S4b terminal records) |

- Because E1c is serialized behind S4b (addendum §9), S4b is finished by then, so its
  row carries terminal counts only: one block, no split between "exposure at T3 start"
  and later overlapping exposure, because no later overlap exists.
- What T3 adds, on the same already-exposed screens, is set out in "Exposure log".
- The reconciliation file was filled before the first E1c solve; this report copies
  its terminal counts, not a prediction. Group 002 was not in S4b.

## Code identity

The attempt-3 identity log precedes smoke and optimise. Source-only and
execution-bound hashes are **different objects**, not identity drift:
`campaign.json` binds `content_id({"code": _code_hash(), "execution": execution_identity})`.
Recomputation below uses immutable **pinned Git blobs**, not this report branch's
later source or an unverified live working tree. It reproduced both recorded
source hashes and all three evaluator/execution-bound campaign hashes exactly.

| Identity | Recorded | Recomputed / comparison |
|---|---|---|
| Campaign git SHA | `126ba9000d524d053a999c0287b968f0e3d26916` | same pinned object; attempt-3 identity log |
| Full source code hash (`_code_hash()`) | `3ecd61e0d0215e69a7fb3e03b47522490c3f4190d64ff2a3d58182f61e2be36f` | equal, every pinned `src/rsi_kernel/` file plus `uv.lock` under the production serialization |
| Kernel-only hash (exclude adapters) | `8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc` | equal; differs from S5b kernel `2781ad329f787e3c2f3e2eb2e482f03b661b1413df83f4abbe389b472599f3e8`; equals S4b kernel in `s4b-continuation.md`; no blanket unchanged-kernel claim |
| Execution-bound campaign `code_hash` | `2b5da45c7faef172d1c1e6ad348af4b614b6bfc59e11ab5796d418fc9ebf37df` | equal in all three campaigns; **not** the source-only hash |
| g001 `evaluator_hash` | `35068c70ba2ba7aded9f3cb0242f655a8dbbcf419f758a57602656cc46fdbed5` | equal in campaign and all 3 outcomes; reproduced from manifest hashes, pinned gdpevo adapter files (including Dockerfile), upstream revision |
| g002 `evaluator_hash` | `6f0b9104ccb327957779d7e4ad49e49c9a598218243e3a4dd8f83d0bbe6fddc1` | same checks, equal |
| g003 `evaluator_hash` | `dfd6a9f6e8f5f0ceb717cf1a3830a1d6054cae5298b8f7bbc8fdaa61dfb049cf` | same checks, equal |

The exact serialized execution identity reproduced from frozen config and the
pinned constructor is:

```json
{"champion": "b95e33ea6f9d2cc0450488afbb4fce1cd3fe65a131b781db5e4ed2ddcb41e374", "limits": {"cpus": 0.05, "file_bytes": 784957, "memory_bytes": 45088768}, "skill": "4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e", "timeout": 3600}
```

Source-only identities from the earlier attempts are preserved separately:

| Attempt | Full source hash | Kernel-only hash | Source |
|---|---|---|---|
| 1 | `8758f56738add8fdda337e96da52ef8f647487887dc92d3e09f1a91355173e25` | `8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc` | original `pilot-005-logs/code-identity.txt` |
| 2 | `0a1b2bd0762094632bffc8ead16f7565455fd6cfb9b99fe8b0800bceae6aebb8` | `8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc` | `pilot-005-logs/attempt-2/code-identity.txt` |

No mid-campaign source or frozen-runtime drift is evidenced in the optimise
records. The wrong-module final-launcher STOP above was the identity guard
rejecting different hooks before any measurement, not proof that candidate code
or the pinned source changed.

## Runtime pins

| Pin | Frozen value | Verified at run |
|---|---|---|
| Solver image base digest | `python:3.12-slim@sha256:b224e2fe306f9d303251ada22961635e5b52a69c0414a0050611be31c59f5f5b` | pinned Dockerfile uses this digest; successful build/solve under attempt-3 pin; base digest not independently re-inspected here |
| Solver CLI release and asset hashes | Codex CLI 0.166.0; `codex-aarch64-unknown-linux-musl.tar.gz` `94eb707605ec2646b2e05b7edf7c4e7b3ccf02b16237c34ae9beb8cfb7f810a9`; `bwrap-…` `b59c26ee2cc939a1f3df81b639fcc4fb965609bdc704ca85777c168c12cfeb26`; `codex-code-mode-host-…` `ac98d1f878e353a16cba711fd47bfef2f6c814109bdd819ee2b6b6d6a19701e7` | pinned Dockerfile checks all three asset hashes at build; solver version guard requires codex-cli 0.166.0 before execution; no session content read |
| Served model identity | `gpt-6.1-sol` via the local model proxy | gpt-6.1-sol / proxy in all smoke measurement receipts; hosted weights have no available hash |
| Reasoning effort | `xhigh` | xhigh in pinned production command; no independent trace-content verification within this read boundary |
| Solver wall-time limit | 3600 s per attempt | 3600 (integer) in reconstructed execution identity, equal bound campaign hashes |
| Evaluator timeout | 3600 s (NAMED LOCAL EXCEPTION) | 3600 in pinned production TIMEOUT; successful pre-run/control path, not a new measurement |
| Spend cap (calls per group campaign) | 42 (`36 solver + 3 proposer + 3 D2`) | 42/42 in each group: 36 solver + 3 proposer + 3 jev; no retry rows in campaign call ledgers |
| Evaluator cap (item-evaluations per group) | 36 | 36/36 each, campaign evaluator_items_used and 36 public rows per group |
| Docker version and image platforms | recorded smoke metadata | 29.5.2; task and solver images linux/arm64 in all smoke metadata |
| Candidate logic container network | `--network none`, read-only filesystem, disposable `/tmp` | production invocation at pinned source; successful smoke path; no standalone live inspect receipt retained |
| Candidate logic container user | invoking host's numeric uid:gid, never root | same host numeric uid:gid in production argv; passing smoke verifies host non-root and agent 501:20; no logic Config.User receipt retained |

## Dev campaign

Only dev scores guided proposals and selection. Dev is not re-run in the final phase
(S4 addendum, adopted by reference); every row is read from the optimise archive.

### Champion dev rows and noise

Each group published 9 champion rows (3 dev tasks × runs 0/1/2) and 27 changed
candidate rows: 36 unique `(candidate_id, item_id, run)` keys, all validated.
The public numeric `candidate_id`, `item_id`, `run`, `score` fields supply the means
below; no feedback or task text was used. Aggregation is run mean per task,
equal-task group mean, then equal-group mean. `std@3` is **population std (`ddof=0`)
per task over three runs**, then mean across tasks, not sample or pooled-score std.
Sources: `prereg-gdpevo-pilot.md`, "Metric and repetitions"; `prereg-s4-addendum.md`,
"What changed, and why"; `gdpevo-pilot.md`, per-task diagnostics; production `_run_spread`
uses `statistics.pstdev`. Mean champion spread across all 9 dev tasks is
`0.019059594329843117`. Neither noise nor dev delta is a retention threshold.

### Per group, selection and stop

| Group | Champion dev mean | Selected candidate dev mean | Champion mean per-task `std@3` | Selected candidate | Attempts | Attempt outcomes | Stop reason | Optimise outcome |
|---|---|---|---|---|---|---|---|---|
| `task_group_001` | `0.5899472222222223` | `0.6788361111111111` | `0.027716000440089872` | `d65e220b04815704a16935231cb50ef71778254f368d0855a577d43f2516b60a` | 3 | a1 `dev_pass`, a2 `dev_pass`, a3 `dev_pass` | `attempts` | `selected`; status `closed` |
| `task_group_002` | `0.7000000000000001` | not applicable (no selected candidate) | `0.0` | none (no final phase) | 3 | a1 `dev_regression`, a2 `dev_regression`, a3 `dev_regression` | `attempts` | `no_improvement`; status `closed` |
| `task_group_003` | `0.8210784313725491` | `0.8419117647058824` | `0.029462782549439483` | `7ca6c7160aa9b218c2776952e88aec5a84229eb71e086248071d48df7c1bc9bd` | 3 | a1 `dev_pass`, a2 `dev_pass`, a3 `dev_pass` | `attempts` | `selected`; status `closed` |

Source: each `campaign.json` and `outcomes.jsonl`; all three process outputs
report the same outcome/stop_reason. These are **optimise**, not acceptance, outcomes. Groups 001 and 003 subsequently
passed final adjudication and completed hash-bound acceptance (below).

### Per attempt: admitted, evaluated, and paired dev delta

All 9 drafts were admitted: changed content under the frozen seed parent, with
9 candidate dev rows per draft. No admission refusal occurred. All evaluated
candidate IDs differ from the seed. Source: `outcomes.jsonl`, candidate-ID counts
in `public/results.jsonl`, and selected lineage in `campaign.json`.

| Group | Attempt | Candidate ID | Admitted | Refusal reason | Candidate evaluated | Exact recorded `mean_delta` | Selection |
|---|---|---|---|---|---|---|---|
| `task_group_001` | 1 | `4668e18039ce268278d0fa116554001b2722142f862e48be482456aab9345810` | yes | not applicable | yes, 9 dev rows | `0.059259111111111124` | `dev_pass`; not selected |
| `task_group_001` | 2 | `cd4652b0aaaddf4b4e7dae10c2d5a7c1b018eec45fb5e29f32b870ad4246f9ff` | yes | not applicable | yes, 9 dev rows | `0.048433000000000004` | `dev_pass`; not selected |
| `task_group_001` | 3 | `d65e220b04815704a16935231cb50ef71778254f368d0855a577d43f2516b60a` | yes | not applicable | yes, 9 dev rows | `0.08888888888888889` | `dev_pass`; selected for final |
| `task_group_002` | 1 | `beee9dfd1ffa3439aa82bc483d19c3f8804246002755c5102df3cfb57915c04f` | yes | not applicable | yes, 9 dev rows | `-0.018518518518518528` | `dev_regression`; not selected |
| `task_group_002` | 2 | `b823f0e7b1841097554027debd6633c85cdba925d7ce2c4fdaad4731dcd50f9b` | yes | not applicable | yes, 9 dev rows | `-0.018518518518518528` | `dev_regression`; not selected |
| `task_group_002` | 3 | `963810e891f9e5673d337995492f06f03d951c713a942fc69724a35cd59ca12c` | yes | not applicable | yes, 9 dev rows | `-0.018518518518518528` | `dev_regression`; not selected |
| `task_group_003` | 1 | `7ca6c7160aa9b218c2776952e88aec5a84229eb71e086248071d48df7c1bc9bd` | yes | not applicable | yes, 9 dev rows | `0.020833333333333332` | `dev_pass`; selected for final |
| `task_group_003` | 2 | `3b1758201d8e1862adac4a7d68b0e8a69569132967e23e8076829686c0e07d6c` | yes | not applicable | yes, 9 dev rows | `0.001225490196078427` | `dev_pass`; not selected |
| `task_group_003` | 3 | `b01a5b7d5d0f1108258225f5648dddf1b43c1cc0fd3f897f6283eb1d6f8612b5` | yes | not applicable | yes, 9 dev rows | `0.020833333333333332` | `dev_pass`; not selected |

Group 003 attempts 1 and 3 have equal maximum dev deltas; the loop keeps the first
because replacement uses strict `>` (`src/rsi_kernel/loop.py`). A `dev_pass` is
eligibility/selection evidence only, **not retained improvement**. All attempts
start from the frozen seed; this is not cumulative within-campaign growth.

D2 records: 3 per group, 9 total, backend `jev`, model `jev-latest`; every
`answer.D2` equals `baseline_answer.D2` (`c1`). Source: `decisions.jsonl`.
This single-component agreement is not evidence that D2 improved selection.

### Dev split table

Two groups have selected candidates (001 and 003), so the fewer-than-two-groups
`unavailable` rule does **not** apply. The equal-group mean of their selected
recorded deltas is `(0.08888888888888889 + 0.020833333333333332) / 2 =
0.05486111111111111` (selection diagnostic only; no group-002 imputation).

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Paired estimator delta | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| dev | selection-only; g001/g003 later `updated` (record-only) | `0.7055128267973857` | `0.7603739379084967` | `0.05486111111111103` | `0.02083333333333326` | `0.0888888888888888` | false | not applicable: dev selects; adjudication decides retention |

Recomputed with pinned `analysis.py` and the recorded entropy/BCa defaults below; two adaptive paired groups, no g002 imputation. The estimator differs in floating-point arithmetic from the mean recorded attempt deltas above. Public payload hashes were verified before and unchanged after analysis:
- g001 `public/results.jsonl`: `e1ef1ed875fcd3d189a89a5aa8ce0f521cc4efd17650374198799815155fc56c`.
- g002 `public/results.jsonl`: `223475cd30987578996237c3701ca7798b56ece1ff0d5cc986d18633aa34f59c`.
- g003 `public/results.jsonl`: `ea5af34714905b6522614e10760fb573a1f87518b633a85696b06feee9af2b8f`.

### Final estimator and evidence binding

Two groups have final pairs: **001 and 003 only**. Apply the registered estimator
(`docs/prereg-gdpevo-pilot.md`, "Uncertainty and unchanged control";
`docs/prereg-s4-addendum.md`, "Reporting"; `docs/prereg-s5b-addendum.md` §6): mean
three runs per task, equal-task mean per group, equal-group paired difference.
Resample the **two group indices**, keeping all task/run pairs in each sampled
group together. The existing `rsi_kernel/analysis.py` uses SciPy
`bootstrap(paired=True)`: BCa, two-sided 95%, 9,999 resamples; no method switching.
The RNG entropy is **`113573787267014796325165670312473268841`**, read from
`pilot-005/entropy.json`, not generated for this report. The final-phase driver
creates it once before solving; its payload sha256 is
`98b7876568ea0049cd23cfd58738830cd68c3ffa2649077c4d0615da4ca0a8ac`.

This is a two-group diagnostic, with only **4 ordered group draws**, not the
three-group/27-draw design case above. Both final BCa intervals are finite and
`degenerate: false`; neither interval is an acceptance gate. Small, repeatedly
exposed adaptive samples do not establish significance, power or independence.
Group 002 is not imputed, and no other campaign is pooled here.

Analysis/hashing/comparison/acceptance helpers and `uv.lock` were byte-identical to
`126ba900` Git blobs. Existing analysis tests passed (20, including exact interval
equality to direct SciPy). Input payload hashes were checked unchanged after analysis:

| Final observations | sha256 |
|---|---|
| `pilot-005/final/task_group_001/observations.jsonl` | `8faca4bf342597bd981bfc7c4b0b0ae34f9e463849f7b0d527f04746cb02db0a` |
| `pilot-005/final/task_group_003/observations.jsonl` | `f6603a996ddb077d38147fb04c5e29566cbe34ce2b51737636e097d57d860780` |

Means use six decimals below; full-precision pooled estimates/intervals follow each
table. No task text or feedback was used.

## Adjudication

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| adjudication | `updated` for g001/g003 (record-only) | 0.766026 | 0.802790 | +0.036765 | 0.000000 | +0.073529 | false | yes, both groups; g001 TIE |

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_001` | `train/004` | 0.230769 | 0.230769 | 0.000000 |
| `task_group_001` | `train/005` | 1.000000 | 1.000000 | 0.000000 |
| `task_group_001` | group mean | 0.615385 | 0.615385 | 0.000000 (TIE) |
| `task_group_002` | — | not run (no candidate; no final phase) | unavailable | unavailable |
| `task_group_003` | `train/004` | 0.833333 | 1.000000 | +0.166667 |
| `task_group_003` | `train/005` | 1.000000 | 0.980392 | −0.019608 |
| `task_group_003` | group mean | 0.916667 | 0.990196 | +0.073529 |

Exact computed pooled champion/candidate macro-means:
`0.7660255833333334` / `0.8027902892156863`; estimate
`0.03676470588235292`; BCa 95% CI `[0.0, 0.07352941176470584]`;
`degenerate: false`. Group 001 means are exactly `0.6153845` / `0.6153845`,
Δ `0.0`: **TIE retained under the zero-margin rule**, not an improvement.
Group 003 means are `0.9166666666666667` / `0.9901960784313726`,
Δ `0.07352941176470584`. Its task-level decrease on `train/005` is reported,
not a separate veto: retention is the existing zero-margin **group-mean** rule.

Record checks: **42 unique observations per selected group**, exact run → sorted
task id → champion/candidate schedule, runs 0/1/2, 21 per arm. No unexpected,
duplicate, missing, malformed or non-finite score; **0 failure rows**, none dropped.
Per group: **12 adjudication (6 + 6)** and **30 holdout records (15 + 15)**.

Final-phase calibration replay passed by control-path evidence: pinned
`final_phase` calls `_prerun` before creating observations, and `_prerun` requires
sha256 `12308ca22e257b47c05099acec8679a9a06f2205c99870578885098adbf6205e`
byte equality before returning. Both final processes reached `updated` with empty
stderr. The replay output itself was **not opened**; total_score `0.533333` remains
the frozen reference value, not a newly inspected score measurement.

Source: `pilot-005/final/task_group_00{1,3}/observations.jsonl`, final stdout/stderr;
`rsi_kernel/analysis.py` aggregation/retention/bootstrap and pinned pre-run control path.

## Holdout

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| holdout | `updated` for g001/g003 (record-only; adjudication decision) | 0.510190 | 0.520599 | +0.010409 | −0.000611 | +0.021429 | false | no, if the same non-regression diagnostic is applied; g003 decreases; **not a gate** |

Exact computed pooled champion/candidate macro-means:
`0.5101901262541381` / `0.5205988828113063`; estimate
`0.010408756557168247`; BCa 95% CI
`[-0.0006111535523301015, 0.021428666666666596]`; `degenerate: false`.

Holdout is report-only: it is not an additional gate. No holdout score is used to
choose anything, because the candidate is frozen at campaign close, before the final
phase starts. The reporting helper's `retention_passed: false` here is the
hypothetical per-group non-regression diagnostic, **not failed acceptance**:
g001 increases, g003 decreases, and both retain on adjudication.

### Per-task holdout diagnostics

Diagnostic only. Candidate mean minus champion mean over the three holdout runs of
each task.

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_001` | `test/001` | 0.562500 | 0.812500 | +0.250000 |
| `task_group_001` | `test/002` | 0.590909 | 0.590909 | 0.000000 |
| `task_group_001` | `test/003` | 0.230769 | 0.230769 | 0.000000 |
| `task_group_001` | `test/004` | 0.142857 | 0.142857 | 0.000000 |
| `task_group_001` | `test/005` | 0.714286 | 0.571429 | −0.142857 |
| `task_group_001` | group mean | 0.448264 | 0.469693 | +0.021429 |
| `task_group_002` | — | not run (no candidate; no final phase) | unavailable | unavailable |
| `task_group_003` | `test/001` | 0.823529 | 0.862745 | +0.039216 |
| `task_group_003` | `test/002` | 0.166667 | 0.166667 | 0.000000 |
| `task_group_003` | `test/003` | 0.705882 | 0.529412 | −0.176471 |
| `task_group_003` | `test/004` | 0.545455 | 0.727273 | +0.181818 |
| `task_group_003` | `test/005` | 0.619048 | 0.571429 | −0.047619 |
| `task_group_003` | group mean | 0.572116 | 0.571505 | −0.000611 |

Exact group-001 holdout means: `0.44826413333333337` / `0.46969279999999997`,
Δ `0.021428666666666596`. Exact group-003 means:
`0.5721161191749428` / `0.5715049656226127`, Δ `-0.0006111535523301015`.
Each group has 15 records per arm. These small adaptive-screen differences are
descriptive and carry no independence or generalisation claim.

Source: `pilot-005/final/task_group_00{1,3}/observations.jsonl`; same validated
aggregation as adjudication.

## Structured failures: OOM, `fsize` and timeout

Exit 137 alone is not OOM. Amendment 1 §1 records the owned-container Docker
`oom` event for the first-smoke agent; timing shows exit 137, allowance 45,088,768
bytes. No subprocess attribution is claimed. Later smoke receipts show exit 0 and
`OOMKilled: false`. Candidate-only limits govern attempt 3.

| Event kind | Preserved smokes | Optimise | Final | Evidence / effect |
|---|---|---|---|---|
| OOM | 1, first-smoke trusted agent | no classified event in authorised optimise records | no classified event in authorised final records; container-event census unavailable | amendment 1 §1; original timing/failure metadata; pre-run operational STOP, preserved separately |
| `fsize` kill | 0 reported | no classified event in authorised optimise records | no classified event in authorised final records; container-event census unavailable | 2 passing smokes; all 9 dev comparisons completed; no owned-container kill receipt available for optimise/final |
| Timeout | 0 reported | no classified event in authorised optimise records | no timeout failure in 84 validated final rows; complete timeout census unavailable | passing smoke timing; final observation validity and empty final stderr |
| Unclassified solver termination | first smoke classified by Docker event, not counted here | no solver failure outcome; container-level census unavailable within allowed paths | 0 solver failure rows; container-level census unavailable | do not convert absence of a permitted container receipt into a verified resource-event count |
| PIPE collector overflow (`logic_output_limit`) | 0 reported | no such failure outcome | 0 such failure rows in 84 final observations | all 9 candidate evaluations reached recorded dev comparison; final rows valid |

The calibration staging exception and wrong-module final-launcher exception are
operational STOPs, **not resource events**. Optimise has 108 published dev rows,
36/group, and nine completed comparison outcomes. Final has 84 complete, valid
rows and empty stderr in both selected groups. This reports what those records
exercise, not a complete container-event audit. No verified OOM/`fsize` count is
invented from missing inspect receipts. Any final resource event or invalid record
would block acceptance under the unchanged rule.

## Cost

Actual logical calls and provider-metered tokens only; **no verified billed price**.
Solver columns deliberately exclude proposer usage, which is reported separately.
D2 usage is null, not zero. Source: each `calls.jsonl`; smoke `measurement.json`.

| Stage | Solver attempts | Proposer calls | D2 calls | Calls against 42 cap | Evaluator items | Input tokens (solver) | Cached input (solver) | Output tokens (solver) | Wall time |
|---|---|---|---|---|---|---|---|---|---|
| Campaign, `task_group_001` | 36 | 3 | 3 | **42 of 42** | 36 | 5,460,929 | 4,681,088 | 190,861 | unavailable (no timing in permitted optimise paths) |
| Campaign, `task_group_002` | 36 | 3 | 3 | **42 of 42** | 36 | 6,050,304 | 5,100,288 | 163,451 | unavailable (no timing in permitted optimise paths) |
| Campaign, `task_group_003` | 36 | 3 | 3 | **42 of 42** | 36 | 8,562,389 | 7,338,624 | 147,108 | unavailable (no timing in permitted optimise paths) |
| Pre-run smoke 1, g001 `train/001` | 1 | not applicable | not applicable | outside campaign caps | 0 completed grading | 43,441 | 24,192 | 298 | pytest 68.42 s |
| Pre-run smoke 2, g001 `train/001` | 1 | not applicable | not applicable | outside campaign caps | 1 completed grading | 103,796 | 90,240 | 6,134 | pytest 196.97 s |
| Pre-run smoke 3, g001 `train/001` | 1 | not applicable | not applicable | outside campaign caps | 1 completed grading | 86,991 | 72,576 | 4,586 | pytest 155.73 s |
| Final phase, g001 | 42 | 0 | 0 | outside campaign caps | 42 | 7,454,403 | 6,485,376 | 269,138 | unavailable (no duration in authorised final records; approval wait is not solve time) |
| Final phase, g003 | 42 | 0 | 0 | outside campaign caps | 42 | 13,551,659 | 11,686,656 | 305,076 | unavailable (same reason) |
| Final phase, g002 | 0 (no candidate) | 0 | 0 | not applicable | 0 | not applicable | not applicable | not applicable | not run |
| Attempt-2 calibration STOP, all groups | 0 | 0 | 0 | 0 | 0 campaign items | 0 | 0 | 0 | unavailable (not measured) |
| Wrong-module final STOP, g001 / g003 | 0 | 0 | 0 | outside campaign caps | 0 | 0 | 0 | 0 | unavailable (not measured) |

| Item | Value |
|---|---|
| Proposer tokens per group | 001 25,605 input / 35,318 output / 60,923 total; 002 21,873 input / 32,519 output / 54,392 total; 003 15,048 input / 42,042 output / 57,090 total |
| Reasoning output tokens (solver) | 001 61,797; 002 36,220; 003 51,807; smoke attempts 1 / 2 / 3: 22 / 3042 / 1506 |
| D2 tokens | unavailable: all 9 `jev` rows have `token_usage: null` |
| Failed calls charged | first-smoke failed solve: 43,739 tokens outside campaign caps; attempt-2/final-launcher STOPs: 0 model calls; optimise: all 126 logical calls metered, solver/proposer usage present and no solver/proposer operational failure recorded |
| Solver attempts failed | 1 preserved pre-run smoke; 0 failed comparison outcomes in optimise; 0 failure rows in 84 final observations |
| Billed cost | unavailable: no real billing record; all smoke `cost_usd` null |
| Estimated price | not reported |

Each group used 42/42 campaign calls, total 126 (108 solver + 9 proposer + 9 D2).
Optimise solver totals: 20,073,622 input, 17,120,000 cached input, 501,420 output,
149,824 reasoning output, 20,575,042 total. Proposer totals: 62,526 input,
109,879 output, 172,405 total. Three smokes total 234,228 input, 187,008 cached
input, 11,018 output, 245,246 total. Cached/reasoning buckets are subsets and are
not added again.

Final tokens, from all 42 `token_usage` records per selected group:

| Group | Input | Cached input (subset) | Output | Reasoning output (subset) | Cache-write input | Total |
|---|---|---|---|---|---|---|
| g001 | 7,454,403 | 6,485,376 | 269,138 | 96,283 | 0 | 7,723,541 |
| g003 | 13,551,659 | 11,686,656 | 305,076 | 114,140 | 0 | 13,856,735 |
| final total | 21,006,062 | 18,172,032 | 574,214 | 210,423 | 0 | 21,580,276 |

All 84 final usage dictionaries are present; every total equals input + output.
Whole-run accounting (108 optimise + 3 smokes + 84 final): **195 solver attempts
/ solve exposures**, 9 proposer + 9 D2 calls = **213 logical calls**; smokes/final
are outside campaign caps. **194 completed grades** (108 + 2 + 84): the failed
smoke counts as exposure, not completed grading. Solver totals: **41,313,912 input,
35,479,040 cached input, 1,086,652 output, 364,817 reasoning output, 42,400,564 total**.
With proposer usage: **42,572,969 known tokens**; missing D2 usage prevents a
complete all-call total. None is billed cost.

Source for final cost: `pilot-005/final/task_group_00{1,3}/observations.jsonl`
(`token_usage` only); preceding stage totals are the optimise/smoke records above.

## Acceptance outcome

Acceptance is final-phase, hash-bound and record-only. The optimiser's `selected`
is **not `updated`**; the two actual acceptance records now each say `updated`.

| Group / event | Known disposition | Acceptance / reason |
|---|---|---|
| g001 | `updated`, candidate `d65e220b…` | adjudication TIE (Δ 0.0), retained by zero margin; all 42 final records valid; matching owner approval |
| g002 | optimise `no_improvement`; no selected candidate; **no final phase** | no retention test or update possible; outcome from the existing campaign record and terminal operational history, not an inspected `acceptance.json` |
| g003 | `updated`, candidate `7ca6c716…` | adjudication Δ `0.07352941176470584`, retention passed; all 42 final records valid; matching owner approval |
| First-smoke OOM STOP | operational STOP, not quality failure | preserved pre-run event; no campaign solve followed |
| Attempt-2 calibration STOP | operational STOP, all three groups | no model call / solve / campaign record |
| Wrong-module final launcher STOP | operational STOP, groups 001 and 003 | 0 solves, 0 exposure; corrected module relaunch, no quality rerun |

| Terminal item | Value |
|---|---|
| `updated` groups | **2**, g001 and g003; both `acceptance.json` and final stdout agree |
| `not_updated` / `failed_gate` groups | **0 / 0** among the two final groups; g002 is `no_improvement`, not a failed gate |
| Approval record and four-hash binding | g001/g003, approver **Billy**; each request matches approval on candidate/data/evaluator/code hashes; not applicable to g002 |
| `apply(hash)` record | called for both approved candidate IDs by the pinned `accept()` path before returning `updated`; **record-only, not deployment**, no enforcement or champion replacement; private decision-store record not opened |
| Independent review of this report | not run by this worker; lead-owned review/disposition remains required |

Owner request/approval/terminal times: **2026-11-07 01:26 / 16:30 / 16:31 CST**.
Owner verbatim: **"yes, no need for me on these. go with your recom"**. The lead
asserted the shown hashes and atomically wrote `approval.json` for **these two
requests only**, not future requests. Wording, times and procedure come from the
authorised operational history, not approval-file fields.

| Binding | g001 | g003 |
|---|---|---|
| Candidate hash | `d65e220b04815704a16935231cb50ef71778254f368d0855a577d43f2516b60a` | `7ca6c7160aa9b218c2776952e88aec5a84229eb71e086248071d48df7c1bc9bd` |
| Data hash | `d4e27d11d602a66b546f81e603bf8d5e3acaf4993b32726a8afd4465d04de444` | `32cd5dab8820d0160d8a2bf6e996e0269197c3c10094287968ea0cb3a11cdab3` |
| Evaluator hash | `35068c70ba2ba7aded9f3cb0242f655a8dbbcf419f758a57602656cc46fdbed5` | `dfd6a9f6e8f5f0ceb717cf1a3830a1d6054cae5298b8f7bbc8fdaa61dfb049cf` |
| Code hash (same frozen campaign binding) | `2b5da45c7faef172d1c1e6ad348af4b614b6bfc59e11ab5796d418fc9ebf37df` | same |
| Approval-file raw sha256 | `813b2b1fb99faa08e98bdf218589de1c8f05ac523430c1cd43f024bcc565b2c0` | `4896e76042ec5af95d5ede0d253580bd968e73cab4317a27ae22c150e1f120ec` |

Each data hash was also independently reproduced with the pinned
`_evaluation_hash` over that group's two adjudication item IDs and 3 runs; it is
**not** the raw observation-file hash. Candidate/evaluator/code identities match
the frozen identities reported above. Both final stderr files are empty; the
terminal operational record reports final launcher exit 0.

Keeping the champion is not counted as success. Group 001's retained tie is not
evidence of improvement. Source: `pilot-005/task_group_00{1,3}/{acceptance.json,
approval-request.json,approval.json}`, final stdout/stderr, authorised operational
approval/terminal history, and pinned `accept()` / `GDPevoAdapter.apply()`.

### Status lines (addendum §8)

| Status | Value / evidence |
|---|---|
| "harness-code campaign tested" | **yes, all three groups**: campaign started from the verified seed under the frozen amended identity and each closed optimise |
| "capability demonstrated (harness-code)" | **yes, execution only**: fresh end-to-end smoke passed and 9 admitted candidate attempts produced 81 candidate dev rows across groups; no efficacy claim |
| "a changed candidate was evaluated or retained" | **evaluated: yes**, 3 per group / 9 total; **retained: yes**, g001/g003 `updated` (record-only); g001 TIE, no candidate selected in g002 |

## Adapter diff against the kernel

Descriptive only, no "thin" threshold. Counts are from read-only Git tree/blobs
and `git diff --numstat` against campaign pin `126ba900`, not this report HEAD.
Lines are file `splitlines()` counts, including non-Python files in the path set.

Against frozen S4 commit `7919829`:

| Path set | Files at pin | Lines at pin | Changed files | Insertions | Deletions |
|---|---|---|---|---|---|
| `src/rsi_kernel/` excluding `adapters/` | 15 | 1,778 | 4 | 433 | 4 |
| `uv.lock` | 1 | 1,702 | 1 | 1,061 | 4 |
| `src/rsi_kernel/adapters/gdpevo_code/` | 4 | 317 | 4 | 317 | 0 |
| `src/rsi_kernel/adapters/gdpevo/` | 9 | 1,949 | 3 | 508 | 139 |

Against S5b commit `f67a45a` (range changes, not all attributable to E1c):

| Path set | Changed files | Insertions | Deletions |
|---|---|---|---|
| `src/rsi_kernel/adapters/gdpevo_code/` | 4 | 317 | 0 |
| `src/rsi_kernel/adapters/gdpevo/` | 3 | 224 | 40 |
| `src/rsi_kernel/loop.py` | 0 | 0 | 0 |

E1c-specific non-src paths in that range: addendum 372/0 inserted/deleted lines,
amendment 1 152/0, amendment 2 51/0; code unit tests 420/0, code container tests
221/0, live smoke 129/0, live guard 37/0, seed fixture 2/0. Other range changes
include unrelated host/docs/tests; this is not a T3-only patch attribution.
Source paths: `docs/prereg-e1c-{harness-code-addendum,amendment-1,amendment-2}.md`,
`tests/adapters/test_gdpevo_code{,_container,_live,_live_guard}.py`,
`tests/fixtures/t3_seed_solver.py`.

## Exposure log

Per the pre-registration ("Isolation and exposure") and the E1c addendum §6. Every
private-split submission or disclosure is recorded; once disclosed, continued
independence is not claimed.

### Prior exposure of the same screens before E1c

| Split | Task group | What was exposed | When | Effect on independence |
|---|---|---|---|---|
| dev, adjudication, holdout | `task_group_001` | the S4, S5, S5b and S4b rows of the pre-registration and the S4b addendum §4, with S5b and S4b's own terminal counts substituted at the pre-start reconciliation | before E1c | every screen used here is already adaptive; no split is fresh |
| dev, adjudication, holdout | `task_group_002` | as above | before E1c | as above |
| dev, adjudication, holdout | `task_group_003` | as above | before E1c | as above |
| pre-run smokes | 001, 002, 003 | prior smoke solves, counted from the S4b terminal record | before E1c | dev tasks, already exposed |

### E1c exposure added by this run (terminal)

| Split / event | Group | Added exposure | When / source | Effect |
|---|---|---|---|---|
| Pre-run smoke 1 | 001 | 1 `train/001` dev solve, failed, 43,739 tokens | agent start 2026-11-06T11:23:42.321342+00:00; original timing/measurement | operational STOP; exposure still counts |
| Pre-run smoke 2 | 001 | 1 `train/001` dev solve, passing, 109,930 tokens | 2026-11-06T12:13:48.534151+00:00; smoke-2 timing/measurement | adaptive dev reuse |
| Pre-run smoke 3 | 001 | 1 `train/001` dev solve, passing, 91,577 tokens | 2026-11-06T12:36:22.402414+00:00; smoke-3 timing/measurement | adaptive dev reuse |
| Dev optimise | 001 | 36 solves: 9 champion + 27 changed candidate; 3 proposals | started after attempt-3 smoke, closed 2026-11-06; public/campaign records; exact start/end unavailable in allowed paths | already adaptive; selection only |
| Dev optimise | 002 | 36 solves: 9 champion + 27 changed candidate; 3 proposals | same sources/order | adaptive; no selected candidate |
| Dev optimise | 003 | 36 solves: 9 champion + 27 changed candidate; 3 proposals | same sources/order | adaptive; selection only |
| Calibration pre-run STOP | all three | 0 model calls, 0 solves, 0 campaign exposure | attempt-2 logs / preserved stop directory | grader-only staging attempt, not a solve |
| Wrong-module final STOP | 001 / 003 | 0 solves, 0 exposure | 2026-11-06 22:44 CST, preserved final-stop-1 logs | no measurement ran |
| Adjudication | 001 / 003 | **12 solves each**, 6 champion + 6 candidate, **24 total** | corrected final phase, observations; completed before requests recorded 2026-11-07 01:26 CST | further reuse; no independence |
| Holdout | 001 / 003 | **30 solves each**, 15 champion + 15 candidate, **60 total** | same observations/request chronology | further reuse; report-only |
| Adjudication / holdout | 002 | 0, no candidate and no final phase | optimise `selected: null` | no new final exposure |

T3 terminal additions: **39 / 36 / 36 dev exposures** (36 optimise each + 3 / 0 / 0
smokes), **111 total**; **42 / 0 / 42 final solves**, **84 total**. Whole-run exposure:
**81 / 36 / 78**, **195 total**. These are actual counts, not planned caps.
Source: final observations, existing campaign/public counts and preserved smokes;
each selected group's 42 final solves comprises 12 adjudication + 30 holdout.

Prior exposure copied from the existing S4b report and terminal reconciliation:
S4 optimise 36/group; S4 feasibility 8 g001 attempts (1 scored, 7 operational
stops), runner smokes 3/1/2; S5 dev 9/group plus 1 g001 smoke; S5b dev 36/36/9,
0 smokes, adjudication 12/0/0 and holdout 30/0/0; S4 final adjudication 12/0/12
and holdout 30/0/30; S4b dev 36/0/36, smoke 1/0/0, adjudication 12/0/12,
holdout 30/0/30. Sources: `s4b-continuation.md` prior exposure/S5b reconciliation,
`e1a-s5b-evaluate-first.md` exposure log, and the pre-start S4b reconciliation.
These counts describe already-used screens, not independent data. S4 feasibility exposure is the historical report count: eight attempts, comprising one scored attempt and seven operational stops. A later reconciliation found seven retained directories; the eight-attempt count is therefore not fully reconciled to retained artifacts and is not revised to seven. Sources: `prereg-gdpevo-pilot.md` feasibility history; `gdpevo-pilot.md` exposure log; later artifact reconciliation recorded 2026-11-07 16:40 CST.

- No independence claim is made for any screen; GDPevo public answers may have
  appeared in model pretraining.
- No additional disclosure is documented in the authorised optimise evidence.
  Final adjudication/holdout solves and numeric results are accounted above, with
  matching approval requests; no proposer or D2 calls occur in final. Task-text or
  trace disclosure outside these authorised records was not audited. The screens
  remain adaptive, and no continued independence is claimed.

## Named local exceptions (carried, not re-derived)

| Exception | Where frozen | Effect on this report |
|---|---|---|
| `cpus`, `memory_bytes`, `file_bytes` required with no defaults; p95 + 0.15 margin, T3-RESOURCE-VALUES | addendum §3, superseded resource scope in amendment 1 §2–3 | local exception, not VPA algorithm or workload standard; candidate code only in successful campaign |
| Complete first-run scope (3 read-only groups, 3 attempts per task), "NAMED LOCAL EXCEPTION — diagnostic only" | `docs/prereg-gdpevo-pilot.md`, "Objective and diagnostic scope" | Scope is cost-sized; no significance or power claim |
| Group selection: first three read-only IDs, "**not** representative sampling" | same | Results describe these three groups only |
| Carving map (NAMED LOCAL EXCEPTION, no seed): dev `train/001`–`003`, adjudication `train/004`–`005`, holdout `test/001`–`005` | same | 9 dev, 6 adjudication, 15 holdout tasks across the groups |
| Model `gpt-6.1-sol` at `xhigh` instead of upstream `gpt-5.5` (the hosted model has no weight hash) | same | Not the upstream model; served-model identity is recorded from the trace |
| Evaluator timeout 3600 s "(NAMED LOCAL EXCEPTION: upstream gives none)" | same | Our value |
| Campaign spend metered as model calls per group campaign, cap 42 (36 solver + 3 proposer + 3 D2) | same, "Caps"; `docs/prereg-e1c-harness-code-addendum.md` §2.4 | Cost is calls and tokens; no billed cost |
| Whole-file `solver.py` rewrite into a fixed path, T3 solver-prompt-script | `docs/design.md` §6 T3 | The artifact is code, not a skill; the trusted runner stays fixed |
| No PID limit on the T3 containers | `docs/design.md` §6 T3 | No workload value is invented |
| Dev re-run dropped and control arm dropped: dev is read from the optimise archive; noise is the champion's spread (`std@3`) | `docs/prereg-s4-addendum.md`, adopted by reference | Dev rows come from the optimise archive |

## Not covered

- No T3-versus-S4, T3-versus-S4b or T3-versus-S5b score comparison or pooling:
  amendment 1 preserves separate campaign reporting even after trusted-agent
  resource limits were removed.
- No significance, power or replication claim of any kind; no screen here is fresh.
- No pooled adjudication or holdout estimate unless at least two groups select a
  candidate; a single-group result is described as such.
- No claim that a changed candidate is better than the identity-passthrough seed
  beyond its own measured dev delta, and no claim that editing code is a better
  artifact form than editing a skill.
- No cumulative-growth claim: each attempt produces at most one candidate from the
  frozen seed.
- No acceptance or release to any product; `apply()` stays record-only.
