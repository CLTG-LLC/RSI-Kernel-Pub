# E2 prereg addendum — the skill tier on six further read-only groups (issue #114)

Amendment to `docs/prereg-gdpevo-pilot.md` for a broader skill-tier experiment. The
frozen pre-registration is untouched; this file records the change under the COS
"Transparent Changes" rule for preregistration amendments
(https://www.cos.io/initiatives/prereg). Forward-only: it governs E2 only.

Scope convention: only what changes is stated here. Everything else — the dev /
adjudication / holdout carve, schedule, arms, metric, retention rule, estimator,
isolation and the skill artifact — is `docs/prereg-gdpevo-pilot.md` (frozen) and
`docs/prereg-s4-addendum.md` (the trimmed final phase), adopted by reference.

Timing: written before any E2 run directory, solve, observation or acceptance
record exists, and before any task, rubric, answer or evaluator text from groups
004–009 has been read by the lead or any worker. Prior group-selection verification
inspected metadata only. It does not change how acceptance is decided.

## 1. Why

Every skill, memory and harness-code campaign so far used groups 001–003. S4, S5b
and E1c each retained an update with a positive adjudication difference in at least
one group; E1c is the only retention among the campaigns sharing kernel-only hash
`8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc`. With at most
three groups, the registered group bootstrap has 27 ordered draws and no power
claim is possible (`docs/prereg-gdpevo-pilot.md`, lines 160–162). E2 adds six
fresh groups to give more independent clusters and broader coverage for **one
tier and one group population**. It narrows uncertainty; it does not give a
universal yes/no.

E2 is a **broader skill-tier experiment**, not an E1c replication: E1c optimised
`solver.py` (the harness-code tier) on groups 001–003; E2 optimises `SKILL.md` on
groups 004–009.

## 2. What changes

### 2.1 Groups

A forward-only extension of the frozen "Groups" rule
(`docs/prereg-gdpevo-pilot.md`, lines 21–25: filter `env.state_mode == read_only`,
sort IDs ascending, take the first N), at the same upstream pin
`5082a777379156a048881e94940d640702e5e09a`:

**E2 groups: `task_group_004`, `task_group_005`, `task_group_006`,
`task_group_007`, `task_group_008`, `task_group_009`** — the next six unused
`read_only` groups after 001–003.

- There are **20 unused `read_only` groups** at the pin; E2 takes the first six.
- `task_group_022` is **`mutable`** and stays excluded, as in the frozen rule.
- This is reproducible **convenience selection, not representative sampling**
  (NAMED LOCAL EXCEPTION, carried from the frozen rule). Declared `read_only` is
  not measured immutability. No claim is made about groups outside 004–009.
- The carving map is unchanged per group: dev = `train_001`–`003`, adjudication =
  `train_004`–`005`, holdout = `test_001`–`005` (`docs/prereg-gdpevo-pilot.md`,
  lines 43–46). Totals over six groups: 18 dev, 12 adjudication, 30 holdout tasks.
  Any group whose layout does not provide exactly these task ids is a pre-run STOP
  (§3), not a re-carve or a substitution.

Groups 001–003 are **not** part of E2.

### 2.2 Tier, champion and proposer

The tier is the native **skill-only `SKILL.md` tier**, the original GDPevo/S4
contract, run through the frozen `gdpevo.pilot.SKILL` hooks. Nothing about the
artifact, proposer or budget changes from S4:

| Item | E2 value (as in S4) | Source |
|---|---|---|
| Champion, every E2 group | the frozen seed skill, the same file as S4 and E1c: candidate id `4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e`, raw file sha256 `b0fe3906ded74360a0c639093f11128a851aada57d12cfa48ce235195c657283` | `docs/results/gdpevo-pilot.md`, "Scope and frozen inputs"; `docs/prereg-e1c-harness-code-addendum.md` §2.3 |
| Allowed edits | the candidate is exactly one UTF-8 `SKILL.md`; no support files (NAMED LOCAL RESTRICTION); one skill per group, never applied across groups | `docs/prereg-gdpevo-pilot.md` lines 31–36; `validate_skill` |
| Proposer | standalone GEPA `InstructionProposalSignature` + `run_proposal` at commit `3d34469165f0d604df3b48f1d5c776e9080f3da0`; dev-only reflection with projected `{score, correct}` | `docs/prereg-gdpevo-pilot.md` lines 123–124, 184–192, 213–216 |
| Proposer and solver model | `gpt-6.1-sol`, reasoning effort `xhigh` | `docs/prereg-gdpevo-pilot.md` lines 59–65 |
| Proposals per group | `max_attempts` 3 | lines 74–76 |
| Evaluation budget | `eval_cap` 36 item-evaluations per group | lines 77–78 |
| Spend | **42 logical model calls per group campaign** (36 solver + 3 proposer + 3 D2); failed calls metered; proposer retries logged, not metered again | lines 79–90; `docs/prereg-s4b-addendum.md` §3 |
| Final phase | adjudication + holdout × 3 runs × champion/candidate = **42 solves per group with a selected candidate**; dev read from the optimise archive; no control arm | `docs/prereg-s4-addendum.md` lines 49–64 |
| Timeouts | 3600 s solver and evaluator | `docs/prereg-gdpevo-pilot.md` lines 69–72 |

Each E2 group starts from the seed, so each campaign is a root campaign with
`champion_id` `4ef108e5…a09e`, as in S4. No loader, format, validation or cap is
added.

### 2.3 Driver support

Running groups 004–009 needs bounded driver support (issue #113): the registered
group set in the driver and CLI, its guards, and tests. It reuses the existing
root-denial and port/health mechanisms. It must not change grading, selection,
retention, approval matching or the calibration identity (§3). D2 token metering
(§4.4), if it needs code, ships in the same pin.

## 3. Run identity and pre-run STOPs

- New run directory: **`pilot-008`**. `pilot-001`–`pilot-007` are separate records
  and are not reused or edited.
- Code pinned to the **first `main` commit that contains both this addendum and the
  merged issue #113 support**, in a clean detached run tree. Its git SHA, the full
  code hash (`_code_hash()`) and the kernel-only hash
  (`_code_hash(exclude=("adapters",))`) go in the code-identity log **before the
  first solve**, including the smoke. Differences from earlier campaigns are
  recorded descriptively; no unchanged-kernel claim is made. **A code pin with
  identity drift is a STOP**, before or during the run.

Pre-run STOPs. All must hold, in this order, before the first E2 campaign solve:

1. **Driver pinned.** The issue #113 driver support is merged and is in the pinned
   commit; its tests pass on the run tree. A missing or unmerged change is a STOP.
2. **Groups restored, not read.** Groups 004–009 are restored at the upstream pin.
   A hash manifest of each group's file tree (path and SHA-256 of every file) is
   recorded before any solve. No task, rubric, answer or evaluator text is read by
   the lead or any worker; the only field the driver reads before the campaign is
   `env.state_mode`, which must be `read_only` for all six (the frozen rule's
   check). Any other value, a missing group or a non-matching task-id layout is a
   STOP.
3. **Per-group runtime health.** For each of 004–009, the existing task-env checks
   pass live: Docker health `healthy`, `/health` ok and judge POST returning 404,
   with `TASK_ENV_ENABLE_JUDGE=0` in the proposer and injected solver config
   (`docs/prereg-gdpevo-pilot.md` lines 194–200). A failing group is a STOP for the
   run, not a silent drop.
4. **Calibration identity preserved.** The calibration task stays
   `task_group_001/train/001` with answer sha256 `5eb5cc63…ae96b` and output sha256
   `12308ca22e257b47c05099acec8679a9a06f2205c99870578885098adbf6205e`, independent
   of the extended group set. The grader-only replay reproduces byte-identically
   (`docs/prereg-gdpevo-pilot.md` lines 227–233). It is not a solve.
5. **Fresh live smoke.** The lead-only live smoke
   `tests/adapters/test_gdpevo_solver_live.py` runs once at the pin with the seed
   skill, `RSI_LIVE_GDPEVO=1`, outside CI, and shows exactly **`1 passed`**; a skip
   or failure is a STOP, not a rescue rerun. It runs on `task_group_001/train/001`,
   so no E2 task is exposed by it.
6. **Exposure reconciled** per §5, from actual records.

## 4. Analysis

### 4.1 Primary estimate

The registered estimator is primary and unchanged: the paired group-cluster
bootstrap in `rsi_kernel/analysis.py` (`paired_group_bootstrap`: macro-mean of
per-group candidate − champion, SciPy `bootstrap(paired=True)` defaults — BCa,
two-sided 95%, 9,999 resamples; degenerate BCa reported as-is). It runs over the
E2 groups that **actually have a selected candidate**, on each split separately;
the primary estimand is the **holdout** paired macro-mean difference. Bootstrap
entropy is recorded once for `pilot-008` before the first final solve. Below two
paired groups the pooled comparison is `"unavailable"`, as before; no replacement
estimator is added. A task-level bootstrap is not run.

### 4.2 What is counted, separately

Reported separately, never imputed: groups **attempted**; groups with a
**selected candidate**; **operational STOPs** (by group and stage); and the actual
**paired task count and cluster count** entering each split's estimate. A group
with no selected candidate contributes no pairs and is reported in the per-group
table only. Missing, corrupt or duplicate records block, as before.

### 4.3 Planning numbers are not guarantees

Planning benchmarks from the measurement plan's lead disposition (kept outside the
published tree), iid normal approximation: n = 26 / 47 / 159 paired tasks for
δ = 0.05 / 0.037 / 0.02 at σ 0.09; minimum detectable effect about 0.046 at
30 pairs, or 0.059 at σ 0.116. These are **planning numbers only**: they ignore
clustering, assume every group selects a candidate and guarantee nothing. A
nonsignificant result is reported as its estimate and interval, not as "no effect".

### 4.4 Historical groups and D2 tokens

Groups 001 and 003 (and 002) keep their own campaign records and estimates; they
are reported in a separate historical table and **never pooled** with E2.

D2 (Jev) token usage is **metered** in E2: earlier rows recorded
`token_usage: null` (`docs/results/s4b-continuation.md`, "Cost"). If this needs
code, it ships in the issue #113 pin, frozen and hashed with the rest of the run
tree; a D2 call with no recoverable usage is recorded as unknown, not zero. D2
effectiveness itself is not evaluated here.

## 5. Exposure

Groups 004–009 have **zero prior exposure** in this project: no prior campaign,
final phase or smoke solved any of their tasks, and the restoration in §3 reads no
task text. The reconciliation still records **actual** counts per split and group
from `pilot-001`–`pilot-007` and every smoke before the first solve; a missing
record is a STOP, not an assumed zero. Groups 001–003 history (all splits
adaptive after S4, S5, S5b, S4b, E1c, S5c and E1d) is stated in a separate
section and does not affect E2's fresh status. The public-repository pretraining
caveat (`docs/prereg-gdpevo-pilot.md` lines 207–209) applies to every group.

What E2 round 1 may add: ≤ 36 solver attempts per group in the campaign, 42 final
solves per group that selects a candidate, and the one smoke on group 001. These
are registered bounds, not predictions.

## 6. Retention and approval

Unchanged: zero-margin per group (non-negative mean paired dev delta selects;
retention on **adjudication**, ties pass); holdout **reported, not gated**
(invalid or incomplete evidence still blocks); approval **hash-bound per request**
to candidate, evaluator, data and code hashes; `apply(hash)` record-only. Under
the owner's recorded standing grant, the lead may approve a record-only apply when
retention passes; each approval is logged with its request hashes and the grant. No new
threshold, significance test or per-item gate is added.

## 7. Round 2

There is **no significance gate** for round 2. Round 2 follows the existing
approved-champion continuation rule (`docs/prereg-s4b-addendum.md` §2–5,
`docs/prereg-s5c-addendum.md`, `docs/prereg-e1d-addendum.md`), on exactly the E2
groups with a **retained approved round-1 champion**; others are excluded, not
restarted from the seed.

- Champion: the approved round-1 `selected` `SKILL.md` bytes, loaded through
  `gdpevo.pilot._champion` with its file sha256 in the run config; the reconstructed
  id must equal the approved `candidate_hash` (STOP otherwise); lineage via
  `parent_ids`.
- Predeclared budget, per eligible group: the same 42-call campaign cap,
  `eval_cap` 36, `max_attempts` 3 and 42 final solves; at most six groups. No
  further round is registered here.
- New run directory `pilot-009`, same pin rule, identity log and pre-run STOPs as
  §3 (a fresh smoke, actual exposure reconciliation including round 1).
- Reported: eligible groups; per group "retained second update" or "no second
  retained update" (STOPs reported as STOPs); the **marginal round-2 differences**
  (round-2 candidate vs round-1 champion, measured contemporaneously); and the
  reused-holdout exposure. Any sum of round-1 and round-2 differences is labelled
  "an indirect chained estimate using separately measured generation-1 scores,
  not a direct contemporaneous comparison"; a positive cumulative estimate does not
  show a positive second increment. No compounding claim is made.

## 8. Cost

Extrapolations only, rebased on measured skill-tier records; actual tokens and
wall time are reported from E2's own records. No billed cost exists
(`cost_usd: null` throughout); none is modelled.

| Measured basis | Per group | Source |
|---|---|---|
| Campaign input tokens | 5.15–7.31M (S4), 5.66–7.76M (S4b) | `docs/results/gdpevo-pilot.md` "Cost"; `docs/results/s4b-continuation.md` "Cost" |
| Final-phase input tokens, per group with a candidate | 8.08–13.85M (S4b); S4 9.03M average over two groups | same |
| Cached input fraction | about 85% (S4 and S4b combined) | same |
| Proposer tokens | 14.8k–38.1k input per group | same |
| D2 tokens | **unknown** (recorded null) | `docs/results/s4b-continuation.md` |

Known-token extrapolation for round 1 over six groups: campaigns about 31–47M
input tokens; finals up to about 48–83M if all six select a candidate; total about
79–130M input tokens, of which about 85% cached. D2 tokens are unknown until
metered. Round 2 adds at most the same per eligible group.

Wall time is a **scheduling estimate**: measured campaigns took 1.57–2.04 h and
finals 2.58–2.76 h per group. Runs follow the **4-heavy-job cap** in waves: groups
004–007 first, then 008–009, campaign then final, so round 1 is roughly two waves of
campaigns and two of finals. Nothing here is a cap or a guarantee.

## 9. Ordering

E2 starts only after **E1d's terminal record** (including its final phase if any;
an operational STOP there is not completion) **and** the merge of issue #113 and
this addendum. Round 2 starts only after every round-1 group has a terminal record.

## 10. Sources

- `docs/prereg-gdpevo-pilot.md` (frozen; line citations above);
  `docs/prereg-s4-addendum.md` (trimmed final phase, lines 49–64).
- `docs/prereg-s4b-addendum.md`, `docs/prereg-s5c-addendum.md`,
  `docs/prereg-e1d-addendum.md`: approved-champion continuation, lineage, exposure
  STOP and status/outcome reporting.
- `docs/prereg-e1c-harness-code-addendum.md` §2.3 (seed skill identities);
  `docs/results/gdpevo-pilot.md` and `docs/results/s4b-continuation.md` (measured
  skill-tier cost and wall time).
- `src/rsi_kernel/analysis.py` (`paired_group_bootstrap`, `retention_per_group`);
  `src/rsi_kernel/adapters/gdpevo/pilot.py` (`SKILL`, `_champion`, `SPEND_CAP`,
  `CALIBRATION_TASK`, `_code_hash`).
- [GDPevo at the pinned revision](https://github.com/Prism-Shadow/GDPevo/tree/5082a777379156a048881e94940d640702e5e09a).
- [SciPy bootstrap](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html).
- [COS preregistration — Transparent Changes](https://www.cos.io/initiatives/prereg).
