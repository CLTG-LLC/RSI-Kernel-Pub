# S5c prereg addendum — a second campaign from the approved S5b memory library (issue #75)

Amendment to `docs/prereg-gdpevo-pilot.md` for a second memory-library campaign.
The frozen pre-registration is untouched; this file records the change under the COS
"Transparent Changes" rule for preregistration amendments
(https://www.cos.io/initiatives/prereg). Forward-only: it governs this campaign only.

Amended 2026-11-06, before any S5c solve existed, under the same COS
"Transparent Changes" rule (https://www.cos.io/initiatives/prereg).

Scope convention: only what changes is stated here. Everything else — the
dev / adjudication / holdout carve, schedule, arms, metric, retention rule,
estimator, isolation, the memory artifact and the trimmed final phase — is
`docs/prereg-gdpevo-pilot.md` (frozen), `docs/prereg-s5-addendum.md` (memory artifact),
`docs/prereg-s5b-addendum.md` (evaluate before admission) and
`docs/prereg-s4-addendum.md` (the trimmed final phase), adopted by reference.

## 1. Why

This tests **continuation from an approved memory artifact**: a candidate built on
an approved memory library, rather than on the empty seed library. S5b ended with
an approved candidate for `task_group_001`, so the archive now holds a parent for a
second memory campaign.

S5b started from the empty library in all three groups and produced one approved
update. Its addendum does not authorize a second campaign from that update. This
addendum records that change before any S5c solve exists. It follows the
`docs/prereg-s4b-addendum.md` pattern, without changing the live admission path.

Precedent for approved inter-campaign continuation: RRSI
(arXiv 2609.24972v3, Appendix D.1) iterates from earlier harness changes. The
continuation assessment §4.14, kept outside the published tree, adopts that
precedent for a new campaign from an approved artifact, not for bypassing approval
or changing the incumbent within a campaign.

Timing: written before any S5c campaign, observation or acceptance record exists,
so it cannot be tuned to the data it will measure. It does not change how
acceptance is decided. Docker solves are serialized: **S4b → E1c → S5c, including
final phases**. S5c starts only after E1c's final phase has a terminal record; an
operational STOP there is not silently treated as completion or permission to
continue.

## 2. What changes

### 2.1 The champion is the approved S5b candidate

`task_group_001` starts from its **approved** S5b candidate, loaded through the
existing hash-checked champion loader (`gdpevo_memory.pilot._champion`). No new
loader, format or validation is introduced.

| Group | Champion for S5c | S5b `selected.id` / `candidate_hash` |
|---|---|---|
| `task_group_001` | approved S5b memory library | `db7af32578f5bcd75114309a0088988bb23e4dcfa4b38a2cca4e314ecd508144` |
| `task_group_002` | **excluded** — see §2.2 | none |
| `task_group_003` | **excluded** — see §2.2 | none |

Owner approval is **R-179**, 2026-11-06; the S5b acceptance outcome is `updated`.
The request and approval match on candidate, evaluator, data and code hashes, and
apply was record-only (`docs/results/e1a-s5b-evaluate-first.md`, "Acceptance
outcome"). The approved candidate's parent is the empty library, content id
`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`.

The champion file holds the candidate serialization from
`pilot-003/task_group_001/campaign.json` `selected` — `components`, `media_type` and
`parent_ids` exactly as that record stores them — and its file sha256 is recorded
in the run config, so the loader's hash check covers the file. Before the first
solve, record that loading it reconstructs a valid `Candidate` whose content id
equals the approved `candidate_hash` above and whose parent is the empty library.
Record the matching S5b approval and acceptance evidence. A mismatch is a STOP.
No file hash is predicted here; it is computed from the actual champion file.

Lineage is recorded, not asserted: the campaign's frozen `champion_id` is the
approved S5b candidate id, and every S5c candidate carries that id in `parent_ids`
(the existing `gdpevo_memory.library.admit` path already does this). The run
records therefore retain the chain empty library → approved S5b library → S5c
candidate.

Admission stays **add-only**. The live pilot wires `admit_draft`
(`src/rsi_kernel/adapters/gdpevo_memory/pilot.py:50–52`), which always selects
`"add"` (`src/rsi_kernel/adapters/gdpevo_memory/proposer.py:50–55`). A valid,
non-duplicate draft becomes an isolated candidate through that existing path;
paired dev evaluation decides selection. Existing entries are not merged or
revised. **Merge and revise stay unexercised live**, even though the champion now
has an entry; their write-guard tests are not live evidence. Exercising them needs
a separately specified adapter change and its own preregistration. **No D4 call
is restored.** The kernel still passes the same original campaign champion to
every proposal; this is inter-campaign continuation, not cumulative incumbent
updates within a campaign.

### 2.2 Groups 002 and 003 are excluded

`task_group_002` selected no candidate in S5b (every attempt was `dev_regression`)
and closed `no_improvement`. It has no approved library to continue from.
`task_group_003` had an **operational STOP** at a proposer HTTP 502; its campaign
was left `open`, with no selected candidate or acceptance record. That is not a
negative result and supplies no approved library.

Both are **excluded** rather than restarted from the empty seed. S5c is group 001
only. Consequence, stated up front: at most **one** group can have a candidate,
so the existing "at least two groups" pooled reporting rule cannot be reached.
Pooled comparisons and group-clustered uncertainty remain `"unavailable"`; no
replacement estimator or threshold is added.

### 2.3 Caps, rules and the final phase stay as frozen

Unchanged and not restated in detail here: the dev / adjudication / holdout carve,
3 runs per task, `max_attempts` 3, `eval_cap` 36 and the **45-call spend cap per
memory campaign** (`docs/prereg-s5b-addendum.md` §2.2: 36 solver + 3 proposer +
3 D2, with 3 unused former D4 slots). Failed calls stay metered. The cap is not
lowered to 42; the unused slots remain headroom. Final solves and smokes are
outside the campaign cap.

The zero-margin rule is unchanged: non-negative mean paired dev delta is eligible,
**ties pass**, and retention applies to **adjudication only**. Holdout is reported,
not a score non-regression gate; invalid or incomplete final evidence still blocks.
The trimmed final shape is adjudication + holdout × 3 runs × champion/candidate =
**42 solves for group 001 if it selects a candidate**; dev is read from the optimise
archive, with no dev re-run and no control arm. Approval binds **candidate,
evaluator, data and code hashes**, and `apply(hash)` is **record-only**: it does not
replace the champion or activate enforcement. No new threshold, significance test
or per-item gate is added. Calibration replay, isolation and the frozen named
local exceptions are carried unchanged.

Historical planning figures only: S5b group 001 measured **78 solver attempts +
3 proposer + 3 D2 = 84 logical model calls**, with **4.11 h** recorded wall time
(36 campaign solves and 1.93 h, plus 42 final solves and 2.18 h;
`docs/results/e1a-s5b-evaluate-first.md:498–503`). These are not a prediction,
guarantee or S5c measurement. Required smokes come on top. Actual calls, tokens,
failures and wall time are reported from S5c's own records; no billed cost is
invented. Logical calls are not an HTTP-request bound: request retries are logged
separately under the existing accounting rule.

## 3. Run identity

- New run directory: **`pilot-006`** for the memory artifact. `pilot-001` (S4),
  `pilot-002` (S5), `pilot-003` (S5b), `pilot-004` (S4b) and `pilot-005` (E1c)
  are separate records and are not reused or edited.
- Code pinned to the **first `main` commit that contains this addendum**. The run
  tree is a clean detached checkout of it; its git SHA and both identity hashes
  go in the run's code-identity log **before the first solve**, including the
  pre-run live smoke (`docs/prereg-s5b-addendum.md` §3).
- Two hashes, one formula (`gdpevo.pilot._code_hash`): the **full code hash**
  (`_code_hash()`) and the **kernel-only hash**
  (`_code_hash(exclude=("adapters",))`), both recomputed on the run tree. Record
  differences from S5b descriptively, rather than assuming an unchanged kernel.
  Identity drift during the run remains a STOP.
- Pre-run STOP, in this order: (a) freeze and verify identity, including the
  champion reconstruction and prior approval in §2.1; (b) run the lead-only fresh
  live smoke `tests/adapters/test_gdpevo_solver_live.py` once at the pinned commit,
  with the approved group-001 library rendered through the existing `render_skill`
  and its exact rendered file hash checked by the smoke, on
  `task_group_001/train/001`, with `RSI_LIVE_GDPEVO=1`, outside CI — **exactly one
  executed, passing test; a skip does not count**; (c) reconcile and record actual
  exposure per split and group across S4, S5, S5b, S4b, E1c and all smokes (§4),
  including this fresh smoke; then (d) the first campaign solve. Until all three
  checks are recorded, the campaign does not start. A smoke failure is a STOP,
  not a passing check or permission for an unregistered rescue rerun.

## 4. Exposure

Every screen used here is already **adaptive**; no split is fresh. Counts are
taken from the actual preceding runs, per split and per group, including smokes.
No predicted counts or ordinal reuse label replaces that reconciliation.

| Prior use | Split and group to reconcile | Source |
|---|---|---|
| S4, including feasibility and runner smokes | dev, adjudication and holdout, separately for 001 / 002 / 003 | `docs/results/gdpevo-pilot.md`, exposure log |
| S5 and its smoke | the same per-split, per-group accounting | `docs/results/e1a-two-artifact.md`, exposure log |
| S5b | the same accounting, including the group-003 operational STOP and disclosures | `docs/results/e1a-s5b-evaluate-first.md`, exposure log |
| S4b, including its final phase and smoke | the same accounting from actual terminal records, including excluded groups | `pilot-004` records; `docs/prereg-s4b-addendum.md` §4 |
| E1c, including its final phase and smoke | the same accounting from actual terminal records | `pilot-005` records; `docs/prereg-e1c-harness-code-addendum.md` |
| Every other smoke, including the fresh S5c smoke | its actual split, group, attempts and outcome | smoke evidence and logs; §3 |

Before the first campaign solve, the reconciliation records **actual counts for
each split and each group**, with source records and separate campaign, final and
smoke contributions. Groups 002 and 003 remain in that accounting even though
S5c excludes them. Missing records are a STOP, not an assumed zero. S4b and E1c
usage is read only after their terminal records exist; no counts or split usage
are predicted here.

Count executed solver attempts and their outcomes, including operational failures
and ungraded attempts, rather than silently counting only successful graded rows.
Record model-request retries separately; they are not additional solver attempts.
Grader-only calibration replays are not solves. Additional disclosures, including
the S5b holdout grader-output disclosure, are recorded separately from solve
counts. Reconcile smoke logs across campaigns without double-counting earlier
smokes listed again in later reports.

What S5c may add, under the unchanged caps on the same exposed screens: at most
9 champion dev solves plus 9 candidate dev solves per attempt (≤ 36 solver
attempts for group 001), and — only if it selects a candidate — the 42 final
solves. These are registered bounds, not predicted exposure counts.

The pre-run live smoke in §3 is its own row. Record the actual solver attempt and
outcome separately from campaign attempts, outside the campaign caps, including
any operational failure. Its required passing result does not make the dev task
fresh. Record S5c's actual dev, adjudication and holdout usage as the run proceeds.

Whatever S5c reads is **further reuse**, disclosed as such: it cannot make those
screens unseen, and it cannot turn a retention pass into an independent
confirmation. **No independence, replication or compounding-efficacy claim is
made.** S5c does not recover a fresh split, does not replicate S5b, and its result
— positive or negative — does not show that continuation compounds.

## 5. What is reported

Two parts, reported separately.

**Status: "continuation from an approved memory artifact demonstrated" or
"not demonstrated".** A factual execution status, not an efficacy or acceptance
outcome. Demonstrated means the campaign started from the verified approved S5b
library — champion id, file sha256, reconstructed id, prior approval and lineage
recorded per §2.1. It is reported whether or not a new candidate is selected.
Without that execution evidence the status is "not demonstrated", with the reason;
it does not turn an operational STOP into a completed negative outcome.

**Terminal outcome for group 001**, read from the existing acceptance record
(`task_group_001/acceptance.json`, the `accept()` result). Exactly one applies to a
completed campaign:

- **"retained second update"** — the `accept()` outcome is `updated`; or
- **"no second retained update"** — any other completed outcome, with the reason
  the record gives.

`updated` means the existing path completed in full: a candidate selected on dev
under the zero-margin rule, adjudication retention passed by the existing rule,
valid and complete evidence on both final splits, and matching four-hash owner
approval. Apply remains record-only. Every one of those is an existing condition;
this addendum adds none.

Holdout score non-regression is **not** an additional gate. `accept()` applies the
retention rule to adjudication; the holdout comparison is reported, and it blocks
only on invalid or incomplete evidence. No numerical gate is attached to it.

An operational STOP stays distinct from a completed negative outcome: a STOP
before or during the campaign is reported as a STOP, with nothing solved after it,
and never as "no second retained update". Excluded groups have no S5c outcome and
are not pooled with group 001.

The S5b §5 reporting checklist is carried: per-attempt candidate evaluated yes/no
and reason, paired dev delta and selection, paired adjudication and holdout rows,
actual cost by call type against the 45 cap (D4 = 0), both identity hashes, the
actual exposure reconciliation and descriptive adapter/kernel differences.
Pooled comparison remains `"unavailable"` below two groups; no bootstrap or interval
is fabricated. Add-only admission and live merge/revise remaining unexercised are
stated as limitations, not claimed as results.

## 6. Sources

- `docs/prereg-gdpevo-pilot.md` (frozen pre-registration);
  `docs/prereg-s5-addendum.md` (memory artifact, isolation and exposure);
  `docs/prereg-s5b-addendum.md` §2–5 (admission, 45 cap, identity and reporting);
  `docs/prereg-s4-addendum.md` (trimmed final phase).
- `docs/prereg-s4b-addendum.md` §1–6: the approved-artifact continuation addendum
  pattern, lineage checks, exposure STOP and separate status/outcome reporting.
- `docs/results/e1a-s5b-evaluate-first.md`, "Scope and frozen inputs", "Per group,
  selection and stop", "Cost" (lines 498–503), "Acceptance outcome" and "Exposure
  log": approved group-001 id, empty-library parent, R-179 approval, record-only
  `updated`, exclusions, measured planning figures and prior exposure.
- `src/rsi_kernel/adapters/gdpevo_memory/pilot.py:33–52` (hash-checked loader and
  live hooks); `src/rsi_kernel/adapters/gdpevo_memory/proposer.py:50–55`
  (`admit_draft` always selects `"add"`); `src/rsi_kernel/adapters/gdpevo_memory/library.py`
  (`admit`, immutable child and parent id).
- `docs/results/gdpevo-pilot.md`; `docs/results/e1a-two-artifact.md`;
  `docs/prereg-e1c-harness-code-addendum.md`; actual `pilot-004`, `pilot-005` and
  smoke records: sources for the pre-start exposure reconciliation, not predicted
  counts.
- [COS preregistration — Transparent Changes](https://www.cos.io/initiatives/prereg).
- [RRSI, arXiv 2609.24972v3, Appendix D.1](https://arxiv.org/html/2609.24972v3):
  inter-campaign continuation; the continuation assessment §4.14 is kept outside
  the published tree. This precedent does not authorize bypassing owner approval,
  live merge/revise or immediate within-campaign incumbent updates.
