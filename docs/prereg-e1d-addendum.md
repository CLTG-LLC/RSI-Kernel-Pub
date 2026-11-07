# E1d prereg addendum — a second harness-code (T3) campaign from the approved E1c champions (issue #98)

Amendment to `docs/prereg-gdpevo-pilot.md` for a second T3 campaign. The frozen
pre-registration is untouched; this file records the change under the COS
"Transparent Changes" rule for preregistration amendments
(https://www.cos.io/initiatives/prereg). Forward-only: it governs this campaign only.

Scope convention: only what changes is stated here. Everything else is adopted by
reference: `docs/prereg-gdpevo-pilot.md` (frozen: carve, schedule, arms, metric,
retention rule, estimator, isolation), `docs/prereg-s4-addendum.md` (trimmed final
phase), and the T3 contract as run in E1c — `docs/prereg-e1c-harness-code-addendum.md`
with `docs/prereg-e1c-amendment-1.md` and `docs/prereg-e1c-amendment-2.md`: the
frozen `CodeLimits` values and rule (`T3-RESOURCE-VALUES`), candidate-only resource
scope with `CodeLimits.agent_argv()` for the trusted agent, the fixed trusted skill,
calibration replay through base staging, the live-smoke assertions and the failure
semantics (E1c §7).

## 1. Why

This tests **continuation on the harness-code tier**: a T3 campaign whose champion
is an approved E1c `solver.py`, rather than the identity-passthrough seed. E1c ended
with approved candidates for `task_group_001` and `task_group_003`; the E1c addendum
does not authorize a campaign from them. This addendum records that change before
any E1d solve exists, following the `docs/prereg-s4b-addendum.md` and
`docs/prereg-s5c-addendum.md` continuation pattern. No kernel change is made.

Precedent for approved inter-campaign continuation: RRSI
([arXiv 2609.24972v3, Appendix D.1](https://arxiv.org/html/2609.24972v3)) iterates
from earlier harness changes; Recursa §5.1
([arXiv 2611.04035](https://arxiv.org/abs/2611.04035)) applies iterative updates to a
retained artifact. Neither precedent authorizes bypassing owner approval or
within-campaign incumbent updates.

Timing: written before any E1d campaign, observation or acceptance record exists. It
does not change how acceptance is decided.

## 2. What changes

### 2.1 The champion is the approved E1c candidate

| Group | Champion for E1d (`selected.id` = approved `candidate_hash`) | E1c parent (seed) |
|---|---|---|
| `task_group_001` | `d65e220b04815704a16935231cb50ef71778254f368d0855a577d43f2516b60a` | `b95e33ea6f9d2cc0450488afbb4fce1cd3fe65a131b781db5e4ed2ddcb41e374` |
| `task_group_002` | **excluded** — E1c selected no approved candidate | none |
| `task_group_003` | `7ca6c7160aa9b218c2776952e88aec5a84229eb71e086248071d48df7c1bc9bd` | `b95e33ea6f9d2cc0450488afbb4fce1cd3fe65a131b781db5e4ed2ddcb41e374` |

Both outcomes are `updated` in `pilot-005/task_group_00{1,3}/acceptance.json`; the
matching hash-bound owner approvals are `pilot-005/task_group_00{1,3}/approval.json`
(candidate, code, data and evaluator hashes equal to the approval requests;
apply record-only). Group 002 has no approved champion and is not restarted from
the seed: at most two groups can have a candidate.

Champion file: for each group, the UTF-8 bytes of
`pilot-005/task_group_<g>/campaign.json` `selected.components["solver.py"]`,
written verbatim (no added or removed newline). Its file sha256 goes in the run
config `champions[<g>]` `{path, sha256}`. It is loaded through the existing
hash-checked T3 loader `gdpevo_code.pilot.load_champion`
(`src/rsi_kernel/adapters/gdpevo_code/pilot.py:42–51`): symlink refusal, file-hash
check, then `Candidate({"solver.py": bytes}, "text/plain")` validated by
`validate_code` (`src/rsi_kernel/adapters/gdpevo_code/adapter.py:9–25`). No new
loader, format or validation is introduced; the same `champions` config key E1c
used for the seed is reused. No file hash is predicted here.

Before the first solve, record that the loaded champion's content id equals the
approved `candidate_hash` above; a mismatch is a STOP. The loader constructs the
champion as a root `Candidate` (no `parent_ids`), which `validate_code` requires;
the E1c parent link is retained in the E1c records, not in the loaded object.

Lineage is recorded, not asserted: the campaign's frozen `champion_id` is the
approved E1c id, and every admitted E1d candidate carries exactly that id in
`parent_ids` (`gdpevo_code.pilot.admit`, `pilot.py:31–39`, and the parent check in
`validate_code`). The records therefore retain seed → approved E1c `solver.py` →
E1d candidate. The kernel still passes the same campaign champion to every
proposal; this is inter-campaign continuation, not within-campaign incumbent
updates.

### 2.2 Caps and rules stay as frozen

Unchanged: the dev / adjudication / holdout carve, 3 runs per task, `max_attempts` 3,
`eval_cap` 36, the **42-call spend cap per group** (`gdpevo.pilot.SPEND_CAP`:
36 solver + 3 proposer + 3 D2; logical calls, proposer retries logged and not
metered again), the zero-margin rule (non-negative mean paired dev delta is
eligible, **ties pass**, retention on **adjudication only**), the trimmed final
phase of **42 solves per group with a candidate**, holdout **reported, not gated**
(invalid or incomplete evidence still blocks), hash-bound owner approval **per
request** (no standing approval), and record-only `apply(hash)`. The frozen
`CodeLimits` values, fixed trusted skill identity and timeout are carried
unchanged. No new threshold, significance test or per-item gate is added.

## 3. Run identity

- New run directory: **`pilot-007`**. `pilot-001`–`pilot-006` are separate records,
  not reused or edited.
- Code pinned to the **first `main` commit that contains this addendum**, in a clean
  detached run tree. Its git SHA, the full code hash (`_code_hash()`) and the
  kernel-only hash (`_code_hash(exclude=("adapters",))`) go in the code-identity log
  before the first solve, including the smoke. The kernel-only hash must equal
  `8ea2ae0a9f644815adb79dab1c883efa17e03396df6785c8b4e930f346e1a2bc`, the value
  recorded for E1c, S4b and S5c, so the unchanged-kernel criterion holds; a
  different value is a STOP. Identity drift during the run is a STOP.
- Pre-run STOPs, in this order:
  (a) identity and champion reconstruction per §2.1, with the E1c approval and
  acceptance records;
  (b) the E1c frozen pre-run STOPs (manifests, calibration replay) and a **fresh live
  T3 smoke** at the pin, `tests/adapters/test_gdpevo_code_live.py` with every E1c §4
  assertion unchanged, `RSI_LIVE_GDPEVO=1`, outside CI — it must show exactly
  **`1 passed`**; a skip or failure is a STOP, not a retune or rescue rerun;
  the smoke executes the frozen seed solver (`tests/fixtures/t3_seed_solver.py`), not
  the E1c champion, so it verifies the T3 infrastructure only; the champion is first
  executed by the campaign's own champion dev evaluation;
  (c) the actual exposure reconciliation of §4;
  then (d) the first campaign solve.

## 4. Exposure

Every screen is already **adaptive**; no split is fresh. Before the first campaign
solve, record actual counts per split and per group — groups 001, 002 and 003 —
with separate campaign, final and smoke contributions, from the terminal records of
S4, S5, S5b, S4b, E1c and S5c and every smoke (including all E1c smokes and this
fresh one): `docs/results/gdpevo-pilot.md`, `docs/results/e1a-two-artifact.md`,
`docs/results/e1a-s5b-evaluate-first.md`, `docs/results/s4b-continuation.md` and
the `pilot-004`–`pilot-006` records. Missing records are a STOP, not an assumed
zero. Operational failures and ungraded attempts are counted; model-request retries
are recorded separately; calibration replays are not solves.

What E1d may add, under the unchanged caps: ≤ 36 solver attempts per group, the
42 final solves per group that selects a candidate, and the smoke. These are
registered bounds, not predicted exposure. Whatever E1d reads is further reuse:
**no independence, replication or compounding claim is made.**

## 5. What is reported

**Status: "continuation tested" or "not tested"** (harness-code). Factual, not an
outcome: tested means the campaign started from the verified approved E1c champion
— champion id, file sha256, reconstructed id, prior approval and lineage recorded
per §2.1 — whether or not a candidate is selected. An operational STOP before that
is reported as a STOP with its reason.

**Per group, separately: "retained second update"** (`accept()` outcome `updated`
in `<group>/acceptance.json`) **or "no second retained update"** (any other
completed outcome, with the record's reason). An operational STOP is reported as a
STOP, never as a negative outcome. Groups are reported per group, never pooled
below the existing two-group rule.

Also reported: the E1c §8 list (admitted yes/no per attempt with reason, paired dev
delta and selection, resource events with classification evidence and unclassified
failures separately, measurement-rule identity, both code identities, exposure,
descriptive adapter diff, candidate-only resource-scope disclosure), plus the
lineage fields (`champion_id`, champion file sha256, each candidate's
`parent_ids`) and the ratchet status above. **No cumulative-improvement or
compounding claim** is made from a second retained update.

## 6. Ordering

Docker solves on the same group are serialized: **S5c → E1d**. E1d starts only after
S5c's terminal record, including its final phase if any; an S5c operational STOP is
not treated as completion. Within E1d, groups start `001 → 003` under the existing
four-job cap; no new reserve or concurrency limit is added.

## 7. Sources

- `docs/prereg-gdpevo-pilot.md` (frozen); `docs/prereg-s4-addendum.md`;
  `docs/prereg-e1c-harness-code-addendum.md` §2–9; `docs/prereg-e1c-amendment-1.md`;
  `docs/prereg-e1c-amendment-2.md`.
- `docs/prereg-s4b-addendum.md` and `docs/prereg-s5c-addendum.md`: the
  approved-artifact continuation pattern, lineage checks, exposure STOP and
  separate status/outcome reporting.
- `src/rsi_kernel/adapters/gdpevo_code/pilot.py:31–51` (`admit`, `load_champion`);
  `src/rsi_kernel/adapters/gdpevo_code/adapter.py:9–25` (`validate_code`);
  `src/rsi_kernel/adapters/gdpevo/pilot.py` (`SPEND_CAP`, `_code_hash`).
- `pilot-005/task_group_00{1,3}/{campaign,approval,acceptance}.json`: approved
  E1c champions.
- [COS preregistration — Transparent Changes](https://www.cos.io/initiatives/prereg).
- [RRSI, arXiv 2609.24972v3, Appendix D.1](https://arxiv.org/html/2609.24972v3).
- [Recursa, arXiv 2611.04035](https://arxiv.org/abs/2611.04035) §5.1.

Publication check: `uv run pytest -q tests/test_publication_markers.py`.
