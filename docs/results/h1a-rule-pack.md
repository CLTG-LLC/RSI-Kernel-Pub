# H1a: offline rule-pack configuration experiment

This is the result of the H1a run under the frozen preregistration
`docs/prereg-h1a-rule-pack-addendum.md` (issue #78). The kernel optimised a **copy**
of the host product's built-in runtime-firewall rule pack. The run was offline,
non-grant and record-only. It used the unchanged `rsi-kernel run-campaign`, the
generic JVM host in `examples/firewall-host/`, and the host product's own golden
tests as the hard guard. This is a configuration-artifact integration probe with
one frozen proposal. It is not a search-depth, efficacy or statistical claim.

Status (prereg §7, reported separately):

- **Execution: configuration-artifact integration demonstrated.** The exact
  candidate bytes were loaded into the offline copy and run through the real
  three-class golden guard. The guard failed, and the host returned HTTP 422
  `guard_failed` before emitting any score.
- **Quality and acceptance: no improvement.** `run-campaign` exited 0 with
  outcome `no_improvement` and no candidate selected. The only proposal was
  ineligible. `accept` was not run because nothing was selected.
- **Holdout not evaluated / no holdout report.** No adjudication item was
  evaluated either.

The run was not an operational STOP. It completed, and its negative result is the
hard-ineligibility path. The proposal never got as far as a quality comparison.

Outputs have never been evaluated on any product sealed set. They cannot be
proposed to the host product's team without a separate disposition (prereg §1, §7).

## Scope

| Item | Value |
|---|---|
| Artifact | One copied built-in rule pack, component key `rules.yml`, registry `["c1"]`, media `application/yaml` (prereg §2.1) |
| Execution | Unchanged `run-campaign` from a clean detached tree; deterministic D2; `spend=lambda: 0` (prereg §2.3) |
| Apply | Record-only. Nothing replaces the champion or publishes rules. Nothing reached that step in this run |
| Product | No host-product code or policy change, activation, deployment or publication. The offline copy's resource was swapped only for the guard call and then restored |
| Data | Public pools only, dev material. No product sealed set was opened or used |
| Grant scope | Not amended; this is a separate, non-grant experiment (owner disposition R-193) |
| Proposal source | One complete proposal written by a data-blind author before evaluation; no live or evaluation-fed proposer (prereg §2.2, §9) |

## Frozen identities

### Execution tree, host and offline copy

| Identity | Value |
|---|---|
| Execution tree | Clean detached tree at RSI-Kernel `main` `83268e40a96c513f1f62dd1836848b57adb92aac`; `git status --porcelain` empty; `uv sync --locked` exit 0 |
| Kernel sources aggregate | `897fd9fe78f07a80830dbfee641a3b4f4ff7adf760bdbf4a1df94a376599edbf` (sha256 over the sorted `<name> <sha256>` lines for `src/rsi_kernel/*.py`) |
| `cli.py` / `loop.py` | `04fb32fe575fef0ba682563de33e2ebd3e5cd6eadf963fbf39fa7b6d7d4b4425` / `a6c5419bcb8c6c8c8ab6d0b4df61307cb77c1ee75877156ab07440f33fc84c66` |
| Host source `examples/firewall-host/FirewallHost.java` @`83268e4` | `8b36b398f45389d54669a9de5c5064084d29c8990fa6bf1a369bcde8b74ea8cc` (includes the guard command from PR #81 and the restore-temp fix from PR #89) |
| Host classes (JDK 17 `javac`) | Manifest `61a1105e38f7a4f265807a5200c99effb27c841aa92bc75647a14e518a210227`; `FirewallHost.class` `f0fceb13e3823c6be96f9ba096903aab9daf20fee670d02e6789990aa45d2591` |
| Host configuration | `host.properties` `08711dcbf81486f687238cdaa0663953a878de4d540c289884e251868ea7d8f5`; guard timeout 600 s (named local operational bound) |
| Offline copy source revision | The host product's commit `83f5e8eb…`, the same commit as the prereg §5 source inventory |
| Offline classes (no jar exists) | `target/classes` tree manifest, 1,593 files, `7076d7c7d077abd80697abce7e0637c13e169405fba755ba398df0df26e46ffe` |
| Toolchain | JDK 17.0.21.0.3; Maven 3.10.0; maven-resources-plugin 3.5.0 (content-based change detection); Python 3.12.15; uv 0.13.4 |
| Execution manifest | `prerun/execution-manifest.json` sha256 `66a08dc233d2d1f9151f0260398a165514222b5a31da8cf78d9956f5f5ee08b9`. It records the execution tree and revision, kernel/CLI and host-source hashes, host/offline classes manifests, golden-resource identity receipt, membership/items/validator hashes, proposal/champion hashes, `eval_cap` 706, `runs` 1 and `max_attempts` 3. Host configuration and toolchain versions are recorded separately in the run and pre-run receipts |

### Golden guard

Selectors (prereg §5, all three classes):
`RuntimeFirewallGoldenFixtureTest,RuntimeFirewallZhGoldenFixtureTest,RuntimeFirewallGoldenInventoryTest`.
Test sources match prereg §5: Fixture `2d07eee5…628d`, Zh `349b06de…bba47c`,
Inventory `ea57a195…a533`.

The five golden resources are recorded **hash-only**; no content was shown. Each one
is equal across the offline source tree, the offline test classpath and the product
commit `83f5e8eb…` (`prerun/golden-resource-identity.json`, sha256
`450578f5752f4ef796f5d7597ae9a19dd0fd1b9259d434a45195ff24b8d85720`):

| Resource | SHA-256 |
|---|---|
| `firewall/runtime-firewall-golden-v1.json` | `d72befe706de1feeae4eba79f4aa9f8b7c30d06fce0edd350e99b27ee71d3c00` |
| `firewall/runtime-firewall-keyword-v1.json` | `11cbbbb53523f9da9b5fd68c33e9046c418801f65b5ff8cdda5ea4f3c60ec9bd` |
| `firewall/runtime-firewall-illegal-sites-v1.json` | `51817d535c57b6f60bea3cf559c052f8c512a7c800dd53b6d896206bf5cc2c4c` |
| `firewall/runtime-firewall-zh-golden-v1.json` | `091eb52221e71b16b8514d3b61827af1b736393527826d5333c20810cc4c168e` |
| `firewall/runtime-firewall-zh-baseline-v1.json` | `df15cc514f13b00e9a249949a8c36f8e5ac863c1a23488702d03ee5085183d38` |

### Data pins and carve

Inputs were re-verified inside `extract.py`, which STOPs on any mismatch.

| Source | Pin | Use |
|---|---|---|
| Arcanum PI taxonomy | `e02cf5b6e202f195c6b6c01484e99519f797acc6`, `taxonomy.json` `fc26b73a…daa7` | 775 attack examples, unchanged strings |
| Akto | `afa02a80a1c10420301b1d7fb4900b158f316be8`, the 8 RETAIN files of prereg §3.2 (all 8 hashes match) | 8 attack strings, one per file. The 8 EXCLUDE files were not read |
| deepset/prompt-injections | `4f61ecb038e9c3fb77e21034b22511b523772cdd`, train `2e10bc7a…4c04`, test `39ac797c…b246e` | `label == 0` only: 399 benign controls (343 train + 56 test), unchanged strings |

The carve is **NAMED LOCAL EXCEPTION H1A-PUBLIC-CARVE** (prereg §9). Each pool was
deduplicated by exact string, its IDs (sha256 of the UTF-8 text) were sorted, it was
shuffled with a fresh `random.Random(20261106)`, and then split as dev =
floor(0.30n), adjudication = floor(0.20n), holdout = remainder.

| Class | Raw | Deduplicated | Dev | Adjudication | Holdout |
|---|---|---|---|---|---|
| attack | 783 | 783 | 234 | 156 | 393 |
| benign | 399 | 399 | 119 | 79 | 201 |

| Artifact | SHA-256 |
|---|---|
| `extract.py` | `58f9ca4d5cb5f74a9480779631fb04bcfa644fb4a3f385747ae90d6b2c7f0c40` |
| `carve.py` (stdlib only) | `ebbe6071919335e5017d0bcc8d614d39f7dc3755f7241a55fe1c12c39fb96d75` |
| `pools.json` | `f8c365cc9a55bf5c85f64c50f286be9778e85b6b1bba9be4457f0e4a8e15daa0` |
| `membership.json` | `45f01418fbd711ba240ff7c74cddff81e2b437457ab611206e01a03934210a89` |
| `items.jsonl` | `a774d26b21c99c2c6171362b0dd28d9c11838a3a6f7715439630df20e84112fb` |
| `validate_carve.py` | `2d3a154b09edf6e02c66f763aecb22af76a56e69b9552e0cc11d42e74c849a66` |

`carve-validation.json` reports `pass: true` on every check:

- every eligible deduplicated item was assigned exactly once, per class;
- the splits are disjoint, and each ID is in one split;
- the floor/remainder counts are correct;
- the item IDs equal the membership IDs;
- a full regeneration gave byte-identical `pools.json`, `membership.json` and `items.jsonl`.

Exact-string deduplication removed nothing, and there were no identical strings
across the two classes. Near-duplicates were not removed.

The campaign configuration loaded dev (353) and adjudication (235) from
`membership.json`. There is no holdout split in the configuration. The host cases
file `dev-cases.json` (`99ebed7a…aa5aa`) contains **only the 353 dev items**, so
adjudication items could not be evaluated in this run by construction.

### Champion and proposal

| Identity | Value |
|---|---|
| Champion | Startup bytes of the copied built-in pack, sha256 `404cd8c4d27086d3dbed6b9431d788846500184516988339f8923b7d63744fd0`, content_id `90da5b4c517c85b3b915b202ecf470aa0792c1584dd08a2f65f4b3b3c846429c`; 62 rules |
| Proposal | `proposal-1.yml` sha256 `acf4837a69c3019dfd3fac8687b890acf86a5099313523120c014566c54a1cff`, content_id `0e8cb2bc27a5ec1e6667c69c69db4ccebe237fba67e8bc5b146253b18c06afc7`, parent = champion; frozen read-only (mode 0444) before evaluation |
| Proposal content (counts only) | The 62 existing rules unchanged, 11 request-phase regex rules appended (10 block, 1 monitor), manifest count updated to 73 (R-213). **Additions only** |
| Author | One fresh bounded writer with the `proposal-author` role, assigned by the lead; one authoring job; one proposal; no repair or replacement |
| Author access (attested in the retained brief) | The champion pack plus the product's loader, rule and phase source files. No dev, adjudication or holdout items, no tests, no golden fixtures, no lane notes and no web access. The author had no JDK, so the proposal was not loaded before evaluation; loader validity was left to the evaluation (422 if invalid) |

Disclosure: prereg §§2.2 and 9 restrict the author's input to the champion pack and frozen task/format instructions. The attested access also included the product's loader, rule and phase source files. These contain no data, test or fixture content, so the author stayed data-blind, but the input boundary was wider than preregistered.

Proposal generation also preceded the required release check: R-213 records the proposal frozen at 20:42 CST on 2026-11-06, before the final-host re-freeze recorded in R-217 at 20:58 and the independent release in R-219 at 21:06. This deviated from the preregistered generation order. R-219 subsequently authorized evaluation of that single frozen proposal; it does not establish that generation followed the required order.

## Pre-run STOPs and the release re-check

Prereg §9 lists the pre-run STOPs in execution order. All were closed with evidence
before the proposal was evaluated.

| Pre-run STOP | Status | Evidence |
|---|---|---|
| H1A-CARVE / H1A-EVAL-CAP | Closed | Carve frozen and validated as above. `eval_cap` = **706** = champion dev 353 × 1 + one registered candidate 353 × 1 (prereg §2.3 formula; lead disposition R-210/R-216). The first pre-run report also offered the attempt-based 1,412; the lead chose the registered-candidate reading the prereg states |
| H1A-GUARD-BINDING | Closed | The guard runs the product's existing golden classes unchanged, against an offline copy whose rules resource holds the exact candidate bytes. Test failure → 422, infrastructure failure → 500 (PR #81, reviewed and merged) |
| 1. Host identity | Closed | Host re-frozen at `83268e4` after PR #89 (the restore temp is now created only after the guard run) |
| 2. Classes build identity | Closed | No jar exists. The `target/classes` tree manifest `7076d7c7…6ffe` was taken at the start and end of the re-freeze and was byte-identical; 0 `.guard-*` files before and after |
| 3. Data hashes and membership map | Closed | As above |
| 4. Guard verified | Closed | Unchanged champion passes all three classes; a known-bad synthetic probe returns 422 (table below) |
| 5. Fresh reproduce-first on frozen dev | Closed | Byte-identical, below |
| 6. Proposal frozen | Closed | `acf4837a…`, 0444, before evaluation |

Guard re-verification at `83268e4`, with two fresh host processes and the surefire
reports cleared before each call. The probe is the champion with one regex
expression replaced by a literal (sha256 `f551594466b95934b616500d6fe9569dc2024cf1bb540880a8d865812b8fda6e`,
content_id `7101db2c…0752`), evaluated with zero items.

| Call | HTTP | Fixture tests/fail/skip | Zh tests/fail/skip | Inventory tests/fail/skip |
|---|---|---|---|---|
| A1 champion (guard ran) | 200 `passed` | 3/0/0 | 139/0/4 | 6/0/0 |
| A2 champion (cached by content_id) | 200 | — | — | — |
| A3 probe | 422 `guard_failed` | 3/2/0 | 139/2/4 | 6/0/0 |
| B1 probe, first call in a fresh host | 422 `guard_failed` | 3/2/0 | 139/2/4 | 6/0/0 |
| B2 champion right after the probe (guard ran) | 200 `passed` | 3/0/0 | 139/0/4 | 6/0/0 |

- The champion passes with 148 tests reported: 144 not skipped and passed, 4 skipped,
  0 errors. The 4 skips are the Zh `stagedGoldenCases` staged assumptions. They are
  recorded as skipped, never as passes.
- After every call, the source resource was byte-identical to `404cd8c4…4fd0`, with
  the same mtime and mode.
- The host evidence log held 5 lines matching the 5 calls: `ok`/`passed` ×3 and
  `ineligible`/`guard_failed` ×2.

Reproduce-first: the champion was scored on the 353 dev IDs in the frozen order. A1
and A2, and B2 in a separate host process, all produced response sha256
`717638f74dea71a8427fc10f3abd20e92289d03022673316a694e8e6ec451b54`. That matches the
two earlier reproductions on the pre-fix host. `runs=1` is adopted on this basis
(prereg §6).

History, in order (dispositions from R-199 to R-219):

1. The prereg PR #79 first failed review (2 S2 findings). The lead applied the
   exact replacements, the re-check passed, and it merged.
2. The first pre-run pass raised three items. Lead dispositions:
   - **F1** (host side effect: restore temp files copied into `target/classes`):
     issue #86, fixed in PR #89.
   - **N1** (only two guard classes run): all three classes from prereg §5 are
     required.
   - **eval_cap**: 706.
   A later correction (R-214) withdrew the proposed Maven overwrite flag. The
   product's plugin 3.5.0 uses content-based change detection, so a stale target
   copy is recopied on the next build. The only real defect was the temp file.
3. Re-freeze at `83268e4`: everything passed. An independent re-check was requested.
4. **Release re-check: HOLD** (R-218), with four findings: S2, golden-resource hashes
   missing; S2, no clean detached execution tree or manifest; S3, a wrong
   validator digest in a receipt; S3, wording that called skipped tests "executed".
5. The lead added `golden-resource-identity.json`, the clean detached tree and
   `execution-manifest.json`, and **corrected receipts**:
   - the validator digest was replaced. An abbreviated earlier form,
     `2d3a154b…6a2b`, did not match; the full digest is
     `2d3a154b09edf6e02c66f763aecb22af76a56e69b9552e0cc11d42e74c849a66`;
   - "executed" became "reported" in three places, so skips are not counted as passes.
6. **Re-check: RELEASE** (R-219). All four findings were closed. The reviewer
   independently rehashed the golden resources against the product commit's blobs,
   33 kernel files against the commit, and every manifest binding. The release
   covered evaluation of the single frozen proposal only: offline, record-only, no
   product change, no replacement proposal and no holdout evaluation.

## Result

Command (`run.sh`, sha256 prefix `19df2edc`):

1. Start the host on JDK 17.
2. Run the detached tree's `rsi-kernel run-campaign --config config/campaign.json`.
3. Stop the host. It exited 143 (SIGTERM) and was confirmed gone.

The configuration (`67f60e83…2ddb`) was generated from its template (`e6c5d26e…4b1879`)
with only the loopback port substituted. Bounds: `max_attempts` 3, `spend_cap` 0,
`eval_cap` 706, `runs` 1.

### Campaign

`run-campaign.stdout.json` (sha256 `767fc70ceb9f6d7ff45e5d5bcf9b18508b90786231d8aef869a9766d6132593e`), exit 0:

```json
{"attempts": 3, "champion_id": "90da5b4c517c85b3b915b202ecf470aa0792c1584dd08a2f65f4b3b3c846429c", "evaluator_items_used": 706, "outcome": "no_improvement", "selected_id": null, "stop_reason": "attempts"}
```

| Attempt | Candidate | Outcome | `mean_delta` |
|---|---|---|---|
| 1 | `0e8cb2bc…` (the proposal) | `dev_failure` | null |
| 2 | none (queue empty; no replacement proposal) | `no_candidate` | null |
| 3 | none | `no_candidate` | null |

The CLI records the 422 as `dev_failure` and does not distinguish 422 from 500
(prereg §4). The host evidence log provides that distinction.

### The proposal was ineligible: 422 before scoring

The host returned **HTTP 422 `guard_failed`**. Surefire for the proposal's guard run
(`surefire-proposal/`):

| Class | Tests | Failures | Errors | Skipped |
|---|---|---|---|---|
| Fixture | 3 | 1 | 0 | 0 |
| Zh | 139 | 1 | 0 | 4 |
| Inventory | 6 | 1 | 0 | 0 |

The failing methods are named below. Fixture text and assertion messages were not read.

- `RuntimeFirewallGoldenFixtureTest.everyRegistryRulePassesTheSharedMustMatchAndMustNotMatchCases`
- `RuntimeFirewallZhGoldenFixtureTest.exactInventoryMetadataAndCombinedGoldenCoverage`
- `RuntimeFirewallGoldenInventoryTest.exactCombinedInventoryProducesNoFailure`

**The candidate was blocked before scoring.** It has no dev score, and no zeros were
fabricated. `store/public/results.jsonl` holds 353 rows, all for the champion.

### Champion dev

| Class | Correct | Score |
|---|---|---|
| attack (`must_match`) | 15 / 234 | 0.0641 |
| benign (`must_not_match`) | 119 / 119 | 1.0000 |
| **Unweighted item mean** | **134 / 353** | **0.3796** |

This matches the re-freeze reproduction. The candidate has no dev mean, paired
delta or per-item flips, because it was not scored.

### Evidence-log and evaluation accounting

| Record | Count |
|---|---|
| Host evidence log (`host-evidence.jsonl`, sha256 `fdb11c59dadf5a622fc50c4fb1a4c7e1a2527646b6f96e63c540b229205abf96`) | 2 lines: `ok` 1 (champion `90da5b4c…`, guard `passed`), `ineligible` 1 (proposal `0e8cb2bc…`, `guard_failed`), `operational` 0 |
| Reconciliation with the CLI | Champion `ok` ↔ 353 champion result rows; proposal `ineligible` ↔ attempt 1 `dev_failure`. No evidence append failed |
| `evaluator_items_used` | **706 reserved**. The kernel reserves `len(dev) × runs` before calling evaluate, so the blocked candidate's 353 count against the budget |
| Item scores produced | **353**, all champion |
| D2 records | 3 deterministic (`budget_used` 353 / 706 / 706; `c1.dev_pass_count` 134, `c1.dev_fail_count` 219) |
| Adjudication evaluations | 0 |
| Holdout evaluations | 0 |
| `accept` | Not run (nothing selected); no approval request or approval file; `campaign-h1a-run-1.json` records `acceptance: null` |

The host evidence log writes `skipped_tests: "unknown"` by design. The skip counts
above come from the surefire XML.

Run store hashes: `campaign-h1a-run-1.json` `f224b56f…a95`, `outcomes.jsonl`
`c0e2aaa6…b8d`, `decisions.jsonl` `120e0bf5…71c`, `public/candidates.jsonl`
`9c8d76aa…a95`, `public/results.jsonl` `30a52001…1ac`. `private/` is empty.

## Interpretation

As measured: the frozen guard rejected the additions-only proposal in all three
golden classes, and the failing method in each class is the one that checks
complete rule coverage or the exact inventory. Prereg §5 describes these methods,
from source only, as follows:

- the Fixture method requires exact registry coverage, so every rule needs its
  golden must-match/must-not-match cases;
- the Zh method requires complete combined registry coverage;
- the Inventory method requires the exact combined inventory.

The host product's golden suite therefore **pins the exact rule inventory and
requires golden cases for every rule.** Any proposal that adds rules without adding
golden cases changes the inventory, so an additions-only proposal cannot pass this
frozen guard **by construction**. Editing the guard or its resources is out of scope
(prereg §5.4). This reading comes from the method names and the prereg's
source-only descriptions; the assertion messages were not read.

- **Demonstrated:**
  - real-host integration: exact candidate bytes went through the real loader path
    and the unchanged three-class golden guard on an offline copy;
  - the hard-ineligibility path end to end: real guard failure → 422 → CLI
    `dev_failure` → no score emitted → campaign `no_improvement`.
- **Not demonstrated:** any improvement. There is no quality comparison, no
  adjudication retention and no `updated` record. The proposal's effect on the dev
  items is unknown, and nothing here suggests whether it would have helped.

This additions-only proposal cannot satisfy the frozen inventory and coverage checks without corresponding golden-resource changes, which are outside this experiment's scope. This run does not establish whether a configuration change that preserves the tested inventory, identities and behavior could pass the unchanged guard.

## Integrity

| Check | Result |
|---|---|
| Proposal hash | `acf4837a…` before and after the run (`hashes-before.txt`, `hashes-after.txt`) |
| Rules resource in the offline source tree | `404cd8c4…4fd0` after the run, byte-identical; 0 `.guard-*` files anywhere in the offline copy (`guard-strays.txt` empty) |
| Stale offline build output | Right after the run, `target/classes/firewall/runtime-firewall-rules.yml` still held the proposal bytes (`acf4837a…`). This is the expected stale-target effect (R-214), not a restore failure. A guard build would recopy it under content-based change detection, as call B2 above showed. `mvn -o -q process-resources` (exit 0) recopied the champion, and the offline classes manifest returned to `7076d7c7…6ffe` (`offline-classes-manifest-restored.txt`). This was harmless to the run: the champion is loaded from the source tree, and the guard rebuilds before testing |
| Host process | Stopped by the script; exit 143; confirmed gone |
| Execution tree | Clean detached tree at `83268e4`; no kernel, CLI or host change during the run |

## Disclosures and limitations

Required by prereg §7:

- **Private-API reflection, offline copy only.** The host calls the product's
  package-private static `load(InputStream, List)` through reflection (precedent:
  the product's own `PolicySnapshotRuntimeFirewallViewTest.java:478–483`;
  R-195). This is not a supported product API.
- **Residual adaptive overfitting.** All data is public, writer-visible research
  material, so it is **adaptive dev material**. The adjudication and holdout
  subsets are **not independent**, even though they were not evaluated here and
  the author never accessed them.
- **Sealed-set overlap cannot be determined** (R-197). A names-and-counts-only
  check found no way to compare the public sources with the host product's sealed
  sets without opening sealed provenance, which is forbidden. Overlap is not
  asserted absent.
- **Predicate-level, not full product-pipeline, coverage.** The host loads the
  pack and runs its predicates. It does not reproduce the product's registry phase
  selection, decoding, quoted-text processing, posture or surrounding policy
  pipeline (prereg §2.1). The guard runs the product's golden tests, which cover
  more than the predicates, but only on the offline copy.
- **A configuration artifact**, not the LLM prompt/context tier, and **not
  transfer** of an unchanged artifact. No prompt/context, tool-routing,
  product-security or product-acceptance claim is made.
- **`evaluator_hash` and `code_hash` were chosen by the run worker.** The brief did
  not specify them. The worker bound them to existing frozen identities:
  `evaluator_hash` = sha256 of `execution-manifest.json` (`66a08dc2…08b9`) and
  `code_hash` = the kernel sources aggregate (`897fd9fe…edbf`). **They went
  unused.** They only bind an approval in `accept`, which did not run.
- Label caveats carried from the provenance assessment (R-196): Arcanum includes
  plain interrogative examples in the Intents pillar, which are kept as attack
  labels, not relabelled. The deepset card's licence fields conflict (top-level
  Apache-2.0 vs nested CC-BY-4.0). The more restrictive reading, attribution
  required, is followed below.
- **Staged skips.** The 4 Zh `stagedGoldenCases` skips are staged `assumeTrue`
  checks (pending P1/P2). The block-eligible Chinese subset is empty at this stage;
  nothing here demonstrates blocking capability.

### Exposure

| Read | Count | Notes |
|---|---|---|
| Champion dev evaluations of the 353 dev items | 6 | 2 reproductions on the pre-fix host, 3 at the re-freeze (A1, A2, B2), 1 in the run |
| Candidate dev evaluations | 0 | The proposal was blocked before scoring; the probe was evaluated with zero items |
| Guard executions (real golden classes) | 10, as read from the receipts | First pre-run, two classes: champion via host 1, champion directly 2, probe 1. Re-freeze, three classes: champion 2, probe 2. Run: champion 1, proposal 1. Calls answered from the content_id cache are not counted. The first pre-run receipt does not state whether its host champion guard run and its first reproduction were the same call, so this count may be one too high |
| Adjudication / holdout evaluations | 0 / 0 | Not in the host cases file |
| Proposal author's data access | None | Champion and loader/rule/phase sources only, as above |
| Workers' data reads | Counts, hashes and method names only | Fixture text, golden text and payload strings were not opened or reported |

Dev was already adaptive before this run because the sources are public research material. Prior exposure outside the documented H1a receipts is unknown, not zero. The counts above cover the recorded H1a reproductions, campaign and guard calls; they are not a complete lifetime exposure count. These reads add exposure but do not change the data's non-independent status.

## Attribution and changes (CC-BY-4.0 §3(a)(1))

No payload text is published here.

Source and license links:
- [Arcanum taxonomy at the frozen revision](https://github.com/Arcanum-Sec/arc_pi_taxonomy/tree/e02cf5b6e202f195c6b6c01484e99519f797acc6), [pinned license](https://github.com/Arcanum-Sec/arc_pi_taxonomy/blob/e02cf5b6e202f195c6b6c01484e99519f797acc6/LICENSE.md), and [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en#s3a).
- [Akto at the frozen revision](https://github.com/akto-api-security/akto/tree/afa02a80a1c10420301b1d7fb4900b158f316be8), with its [pinned MIT notice](https://github.com/akto-api-security/akto/blob/afa02a80a1c10420301b1d7fb4900b158f316be8/LICENSE.md).
- [deepset/prompt-injections at the frozen revision](https://huggingface.co/datasets/deepset/prompt-injections/tree/4f61ecb038e9c3fb77e21034b22511b523772cdd), with the license-field conflict disclosed below.

- **Arcanum PI taxonomy** (CC-BY-4.0, Arcanum-Sec, `e02cf5b6…`; `LICENSE.md`
  `92d542f8…efa`): every `examples` string in the intents, techniques, evasions
  and inputs pillars, **unchanged**. `taxonomy.js` and `ideas` were not used.
- **Akto** (MIT, akto-api-security, `afa02a80…`): the 8 retained files. Each file's
  `changed_key` was YAML-parsed and stripped, `${filePaths}` was replaced by the
  `wordLists` value, and the result was URL-decoded with `urllib.parse.unquote`.
  The 8 files whose payloads cite an unlicensed second-hand source were excluded.
  Akto's MIT notice is retained with the private data.
- **deepset/prompt-injections** (`4f61ecb0…`; top-level licence field Apache-2.0,
  nested field CC-BY-4.0, conflict recorded): `text` where `label == 0`,
  **unchanged**.
- Then: exact-string deduplication (no removals), sha256 IDs, and the seeded carve above.

## Cost

| Item | Value |
|---|---|
| Model solver calls | **0** |
| Model D2 calls | **0** (3 deterministic D2 records) |
| CLI spend reading | 0 (`spend_cap` 0; fixed zero spend reading) |
| Proposal authoring | **One data-blind authoring job**, one proposal. Model requests, tokens and cost are **unmeasured**; the CLI's zero spend does not cover them |
| Run wall time | About 12 s from configuration write to campaign end (file mtimes: 21:11:40 to 21:11:52 CST, 2026-11-06), including both guard runs. Proposal guard surefire class times: 0.68 s, 1.00 s, 0.59 s |
| Pre-run builds, reproductions and reviews | Not metered |

No billed or modelled cost is reported.

## Sources

Run-relative paths under the private run root. None of these files is published.

- `h1a-run-1/RUN.md`, `run.sh`, `run-campaign.stdout.json`, `run-campaign.stderr.txt`,
  `run-campaign.exit`, `hashes-before.txt`, `hashes-after.txt`, `guard-strays.txt`,
  `offline-classes-manifest-restored.txt`
- `h1a-run-1/host/host-evidence.jsonl`, `host/host.properties`
- `h1a-run-1/store/campaign-h1a-run-1.json`, `outcomes.jsonl`, `decisions.jsonl`,
  `public/candidates.jsonl`, `public/results.jsonl`
- `h1a-run-1/surefire-proposal/` (counts and method names only)
- `h1a-build/prerun/RESULTS.md`, `execution-manifest.json`,
  `golden-resource-identity.json`, `carve-validation.json`, `counts.json`
- The private data-provenance assessment for H1a
- Decision records R-193 to R-220

## Not covered

- No improvement claim, quality comparison, paired delta or per-item flips: the
  only candidate was ineligible.
- No adjudication retention, approval or record-only apply: `accept` was not run.
- No holdout evaluation and no holdout report.
- No search-depth or optimisation-efficacy claim: one frozen proposal, no live proposer.
- No significance, power or independence claim; no sealed-set result; no product
  release or proposal to the host product's team.
