# E2: the skill tier on six further read-only groups

Issue #114, with the health-route correction in issue #123. One root skill-artifact
campaign per group under the frozen pre-registration `docs/prereg-gdpevo-pilot.md`,
as extended by `docs/prereg-e2-skill-groups.md` and amended by
`docs/prereg-e2-amendment-1.md`. The trimmed final phase in
`docs/prereg-s4-addendum.md` is adopted by reference. E2 optimises one `SKILL.md`
per group for `task_group_004` through `task_group_009`, starting from the frozen
seed skill. This is a broader skill-tier experiment, not an E1c replication and
not a universal efficacy claim.

Status: **round 1 is terminal for all six groups.** Wave-1 finals are 004
`failed_gate`, 005 `failed_gate`, 006 `updated`, and 007 `failed_gate`. Group 006
is **retained without demonstrated improvement (zero-margin tie)**. Wave-2 optimise
is 008 `selected` and 009 `no_improvement`; 008's final is `failed_gate`. The
round-1 pooled adjudication estimate and complete-case holdout diagnostic appear
below; the registered all-selected-group holdout result is unavailable. Round 2
(group 006 only) is terminal: `no_improvement`; see "Round 2 (terminal)".

**Exit criterion 4 is still not demonstrated.** It requires a second retained
update from an approved champion. Group 006's round-1 update is a root update
from the seed; its round-2 campaign ended `no_improvement`, with no candidate
selected and no second retained update.

### Evidence references

Run evidence paths are relative to the external run-evidence root, not this
repository. Fixed pre-run facts come from `docs/prereg-e2-skill-groups.md`,
`docs/prereg-e2-amendment-1.md`, the pinned run configuration and launchers, and
the pre-run identity, health, smoke and exposure records. Result sections cite
`pilot-008/<group>/{campaign.json,outcomes.jsonl,calls.jsonl,decisions.jsonl,public/results.jsonl}`,
`pilot-008/final/<group>/observations.jsonl`, `pilot-008/entropy.json` and
`pilot-008/<group>/{acceptance.json,approval-request.json,approval.json}`.
Per-attempt timing, exit codes, failure reasons and usage come from the
corresponding `evidence/<attempt>/` metadata only. Private archives, score files,
task prompts, answers, evaluator scripts, notes and candidate-source content were
not report inputs. Where a required source is outside the permitted public record,
the value is marked `not measured (source not readable under the lane's data rules)`.

## Diagnostic scope and interpretation

E2 adds six read-only groups to the skill-tier record. Group selection is the
registered convenience selection, not representative sampling. Groups 001–003 are
not part of E2 and are never pooled with it. E2 does not pool or compare its rows
with S4, S4b, S5b, S5c, E1c or E1d.

The primary estimand is the holdout paired macro-mean difference over E2 groups
that actually selected a candidate. Below two paired groups the pooled comparison
is `unavailable`, as registered; no replacement estimator is added. Degenerate BCa
output is reported as-is. No significance, power or universal yes/no claim is made.

## What is frozen for E2

| Item | Registered value | Source |
|---|---|---|
| Groups | `task_group_004`–`task_group_009`, the next six unused `read_only` groups after 001–003 at the upstream pin | E2 prereg §2.1 |
| Upstream revision | `5082a777379156a048881e94940d640702e5e09a` | E2 prereg §2.1 |
| Run directory | `pilot-008`; earlier run directories are not reused or edited | E2 prereg §3 |
| Artifact | exactly one UTF-8 `SKILL.md` per group; no support files; one skill per group | E2 prereg §2.2 |
| Champion | frozen seed skill, candidate id `4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e`; raw file sha256 `b0fe3906ded74360a0c639093f11128a851aada57d12cfa48ce235195c657283` | E2 prereg §2.2 |
| Campaign | root campaign from the seed; 3 proposals per group; 36 evaluator item-evaluations per group | E2 prereg §2.2 |
| Spend cap | 42 logical model calls per group campaign: 36 solver + 3 proposer + 3 D2; failed calls metered; proposer retries logged, not metered again | E2 prereg §2.2 |
| Dev / adjudication / holdout carve | `train/001`–`003` / `train/004`–`005` / `test/001`–`005`, unchanged per group | E2 prereg §2.1 |
| Runs | 3 runs per task; equal-task group macro-mean | frozen prereg and S4 addendum |
| Final phase | 42 solves per group with a selected candidate: adjudication + holdout × 3 runs × champion/candidate; no control arm; dev read from optimise archive | E2 prereg §2.2 |
| Selection and retention | non-negative paired dev delta selects; zero-margin per-group retention on adjudication, ties pass | E2 prereg §6 |
| Holdout | reported, not gated; invalid or incomplete evidence still blocks | E2 prereg §6 |
| Solver and evaluator timeouts | 3600 s each | E2 prereg §2.2 |
| Approval | hash-bound per request to candidate, evaluator, data and code hashes; record-only `apply(hash)` under the owner's standing grant | E2 prereg §6; amendment 1 §4 |
| Health route | the group's declared route: `/health` if listed, else `/api/health`; any other case is a STOP | amendment 1 §2 |

No threshold, significance test or per-item gate is added. A tie retained under
the zero-margin rule is not an improvement.

## Waves and per-group status

Wave 1 is groups 004–007; wave 2 is groups 008–009. The waves implement the
registered scheduling plan and do not change group membership, budgets, selection,
retention or analysis. Campaign then final ordering applies within each wave.

| Wave | Group | Current status | Optimise outcome | Selected candidate | Final-phase status | Acceptance / terminal outcome |
|---|---|---|---|---|---|---|
| wave 1 | `task_group_004` | terminal | `selected`, stop `attempts` | `c5c4ceaf265d01962af244a4d07777cd18ac2d10a5073f41045a036f4c58ec3e` | complete; one candidate holdout STOP | `failed_gate` |
| wave 1 | `task_group_005` | terminal | `selected`, stop `attempts` | `e0d9e45082745093374ca951aea51f5c4a38e1bb571a589950d58ca4ceb69f33` | complete, 42 observations | `failed_gate` |
| wave 1 | `task_group_006` | terminal | `selected`, stop `attempts` | `fb9f14a0583bfa41e56ef841e6a8dd37dd36e3a360a9b054b4976b58af596be3` | complete, 42 observations; adjudication tie | `updated`, record-only; retained tie, not demonstrated improvement |
| wave 1 | `task_group_007` | terminal | `selected`, stop `attempts` | `2d126cb25b7b5233fed7365a35145fdc8ab977b093fc76524399545e7910106c` | complete; one candidate holdout STOP | `failed_gate` |
| wave 2 | `task_group_008` | terminal | `selected`, stop `attempts` | `7e078df09bd9ce517d7f3e98d336fcbac5edc39514c1df5afff43394d1952a70` | complete, 42 observations | `failed_gate` |
| wave 2 | `task_group_009` | terminal | `no_improvement`, stop `attempts`; no candidate | none | not run (no selected candidate) | `no_improvement` |

Sources: each group's `campaign.json`, terminal process output, and, for 004–008,
`acceptance.json` and final `observations.jsonl`.

**Group 004 exposure disclosure (amendment 1 §3):** before E2, the lead saw at
most three lines across three evaluator scripts covering `train/001`, `train/003`
(dev) and `test/003` (holdout), comprising an account identifier with numeric
fields. Group 004 is not wholly unexposed; no independence claim is made. See the
full disclosure under "Exposure log".

### Wave 1 execution record

| Item | Value |
|---|---|
| Campaign start / end | first solve 2026-11-07 18:59:19.635722 UTC; last solve end 2026-11-07 21:29:40.728624 UTC |
| Groups reaching a terminal optimise record | 4 of 4: 004–007, all `selected`, stop reason `attempts` |
| Final-phase start / end | first solve 2026-11-07 21:31:54.893010 UTC; last solve end 2026-11-08 01:16:24.000707 UTC |
| Groups reaching a terminal final or acceptance record | 4 of 4: 004 `failed_gate`, 005 `failed_gate`, 006 `updated`, 007 `failed_gate` |
| Operational STOPs by group and stage | 004 final candidate `test/005` run 1: 1 `missing_prediction`; 007 final candidate `test/001` run 1: 1 `missing_prediction`; 005/006: 0; optimise: 0 |
| Identity drift or rebind | none recorded; every campaign `code_hash` is `4420c420…989e`, and final phases used the same pin without rebind |

