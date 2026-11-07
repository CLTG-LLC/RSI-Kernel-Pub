# E2 amendment 1: per-group health route and a lead exposure disclosure (pre-run, forward-only)

Recorded 2026-11-08, after pre-run STOP 3 fired and **before any E2 solve, smoke,
campaign or final phase exists**. This follows COS **Transparent Changes**
(https://www.cos.io/initiatives/prereg) and the in-repo amendment precedent
(`docs/prereg-e1c-amendment-1.md`, `docs/prereg-e1d-amendment-1.md`). The original
`docs/prereg-e2-skill-groups.md` (**E2 prereg**) remains the frozen historical record.

## 1. What happened

- Pre-run STOPs 1 and 2 passed: the driver is pinned, and groups 004–009 were restored
  at the upstream pin with hash manifests recorded.
- **STOP 3 fired on `task_group_004`**: `environment_unhealthy`. The run stopped there,
  and groups 005–009 were not health-checked. No group was dropped.
- **Cause: an adapter assumption, not the group.** The Docker solver hard-coded the
  health route `/health`. Each upstream group declares its own route in its staged,
  hash-bound `env/endpoints.txt`. Groups 001–003, 006, 007 and 009 list `GET /health`.
  Groups 004 and 008 list only `GET /api/health`. Group 005 lists both. The upstream
  environment guide documents the health endpoint per environment and treats it as
  orchestration-only (`data_construction/Stage_2_Task_Group_Synthesis/task_factory/guides/environment_and_data.md`,
  lines 28–29 and 157).

This is an operational STOP. It is not a quality result.

## 2. What changes

1. **Health route.** E2 prereg §3 STOP 3 says "`/health` ok". That phrase is superseded
   by: "the group's declared health route ok". The route is `/health` when
   `env/endpoints.txt` lists `GET /health`, else `/api/health` when it lists
   `GET /api/health`; any other case is a STOP. The adapter change (issue #123) also
   omits both health routes from the solver-visible access note, because upstream
   treats health as orchestration-only. For groups that list only `/health`, the note
   is byte-identical to before.
2. **Code pin.** E2 prereg §3 pins "the first `main` commit that contains both this
   addendum and the merged issue #113 support". That pin is superseded by **the first
   `main` commit that contains this amendment and the merged issue #123 change**. That
   commit sits in a clean detached run tree, and the same identity log and drift STOP
   apply. The kernel-only hash is expected to be unchanged from the superseded pin,
   because only adapter files change; the identity log records the observed value.
3. **STOPs re-run in full.** Pre-run STOPs 1–6 run again in order at the new pin. That
   includes the restoration manifests and a health receipt for every group, 004–009.
   Receipts from the stopped attempt are kept as evidence and are not reused.
4. **Endpoint-file read.** For subsequent E2 pre-run checks, E2 prereg §3 STOP 2's phrase
   "the only field the driver reads before the campaign is `env.state_mode`" is superseded
   by "before the campaign, the driver reads `env.state_mode` and the health-route
   declarations in `env/endpoints.txt`". The prohibition on reading task, rubric, answer or
   evaluator text is unchanged.

## 3. Lead exposure disclosure

E2 prereg §3 STOP 2 says no task, rubric, answer or evaluator text is read by the lead.
While diagnosing STOP 3, a lead search over the group 004 tree used exclusions that
missed the evaluator scripts. It printed fragments of three group 004 evaluator
scripts, at most three lines in all: an account identifier with numeric fields. The
three scripts cover tasks `train/001`, `train/003` (dev) and `test/003` (holdout).
This is disclosed and kept, not repaired:

- The lead authors no candidate. E2 champions, configuration and caps were frozen before
  the incident. Candidates come from the frozen proposer and solver path.
- Group 004 stays in E2. For subsequent execution and reporting, E2 prereg §5's statement
  "Groups 004–009 have **zero prior exposure** in this project" is superseded by "Groups
  004–009 have zero prior solve exposure; group 004 additionally has the lead
  evaluator-text exposure disclosed here". Section 5's phrase "does not affect E2's fresh
  status" does not apply to this incident. This does not retroactively satisfy STOP 2's
  no-read requirement, which stays binding from now on. The exposure reconciliation and
  the report record the incident separately from solve counts, without claiming that
  group 004 is wholly unexposed.
- Retention follows the COS guidance on prior data access: disclose the access and explain
  why inference remains defensible, rather than exclude automatically. Here the candidates,
  configuration and selection rule were frozen before the incident.
- From now on, the lead inspects a group only through `env/endpoints.txt`, never through
  a recursive search of the group tree.

## 4. What does not change

Everything else in E2 prereg is unchanged: groups, champions, splits, caps, waves, the
run directory `pilot-008`, the estimator and its counting rules, zero-margin retention
on adjudication (ties pass), holdout reported and not gated, hash-bound approval under
the owner's standing grant, record-only apply, and round 2. No threshold, gate,
measurement or analysis rule changes.

## 5. Why this is not outcome-driven

No E2 solve output or score exists when this is recorded. The change corrects health
checking and removes orchestration-only routes from solver-visible notes. Candidate
format, scoring rules and analysis remain unchanged.

Publication check for this documentation change:

```sh
uv run pytest -q tests/test_publication_markers.py
```
