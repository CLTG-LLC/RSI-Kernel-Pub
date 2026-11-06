# H1b: inventory-preserving rule-pack edit

This report covers the H1b run under `docs/prereg-h1b-rule-pack-addendum.md`
(issue #92), a forward-only addendum to H1a. Following that addendum, only the
differences from `docs/results/h1a-rule-pack.md` (the **H1a report**) are stated
here. Scope, host, guard, data pins, carve, metric, bounds and limitations are
adopted from the H1a report by reference. As with H1a, this is a
configuration-artifact probe with one frozen proposal. It makes no search-depth,
efficacy or statistical claim.

Status (H1a prereg §7, reported separately):

- **Execution: completed, no operational STOP.**
  - All run-time identities matched the frozen H1a values.
  - The champion reproduced byte-identically.
  - The proposal passed the mechanical admission check, then went through the
    real three-class golden guard on the offline copy.
- **Quality and acceptance: no improvement.**
  - The guard failed and the host returned HTTP 422 `guard_failed` before scoring.
  - `run-campaign` exited 0 with `no_improvement` and nothing selected.
  - `accept` was not run.
- **Holdout not evaluated / no holdout report.** No adjudication item was
  evaluated either.

The outputs were not evaluated on any product sealed set. They may not be
proposed to the host product's team without a separate disposition (H1a prereg §1, §7).

## Order of events

H1b prereg §3 requires the author to be assigned only after the prereg is merged
and an independent release record exists. That order was followed this time,
unlike H1a (R-221, disclosed in the H1a report):

| Step | Record |
|---|---|
| Prereg merged | `51404d1` (#93), R-225 |
| Independent release re-check: frozen identities rehashed, no H1b proposal present | GENERATION-RELEASE, R-226 |
| Author assigned | R-227, after R-226 |
| Proposal frozen, admission check passed | R-228 |
| Run-time re-verify, reproduce-first, dev campaign | R-229, R-230 |

## Proposal and admission

| Item | Value |
|---|---|
| Champion | Unchanged from H1a: sha256 `404cd8c4…4fd0`, content_id `90da5b4c…429c`, 62 rules |
| Proposal | `proposal-1.yml` sha256 `31b4d64984b35b92090c165522503b8c28a8806c29d98284da3e6c92e0518f44`, content_id `e333ef60bdaf02466b8474df9e43427f817975aea7c25bab8b29adb99f0b6b24`, parent = champion; frozen read-only (0444) at 2026-11-06 22:11:36 CST, before admission and evaluation |
| Content (counts only) | 8 of the 35 regex `matcher.expression` values edited, widening phrasing for instruction-override, system-prompt-disclosure and jailbreak-persona rules, including Chinese variants. Rule count, ids, order and every other byte unchanged |
| Author | One fresh data-blind writer, GPT-6.1-Sol, role `proposal-author`, separate from the prereg writer and the release reviewer. One authoring job, one proposal, no repair or replacement. 9 tool calls by its own count, one of which failed; tool calls are not model requests |
| Author access (attested in the retained brief) | The champion copy plus the product's loader, rule and phase source files, the boundary H1b prereg §3 preregistered. No data, outcomes, H1a artifacts, tests, fixtures, golden text, lane notes or web datasets. No JDK run; loader validity was left to evaluation |
| **Admission check (§2)** | **Passed.** A line-aligned byte comparison against the champion found exactly 8 changed lines, each still a single-quoted `expression:` scalar with an unchanged prefix, and 0 other changed bytes. The script (sha256 `e3ed5b8c…d833`) was self-tested on an unchanged copy (rejected: no edit), an all-expression edit (admitted) and a non-expression edit (rejected). The diff and the JSON result are retained |

Passing admission does not replace the guard, as §2 states.

## Run-time verification

Everything ran in a new directory, `h1b-run-1`. No H1a receipt was reused.

- **Identities: 53 of 53 recomputed and matched** the frozen H1a values. They cover:
  - the kernel tree at `83268e4` (clean, detached, locked sync, sources aggregate);
  - host source and classes, and the JDK;
  - the offline classes manifest, 1,593 files;
  - the champion in the source, built and staged copies;
  - the golden-resource receipt and its five resources;
  - membership and items hashes;
  - a dev-only cases file with 353 ids and no adjudication or holdout ids;
  - bounds `max_attempts` 3, `spend_cap` 0, `eval_cap` 706, `runs` 1, with no holdout split;
  - the proposal hash and mode.
- **Guard binding:** unchanged host configuration. All three golden classes run with
  a 600 s timeout against exact candidate bytes. There were 0 `.guard-*` files before the run.
- **Reproduce-first:** two fresh champion passes, both byte-identical to the frozen
  H1a reproduction. On the dev items that is attack 15/234, benign 119/119, mean
  **0.3796**. The champion's guard run passed: Fixture 3/0/0, Zh 139 tests with
  0 failures and 4 staged skips, Inventory 6/0/0.

## Result

`run.sh` (sha256 prefix `bab78781`) is the H1a script with only the run directory
and proposal path changed. Its configuration was generated from a template, with
only the loopback port substituted.

`run-campaign.stdout.json`, exit 0:

```json
{"attempts": 3, "champion_id": "90da5b4c517c85b3b915b202ecf470aa0792c1584dd08a2f65f4b3b3c846429c", "evaluator_items_used": 706, "outcome": "no_improvement", "selected_id": null, "stop_reason": "attempts"}
```

| Attempt | Candidate | Outcome |
|---|---|---|
| 1 | `e333ef60…` (the proposal) | `dev_failure`: host 422 `guard_failed` |
| 2 | none (queue empty; no replacement) | `no_candidate` |
| 3 | none | `no_candidate` |

The stdout, `decisions.jsonl`, `public/results.jsonl` (353 champion rows) and
`campaign-h1b-run-1.json` are byte-identical to H1a's. That is expected: the
champion, bounds and outcome path are identical and those files carry no candidate
id. `outcomes.jsonl` and `public/candidates.jsonl` differ by the candidate id.
`evaluator_items_used` 706 is reserved before evaluation, as explained in the H1a
report; 353 item scores were produced, all for the champion.

**Host evidence:** `ok` 1 (champion), `ineligible` 1 (proposal, `guard_failed`),
`operational` 0.

### Proposal guard

| Class | Tests | Failures | Errors | Skipped |
|---|---|---|---|---|
| Fixture | 3 | 1 | 0 | 0 |
| Zh | 139 | 2 | 0 | 4 (staged) |
| Inventory | 6 | 0 | 0 | 0 |

The failing methods are named below. Fixture text and assertion messages were not read.

- `RuntimeFirewallGoldenFixtureTest.identityHashesMatchRegistry`
- `RuntimeFirewallZhGoldenFixtureTest.existingRuleIdsAndHashesUnchanged`
- `RuntimeFirewallZhGoldenFixtureTest.existingRulesHitSetsUnchangedOnZhNegatives`

## Interpretation

What was measured:

- The **inventory checks now pass**. The Inventory class passed, and neither
  coverage method that failed in H1a failed here. Preserving the inventory removed
  H1a's blocker.
- The guard still rejects the edit, through different methods. H1a prereg §5
  describes the Fixture method, from source only, as requiring exact
  `matcherIdentity` / `ruleVersionHash` equality to the fixture. The two Zh method
  names state the same kind of check: existing rule hashes, and existing rules'
  hit sets on the Zh negatives, must be unchanged.

The unchanged guard rejected this proposal on identity/hash checks and on the
existing-rule hit-set check for Chinese negatives. The source-only descriptions
establish checks over fixture-listed identities; exhaustive identity coverage of
every existing rule was not established here. This result shows that the frozen
H1b proposal is ineligible, not that every possible rule-pack edit is ineligible.
As in H1a, this reading rests on method names and source-only descriptions, not
on assertion messages.

- **Demonstrated:** H1a's integration and hard-ineligibility path, now
  reproduced on a fresh run directory. Also:
  - a preregistered admission check run before evaluation;
  - a generation order that followed the release record.
- **Not demonstrated:** any improvement, quality comparison, paired delta or
  adjudication retention. The proposal's effect on the dev items remains unknown.

**Consequence for this host line:** H1a tested one additions-only proposal and
H1b tested one inventory-preserving, pattern-only proposal. The unchanged guard
rejected both. These results do not establish whether another configuration
change that preserves the tested inventory, identities and behavior could pass.
No further experiment is proposed here. Changes to the guard or its golden
resources need a separate owner disposition.

## Integrity

| Check | Result |
|---|---|
| Proposal | `31b4d649…` and 0444 before and after |
| Offline source resource | `404cd8c4…` after the run; 0 `.guard-*` files |
| Stale build output | As in H1a, `target/classes` held the proposal bytes after the run (R-214). `mvn -o -q process-resources` (exit 0) recopied the champion, and the classes manifest returned to `7076d7c7…`. The lead independently confirmed both resource copies at `404cd8c4…` afterwards |
| Host process | Stopped by its own PID; no host process remained |
| Execution tree | Unchanged at `83268e4` |

## Exposure

| Read | Count |
|---|---|
| Additional champion dev evaluations of the 353 dev items | 3 (2 reproduce-first passes, 1 in the campaign) |
| Candidate dev evaluations | 0 (blocked before scoring) |
| Guard executions | Reproduce-first: 1 champion guard execution; the second champion call used the content-id cache (`repro/drive-log.json` shows populated Surefire reports for pass 1 and none for pass 2). Campaign: 1 champion and 1 proposal. Total: 3. Both reproduction calls still scored all 353 dev items |
| Adjudication / holdout | 0 / 0 |
| Author data access | None |

These add to H1a's recorded exposure (H1a report, "Exposure"). Dev remains
adaptive. Prior exposure outside the documented receipts is unknown, not zero.
No independence claim is made.

## Cost

Model solver calls 0. Model D2 calls 0 (deterministic). CLI spend reading 0.
One authoring job. The author reports 9 tool calls, including one failed tool
call. Model-request count, model-request failure count, token usage and cost
were not measured; tool calls are not model requests. The campaign took about 25 s by epoch stamps, including both guard
runs. The whole run directory, from identity checks to post-run restore, took
about 3 min 52 s, as reported by the run worker. Reviews are not metered.

## Sources

Private run-relative paths; none is published.

- `h1b-build/proposal/` (`proposal-1.yml`, `champion-rules.yml`, `freeze-time.txt`),
  `h1b-build/admission/` (`admission_check.py`, `admission-result.json`, `admission-diff.txt`)
- `h1b-run-1/IDENTITIES.md`, `verify_identities.py`, `repro/`, `RUN.md`, `run.sh`,
  `run-campaign.*`, `hashes-*.txt`, `guard-strays.txt`,
  `offline-classes-manifest-*.txt`, `host/`, `store/`, `surefire-proposal/`
  (counts and method names only)
- Decision records R-225 to R-230

## Not covered

- No improvement claim, quality comparison, paired delta or per-item flips.
- No adjudication retention, approval or record-only apply.
- No holdout evaluation or holdout report.
- No search-depth, efficacy, significance, power or independence claim. No
  sealed-set result, product release or proposal to the host product's team.
