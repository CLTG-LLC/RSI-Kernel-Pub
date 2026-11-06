# S4b prereg addendum — a second campaign from the approved S4 champions (issue #48)

Amendment to `docs/prereg-gdpevo-pilot.md` for a second S4 skill-artifact campaign.
The frozen pre-registration is untouched; this file records the change under the COS
"Transparent Changes" rule for preregistration amendments
(https://www.cos.io/initiatives/prereg). Forward-only: it governs this campaign only.

Amended 2026-11-06, before any S4b solve existed, under the same COS
"Transparent Changes" rule (https://www.cos.io/initiatives/prereg).

Scope convention: only what changes is stated here. Everything else — groups, the
dev / adjudication / holdout carve, schedule, arms, metric, retention rule,
estimator, isolation, the skill artifact and the trimmed final phase — is
`docs/prereg-gdpevo-pilot.md` (frozen) and `docs/prereg-s4-addendum.md` (the trimmed
final phase), adopted by reference.

## 1. Why

This is the first test of **continuation**: a champion N+1 built on an approved
champion N, rather than on the frozen seed skill. S4 ended with an approved candidate
per paired group, so the archive now holds a parent for a second campaign.

The S4 campaign started from the same frozen champion in all three groups and
produced one update per paired group. Nothing in the frozen pre-registration lets a
second campaign start from an update; it names one champion per group, frozen before
the run. This addendum records that change before any S4b solve exists.

Precedent for iterating from an archive rather than a fixed seed: GEPA
(arXiv 2507.19457) and the Darwin Gödel Machine (arXiv 2505.22954) both continue from
their own archived results.

Timing: written before any S4b run directory, campaign, observation or acceptance
record exists, so it cannot be tuned to the data it will measure. It does not change
how acceptance is decided.

## 2. What changes

### 2.1 The champion is the approved S4 candidate

Each campaign group starts from that group's **approved** S4 candidate, loaded
through the existing hash-checked champion loader (`gdpevo.pilot._champion`). No new
loader, format or validation is introduced.

| Group | Champion for S4b | S4 `selected.id` |
|---|---|---|
| `task_group_001` | approved S4 candidate | `3ef20ac564f77e7276361ac1305b3dbded320e6df258326f4102d59d3bc1688c` |
| `task_group_003` | approved S4 candidate | `96f5e060365012822c6914bdddfdd7b45922d41b6e49c85d16408ecb5e2dfc10` |
| `task_group_002` | **excluded** — see §2.2 | none |

The champion file holds the candidate serialization from S4's
`<group>/campaign.json` `selected` — the `SKILL.md` component bytes exactly as that
record stores them — and its sha256 is recorded in the run config, so the loader's
hash check covers the file. One pre-run check is recorded with the run: loading the
file reconstructs a `Candidate` whose content id equals the recorded
`selected.id`. A mismatch is a STOP before the first solve.

Champion file sha256, computed when the files were written from the S4 records
(the reconstruction check above already passed for both):

- `task_group_001`: `bea09d29f38484f2616a98a8de631e5b1e18530ddfa54500f868041955c80be3`
- `task_group_003`: `1d1065e73893ffbc5a0b99e572ff6f03cab7040cfdaf43b1f5e22b0f130258c0`

Lineage is recorded, not asserted: the campaign's frozen `champion_id` is the
approved S4 candidate id, and every S4b candidate carries that id in `parent_ids`
(the existing `_admit_skill` path already does this). So each selected S4b candidate
is a child of an approved artifact, and the chain seed → N → N+1 is in the run
records.

### 2.2 Group 002 is excluded

`task_group_002` selected no candidate in S4 (every attempt was `dev_regression`) and
closed `no_improvement`. It has no approved champion to continue from, so it is
**excluded** from this campaign rather than started again from the seed. This is the
smallest choice and keeps spend down. Consequence, stated up front: S4b has at most
**two** groups with a candidate, so its paired tables can reach the existing
"at least two groups" reporting rule at best at the lower bound; no third group is
available to absorb a no-candidate outcome.

### 2.3 Caps, rules and the final phase stay as frozen

Unchanged and not restated in detail here: the dev / adjudication / holdout carve
(`docs/prereg-gdpevo-pilot.md`, "Frozen inputs, artifact and carving rule"), 3 runs
per task, `max_attempts` 3, `eval_cap` 36 and the **42-call spend cap per group**
(36 solver + 3 proposer + 3 D2), the zero-margin non-regression rule, the trimmed
final shape (adjudication + holdout × 3 runs × champion/candidate = **42 solves per
group with a candidate**; dev read from the optimise archive, no control arm), and
hash-bound owner approval, which binds `code_hash` in the approval record as of
`fc838e5` (issue #42). No new threshold, significance test or per-item gate is added.

## 3. Run identity

- New run directory: **`pilot-004`** for the skill artifact. `pilot-001` (S4),
  `pilot-002` (S5) and `pilot-003` (S5b) are separate records and are not reused or
  edited.
- Code pinned to the first `main` commit that contains this amendment, superseding the
  earlier pin to the commit that first added this addendum. The run tree is a clean
  detached checkout of it; its git SHA and both identity hashes go in the run's
  code-identity log **before the first solve** (`docs/prereg-s5b-addendum.md` §3).
- What the pin changes. Grading, selection, retention and approval-matching criteria
  are unchanged — `loop.py`, `analysis.py` and `gdpevo/scoring.py` are byte-identical
  between `6f04c52` and the new pin. Changed on the S4b path: #57 (PR #62) the proposer
  model call retries transient errors — connection errors, 408/409/429/>=500, 2
  retries — exactly as the openai-python SDK does by default, trigger S5b group 003
  lost to one upstream HTTP 502 (report pending); #60 (PR #64) the approval request is
  published atomically (temp file + `os.replace`), schema/wait/matching unchanged;
  #49 (PR #55) the candidate is validated before staging and the solver, final phase
  included, not after — valid ones score the same. `code_hash` and `evaluator_hash`
  differ since both include adapter source bytes; #59 is T3-only; CLI/MCP/plugin are
  not called by the pilot.
- Retry accounting: the 42-call cap counts **logical** calls; a proposer call may make
  its initial request plus up to two retries, logged as `retry` rows but not metered
  again, so "failed calls included" (`docs/prereg-gdpevo-pilot.md` lines 79–89) is per
  logical call and failed attempts' tokens may be unknown — 42 is not an HTTP bound.
- Pre-run STOP, in this order: (a) freeze identity and reconcile the S5b exposure
  (§4); (b) run the lead-only live smoke `tests/adapters/test_gdpevo_solver_live.py`
  once at the pinned commit, using the approved group-001 champion on
  `task_group_001/train/001`, with `RSI_LIVE_GDPEVO=1`, outside CI — one executed,
  passing test; a skip does not count; (c) record its actual exposure, including any
  operational failure; then (d) the first campaign solve. S5b did not run this fresh,
  per its report.
- Two hashes, one formula (`gdpevo.pilot._code_hash`): the **full code hash**
  (`_code_hash()`) and the **kernel-only hash** (`_code_hash(exclude=("adapters",))`),
  both recomputed on the run tree. Both are expected to differ from the S4 values
  recorded in `docs/results/gdpevo-pilot.md`: the kernel has changed since S4 (issue
  #42 bound `code_hash` in the approval record), and the adapter has changed since S5.
  No unchanged-kernel premise is claimed here. Drift during the run remains a STOP.

## 4. Exposure

Every screen used here is already **adaptive**; no split is fresh. Counts are taken
from the actual preceding runs, per split and per group, including smokes.

| Split | Group | Prior solves | Source |
|---|---|---|---|
| dev | `task_group_001` | 36 (S4 optimise: 3 tasks × 3 runs × 4 artifacts) + 8 feasibility attempts of `train/001`, of which 1 was scored and 7 stopped operationally (3 of those consumed tokens with no answer) + 3 runner smoke solves | `docs/prereg-gdpevo-pilot.md` lines 4–8; `docs/results/gdpevo-pilot.md`, exposure log |
| dev | `task_group_002` | 36 (S4 optimise) + 1 pre-run smoke solve | `docs/results/gdpevo-pilot.md`, exposure log |
| dev | `task_group_003` | 36 (S4 optimise) + 2 pre-run smoke solves | same |
| dev | 001 / 002 / 003 | + 9 each from S5 (champion dev, 3 attempts), + 1 S5 pre-run smoke solve (001) | `docs/results/e1a-two-artifact.md`, "S5 exposure added by this run" |
| adjudication | `task_group_001` | 12 graded solves (S4 final) | `docs/results/gdpevo-pilot.md`, exposure log |
| adjudication | `task_group_003` | 12 graded solves (S4 final) | same |
| adjudication | `task_group_002` | 0 (no candidate) | same |
| holdout | `task_group_001` | 30 graded solves (S4 final) | same |
| holdout | `task_group_003` | 30 graded solves (S4 final) | same |
| holdout | `task_group_002` | 0 (no candidate) | same |

S5b (`pilot-003`) is running now and may also use these screens, including
adjudication and holdout: the S5b addendum runs the 42 final solves for any group
that selects a candidate (`docs/prereg-s5b-addendum.md` §4), so it can add a further
read of those splits for groups 001 and 003. Before the first S4b solve, a pre-start
reconciliation reads S5b's own record and adds its **actual** dev solves, smoke
solves, adjudication solves and holdout solves per group to the table above. That
reconciliation is a STOP condition, not an estimate: until it is recorded, the
campaign does not start, no S5b count or split usage is predicted here, and zero is
not assumed for any S5b line above.

What S4b adds, on the same already-exposed screens: at most 9 champion dev solves
plus 9 candidate dev solves per attempt per group (≤ 36 solver attempts per group),
and — only if a group selects a candidate — the 42 final solves.

The pre-run live smoke in §3 is its own row: one dev solve of
`task_group_001/train/001`. Record the single smoke solver attempt and its outcome
separately from campaign attempts, outside the campaign caps. Record any
model-request retries separately; they are not additional solver attempts.

The adjudication and holdout splits of groups 001 and 003 were each read once
already, in the S4 final, and S5b may read them again before this campaign starts, as
recorded by the reconciliation above. Whatever S4b reads there is **further reuse**,
disclosed as such: it cannot make those screens unseen, and it cannot turn a retention
pass into an independent confirmation. **No independence, replication or
compounding-efficacy claim is made.** S4b does not recover a fresh split, does not
replicate S4 or S5b, and its result — positive or negative — does not show that
continuation compounds.

## 5. What is reported

Two parts, reported separately.

**Status: "continuation tested".** A factual status, not an outcome. It holds once
the campaign started from the verified approved artifact — the champion id, file
sha256 and reconstructed id recorded per §2.1, and lineage present in the run records.
It is reported whether or not any candidate is selected, and it is not a claim about
the result.

**Terminal outcome, one per group**, read from the existing acceptance record
(`<group>/acceptance.json`, the `accept()` result). Exactly one applies — now
mutually exclusive, unlike the earlier status/outcome wording:

- **"retained second update"** — the `accept()` outcome is `updated`; or
- **"no second retained update"** — any other completed outcome, with the reason the
  record gives.

`updated` means the existing path completed in full: a candidate selected on dev
under the zero-margin rule, adjudication retention passed by the existing rule,
valid and complete evidence on both final splits, and a matching hash-bound owner
approval. Every one of those is an existing condition; this addendum adds none.

Holdout score non-regression is **not** an additional gate. `accept()` applies the
retention rule to adjudication; the holdout comparison is reported, and it blocks
only on invalid or incomplete evidence. Reporting the holdout result is not a
condition of "retained second update", and no numerical gate is attached to it.

An operational STOP stays distinct from a completed negative outcome: a STOP before
or during the campaign is reported as a STOP, with nothing solved after it, and
never as "no second retained update". A partial result (one group `updated`, one
not) is reported per group, never pooled.

## 6. Sources

- `docs/prereg-gdpevo-pilot.md` (frozen pre-registration); `docs/prereg-s4-addendum.md`
  (trimmed final phase); `docs/prereg-s5b-addendum.md` §3 (code-identity recording);
  `docs/results/gdpevo-pilot.md` (S4 results, approved candidate ids and exposure log);
  `docs/results/e1a-two-artifact.md` (S5 exposure log).
- [COS preregistration — Transparent Changes](https://www.cos.io/initiatives/prereg).
- GEPA, arXiv 2507.19457: iterative refinement that continues from previously
  evaluated candidates held in its archive.
- Darwin Gödel Machine, arXiv 2505.22954: open-ended self-modification that samples
  its next parent from an archive of its own earlier variants.
