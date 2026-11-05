# S5 prereg addendum — memory/skill-library run (issue #35)

Amendment to `docs/prereg-gdpevo-pilot.md` for slice S5 (issue #6). The frozen
preregistration is untouched; this file records the changes under the COS
"Transparent Changes" rule for preregistration amendments
(https://www.cos.io/initiatives/prereg). Forward-only: it applies to the S5 run
only, and the S4 skill pilot stays governed by the frozen file.

Relationship to S4: S4 is the skill artifact; S5 is the same bed with a
memory/skill-library artifact on the **unchanged kernel** (`docs/design.md` §7
item 5, E1a). Everything not listed here — groups, carving map, schedule, arms,
metric, retention rule, estimator, isolation — carries over unchanged.

## 1. Artifact: a JSON library, evaluated as one rendered SKILL.md

- The champion/candidate is a JSON library: one brief per entry, keyed
  `entries/e<n>.json`, with exactly `task_pattern`, `action`,
  `completion_criteria`, `pointers` (arXiv 2611.05306v1 App. A; the wire format
  is a named local adapter template, not a paper-defined one).
- The evaluated artifact is the deterministic rendering of that library as a
  single `SKILL.md` (`gdpevo_memory/library.py:render_skill`). The host stages it
  before each solve and re-hashes it after, so the solver only ever sees a text
  skill — the same isolation boundary as S4.
- **Empty seed library**, i.e. `library_candidate([])`. Precedent: the S4
  seed carries no guidance either (`_champion` loads a champion file, not
  guidance learned in-pilot). One smoke solve on an already exposed dev task
  precedes any S5 measurement, as in S4.
- The champion config file keeps the pilot's own candidate shape — the same
  fields `campaign.json` stores for a selected candidate:

  ```json
  {"components": {}, "media_type": "application/json", "parent_ids": []}
  ```

  No new on-disk format is invented for S5. The loader rejects a hash mismatch
  and any file that is not that shape (`gdpevo_memory.pilot._champion`).
- The library size is **unbounded**: no documented bound exists for this
  artifact, so none is invented. Per-entry metrics are **not** collected for the
  same reason; see §5.

## 2. Limitation: live D4 is add/discard only

The unchanged kernel passes the same original champion to every proposal inside
one campaign (`loop.py:run_campaign` -> `proposer(champion, ...)`). With an empty
seed, every live D4 call therefore offers only `add` and `discard`: `merge` and
`revise` require an existing registered entry, and only the selected candidate —
not the champion — could carry one. Consequences, stated up front:

- the S5 run yields **no merge/revise claim** and **no cumulative-growth claim**
  (one admitted entry per attempt, from an empty library);
- `merge`/`revise` remain covered by the adapter's write-guard tests only.

## 2a. Final phase: the trimmed S4 shape (shared with #36)

S5 runs the **same trimmed final phase** as S4 — `docs/prereg-s4-addendum.md`
(frozen into main as `13d5da8`, issue #36) — not the frozen prereg's original
schedule. Rather than restate it, this addendum adopts it by reference. In
summary, for S5 as for S4:

- **Items:** adjudication + holdout only. Dev is **never re-run**; the report
  reads dev rows from the optimise archive.
- **Arms:** champion and candidate only. The control arm is gone; run-to-run
  noise is the champion's dev spread (the upstream `std@3` statistic).
- **Solves per group with a candidate:** 7 tasks × 3 runs × 2 arms = **42**.
  Order is run → task id → arm.
- **Per-group process:** `final --group G`, observations under
  `run_dir/final/<group>/observations.jsonl`, the "already ran" STOP per group,
  `entropy.json` written once.
- **No candidate:** no final solves, `acceptance.json` = `no_improvement`.
- **Rebind:** `rebind --group G --addendum PATH` records one reviewed
  pre-measurement identity change; otherwise drift STOPs before any solve.
- **Reporting:** dev / adjudication / holdout tables, paired tables only for
  groups with a candidate, `"unavailable"` below two such groups.

S5's only delta from the S4 trimmed phase is the artifact: the library is
rendered to `SKILL.md` before each solve and the staging hash is re-verified
(§1). Everything else is the S4 addendum's behaviour, unchanged.

Derivation of the numbers and their upstream source (`acc@3`/`std@3`,
`metric_and_scoring.md:115–139`) are in `docs/prereg-s4-addendum.md`; they are
not restated here. The S5 library run therefore totals 2 × 42 = 84 final solves
when two groups select a candidate.

## 3. D4 placement: host side (lead choice)

D4 admission runs on the host, inside the logical PROPOSE and before any
evaluation. The proposer container only drafts entry text: it has no credentials
(prereg "Isolation"), and `JevBackend` needs the key. So `propose` is split into

- `gdpevo_memory.proposer.draft` — in the container, one model call, text only;
- `gdpevo_memory.proposer.admit_draft` — on the host, validates the draft and
  builds the D4 envelope.

The host builds the envelope from **host-owned ids only**:
`EnvelopeBuilder(component_ids=("c1",), entry_ids=<library ids>)`. Container
output can never contribute an envelope, an operation or an entry id: the draft
is validated to exactly the four brief fields, and ids/operations come from the
host (`library.admit`). D4 uses the same `Decider` as D2, with the
`DeterministicBackend` baseline (`discard`) recorded as `baseline_answer`, and
the Jev call is metered as `jev` by the existing `_MeteredBackend`.

This split is a **lead implementation choice**, not something the prereg
mandates.

## 4. Spend cap: 45 calls per group campaign

The S4 cap of 42 covers 36 solver + 3 proposer + 3 D2. S5 adds one D4 per
attempt, so the cap is **45 = 36 solver + 3 proposer + 3 D2 + 3 D4**. The
derivation is unchanged arithmetic from the frozen prereg ("Caps"): `eval_cap`
36 solver attempts per group, 3 proposals per campaign (GDPevo `reflect-3`,
`codex/guides/skill_modes.md:119–121`), one D2 and one D4 per proposal. Failed
calls stay metered, and the campaign still halts at the first check past the cap.

## 5. D4 state: artifact-level counts only

`c1.dev_pass_count` / `c1.dev_fail_count` come from the same champion dev results
D2 sees (pass = score 1.0, as in issue #33), and are artifact-level: `c1` is the
whole library. There are **no per-entry metrics** — no documented equivalent
exists, so none is invented (same named local exception as the D3 metrics in the
frozen prereg). No entry text enters the envelope or the decision log; a canary
test asserts it.

## 6. Disclosure of S4 exposure

Prior use of the GDPevo screens before S5, by campaign and split (task-level
counts come from the S4 run records, not from this text):

- **Pre-run smokes and feasibility** (`docs/prereg-gdpevo-pilot.md`,
  `docs/prereg-s4-addendum.md` "Timing and data exposure"): group 001 `train_001`
  in the eight recorded feasibility attempts; groups 002 and 003 `train_001` in
  one or two seed-skill smoke solves each.
- **S4 optimise phase:** every dev task (`train_001`–`train_003`) of groups
  001–003, solved by the champion and by each evaluated candidate.
- **S4 final phase** (`docs/prereg-s4-addendum.md`): adjudication (`train_004`,
  `train_005`) and holdout (`test_001`–`test_005`) tasks of the groups whose S4
  campaign selected a candidate only (groups 001 and 003); group 002 selected none
  and has no final solves. Whether the S4 final completed, and its per-task solve
  counts, are **pending** until the S4 results are recorded; the S5 report must
  state them from that evidence before any S5 solve.

All of these screens are therefore **adaptive** for S5: no independence claim is
made for any of them, and S5 must not be presented as a fresh-split confirmation.
S5's champions seed from an empty library, so the S5 artifacts did not learn from
earlier rows; the limit on independence comes from prior use of the task screens
themselves.

## 7. Report additions (checklist for issue #6)

In addition to the frozen prereg report (per-split paired results, cost, exposure
log):

- [ ] dev rows read from the optimise archive (not re-run), plus paired
      adjudication and holdout results per group, champion vs candidate;
- [ ] paired tables only for groups with a candidate; `"unavailable"` when fewer
      than two such groups exist; noise = the champion's dev run-to-run spread;
- [ ] D4: Jev answer vs `baseline_answer` (`discard`) for every record, from
      `baseline_answer` only — no fabricated comparisons;
- [ ] per-call cost: solver, proposer, D2 and D4 counts against the 45 cap;
- [ ] both identity hashes below, recomputed on the run tree;
- [ ] the §2 limitation stated verbatim as a limitation, not a result;
- [ ] the §6 exposure disclosure;
- [ ] adapter diff against the kernel, reported descriptively (lines and files,
      no "thin" threshold).

## 8. Identity: full-code and kernel-only hashes

Two hashes are recorded, both against the frozen S4 commit `7919829`. Both use
**one formula** — `pilot._code_hash` — so they are comparable rather than derived
two different ways:

> sha256 over `json.dumps([*sorted (path relative to src/, sha256) for every
> src/rsi_kernel file excluding __pycache__ and the excluded package dirs,
> ("uv.lock", sha256)])`

| Identity | Call | S4 `7919829` |
|---|---|---|
| full code hash | `_code_hash()` | `ad9447f6154165298314283ccec2610aec41d0d1a0c6eb1bf880adeb402ad082` |
| kernel-only hash | `_code_hash(exclude=("adapters",))` | `e8d7b2b5d14018ab0ff68ee5b811aa133f07f60b0843638fb395c12ee6c4d209` |

Paths are relative to `src/` (e.g. `rsi_kernel/loop.py`), matching the S4
driver's own `code_hash`. Both values are pinned by
`test_addendum_identities_match_the_frozen_s4_commit`, which unpacks a
`git archive` of `7919829` and recomputes them; the test skips when the commit is
not in the local clone.

- **Full code hash** gives optimise→final continuity per group: the S4 driver
  already freezes `code_hash` in `campaign.json` and rechecks it at the final
  phase. S5 keeps that behaviour, so a mid-run code change is a STOP.
- **Kernel-only hash** gives the cross-artifact claim: the kernel must be
  identical between S4 and S5. S5 requires an empty diff on that path set:

  ```
  git diff 7919829 -- src/rsi_kernel ':(exclude)src/rsi_kernel/adapters' uv.lock
  ```

  An empty kernel-only hash difference is the E1a premise that the second
  artifact ran on the unchanged kernel; it says nothing about the adapters,
  which are expected to differ.

## 9. D4 probe: a diagnostic, a conditional prediction and its limitation

### 9.1 The probe (diagnostic, not a result)

Before the S5 run, D4 was probed live with **no task content**, to find out what
the unchanged kernel's D4 asks and how the model answers. The probe called the
kernel `JevBackend` (`jev-latest`) **directly** — not through the `Decider` —
so there is no fallback path and every answer in the table is a successful live
response. The envelope was `EnvelopeBuilder(component_ids=("c1",), entry_ids=())`
over a synthetic `DevPublicView`, with criteria `{add, discard}` (an empty
library has no merge/revise target, §2). Each row was asked twice:

| state | answers (2 calls each) |
|---|---|
| `{c1.dev_pass_count: 3, c1.dev_fail_count: 6}` | discard, discard |
| `{c1.dev_pass_count: 6, c1.dev_fail_count: 3}` | add, add |
| `{c1.dev_pass_count: 4, c1.dev_fail_count: 5}` | discard, discard |
| `{}` | discard, discard |
| `{attempt_count: 0, budget_used: 9}` | discard, discard |
| `{attempt_count: 0, budget_used: 9, c1.dev_pass_count: 3, c1.dev_fail_count: 6}` | discard, discard |

n = 12 live calls (6 states × 2), model `jev-latest`, one direct `JevBackend`,
zero fallbacks, zero non-successful responses, no task content sent.
Source: lane probe record, 2026-11-06.

Both calls returned discard for the 3/9 and 4/9 pass states, and add for the
6/9 pass state. Adding `attempt_count` and `budget_used` to the 3/9 state did not
change either response. These are observations from synthetic probe states, not
an inferred threshold and not a result.

### 9.2 Conditional prediction

**If** all of the following hold for a group, **then** the S5 campaign most
likely selects no candidate:

1. the champion's nine dev observations (3 tasks × 3 runs) are valid;
2. D2 answers `c1` on each of the three attempts;
3. three valid drafts reach D4 (D2 can answer `none`; an empty draft skips D4);
4. every live D4 response succeeds.

Under those assumptions, a champion whose probed-state dev counts look like the
≤ 4/9 rows (the S4 champions were 3/6, 3/6 and 4/5) would plausibly get
`discard` ×3 → no candidate → no final solves → `acceptance.json` =
`no_improvement` → the report's status is "unavailable".

This is a **hypothesis from the observed states, not a threshold**, and it is
not a prediction of the reported numbers. A fallback `discard` (timeout,
malformed, off-list answer) is an **operational outcome, not a Jev choice**, and
must be reported as such — never counted as agreement with the baseline.

### 9.3 How an all-discard run is reported

If every D4 response is `discard`, the report says:

> Jev matched the recorded discard baseline on every successful D4 response; no
> improvement was demonstrated, and paired efficacy comparisons are unavailable.

Agreement is **not** evidence that the proposed entries were bad: the entries
were never evaluated, because D4 is admission, not a quality judgement (§3).

### 9.4 Limitation: the D4 state cannot see the proposed entry

The kernel is frozen for #6, and its D4 envelope carries the champion's state
only (`loop.py:143–198`; `docs/design.md:33–55`). The D4 request therefore
describes **the champion, not the proposed entry**, so a D4 `discard` is a
statement about the champion's dev record as much as about the draft. Adding
post-evaluation or entry-level metrics to admission would change the registered
flow, so it is **not applied in S5**; the remedy is deferred to a later kernel
slice. S5 runs as pre-registered (option a: run it and disclose the limit).

### 9.5 Spend and exposure

- **Expected spend on the all-discard path: 18 calls per group** = 9 solver
  (champion dev: 3 tasks × 3 runs) + 3 proposer + 3 D2 + 3 D4. The §4 cap of
  **45 is unchanged**; the difference is unused headroom, not a lower cap.
- The probe's 12 calls and the pre-run smoke are **diagnostic/operational
  calls, metered separately** from the per-group campaign cap.
- **Task-content exposure: none added by the probe** (numeric state only, no
  task text). S5 itself still adds 9 champion dev solves per group plus the one
  smoke solve on an already exposed dev task (§1, §6).
- The §6 **S4 pending counts are resolved from the S4 run records before any S5
  solve**, as §6 requires.

## Sources

- Local: `docs/prereg-gdpevo-pilot.md`; `docs/prereg-s4-addendum.md` (the trimmed
  final phase S5 adopts); `docs/design.md` §2, §3, §7; issues #6, #33, #35, #36.
- [COS preregistration — Transparent Changes](https://www.cos.io/initiatives/prereg).
- [GDPevo pinned layout](https://github.com/Prism-Shadow/GDPevo/tree/5082a777379156a048881e94940d640702e5e09a): `codex/guides/skill_modes.md:119–121`,
  `codex/guides/metric_and_scoring.md:115–139`.
- [Kernel `pilot._code_hash`](../src/rsi_kernel/adapters/gdpevo/pilot.py): the
  full-code hash semantics this addendum reuses for both identities.
- TypeSafe Choice and State primitives, whose add/discard choice and
  champion-level state D4 mirrors: https://docs.typesafe.ai/primitives/choice,
  https://docs.typesafe.ai/concepts/state
- Lane probe record, 2026-11-06 (the §9.1 table; 12 live calls, direct backend).
