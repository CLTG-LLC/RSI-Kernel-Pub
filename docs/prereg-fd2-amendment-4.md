# FD2 amendment 4: operational transport change and fresh noise-floor run

Recorded 2026-11-09 UTC, after a partial noise-floor attempt and before attempt 2
or any campaign solve, under COS **Transparent Changes**
(https://www.cos.io/initiatives/prereg). FD2 prereg and amendments 1–3 remain
unchanged historical records. The in-repo precedent is
`docs/prereg-e1c-amendment-1.md` §§1, 5–6: preserve an operational STOP and its
exposure, amend prospectively, then run a fresh attempt rather than recycle it.

## 1. What happened

Attempt 1 used the seed skill, adjudication, `--jobs 4`, solver code `c590af8`
and grading tag `fd2-eval-1` → `e3318b7`. At **2026-11-09T00:41:14Z** it latched
an **operational STOP, not a quality result**: `binding_mismatch` about 3 s after
dispatch of hosted run **42541522630**, for
`c/DeusData__codebase-memory-mcp-632`, run 1. That same run later showed the
expected ID, title (= request ID) and commit. Cancellation worked; it concluded
cancelled at **00:46:15Z**. The failure record did not capture which field
mismatched, so transient title propagation is an **inferred cause**, not proved.
Four model solves were consumed: three graded, one `None`; the other **74**
(item, run) pairs were **NOT_DISPATCHED**, never solved.

## 2. Changes A and B

**A — operational transport only.** The frozen grading-client file is unchanged:
it belongs to the frozen evaluator identity. The solve-host launcher wraps its
GitHub CLI call. **For a run-status query only**, while the reported title equals
the workflow name and status is pre-run (`queued`, `waiting`, `pending`,
`requested`, the client's existing states), it re-queries **the same run ID** at
the client's existing **5 s cadence**, within the existing deadline, logging
every observation. It never alters a returned field. The frozen ID/commit/title
checks and artifact binding check remain intact; other mismatches still STOP.

Precedents: [actions/runner #4141](https://github.com/actions/runner/issues/4141)
reports workflow-name/title differences between requested and completed events;
[mento deployment recovery](https://github.com/mento-protocol/frontend-monorepo/blob/main/docs/vercel-deployments.md)
(the paragraph beginning “The returned run is re-queried”) re-queries the returned
run while its title is the exact workflow default. This is **a project's practice,
not a GitHub guarantee**; its retry numbers are not adopted here.

**B — fresh measurement, no rescue.** Attempt 1 is void as a noise-floor
measurement. Its scores are not used anywhere, not reported as results and not
given to any proposer. Its `None` is **not regraded**, redispatched or replaced
with a late result (amendment 2 §3 item 5). Preserve all attempt-1 evidence.
Execute a fresh, complete **26 × 3 = 78** seed-skill solves under the same
registered rules in new directory **`rsi-runs/fd2-noise-floor-2`**; do not resume
or fill the partial attempt. **This amendment is written after three voided
partial scores were observed.** The transport failure drives this decision;
the voided scores have no role in any decision. It is not outcome-independent.

## 3. Exposure and reconciliation

Adjudication carries **four extra seed-skill solves**, irrespective of voiding:

| Evidence directory under `fd2-noise-floor/evidence/` | Item | Run |
|---|---|---:|
| `swe-40a78b3e` | `c/DeusData__codebase-memory-mcp-632` | 0 |
| `swe-7a46233d` | `c/DeusData__codebase-memory-mcp-632` | 1 |
| `swe-1f739d15` | `c/DeusData__codebase-memory-mcp-632` | 2 |
| `swe-585f9e35` | `c/colbymchenry__codegraph-1051` | 0 |

Bindings were checked using only result/failure identity fields and
`results.jsonl`'s `item_id`, `run`, `evidence_dir` fields; no scores or patch
contents were read for this amendment. The filename-only scanner explicitly
binds all four (item, run) pairs. Only the registered stopped solve accepts
`failure.json` instead of `result.json`, still requiring `attempt.json`,
`model_patch.diff` and `measurement.json`. Its exact nested transport
`harness/run-1/failure.json` is not a second solve. Missing/incomplete bindings
remain STOPs. Root-level launch logs are ignored; `pilot-config` is outside the
scan. Attempt 2 has **no binding yet**: its appearance makes reconciliation STOP
until its actual records are bound before any campaign solve.

Actual scan at **2026-11-09T00:58:24Z**, command
`python tools/fd2/exposure.py --runs-root <rsi-runs>` (exit 0):

```text
rsi-runs/fd2-code-c590af8: code checkout, not an execution record
rsi-runs/fd2-codex-assets-0.166.0: runtime assets, not an execution record
rsi-runs/fd2-freeze: image metadata freeze, no model call
rsi-runs/fd2-gold-smoke-1: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-2: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-3: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-4: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-6: gold run, no model call; local dir empty; failed/cancelled artifact-download target (lead-recorded)
rsi-runs/fd2-gold-smoke-7: gold run, no model call; summary record present
rsi-runs/fd2-gold-smoke-8: gold run, no model call; summary record present
rsi-runs/fd2-gold-validity-1: gold validity, no model call; aggregate record present
rsi-runs/fd2-host-smoke: gold host-fidelity run, no model call; summary present; vendored result.json files are not solves
rsi-runs/fd2-noise-floor: voided partial noise floor, operational STOP
rsi-runs/fd2-smoke: solver smoke; root result.json is not a second solve
rsi-runs/fd2-smoke-prerun: preflight records (4 dry-run, 1 run launcher); solve counted at fd2-smoke, not again here
c/DeusData__codebase-memory-mcp-632: 3
c/colbymchenry__codegraph-1051: 1
rust/yvgude__lean-ctx-632: 1
total_model_solves=5
```

Before attempt 2: **5 model solves = 1 dev smoke + 4 voided adjudication**, zero
holdout. After a complete attempt 2: expected **83 = 5 + 78**, with actual
records reconciled before campaign. No fresh-independent-adjudication claim is
made; amendment 2 §5's separate drafting exposure remains disclosed unchanged.
The historical 1,447 whole-plan ceiling gains four sunk solves: **1,451**;
campaign/final allocations remain unchanged.

## 4. Forward-only parallelism; unchanged rules

One attempt-1 window (**n=1**, not a throughput guarantee) observed up to **4
concurrent solves**. Across **148** Docker-stats samples, own-container total
memory peaked at **4.29 GiB**, with at most **8 containers**, in a **24 GiB**
Docker VM raised from 8 GiB to Docker's documented default, “50% of your host's
memory” ([Resources / Advanced](https://docs.docker.com/desktop/settings-and-maintenance/settings/)).
For the three graded solves, solve walls were **405–479 s**, grade queue **0 s**,
and grade jobs **302–637 s**. Amendment 3's **4-job cap is a ceiling**, not a
sustained-throughput or whole-workload capacity promise; no speedup is inferred.

Unchanged: splits, exclusions, three repetitions, report-only noise-floor
statistic, selection, zero-margin/ties-pass retention, paired cluster-aware
analysis, isolation, approval, solver timeout **21,600 s**, dispatch-to-result
deadline **43,705 s**, evaluator identity and **`fd2-eval-1` → `e3318b7`** tag.
The solver pin remains `c590af8`; the launcher transport wrapper is separately
recorded and hashed before attempt 2. This amendment is prospective for attempt
2, campaign and final solves, not for the observed partial attempt. It changes
no quality threshold and does not certify other pre-run gates or launch a run.
