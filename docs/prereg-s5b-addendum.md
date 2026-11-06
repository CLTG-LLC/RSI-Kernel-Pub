# S5b prereg addendum — evaluate drafts before admission (issue #45)

Amendment to `docs/prereg-gdpevo-pilot.md` for a re-run of the S5 memory-library
experiment. The frozen pre-registration is untouched; this file records the change
under the COS "Transparent Changes" rule for preregistration amendments
(https://www.cos.io/initiatives/prereg). Forward-only: it governs this re-run only.

Scope convention: only what changes is stated here. Everything else — groups,
carving map, schedule, arms, metric, retention rule, estimator, isolation, the S5
artifact and the trimmed final phase — is `docs/prereg-s5-addendum.md` (S5),
adopted by reference, which in turn adopts `docs/prereg-s4-addendum.md` for the
final phase.

## 1. Why

The S5 run evaluated **no entry at all**. Every attempt closed `no_candidate`
because D4 admission was asked to judge a draft from champion-only state: the D4
envelope carries `c1.dev_pass_count` and `c1.dev_fail_count` and nothing about the
proposed entry (`docs/prereg-s5-addendum.md` §9.4). A `discard` returns no
candidate and `loop.py` skips evaluation, so no draft was ever measured; S5
reported "no improvement demonstrated; efficacy comparison unavailable" with zero
paired rows (issue #6; S5 report `docs/results/e1a-two-artifact.md`, PR #44).

The S5 addendum deferred the remedy to a later slice (§9.4). That slice is issue
#45: retire the D4 pre-evaluation veto and let the existing paired dev evaluation
decide. The precedent — evaluate before retention in Voyager
(arXiv 2305.16291 §2.3), Recursa §5.1 (arXiv 2611.04035) and GEPA's
evaluate-then-accept rule (arXiv 2507.19457), and no examined system rejecting a
new entry on champion-only counts — is recorded in the D4 entry-admission research
note kept outside the published tree, with pinned source locations.

Timing: this change is made **before** any S5b solve exists. No S5b run directory,
observation or acceptance record has been produced, so it cannot be tuned to the
data it will measure. It does not alter how acceptance is decided.

## 2. What changes

### 2.1 The D4 call is removed from PROPOSE

A valid, non-duplicate draft now becomes the candidate library through the
existing validated `add` path, and the existing paired dev evaluation plus the
zero-margin selection rule decide. No D4 call is made on this path, so no Jev
answer can veto a draft before it is measured.

Unchanged on this path: draft validation (exactly the four brief fields), exact
dedupe, immutable candidate construction, D2, the content-free constraint that
no entry text reaches any Jev envelope (adapter canary test), and promotion only
through adjudication plus hash-bound approval.

### 2.2 Spend

| Item per group campaign | S5 | S5b |
|---|---|---|
| solver | 36 | up to 36 (9 champion dev + 3 × 9 candidate dev) |
| proposer (drafting) | 3 | 3 |
| D2 | 3 | 3 |
| D4 | 3 | 0 — call removed |
| **cap** | **45** | **45, unchanged** |

The cap of **45 stays**. The three former D4 slots are unused headroom, **not** a
lower cap, and must not be lowered: the registered cap is what bounds a campaign,
and the worst case here already exactly fills the 36-solver `eval_cap` (issue #45
acceptance test 5). Failed calls stay metered; the campaign still halts at the
first check past the cap.

### 2.3 Unchanged

Groups `task_group_001`–`003`, the dev / adjudication / holdout carve, 3 runs per
task, and the empty seed library `pilot-config/s5-seed-library.json`, sha256
`9399b563…`. The zero-margin retention rule (champion vs candidate mean paired
delta, ties eligible). The trimmed S4 final shape
(`docs/prereg-s4-addendum.md`): adjudication + holdout × 3 runs ×
champion/candidate = **42 solves per group with a candidate**; no dev re-run; no
control arm. Hash-bound owner approval, which now also binds **`code_hash`** in the
approval record (issue #42, PR #43) — previously a separate identity check only.
Every pre-run STOP, the calibration replay, the isolation boundary and the named
local exceptions carried by the frozen prereg and the S5 addendum.

## 3. Run identity

- New run directory: **`pilot-003`**. `pilot-002` is the frozen S5 run record and
  is not reused or edited.
- Code pinned to the first `main` commit that contains both #45 and this
  addendum. The run tree is a clean detached checkout of that commit; its SHA is
  recorded in the run's code-identity log before the first solve and reported
  with the results.
- Two hashes recorded, one formula (`pilot._code_hash`, S5 addendum §8):
  **full code hash** and **kernel-only hash** (`exclude=("adapters",)`), both
  recomputed on the run tree.
- The **kernel-only hash is expected to change**. #43 (merged as `fc838e5`)
  modified `src/rsi_kernel/loop.py` to carry `code_hash` into `ApprovalRequest` /
  `ApprovalRecord` and `accept()`, so the kernel path set is no longer
  byte-identical to S4's `e8d7b2b5…`. That is a recorded, expected difference:
  this run does **not** claim an unchanged kernel. The S5 addendum §8 "empty
  kernel diff" premise applies to S5 (`pilot-002`), not here; further kernel drift
  during the run is still a STOP.

## 4. Exposure

Every GDPevo screen used here is already **adaptive**; no split is fresh.

| Prior use | Scope | Source |
|---|---|---|
| S4 optimise | dev of all three groups, champion and each candidate | S5 addendum §6 |
| S4 final | adjudication + holdout for groups 001 and 003 (42 / 0 / 42 solves, 0 failures); group 002 read neither | S4 report, exposure log |
| S5 | 27 dev solves (9 per group) + 1 pre-run smoke solve; zero adjudication, zero holdout | `docs/results/e1a-two-artifact.md`, "Exposure log → S5 exposure added by this run" |

S5b adds, on the same already-exposed screens, at most 9 champion dev solves plus
9 candidate dev solves per attempt per group (≤ 36 solver attempts per group), and
— only if a group selects a candidate — the 42 final solves.

**No independence claim is made for any screen, and this run must not be presented
as a fresh-split confirmation.** Its artifacts start from the empty seed library,
so they did not learn from earlier rows; the limit comes from prior use of the
screens themselves.

## 5. What is reported

The S5 addendum §7 checklist, minus the D4-vs-baseline item (no D4 call exists to
compare), plus two per-attempt additions:

- [ ] dev rows read from the optimise archive; paired adjudication and holdout
      results per group, champion vs candidate;
- [ ] paired tables only for groups with a candidate; `"unavailable"` below two
      such groups;
- [ ] cost per call type against the 45 cap, with the D4 column reading 0;
- [ ] both identity hashes from §3, recomputed on the run tree;
- [ ] the S5 addendum §2 limitation (add/discard only, no merge/revise, no
      cumulative-growth claim) stated as a limitation, not a result;
- [ ] the §4 exposure disclosure;
- [ ] adapter diff against the kernel, reported descriptively (files and lines, no
      "thin" threshold);
- [ ] per-attempt **`candidate evaluated: yes / no`**, with the reason when `no`
      (invalid brief, duplicate, hash mismatch, cap reached);
- [ ] per-attempt **paired dev delta** (candidate − champion, mean over dev) and
      the selection outcome.

## 6. Expected outcomes

Stated neutrally, with no prediction of numbers:

- Any group, including all three, may still select **no candidate**. The rule is
  unchanged: a non-negative mean paired dev delta is required, so a negative delta
  on every attempt ends the campaign with `no_improvement` and no final solves.
- A group that selects a candidate runs the 42 final solves and reports paired
  adjudication and holdout rows; acceptance remains the owner's, bound to the
  candidate, evaluator, data and code hashes.
- A partial result — one or two groups with a candidate — is a normal outcome, not
  a failure. Report the pooled comparison when at least two groups have a
  candidate; otherwise report `"unavailable"`.

## Sources

- Local: `docs/prereg-gdpevo-pilot.md` (frozen); `docs/prereg-s5-addendum.md` §1,
  §2, §2a, §4, §6, §7, §8, §9.4; `docs/prereg-s4-addendum.md` (trimmed final
  phase); `docs/design.md` §7 item 5.
- Issues #45 (this change), #42 / PR #43 (code hash bound in approval), #6 / PR #44
  (S5 and its report).
- [COS preregistration — Transparent Changes](https://www.cos.io/initiatives/prereg).
- Voyager, arXiv 2305.16291 §2.3: insert a skill only after the program passes
  verification.
- Recursa, arXiv 2611.04035 §5.1: "keep an edit only if it fixes failures without
  causing regressions."
- GEPA, arXiv 2507.19457: evaluate the child, then apply the acceptance rule; the
  documented alternative criterion permits ties, which is our existing zero-margin
  rule.
- The D4 entry-admission research note (per-system precedent table over Voyager,
  Mem0, ExpeL, A-MEM, Letta, Recursa and GEPA; kept outside the published tree,
  pinned to the sources above).
