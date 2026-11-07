# Per-campaign historical results (M0)

Issue #112. One row per campaign, copied from the merged reports in this directory. No value here is newly computed; anything a report does not give is marked "not reported". This is a historical record, not an efficacy result and not a forecast.

## Do not pool these rows

The rows measure different estimands and must not be combined into one cross-campaign "RSI effect":

- **Root versus continuation.** S4, S5b and E1c start from a root artifact, so their differences are root gains over a seed. S4b and S5c start from an approved champion, so their differences are incremental continuation gains over that champion.
- **Different tiers.** Skill (S4, S4b), memory library (S5b, S5c) and harness code (E1c) are different artifacts; the real-host H1 line is a configuration artifact with a different metric.
- **Reused task identities.** Every GDPevo campaign reuses the same task identities (2 adjudication + 5 holdout tasks per group) in `task_group_001` and `task_group_003`, so later reads are not independent of earlier ones.

The E1c report states the prohibition directly: "T3 rows remain separate campaign records, not pooled with S4, S4b or S5b and not an efficacy comparison", and lists "No T3-versus-S4, T3-versus-S4b or T3-versus-S5b score comparison or pooling" under "Not covered" (`e1c-harness-code.md`, "Diagnostic only" and "Not covered"). Every pooled estimate in the table below is a within-campaign pooled row as its own report gives it, never a pool across campaigns.

## Summary

S4, S5b and E1c retained updates with positive adjudication differences in at least one group. E1c is the only retention among the campaigns sharing kernel-only hash `8ea2ae0a…`; S4b and S5c, on the same kernel bytes, ended `failed_gate`. There is no second retained update so far: both continuation campaigns (S4b, S5c) kept the champion. E1d (harness-code continuation) is running; its result is **pending** and is not in this table. The samples are small (at most three groups, two or fewer paired) and adaptive: every adjudication and holdout screen had already been read before most of these campaigns. Historical groups 001/003 remain separate from E2's fresh primary analysis. A larger preregistered experiment narrows uncertainty for one tier and group population and gives no universal yes/no.

## Table

"Groups" counts are attempted / with a selected candidate / retained (`updated`). Adjudication decides retention; holdout is report-only. Estimates are candidate minus champion. "g001", "g002", "g003" are `task_group_001`–`003`.