### Wave 2 execution record

| Item | Value |
|---|---|
| Campaign start / end | 008 first solve 2026-11-08 02:30:17.863117 UTC; 008 last solve end 04:12:15.088854 UTC; 009 has 9 documented pre-solve STOPs with no timing receipts, while the tenth reported attempt's disposition is unverified in the permitted receipts; both campaigns terminal by 2026-11-08 12:12 CST |
| Groups reaching a terminal optimise record | 2 of 2: 008 `selected`; 009 `no_improvement`, both stop reason `attempts` |
| Final-phase start / end | 008 not measured (timing receipts not among the permitted report inputs); 009 not run (no candidate) |
| Groups reaching a terminal final or acceptance record | 008 `failed_gate`; 009 `no_improvement` at campaign close, no final acceptance record |
| Operational STOPs by group and stage | 009 optimise: 9 of 10 attempts, `grader_sanity` (pre-solve check grading an empty prediction; operational, not a quality result); 008 optimise: 0; 008 final: 0 null-scored STOP observations in 42 complete records |
| Identity drift or rebind | none recorded in either campaign; 008 final not measured (identity receipts not among the permitted report inputs) |

## Code identity

Per E2 prereg §3 as superseded by amendment 1 §2. Identity was recorded before the
first solve, including the smoke. Both wave identity files are byte-identical and
record the amended pin, full hash, kernel-only hash, all six health checks and the
calibration identity.

