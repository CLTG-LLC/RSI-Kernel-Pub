# S4 addendum — trim the pilot final phase to the GDPevo comparison (issue #36)

Applies to `docs/prereg-gdpevo-pilot.md` (frozen by issue #4). The pre-registration
itself is unchanged. This addendum records a **pre-measurement** change to the final
phase under COS "Transparent Changes": a change made before the affected data
exists is disclosed here rather than silently edited into the frozen text.
<https://www.cos.io/initiatives/prereg> (Transparent Changes).

## Timing and data exposure

**No final-phase data existed when this change was made.** The final phase
(adjudication and holdout) had never run: no `final/<group>/observations.jsonl`,
no adjudication or holdout row, and no acceptance decision existed for any group.
No adjudication or holdout task had been solved, so this change cannot be tuned to
the data it later measures.

Disclosed exposure at the time of the change: every dev task of groups 001–003 had
been solved during the optimise phase (its intended use), and train 001 of groups
001–003 had also been solved in pre-run smoke tests (group 001 in the eight recorded
feasibility attempts; groups 002 and 003 once or twice each with the seed skill).
The change was decided **after** the dev outcomes were known, including that group
002 selected no candidate. It only removes arms and tasks that do not enter the
accept decision; it does not change what is compared or how acceptance is decided.

The optimise phase and the accept/approval rules are untouched: this addendum
changes what the final phase runs, not how the outcome is decided.

## What changed, and why

The pre-registration's schedule was group → attempt → task id → champion, candidate,
**control**, over every frozen task of the group, with the control arm contributing
a full independent re-run (`docs/prereg-gdpevo-pilot.md`, "Metric and repetitions",
"Uncertainty and unchanged control"). GDPevo's own protocol compares conditions on
test tasks with three attempts (`evaluation/eval_workspace/codex/guides/metric_and_scoring.md`
at `5082a777…`, acc@3). Two parts of the previous final phase go beyond that
comparison and add no decision value:

1. **The dev re-run.** The optimisation campaign already holds the same dev
   results for the champion and for the selected candidate; re-running them in a
   separate process produces no new information. The report now reads dev from the
   optimise archive instead.
2. **The control arm.** It is not part of the upstream comparison, it is
   diagnostic only, and its purpose — estimating run-to-run noise — is served by
   the champion's three dev runs per task, which the campaign already records.
   Noise is reported as that spread (the same statistic as upstream `std@3`:
   population standard deviation over three attempts,
   `metric_and_scoring.md:115–139`).

The remaining comparison is exactly the one the pre-registration's retention rule
uses: champion versus candidate on adjudication and holdout, three independent
runs per task, in the same equal-task and equal-group aggregation.

### Solve counts

| | Tasks per group | Runs | Arms | Solves per group | Total (3 groups, each with a candidate) |
|---|---|---|---|---|---|
| Before | 10 (dev + adjudication + holdout) | 3 | 3 (champion, candidate, control) | 90 | 270 |
| After | 7 (adjudication + holdout) | 3 | 2 (champion, candidate) | 42 | 126 |

Dropped per group: the dev re-run in all three arms (3 tasks × 3 runs × 3 arms = 27
of the 90) and the control arm on adjudication and holdout (7 × 3 = 21). The exact
expectation is now per group with a selected candidate: 7 tasks × 3 runs × 2 arms =
42. A group with no selected candidate runs no final solves; in this pilot group 002
selected none, so the final phase runs 2 × 42 = 84 solves.

## The per-group process

The launcher runs groups in parallel (host cap 4), so each group is now its own
process and needs only its own campaign closed:

- `final --group G` runs one group. Observations go to
  `run_dir/final/<group>/observations.jsonl`, and the "already ran" STOP is per
  group: a second run of the same group stops before any solve; other groups are
  unaffected. The holdout is still reported exactly once per campaign.
- Order within a group is run → task id → arm, the pre-registration's schedule
  with the dropped parts removed. Task ids are the group's adjudication and
  holdout items in ascending order.
- A group whose campaign selected no candidate gets no solves and
  `acceptance.json` = `no_improvement`; `accept()` already returns that for an
  unchanged champion.
- `run_dir/entropy.json` is created exactly once (`open(..., "x")`, ignored if it
  already exists), so parallel groups never race to record it and the estimator
  keeps one recorded entropy value.

## Rebind: a recorded identity change

The pre-registration makes identity drift a STOP before any solver call, which is
right, but it left no way to record a reviewed, pre-measurement change. `rebind
--group G --addendum PATH` writes `run_dir/<group>/rebind.json` with:

- `from`: the campaign's frozen `champion_id`, `evaluator_hash` and `code_hash`
  (equal to `campaign.json` by construction, so a wrong `from` cannot pass);
- `to`: the current identity;
- `champion_id`: the champion the final will use (must be unchanged);
- `addendum`: the addendum path, and `addendum_sha256`: its hash.

The final phase accepts the current identity only if it equals `to`, `from` equals
`campaign.json`, the addendum still hashes to the recorded value, and the champion
is unchanged. Anything else is a STOP before any solve. Without `rebind.json`, the
behaviour is unchanged: drift still stops the phase. A second rebind for the same
group is refused, so one recorded change stays one recorded change.

## Reporting

`report()` now has three tables — dev (champion and selected-candidate rows read
from the optimise archive), adjudication and holdout (from the final phase), each
champion versus candidate — and reports the champion's run-to-run spread on dev as
the noise estimate. The control table is gone with the control arm. Aggregation,
the paired group bootstrap and the retention rule are the same code as before
(`rsi_kernel/analysis.py`), so the estimator and its recorded entropy are
unchanged.

## What this does not change

- The optimise phase, its caps, and the selection rule.
- The accept/approval rules: zero margin per group, approval bound to candidate,
  evaluator and data hashes, `apply()` record-only.
- The metric, the evaluator, the task manifests, the calibration replay and every
  pre-run STOP.
- The `acc@3` aggregation (mean of three attempts, not pass@3) and its disclosure
  that one frozen candidate is reused across repetitions.

## Sources

- GDPevo `evaluation/eval_workspace/codex/guides/metric_and_scoring.md` at
  `5082a777379156a048881e94940d640702e5e09a` (acc@3 and std@3 on test tasks,
  lines 115–139).
- [COS pre-registration — Transparent Changes](https://www.cos.io/initiatives/prereg).
- `docs/prereg-gdpevo-pilot.md` (frozen pre-registration, issue #4); issue #27
  (pilot driver); issue #36 (this change).