| Campaign | Tier | Generation | Kernel-only hash | Groups (attempted / selected / retained) | Adjudication estimate and interval | Holdout estimate and interval | Retention outcome per group | Adjudication / holdout exposure | Report |
|---|---|---|---|---|---|---|---|---|---|
| S4 | skill (`SKILL.md`) | root (frozen seed skill) | `e8d7b2b5…c4d209` | 3 / 2 / 2 | pooled +0.106335, CI [0.058824, 0.153846] (two clusters; "not an uncertainty claim"); group means g001 0.615385 → 0.769231, g003 0.848039 → 0.906863; per-group difference not reported | pooled +0.161558, CI [0.077602, 0.245513]; group means g001 0.495883 → 0.741396, g003 0.597326 → 0.674929 | g001 `updated`; g002 `no_improvement` (no candidate); g003 `updated` | adjudication 12 / 0 / 12 solves, holdout 30 / 0 / 30 (g001 / g002 / g003); first read of each split | [gdpevo-pilot.md](gdpevo-pilot.md) |
| S5b | memory library | root (empty seed library) | `2781ad32…99f3e8` | 3 / 1 / 1 (g003 operational STOP) | g001 single-group difference +0.202992 (0.615385 → 0.818376); pooled and interval `unavailable` (one paired group) | g001 single-group difference +0.160531 (0.448264 → 0.608795); pooled and interval `unavailable` | g001 `updated`; g002 `no_improvement`; g003 operational STOP (not a negative result) | g001 adjudication 12, holdout 30 solves (second read of each, after S4); g002, g003 0; plus one disclosed holdout grader-output disclosure (not a solve) | [e1a-s5b-evaluate-first.md](e1a-s5b-evaluate-first.md) |
| S4b | skill (`SKILL.md`) | continuation from the approved S4 champions | `8ea2ae0a…e1a2bc` | 2 / 2 / 0 (g002 excluded: no approved champion) | pooled −0.027778, CI [−0.027778, −0.027778], not degenerate; g001 −0.027778, g003 −0.027778 | pooled +0.016604, CI [0.000000, 0.033209]; g001 0.000000, g003 +0.033209 | g001 `failed_gate`; g003 `failed_gate`; terminal outcome "no second retained update" for both | adjudication 12 / 12, holdout 30 / 30 solves (g001 / g003); third read for g001, second for g003 | [s4b-continuation.md](s4b-continuation.md) |
| E1c | harness code (`solver.py`) | root (identity-passthrough seed solver) | `8ea2ae0a…e1a2bc` | 3 / 2 / 2 | pooled +0.036765, BCa CI [0.0, 0.073529]; g001 0.000000 (TIE, retained under the zero-margin rule), g003 +0.073529 | pooled +0.010409, BCa CI [−0.000611, +0.021429]; g001 +0.021429 (0.448264 → 0.469693), g003 −0.000611 (0.572116 → 0.571505) | g001 `updated` (tie, not an improvement); g002 `no_improvement`; g003 `updated` | adjudication 12 / 0 / 12, holdout 30 / 0 / 30 solves (g001 / g002 / g003); read number not reported in this report; cumulative before S5c, per the S5c reconciliation: g001 48 / 120, g003 36 / 90 | [e1c-harness-code.md](e1c-harness-code.md) |
| S5c | memory library | continuation from the approved S5b library | `8ea2ae0a…e1a2bc` | 1 / 1 / 0 (g002, g003 excluded) | g001 −0.051282 (0.846154 → 0.794872); pooled and interval `unavailable` | g001 −0.038095 (0.705132 → 0.667037); pooled and interval `unavailable` | g001 `failed_gate`; terminal outcome "no second retained update" | g001 adjudication 12, holdout 30 solves; fifth read of each; g001 after S5c: adjudication 60, holdout 150 | [s5c-memory-continuation.md](s5c-memory-continuation.md) |
| H1a (real host, separate line) | configuration artifact (host rule pack) | root (built-in rule-pack copy) | not reported in this formula; kernel sources aggregate `897fd9fe…` | 1 / 0 / 0 | not evaluated (proposal ineligible, 422 `guard_failed` before scoring) | not evaluated (no holdout split) | `no_improvement` | adjudication 0, holdout 0 | [h1a-rule-pack.md](h1a-rule-pack.md) |
| H1b (real host, separate line) | configuration artifact (host rule pack) | root (built-in rule-pack copy) | not reported in this formula; kernel sources aggregate `897fd9fe…` | 1 / 0 / 0 | not evaluated (proposal ineligible, 422 `guard_failed` before scoring) | not evaluated (no holdout split) | `no_improvement` | adjudication 0, holdout 0 | [h1b-rule-pack.md](h1b-rule-pack.md) |
| H1c (real host, separate line) | configuration artifact (tenant rule list) | root (empty tenant list) | not reported in this formula; kernel sources aggregate `897fd9fe…` | run 1: 1 / 0 / 0; run 2: 1 / 1 / 1 | run 1: adjudication not evaluated; run 2: exact tie, 0.3915 → 0.3915, 0 flips; no interval reported | not evaluated (no holdout split) | run 1 `no_improvement`; run 2 `updated` (retained tie, zero measured improvement) | +2 adjudication reads (470 item exposures), holdout 0 | [h1c-tenant-rules.md](h1c-tenant-rules.md) |

Notes on the table:

- S5 (`e1a-two-artifact.md`) is not a row: no group selected a candidate for final-split evaluation (`no_improvement` ×3) and it ran no adjudication or holdout solves; its 27 dev solves appear in the later exposure logs.
- Kernel-only hashes are `_code_hash(exclude=("adapters",))` as each report records it. The cross-tier kernel identity for S4b, E1c and S5c is reported in `plug-and-play-exit.md` §3, which also states that "close" means a terminal outcome, not a retained update.
- Exposure counts are graded solves added by that campaign unless marked cumulative. No independence is claimed for any screen in any report.

## Sources

`gdpevo-pilot.md`, `e1a-s5b-evaluate-first.md`, `e1a-two-artifact.md`, `s4b-continuation.md`, `e1c-harness-code.md`, `s5c-memory-continuation.md`, `h1a-rule-pack.md`, `h1b-rule-pack.md`, `h1c-tenant-rules.md`, `plug-and-play-exit.md`, all in `docs/results/`.