| Identity | Value | Verification / comparison |
|---|---|---|
| Code pin (first `main` commit containing amendment 1 and the merged issue #123 change) | `f2cd1c067c0d206f69dbf9e6934185f6848b8c4f` | clean detached run tree, recorded before smoke; `git_sha` equal in both identity logs |
| Kernel-only hash (`_code_hash(exclude=("adapters",))`) | `cb1d650a889f15bee95b6a2cbc1b2fec6a856adb10ab0d3ae0f6bbf28bbf2e9f` | supplied known fact; equal in both identity logs |
| Full source hash (`_code_hash()`) | `4420c420c4495d74306aac736da45cd0f17e484b87b3e8ce6cabbe93c4bb989e` | both identity logs and every campaign `code_hash` agree |
| Identity-log file and sha256 | `pilot-008-logs/code-identity-wave1.txt` and `code-identity-wave2.txt`; each `4380b1e3b21168d08a2ac8c1a140e749d4696991b510a43865bf28c2e8745eb8` | byte-identical |
| Per-group execution-bound campaign `code_hash` | 004–009 all `4420c420c4495d74306aac736da45cd0f17e484b87b3e8ce6cabbe93c4bb989e` | each `campaign.json` |
| Per-group `evaluator_hash` | 004 `b8145ee8f6158f5869e9484f00b6b80335d097a63dd8cf1e3048770013b2ce68`; 005 `9a83357dbdb15fcb63032750d8fb9e3f2df37f357f777fc864e1108e4d64b043`; 006 `4f1d89af743449170913de907b647b4f6d754dae64aba9c26dd5417072c48eb4`; 007 `9ac89e0071801d8a17fbdfed7a4032d9fbd9f0aa18ba35382dfb63065255ba7a`; 008 `a7628383f7926e64e5afdcaaff643c18aa1e5aa54def807db70adf2f4981c739`; 009 `20a0a5454d0ae50f7001d60701824f53912c359ee18437bf45a983c2fb060299` | each `campaign.json`; equal in every outcome row |
| Champion reconstruction and champion id, per group | 004–009 all `4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e` | equals frozen seed identity; every admitted candidate has exactly this root as its only parent |
| Mid-run identity drift | none recorded | both identity logs and all campaign hashes agree |
| Final-phase pin and rebind status | 004–007: same pin, no rebind; 008: not measured (identity receipts not among the permitted report inputs); 009: not applicable | final terminal narrative and campaign identity records |

### Frozen skill, limits and launchers

| Item | Value |
|---|---|
| Trusted seed skill file and hash verification | `pilot-config/seed-SKILL.md`, sha256 `b0fe3906ded74360a0c639093f11128a851aada57d12cfa48ce235195c657283`; every campaign reconstructed champion id `4ef108e5…a09e` |
| Group manifests and per-file tree hashes | six `manifest.json` payloads, each 10 task entries with per-file sha256. Payload sha256 / file counts: 004 `507e5e711173daf43805f441318f45be3ab0cc47cba58c6fdfd222f9c48508d8` / 50; 005 `8fd03b0d0964754ac304f4c27c8428acb6293467b5b97f547b4136a28ca0b126` / 68; 006 `73a215d36b5cadd0eaf57b08e25aa8489f06f0ccbf682bd41d71f715e2b2f7f6` / 71; 007 `0d7484b5c706cf7b2bd5384f243fe06b7ace5fc73a62939f9533db2481e89077` / 71; 008 `0ec61c68defa3fbd43986b8407ad2a5ed48d0e88a04e7dcba8ddb42dc4eb10ed` / 80; 009 `1ee2ca6534889954b5495032898df8197289fd4c910971400278a20759e43b2d` / 80 |
| Run configuration path and sha256 | `pilot-config/config-e2.json`; `c846f257e273126eb759cef5fce999fb6d5e87f3ec1603ecb913877c151922f8` |
| Wave-1 launcher path and sha256 | `pilot-config/launch-e2.sh`; post-fix sha256 prefix `b6b3aea1` (full hash not present in permitted records) |
| Wave-2 launcher path and sha256 | not measured (source not readable under the lane's data rules) |
| Final-phase launcher path(s) and sha256 | `pilot-config/launch-e2-final.sh`; sha256 prefix `4dc22ffa` for wave 1; 008 final not measured (launcher receipt not among the permitted report inputs) |
| Solver image, CLI asset pins and reasoning effort | not measured (source not readable under the lane's data rules) |
| Runtime model identity and provider | `gpt-6.1-sol`, provider `proxy`, in every available campaign and wave-1 final `measurement.json`; 008 final not measured (model receipt not among the permitted report inputs); 009 has no model receipt |
| Docker version and image platforms | not measured (source not readable under the lane's data rules) |

## Pre-run STOPs

Amendment 1 required STOPs 1–6 to run again in full at the new pin. Receipts from
the stopped attempt were retained and not reused. No group was dropped.

| Ordered STOP | Result at the amended pin | Evidence |
|---|---|---|
| 1. Driver pinned and its tests pass | passed: 1,032 passed, 2 skipped at the amended pin | pre-run gate record; amended-pin merge record |
| 2. Groups restored at the upstream pin; read-only state, exact task layout and hash manifests verified without prohibited text reads | passed for all six; six manifests retained | six `manifest.json`; identity and restore records |
| 3. Per-group runtime health on each declared health route | passed: 004–009 all `health_ok` | both `code-identity-*.txt` |
| 4. Calibration identity preserved and grader-only replay byte-identical | passed: `calibration_identity_ok`, answer `5eb5cc63…ae96b`, output `12308ca2…6205e` | both `code-identity-*.txt` |
| 5. Fresh live smoke at the amended pin shows exactly `1 passed` | passed: `1 passed in 172.84s (0:02:52)` | `pilot-008-logs/smoke.log` |
| 6. Exposure reconciled from actual records | passed: reconciliation present before first E2 solve; 0 prior dev/adjudication/holdout solves for 004–009 | `pilot-config/e2/e2-exposure-reconciliation.md`, sha256 `cbf941d4df489caadd86a6203a2e8857b0a90f15d97075c9ba107171838c768d` |
| First campaign solve occurs only after 1–6 | yes: first solve 2026-11-07 18:59:19.635722 UTC (2026-11-08 02:59:19 CST), after the successful pre-run sequence | earliest `attempt-timing.json`; pre-run records |

### Known pre-solve incident: attempt 1, STOP 3 on group 004

Attempt 1 stopped at pre-run STOP 3 on `task_group_004` with
`environment_unhealthy`. The solver had assumed `/health`, while group 004 declares
only `GET /api/health`. This was an adapter assumption, not a quality result. Groups
005–009 were not health-checked in that attempt, and no group was dropped. Issue
#123 and amendment 1 changed the check to the group's declared health route, removed
both health routes from solver-visible access notes, moved the pin and required a
full re-run of STOPs 1–6. No E2 solve, smoke, campaign or final phase existed when
amendment 1 was recorded.

### Known pre-solve incident: launcher calibration-check STOP

At 2026-11-08 02:55 CST the launcher calibration check STOPped before smoke or any
solve. The inline check constructed a solver with every group-001 task, although
the optimise-stage constructor admits train tasks only. The production pre-run path
was unaffected. The launcher was restricted to the train subset, preserving the
grader-only replay; receipts are under `pilot-008-logs/attempt-1-stop4/`. The
relaunch then passed STOPs 1–6 and the live smoke. This was neither an optimise,
final nor acceptance outcome.

## Runtime pins and structured failures

| Check | Wave 1 optimise | Wave 2 optimise | Final phase |
|---|---|---|---|
| Served model identity and reasoning effort | `gpt-6.1-sol` / `proxy` in all 144 receipts; effort not measured (source not readable under the lane's data rules) | 008 same in 36 receipts; 009 no model receipt; effort not measured | 004–007 same in all 168 receipts; 008 not measured (model receipt not among the permitted report inputs); effort not measured |
| Docker version and image platforms | not measured (source not readable under the lane's data rules) | not measured (source not readable under the lane's data rules) | not measured (source not readable under the lane's data rules) |
| Solver attempts and elapsed-time range | 36 per group. Range seconds: 004 84.287–394.359; 005 64.675–175.280; 006 87.275–173.716; 007 71.433–280.662 | 008 36 attempts, 75.483–174.890 s; 009 10 attempts, no timing receipts | 42 per terminal group. Range seconds: 004 87.100–639.329; 005 86.516–233.615; 006 88.262–260.221; 007 89.772–303.531; 008 42 attempts, range not measured (timing receipts not among the permitted report inputs); 009 not run |
| Attempts approaching the 3600 s limit | 0; maximum 394.359 s | 008: 0, maximum 174.890 s; 009 not measured (no timing receipts) | 004–007: 0, maximum 639.329 s; 008 not measured (timing receipts not among the permitted report inputs) |
| Evaluator item-evaluations against cap | 36 of 36 per group | 008 36 of 36; 009 9 recorded pre-solve evaluations, all STOP; 0 publicly recorded scores | not applicable |
| Logical calls against the 42-call cap | 42 of 42 per group: 36 solver + 3 proposer + 3 D2 | 008 42 of 42; 009 12 of 42: 9 solver + 0 proposer + 3 D2 | not applicable |
| Retry rows and metering treatment | 0 retry rows; all measured solver calls included | 0 retry rows; 009's 9 failed solver calls logged with null usage, not zero usage | no proposer/D2 calls; all 42 terminal-group solver calls measured in observations, including 008; retry-row reconciliation not measured (receipts not among the permitted report inputs) |

| Event kind | Wave 1 optimise | Wave 2 optimise | Final | Evidence / effect |
|---|---|---|---|---|
| OOM | not measured (source not readable under the lane's data rules) | not measured (source not readable under the lane's data rules) | not measured (source not readable under the lane's data rules) | no OOM inference from missing receipts |
| `fsize` kill | not measured (source not readable under the lane's data rules) | not measured (source not readable under the lane's data rules) | not measured (source not readable under the lane's data rules) | no `fsize` inference from missing receipts |
| Timeout | 0 observed; all exit codes 0, max 394.359 s | 008: 0 observed, exit codes 0; 009 not measured | 004–007: 0 observed, all exit codes 0; 008 not measured (exit/timing receipts not among the permitted report inputs) | `attempt-timing.json` |
| Unclassified solver failure | 0; no `failure.json` | 008: 0; 009: 9 `grader_sanity` pre-solve STOPs, separately classified | 004/007: one `missing_prediction` each; 005/006: 0; 008: 0 null-scored observations, failure-reason receipts not measured | `failure.json` reason only; permitted final observations for 008 |
| Missing, corrupt or duplicate records | 0 duplicate or malformed public rows; 36 unique rows per group | 008 same; 009 has no public result rows available, and the tenth attempt's disposition is unverified | 004–008 each 42 unique `(item,run,arm)` observations; 004/007 each one null-scored STOP, so candidate holdout incomplete; 008 has 0 null scores and complete arms | public results and observations |

No OOM or `fsize` count is inferred from absent receipts. Solver-result
failures, operational STOPs and quality outcomes remain distinct.

## Dev campaign

Only dev scores guide proposals and selection. Dev is not re-run in the final
phase. Aggregation is run mean per task, equal-task group mean. Noise is the
champion's population standard deviation over three runs per task (`std@3`), then
the mean across tasks. Neither noise nor dev delta is the final retention gate.

### Champion dev rows and noise

| Group | Champion dev mean | Champion mean per-task `std@3` | Champion rows | Spread of run-level group means |
|---|---|---|---|---|
| `task_group_004` | 0.5555555555555556 | 0.0934024765394212 | 9 | 0.1166666666666667 (run means 0.6333333333333333 / 0.5166666666666667 / 0.5166666666666667) |
| `task_group_005` | 0.7962418300653594 | 0 | 9 | 0 |
| `task_group_006` | 0.9144880174370371 | 0.0261891400439462 | 9 | 0.0555555555555555 (0.933006535955555 / 0.933006535955555 / 0.8774509804) |
| `task_group_007` | 0.5424836601307189 | 0 | 9 | 0 |
| `task_group_008` | 0.7536765555555555 | 0.0566147401379613 | 9 | 0.0367646666666667 (0.778186333333333 / 0.741421666666667 / 0.741421666666667) |
| `task_group_009` | no complete public dev mean; 9 recorded champion failure receipts are pre-solve STOPs | not measured | 0 valid public rows | not measured |

Source: `public/results.jsonl` for 004–008; group 009 `attempt.json` and
`failure.json` reason fields. No private or grade artifact was used.

### Per-group optimise outcomes

| Group | Champion dev mean | Selected candidate dev mean | Selected candidate | Attempts | Attempt outcomes | Stop reason | Optimise outcome |
|---|---|---|---|---|---|---|---|
| `task_group_004` | 0.5555555555555556 | 0.6416666666666667 | `c5c4ceaf265d01962af244a4d07777cd18ac2d10a5073f41045a036f4c58ec3e` | 3 | `dev_regression`, `dev_pass`, `dev_regression` | `attempts` | `selected`, closed |
| `task_group_005` | 0.7962418300653594 | 0.7990196078431372 | `e0d9e45082745093374ca951aea51f5c4a38e1bb571a589950d58ca4ceb69f33` | 3 | `dev_regression`, `dev_regression`, `dev_pass` | `attempts` | `selected`, closed |
| `task_group_006` | 0.9144880174370371 | 0.9144880174370371 | `fb9f14a0583bfa41e56ef841e6a8dd37dd36e3a360a9b054b4976b58af596be3` | 3 | `dev_regression`, `dev_regression`, `dev_pass` | `attempts` | `selected`, closed |
| `task_group_007` | 0.5424836601307189 | 0.5424836601307189 | `2d126cb25b7b5233fed7365a35145fdc8ab977b093fc76524399545e7910106c` | 3 | `dev_pass`, `dev_pass`, `dev_pass` | `attempts` | `selected`, closed |
| `task_group_008` | 0.7536765555555555 | 0.7806373333333334 | `7e078df09bd9ce517d7f3e98d336fcbac5edc39514c1df5afff43394d1952a70` | 3 | `dev_pass`, `dev_pass`, `dev_pass` | `attempts` | `selected`, closed |
| `task_group_009` | no valid mean | not applicable | none | 3 campaign/proposal attempts, 10 solve attempts | `no_candidate` ×3; 9 `grader_sanity` STOPs | `attempts` | `no_improvement`, closed |

Sources: `campaign.json`, `outcomes.jsonl`, public results and terminal process
output. Selection uses the largest passing delta, replacing only on a strict
increase: group 007 retains the first of three zero-delta candidates; group 008's
second candidate has the largest recorded delta.

**Group 004 result exposure:** its dev mean and optimise outcome must be read with
the amendment 1 §3 evaluator-text disclosure under "Exposure log". Group 004 is
not wholly unexposed; no independence claim is made.

A `dev_pass` is eligibility/selection evidence only, not retained improvement.
A group with no selected candidate has no final phase and contributes no pairs to
the estimator; it remains in the per-group tables and is never imputed.

### Per attempt: admission, evaluation, paired dev delta and lineage

Every actual proposal is listed. All admitted candidates have exactly
`[4ef108e5317266f8a3b87551a47724e10283c8dfc294141dd56be3f582a5a09e]`
as `parent_ids`; this root parent is abbreviated `[seed]` below. No admission
refusal occurred. Each evaluated candidate has 9 valid dev rows.

| Group | Attempt | Candidate id | `parent_ids` | Admitted | Refusal reason | Candidate evaluated | Recorded `mean_delta` | Selection outcome |
|---|---|---|---|---|---|---|---|---|
| 004 | 1 | `d418fa441d4893489e505efdf25c6751e38c643ae67a8adc967cd0bcfc0639a9` | `[seed]` | yes | none | yes, 9 rows | -0.05138888888888889 | `dev_regression` |
| 004 | 2 | `c5c4ceaf265d01962af244a4d07777cd18ac2d10a5073f41045a036f4c58ec3e` | `[seed]` | yes | none | yes, 9 rows | 0.08611111111111112 | `dev_pass`; selected |
| 004 | 3 | `a4e63ad4f16f9767fcf0b121bbf184d767b775ec756fbe550e5838ae379e8bd9` | `[seed]` | yes | none | yes, 9 rows | -0.023611111111111107 | `dev_regression` |
| 005 | 1 | `90e05e747e6438fe8506fd55a4854beef99d8dbd2e16916fc9046187a72684c5` | `[seed]` | yes | none | yes, 9 rows | -0.06781045751633988 | `dev_regression` |
| 005 | 2 | `20e7d397540892ba05218d66b771dc14dd685748bfd7b6330bdd96c650f8b34f` | `[seed]` | yes | none | yes, 9 rows | -0.06851851851851852 | `dev_regression` |
| 005 | 3 | `e0d9e45082745093374ca951aea51f5c4a38e1bb571a589950d58ca4ceb69f33` | `[seed]` | yes | none | yes, 9 rows | 0.002777777777777768 | `dev_pass`; selected |
| 006 | 1 | `610935ef988410c6f7435267781ea5180a8e46557dd82e0e264f0ae6a7adfda1` | `[seed]` | yes | none | yes, 9 rows | -0.03703703703703703 | `dev_regression` |
| 006 | 2 | `8393b99c591001fcb2abb6f38be5ac6faed28f794a89fdaa7d41fb3761ea150d` | `[seed]` | yes | none | yes, 9 rows | -0.03703703703703703 | `dev_regression` |
| 006 | 3 | `fb9f14a0583bfa41e56ef841e6a8dd37dd36e3a360a9b054b4976b58af596be3` | `[seed]` | yes | none | yes, 9 rows | 0.0 | `dev_pass`; selected |
| 007 | 1 | `2d126cb25b7b5233fed7365a35145fdc8ab977b093fc76524399545e7910106c` | `[seed]` | yes | none | yes, 9 rows | 0.0 | `dev_pass`; selected (first strict maximum) |
| 007 | 2 | `a0d17c59c26717a8f7e18cb0034f3003d14abec6138907acd04a1c45b7bd5726` | `[seed]` | yes | none | yes, 9 rows | 0.0 | `dev_pass`; not selected |
| 007 | 3 | `9d57d0e58af4b860e681fae244859beeb2a40dbd0d670ec5ed985b184d93c0a9` | `[seed]` | yes | none | yes, 9 rows | 0.0 | `dev_pass`; not selected |
| 008 | 1 | `232765da1f42b0a0ea207e653da61153420616a73e1e6ea5298983f59d965c36` | `[seed]` | yes | none | yes, 9 rows | 0.02696077777777777 | `dev_pass`; not selected |
| 008 | 2 | `7e078df09bd9ce517d7f3e98d336fcbac5edc39514c1df5afff43394d1952a70` | `[seed]` | yes | none | yes, 9 rows | 0.026960777777777785 | `dev_pass`; selected |
| 008 | 3 | `3838d209b8ae9cb5b1b600c8b978ca1dcb90d256ff0b805a12e1617556d674f3` | `[seed]` | yes | none | yes, 9 rows | 0.02696077777777777 | `dev_pass`; not selected |
| 009 | 1–3 | none | not applicable | no candidate produced | pre-solve `grader_sanity`, not an admission refusal | no candidate evaluations; 9 champion attempts STOPped | null | `no_candidate` ×3; no final |

Sources: `outcomes.jsonl`, `public/candidates.jsonl`, `public/results.jsonl`, and
for 009 its 9 permitted failure records. Candidate-source content was not opened.

### D2 advisory record

D2 token usage is metered in E2. Missing recoverable usage is unknown, not zero.
D2 effectiveness is not evaluated.

| Group | Records | D2 choices | Baseline choices | Agreements | Fallbacks / malformed answers | Token usage |
|---|---|---|---|---|---|---|
| 004 | 3 | `c1`,`c1`,`c1` | `c1`,`c1`,`c1` | 3 of 3 | 0 / 0 | 1,128 input; 102 output |
| 005 | 3 | `c1`,`c1`,`c1` | `c1`,`c1`,`c1` | 3 of 3 | 0 / 0 | 1,129 input; 102 output |
| 006 | 3 | `c1`,`c1`,`c1` | `c1`,`c1`,`c1` | 3 of 3 | 0 / 0 | 1,129 input; 102 output |
| 007 | 3 | `c1`,`c1`,`c1` | `c1`,`c1`,`c1` | 3 of 3 | 0 / 0 | 1,095 input; 102 output |
| 008 | 3 | `c1`,`c1`,`c1` | `c1`,`c1`,`c1` | 3 of 3 | 0 / 0 | 1,128 input; 102 output |
| 009 | 3 | `c1`,`c1`,`c1` | `c1`,`c1`,`c1` | 3 of 3 | 0 / 0 | 1,068 input; 102 output |

All D2 rows identify backend `jev`, model `jev-latest`; usage comes from
`calls.jsonl`. These agreements do not evaluate D2 effectiveness.

## Primary estimator and evidence binding

Per E2 prereg §4.1, the primary estimator is the existing
`rsi_kernel/analysis.py::paired_group_bootstrap`: macro-mean of per-group candidate
minus champion, over E2 groups that actually have a selected candidate, separately
on each split. SciPy `bootstrap(paired=True)` defaults provide BCa, a two-sided 95%
interval and 9,999 resamples. Group indices are resampled with all task/run pairs
of each sampled group kept together. Degenerate BCa is reported as-is. Below two
paired groups every pooled row is `unavailable`; no task-level bootstrap or
replacement estimator is used.

The **primary estimand is holdout**. Adjudication decides retention; holdout is
reported, not gated. Dev selects only. The dev bootstrap below is therefore a
selection diagnostic, not a retention result. Pooled adjudication uses all five
selected groups. The registered all-selected-group holdout estimate is unavailable
because null-scored candidate observations in 004 and 007 block the registered
helper. A separately labelled complete-case diagnostic applies the same estimator
to 005, 006 and 008, a narrower estimand; no partial-arm mean is substituted for
the registered group mean.

| Item | Value |
|---|---|
| Groups with selected candidates entering paired estimates | dev and adjudication: 004, 005, 006, 007, 008 (5 groups); registered holdout: the same 5 groups are required, but its estimate is unavailable because 004/007 candidate arms are incomplete; complete-case diagnostic: 005, 006, 008 (3 groups); 009 excluded throughout (no candidate) |
| Bootstrap RNG entropy (`pilot-008/entropy.json`) | `92966130742029553693055347005560855011` |
| `entropy.json` payload sha256 | `ef8f159b39890fadbf8f8f87810cdc7f9dc4e74180665a4ca97c8ffd6c7afb0f` |
| Entropy recorded before the first final solve | yes: 2026-11-07 21:31:21.405211 UTC; first final solve 21:31:54.893010 UTC |
| Final observations file and sha256, per group | 004 `pilot-008/final/task_group_004/observations.jsonl`, `9ad98367d810bccde3eeb5e92d743a66b65af1a3ca7bed685fb9f7c9359b6dea`; 005 corresponding path, `2b67548b1397293b23544229b0c104e18f9afa3405e36a2d0c69ac8ab62c96f6`; 006 corresponding path, `33d0d717438969545516b5c0c70260d140c2b9e8bd0cc4f0fe04f1ddff4a00c5`; 007 corresponding path, `878c6cfe72911827bb12a3715746c08647de581ad303b4435aeff1f4c0a089e1`; 008 corresponding path, `07386ab8e79b7fd35c362f117e6786b16fd8d5bd2e5484ab9ff272c872ee9427`; 009 not run |
| Public results payload sha256, per group | 004 `00472466bb2e3dc81a3138794c94e90479cb5704876865a9ad978c46d0bc51c6`; 005 `af3daae55cba3d5c5df37d556c177fdc5106267a7d431b91d254d0090119a59e`; 006 `8cd612cd42573ce13e15b3ac08b478035d0a3c6ed107add5b8b48e1a00508444`; 007 `bd5829a3b4146a74c96b06f05992657f7be0fd7da6035f2bb76f42c44c65f897`; 008 `8d56b7c4d43cc8b8a50e38f9485a4a00ae159c4a8c51335314d7a5ee4a5f3453`; 009 no public results payload (no valid rows) |
| Estimator code identity used for reported rows | `rsi_kernel.analysis.report_table` / `paired_group_bootstrap` at the pinned run source, executed with `uv run` over public observations and `entropy.json`; full run code hash `4420c420…989e` |

### Counts required by prereg §4.2

These counts are reported separately and never imputed.

| Count | Actual value |
|---|---|
| Groups attempted | 6 of 6 |
| Groups with a selected candidate | 5: 004–008 |
| Operational STOPs, by group and stage | pre-run: health-route STOP and launcher calibration STOP, both before any solve; 004 final 1 `missing_prediction`; 007 final 1 `missing_prediction`; 009 optimise 9 `grader_sanity`; 008 final 0 null-scored STOP observations |
| Actual paired task count entering dev estimate | 15 (5 groups × 3 tasks) |
| Actual cluster count entering dev estimate | 5 |
| Actual paired task count entering adjudication estimate | 10 (5 groups × 2 tasks) |
| Actual cluster count entering adjudication estimate | 5 |
| Actual paired task count entering registered holdout estimate | unavailable (004/007 incomplete candidate arms block the all-selected-group input) |
| Actual cluster count entering registered holdout estimate | unavailable |
| Paired task count entering complete-case holdout diagnostic | 15 (3 complete groups × 5 tasks) |
| Cluster count entering complete-case holdout diagnostic | 3 |

### Dev split table

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| dev | selection complete; 5 selected candidates (final acceptance separate) | 0.7124891237488453 | 0.7356590570821787 | 0.02316993333333337 | 0.0016666666666666607 | 0.06944444444444446 | false | selection only; all 5 selected candidates have non-negative dev deltas; adjudication decides retention |

Computed once from public dev results with the registered helper, five group
clusters and the recorded entropy. No group-009 imputation.

## Adjudication

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| adjudication | `failed_gate` | 0.6040326890756302 | 0.5931926943977591 | -0.010839994677871122 | -0.016619981325863686 | -0.0044817927170868075 | false | false; 004/005/007/008 fail, 006 passes on an exact tie |

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_004` | `train/004` | 0.1111111111111111 | 0.1111111111111111 | 0.0000000000000000 |
| `task_group_004` | `train/005` | 0.2698412698412698 | 0.2380952380952381 | -0.0317460317460317 |
| `task_group_004` | group mean | 0.1904761904761905 | 0.1746031746031746 | -0.0158730158730159 |
| `task_group_005` | `train/004` | 0.5111111111111111 | 0.4000000000000000 | -0.1111111111111111 |
| `task_group_005` | `train/005` | 0.5490196078431373 | 0.6470588235294118 | +0.0980392156862745 |
| `task_group_005` | group mean | 0.5300653594771241 | 0.5235294117647059 | -0.0065359477124182 |
| `task_group_006` | `train/004` | 1.0000000000000000 | 1.0000000000000000 | 0.0000000000000000 |
| `task_group_006` | `train/005` | 0.8888890000000000 | 0.8888890000000000 | 0.0000000000000000 |
| `task_group_006` | group mean | 0.9444445000000000 | 0.9444445000000000 | 0.0000000000000000 |
| `task_group_007` | `train/004` | 0.8039215686274510 | 0.7647058823529412 | -0.0392156862745098 |
| `task_group_007` | `train/005` | 0.5555555555555556 | 0.5555555555555556 | 0.0000000000000000 |
| `task_group_007` | group mean | 0.6797385620915033 | 0.6601307189542484 | -0.0196078431372549 |
| `task_group_008` | `train/004` | 0.6842110000000000 | 0.7894739999999999 | +0.1052629999999999 |
| `task_group_008` | `train/005` | 0.6666666666666666 | 0.5370373333333334 | -0.1296293333333333 |
| `task_group_008` | group mean | 0.6754388333333333 | 0.6632556666666667 | -0.0121831666666666 |
| `task_group_009` | `train/004` | not applicable (no final phase) | not applicable | not applicable |
| `task_group_009` | `train/005` | not applicable (no final phase) | not applicable | not applicable |
| `task_group_009` | group mean | not applicable (no final phase) | not applicable | not applicable |

Retention per group: 004, 005, 007 and 008 fail the zero-margin rule; **006 passes
on an exact tie** and is retained without demonstrated improvement (zero-margin
tie). Each selected group has 3 runs per task per arm, hence 6 valid observations
per arm across the two tasks.

**Group 004 adjudication exposure:** the disclosed evaluator fragments included
`train/001` and `train/003` (dev), and `test/003` (holdout), not `train/004` or
`train/005`. The amendment 1 §3 disclosure still accompanies these results; group
004 is not wholly unexposed and no independence claim is made.

Final-phase completeness, ordering, uniqueness and failure-record checks: 004–008
each have 42 unique observations and the expected 21 per arm. Adjudication has no
null scores. Holdout has one candidate null-scored `missing_prediction` STOP in
004 and one in 007; 005/006/008 have no null-scored observations. Group 009 did
not run. Zero-margin retention is decided per group on adjudication; ties pass. A
retained tie is not improvement.

## Holdout

Holdout is the primary estimand and is report-only for retention. Invalid or
incomplete evidence still blocks. No holdout score chooses a candidate: the
candidate is frozen at campaign close before the final phase.

| Split | Outcome | Champion macro-mean | Candidate macro-mean | Estimate | CI low | CI high | Degenerate | Retention passed |
|---|---|---|---|---|---|---|---|---|
| holdout (registered, all selected groups) | unavailable: 004/007 candidate arms incomplete | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | not a gate |
| holdout complete-case diagnostic (005/006/008; narrower estimand) | diagnostic using the registered estimator, not the registered all-selected-group result | 0.7184841403050108 | 0.7007634346093994 | -0.01772070569561157 | -0.044054600000000055 | 0.010185200000000005 | false | not a gate |

### Per-task holdout diagnostics

Means below use the available valid runs. `n=2 + STOP` identifies an incomplete
candidate task mean; it is diagnostic only and is not used as a complete registered
arm. The corresponding candidate group mean and difference are marked incomplete
rather than computed from 14 valid rows as if they were 15.

| Group | Task | Champion mean | Candidate mean | Difference |
|---|---|---|---|---|
| `task_group_004` | `test/001` | 0.2424242424242424 | 0.3333333333333333 | +0.0909090909090909 |
| `task_group_004` | `test/002` | 0.6041666666666667 | 0.5625000000000000 | -0.0416666666666666 |
| `task_group_004` | `test/003` | 0.4705882352941176 | 1.0000000000000000 | +0.5294117647058824 |
| `task_group_004` | `test/004` | 0.1904761904761905 | 0.0317460317460317 | -0.1587301587301588 |
| `task_group_004` | `test/005` | 0.2307692307692308 | 0.3461538461538462 (n=2 + 1 STOP) | +0.1153846153846154, incomplete candidate task |
| `task_group_004` | group mean | 0.3476849131260896 | incomplete: 14 valid + 1 STOP | not measured (complete candidate arm unavailable) |
| `task_group_005` | `test/001` | 0.8750000000000000 | 0.6875000000000000 | -0.1875000000000000 |
| `task_group_005` | `test/002` | 0.9607843137254902 | 0.8823529411764706 | -0.0784313725490196 |
| `task_group_005` | `test/003` | 0.4705882352941176 | 0.5686274509803921 | +0.0980392156862745 |
| `task_group_005` | `test/004` | 0.7777777777777778 | 0.8333333333333334 | +0.0555555555555556 |
| `task_group_005` | `test/005` | 0.4444444444444444 | 0.4603174603174603 | +0.0158730158730159 |
| `task_group_005` | group mean | 0.7057189542483661 | 0.6864262371615313 | -0.0192927170868348 |
| `task_group_006` | `test/001` | 0.7916670000000000 | 0.7500003333333333 | -0.0416666666666667 |
| `task_group_006` | `test/002` | 0.3333330000000000 | 0.4259256666666667 | +0.0925926666666667 |
| `task_group_006` | `test/003` | 0.8333333333333334 | 0.8333333333333334 | 0.0000000000000000 |
| `task_group_006` | `test/004` | 1.0000000000000000 | 1.0000000000000000 | 0.0000000000000000 |
| `task_group_006` | `test/005` | 0.6666666666666667 | 0.6666666666666667 | 0.0000000000000000 |
| `task_group_006` | group mean | 0.7250000000000000 | 0.7351852000000000 | +0.0101852000000000 |
| `task_group_007` | `test/001` | 0.1458333333333333 | 0.3125000000000000 (n=2 + 1 STOP) | +0.1666666666666667, incomplete candidate task |
| `task_group_007` | `test/002` | 0.1052631578947368 | 0.1052631578947368 | 0.0000000000000000 |
| `task_group_007` | `test/003` | 0.8947368421052632 | 0.8947368421052632 | 0.0000000000000000 |
| `task_group_007` | `test/004` | 0.2352941176470588 | 0.2352941176470588 | 0.0000000000000000 |
| `task_group_007` | `test/005` | 0.2777777777777778 | 0.2777777777777778 | 0.0000000000000000 |
| `task_group_007` | group mean | 0.3317810457516340 | incomplete: 14 valid + 1 STOP | not measured (complete candidate arm unavailable) |
| `task_group_008` | `test/001` | 1.0000000000000000 | 1.0000000000000000 | 0.0000000000000000 |
| `task_group_008` | `test/002` | 0.5000000000000000 | 0.5000000000000000 | 0.0000000000000000 |
| `task_group_008` | `test/003` | 0.6470590000000001 | 0.6470590000000001 | 0.0000000000000000 |
| `task_group_008` | `test/004` | 0.7543863333333333 | 0.7192986666666666 | -0.0350876666666666 |
| `task_group_008` | `test/005` | 0.7222220000000000 | 0.5370366666666667 | -0.1851853333333333 |
| `task_group_008` | group mean | 0.7247334666666667 | 0.6806788666666667 | -0.0440546000000001 |
| `task_group_009` | `test/001`–`005` and group mean | not applicable (no final phase) | not applicable | not applicable |

The complete-case diagnostic estimate is -0.01772070569561157 with 95% BCa
interval [-0.044054600000000055, 0.010185200000000005], computed by the registered
estimator over complete groups 005, 006 and 008. It is not the registered
all-selected-group result. Groups 004 and 007 do not enter the diagnostic because
their candidate arms are incomplete; their valid per-task diagnostics remain above
without imputation.

Group 006's holdout change 0.7250 → 0.7351852 (+0.0101852) is **reported, not
gated**, and does not turn its adjudication tie into a demonstrated improvement.

**Group 004 holdout exposure:** amendment 1 §3 discloses lead access to fragments
of the `test/003` evaluator, as well as two dev evaluators. This disclosure applies
to every group 004 holdout value above; group 004 is not wholly unexposed and no
independence claim is made.

## Acceptance outcome and approvals

Acceptance is final-phase, hash-bound and record-only; optimiser `selected` is not
`updated`. Under the owner's standing grant, the lead may approve record-only apply
when retention passes. Each approval must bind the request's candidate, data,
evaluator and code hashes and cite the grant. `apply(hash)` never replaces the
champion, starts enforcement or deploys anything.

| Group | Disposition | Acceptance reason | Approval request / binding | Approval under standing grant | `apply(hash)` record |
|---|---|---|---|---|---|
| `task_group_004` | `failed_gate` | adjudication delta -0.0158730158730159; candidate holdout also has one STOP | none | not applicable | none |
| `task_group_005` | `failed_gate` | adjudication delta -0.0065359477124182 | none | not applicable | none |
| `task_group_006` | `updated`, retained without demonstrated improvement (zero-margin tie) | adjudication champion = candidate = 0.9444445; ties pass; holdout report-only +0.0101852 | candidate `fb9f14a0583bfa41e56ef841e6a8dd37dd36e3a360a9b054b4976b58af596be3`; code `4420c420c4495d74306aac736da45cd0f17e484b87b3e8ce6cabbe93c4bb989e`; evaluator `4f1d89af743449170913de907b647b4f6d754dae64aba9c26dd5417072c48eb4`; data `953af24cf45d76e9dae4f2e0275d36b2fff9729e4bad710f5604e9a17e6098e6` | approved under the owner's standing grant after independent hash verification; approval matches request on all four hashes | record-only `apply(fb9f14a0…)`; `acceptance.json` = `updated`; no enforcement or deployment |
| `task_group_007` | `failed_gate` | adjudication delta -0.0196078431372549; candidate holdout also has one STOP | none | not applicable | none |
| `task_group_008` | `failed_gate` | adjudication delta -0.0121831666666666 | none | not applicable | none |
| `task_group_009` | `no_improvement` at campaign close | no selected candidate; no final phase | none | not applicable | none |

Sources: terminal `acceptance.json` for 004–008, `campaign.json` for 009, and
006's `approval-request.json` / `approval.json`. The request's candidate equals
the selected campaign id; code equals the identity log; evaluator equals the
campaign hash; data binding was independently recomputed before approval.

**Group 004 acceptance exposure:** any group 004 acceptance, approval or apply
result above is subject to the amendment 1 §3 evaluator-text disclosure under
"Exposure log". Group 004 is not wholly unexposed; no independence claim is made.

| Acceptance category | Reported groups / count |
|---|---|
| `updated` with matching hash-bound approval | 1 terminal group: 006, retained without demonstrated improvement (zero-margin tie) |
| `no_improvement` or no selected candidate | 1 group: 009 |
| `failed_gate` | 4 groups: 004, 005, 007, 008 |
| `not_updated` | 0 terminal groups |
| Operational STOP, by group and stage | pre-run health and calibration STOPs before any solve; final 004 and 007 one each; optimise 009 nine; 008 final 0 null-scored STOP observations |

Keeping the champion is not counted as success. The acceptance table above covers
round 1; the terminal round-2 outcome is reported under "Round 2 (terminal)".
**Exit criterion 4 is not demonstrated**: group 006's root update was followed
by a round-2 campaign with no selected candidate and no second retained update.

## Cost and metering

Actual logical calls and provider-metered tokens only. No billed price is inferred
from token counts. D2 usage is reported as measured; unrecoverable usage is unknown,
not zero. Failed calls are metered and included by rule. Token columns in the main
table are solver-only; proposer and D2 totals follow separately. Cached input and
reasoning output are subsets of their respective input/output buckets.

| Stage | Solver attempts | Proposer calls | D2 calls | Calls against 42 cap | Evaluator items | Input tokens | Cached input | Output tokens | Wall time |
|---|---|---|---|---|---|---|---|---|---|
| Wave-1 campaign, 004 | 36 | 3 | 3 | 42 of 42 | 36 | 9,757,721 | 8,404,224 | 282,664 | solves 18:59:19–21:29:40 UTC; sum 6,986.954 s |
| Wave-1 campaign, 005 | 36 | 3 | 3 | 42 of 42 | 36 | 7,194,805 | 6,038,016 | 143,438 | solves 18:59:19–20:38:02 UTC; sum 3,857.400 s |
| Wave-1 campaign, 006 | 36 | 3 | 3 | 42 of 42 | 36 | 6,230,989 | 5,249,536 | 177,363 | solves 18:59:19–20:43:05 UTC; sum 4,443.200 s |
| Wave-1 campaign, 007 | 36 | 3 | 3 | 42 of 42 | 36 | 8,879,943 | 7,751,296 | 260,614 | solves 18:59:19–21:17:48 UTC; sum 6,360.746 s |
| Wave-2 campaign, 008 | 36 | 3 | 3 | 42 of 42 | 36 | 6,973,069 | 5,941,632 | 165,873 | solves 02:30:17–04:12:15 UTC; sum 4,211.136 s |
| Wave-2 campaign, 009 | 10 (9 documented pre-solve STOPs) | 0 | 3 | 12 of 42 | 9 recorded pre-solve evaluations; 0 publicly recorded scores | 0 measured (usage unknown, not zero) | 0 measured | 0 measured | not measured (no timing receipts) |
| Final phase, 004 | 42 | 0 | 0 | outside campaign caps | 42 | 18,920,107 | 16,905,216 | 502,679 | solves 21:31:55–01:16:24 UTC; sum 12,043.717 s |
| Final phase, 005 | 42 | 0 | 0 | outside campaign caps | 42 | 9,925,368 | 8,587,008 | 241,446 | solves 21:31:55–23:35:29 UTC; sum 5,983.656 s |
| Final phase, 006 | 42 | 0 | 0 | outside campaign caps | 42 | 7,503,408 | 6,419,072 | 285,323 | solves 21:31:55–23:46:55 UTC; sum 6,679.755 s |
| Final phase, 007 | 42 | 0 | 0 | outside campaign caps | 42 | 12,102,949 | 10,648,064 | 335,819 | solves 21:31:54–00:09:55 UTC; sum 8,061.567 s |
| Final phase, 008 | 42 | 0 | 0 | outside campaign caps | 42 | 8,973,875 | 7,798,144 | 227,010 | not measured (timing receipts not among the permitted report inputs) |
| Final phase, 009 | 0 (no candidate) | 0 | 0 | not applicable | 0 | not applicable | not applicable | not applicable | not run |
| Pre-run smoke | 1 | not applicable | not applicable | outside campaign caps | 1 | not measured (source not readable under the lane's data rules) | not measured (source not readable under the lane's data rules) | not measured (source not readable under the lane's data rules) | pytest 172.84 s |

| Item | Value |
|---|---|
| Solver reasoning output and cache-write buckets | campaign 004 129,740 / 0; 005 55,724 / 0; 006 44,099 / 0; 007 92,737 / 0; 008 65,618 / 0. Final 004 296,636 / 0; 005 108,793 / 0; 006 85,727 / 0; 007 126,739 / 0; 008 105,561 / 0. 009 unknown |
| Proposer token totals | 004 34,464 input / 32,171 output / 66,635 total; 005 22,266 / 29,504 / 51,770; 006 26,472 / 22,550 / 49,022; 007 42,606 / 27,332 / 69,938; 008 13,911 / 26,988 / 40,899; 009 0 calls |
| D2 token totals or unknown rows | 004 1,128 input / 102 output; 005 1,129 / 102; 006 1,129 / 102; 007 1,095 / 102; 008 1,128 / 102; 009 1,068 / 102; no unknown usage rows |
| Failed solves charged and their tokens | 004 final `test/005` candidate run 1: 1,144,155 input, 1,075,328 cached, 20,163 output, 1,164,318 total; 007 final `test/001` candidate run 1: 440,701 input, 376,832 cached, 8,681 output, 449,382 total. Included in final totals. 009's 9 failed solver calls have null usage, unknown not zero |
| Reconciliation of `calls.jsonl` with `measurement.json` and final observations | exact bucket-for-bucket agreement for all 180 campaign solver calls with available usage (36 each for 004–008), and all 168 wave-1 final observation / measurement pairs. 009 has 9 null-usage solver rows and no measurement receipts, consistently pre-solve; 008 final observation token totals are reported directly from `observations.jsonl`, while reconciliation to calls/measurement receipts is not measured (receipts not among the permitted report inputs) |
| Real billed cost | unavailable: every available campaign and wave-1 final `measurement.json` has `cost_usd: null`; no billing record supplied; 008 final likewise has no billing record among the permitted report inputs |
| Modelled price | not reported |

Campaign solver totals (input + output): 004 10,040,385; 005 7,338,243; 006
6,408,352; 007 9,140,557; 008 7,138,942. Final solver totals: 004 19,422,786;
005 10,166,814; 006 7,788,731; 007 12,438,768; 008 9,200,885. Wall time is
solve-attempt span and summed elapsed solve time, not overall launcher runtime;
parallel attempts overlap.

### Planning numbers only — not measured results

The following figures are copied from E2 prereg §4.3 solely to preserve their
context. **They are planning numbers only, not E2 measurements, guarantees, caps or
acceptance criteria.** They use an iid normal approximation, ignore clustering,
assume every group selects a candidate and guarantee nothing.

| Planning quantity | Planning-only value |
|---|---|
| Paired tasks for δ = 0.05 / 0.037 / 0.02 at σ = 0.09 | n = 26 / 47 / 159 |
| Approximate minimum detectable effect at 30 pairs | 0.046 |
| Approximate minimum detectable effect at σ = 0.116 | 0.059 |

A nonsignificant result will be reported as its measured estimate and interval,
not as "no effect". Historical extrapolations in E2 prereg §8 are likewise not E2
actuals; the cost tables above must use E2's own records.

## Exposure log

Every private-split submission or disclosure is recorded. Once disclosed,
continued independence is not claimed. The public-repository pretraining caveat
applies to every group.

### Exposure before E2

E2 prereg §5's zero-prior-exposure statement is superseded as follows by amendment
1 §3: groups 004–009 have **zero prior solve exposure**; group 004 additionally
has the lead evaluator-text exposure disclosed below. The incident does not
retroactively satisfy STOP 2's no-read requirement and is not repaired or omitted.

| Group | Prior dev solves | Prior adjudication solves | Prior holdout solves | Prior smoke solves | Other prior exposure |
|---|---|---|---|---|---|
| `task_group_004` | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | lead evaluator-text disclosure, amendment 1 §3; no-solve health contacts |
| `task_group_005` | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | no-solve health checks only |
| `task_group_006` | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | no-solve health checks only |
| `task_group_007` | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | no-solve health checks only |
| `task_group_008` | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | no-solve health checks only |
| `task_group_009` | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | 0 (reconciled) | no-solve health checks only |

The zero-solve statements above are the reconciled pre-E2 fact, not measured E2
results. Reconciliation payload sha256 is
`cbf941d4df489caadd86a6203a2e8857b0a90f15d97075c9ba107171838c768d`.
Groups 001–003 have separate historical exposure records and are not pooled with
E2.

### Group 004 lead evaluator-text disclosure — must accompany every group 004 result

While diagnosing attempt-1 STOP 3, a lead search over the group 004 tree printed
fragments of three evaluator scripts, at most three lines in total: an account
identifier with numeric fields. The scripts cover `train/001`, `train/003` (dev)
and `test/003` (holdout). The lead authors no candidate; champions, configuration,
caps, candidate path and selection rule were frozen before the incident. Group 004
stays in E2 with this disclosure. It is not wholly unexposed, and no independence
claim is made for it.

This disclosure applies to **all group 004 optimise, adjudication, holdout,
acceptance and approval results above**. Any later group 004 result copied out of
this report must carry the same disclosure.

### E2 exposure added by this run

Registered bounds, not predictions: at most 36 solver attempts per group campaign,
42 final solves per group with a selected candidate, and one smoke on group 001.
The smoke exposes no E2 task.

| Group | Dev campaign solves | Dev smoke | Adjudication solves | Holdout solves | Actual reconciliation / source |
|---|---|---|---|---|---|
| `task_group_004` | 36 | 0 | 12 | 30 attempts; 1 candidate STOP | 36 public results; 42 final observations; evaluator-text disclosure above also applies |
| `task_group_005` | 36 | 0 | 12 | 30 | 36 public results; 42 final observations |
| `task_group_006` | 36 | 0 | 12 | 30 | 36 public results; 42 final observations |
| `task_group_007` | 36 | 0 | 12 | 30 attempts; 1 candidate STOP | 36 public results; 42 final observations |
| `task_group_008` | 36 | 0 | 12 | 30 | 36 public results; 42 final observations |
| `task_group_009` | 10 attempts; 9 recorded pre-solve STOPs; no candidate produced | 0 | 0 | 0 | 9 failure receipts, no valid public results; no final phase |

Proposer-input and D2 numeric-state exposure: 004–008 each had 3 proposer calls
and 3 D2 calls; 009 had 0 proposer and 3 D2 calls. Dev is exposed to the proposer
by design. The final phase has no proposer, so it adds no proposer disclosure.
Group 009's 9 pre-solve STOPs are operational failures, not nine scored dev
outcomes. No independence, replication or compounding claim is inferred from solve
counts alone.

## Adapter diff against the kernel

Descriptive only: file and line counts, with no "thin" threshold and no efficacy
interpretation. The counts are reproduced by repository `git diff --numstat` from
the registered E2 prereg commit `a7abf0a` to the amended run pin `f2cd1c0`, with
path restrictions matching the table rows. The health-route change is adapter
behaviour governed by amendment 1; grading, selection, retention, approval matching
and calibration identity are unchanged by registration.

| Path set / comparison | Changed files | Insertions | Deletions | Result |
|---|---|---|---|---|
| Kernel excluding adapters, against the registered comparison pin | 1 (`src/rsi_kernel/decision/backends.py`) | 4 | 0 | D2 usage metering only |
| `uv.lock` | 0 | 0 | 0 | byte-identical in the comparison |
| Skill adapter, including issue #123 health-route change | 3 (`health.py`, `pilot.py`, `solver_docker.py` under `src/rsi_kernel/adapters/gdpevo/`) | 122 | 24 | registered E2 support plus declared health-route correction |
| Grading, selection, retention and approval-matching paths | 0 in `analysis.py`, `loop.py`, `compare.py` | 0 | 0 | no diff in the comparison |

## Named local exceptions (carried, not re-derived)

| Exception | Where frozen | Effect on this report |
|---|---|---|
| Convenience selection of the next six unused read-only groups, not representative sampling | E2 prereg §2.1 | Results describe groups 004–009 only; declared read-only is not measured immutability |
| Fixed dev / adjudication / holdout carving map | frozen prereg; E2 prereg §2.1 | No re-carve or substitution if layout differs; pre-run STOP instead |
| Exactly one UTF-8 `SKILL.md`, no support files, one skill per group | E2 prereg §2.2 | No universal or cross-group skill claim |
| Served model and reasoning effort named in the frozen prereg | E2 prereg §2.2 | Runtime identity is recorded from measurement; effort is not inferred from an unreadable trace |
| Solver and evaluator timeout 3600 s | E2 prereg §2.2 | Observed failures are classified from receipts |
| Spend metered as 42 logical model calls per group campaign | E2 prereg §2.2 | Calls and tokens, not an HTTP-request bound or billed price |
| Proposer retries logged but not metered again | E2 prereg §2.2 | Failed calls and retries remain distinguishable |
| Dev re-run and control arm dropped | S4 addendum, adopted by E2 | Dev comes from optimise archive; noise is champion dev spread |
| Group-cluster bootstrap over groups with selected candidates; fewer than two is unavailable | E2 prereg §4.1–4.2 | No imputation or estimator switching |

## Round 2 boundary

E2 prereg §7 registers a possible round 2 only after every round-1 group has a
terminal record, on exactly the groups with a retained approved round-1 champion.
Group 006 was the only eligible group. Its approved round-1 champion
(`fb9f14a0583bfa41e56ef841e6a8dd37dd36e3a360a9b054b4976b58af596be3`) was
reconstructed and continued at the same pin, with a fresh smoke and an exposure
reconciliation recorded before the first round-2 solve. All splits were reused
from round 1, so they are adaptive, not untouched.

### Round 2 (terminal)

| Attempt | Candidate | Parent | Dev paired mean delta | Outcome |
|---|---|---|---:|---|
| 1 | `2124aeaafd31…` | `fb9f14a0583b…` | -0.018518518518518514 | `dev_regression` |
| 2 | `50e098fcbb31…` | `fb9f14a0583b…` | -0.018518518518518514 | `dev_regression` |
| 3 | `4b82e5c6d5fd…` | `fb9f14a0583b…` | -0.018518518518518514 | `dev_regression` |

- Campaign outcome: `no_improvement` (stop reason `attempts`).
- Dev rows: 36 = 4 arms × 3 tasks × 3 runs, with no null scores.
- No candidate was selected, so no final phase ran. Per E2 prereg §7 the marginal round-2 adjudication and holdout increments are **unavailable**. Nothing is imputed.

No round-2, cumulative-growth or indirect chained estimate exists. Group 006's root
update alone does not satisfy exit criterion 4, and round 2 produced no second
retained update.

## Not covered

- No universal yes/no or cross-group-population claim: selection is convenience,
  not representative sampling.
- No significance, power or p-value claim; planning numbers in §4.3 are not
  guarantees and are not measured E2 results.
- No independence claim for group 004: the lead evaluator-text disclosure in
  amendment 1 §3 accompanies every group 004 result. Zero prior solve exposure is
  not zero prior exposure of every kind.
- No pooling with groups 001–003 or any earlier campaign; no imputation of a group
  without a selected candidate.
- No estimator replacement or task-level bootstrap; fewer than two paired groups
  makes the pooled comparison unavailable.
- No improvement claim from `dev_pass`, selection, a retained tie or holdout alone.
  Adjudication decides retention; holdout is reported, not gated. Group 006 is a
  retained root update on a tie, not a demonstrated improvement.
- Exit criterion 4 remains undemonstrated: no second retained update from an
  approved champion is reported.
- No operational STOP treated as a completed negative quality outcome. The two
  known launcher/health incidents occurred before any solve; group 009's nine
  pre-solve STOPs are also operational.
- No D2 effectiveness claim; missing token usage is unknown, not zero.
- No billed-cost claim without a real billing record and no modelled price.
- No approval or apply claim without matching candidate, data, evaluator and code
  hashes; record-only apply is not deployment or enforcement.
- No round-2 increment, compounding, cumulative-improvement or indirect chained
  result: round 2 selected no candidate.
- No release to any product and no cross-product transfer claim.
