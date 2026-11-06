# H1a prereg addendum — offline rule-pack configuration experiment (issue #78)

Drafted 2026-11-06, before any H1a proposal or candidate evaluation. This is a
forward-only preregistration amendment, following COS **Transparent Changes**
(https://www.cos.io/initiatives/prereg) and the shapes of
`docs/prereg-e1c-harness-code-addendum.md` and `docs/prereg-s5c-addendum.md`.
Earlier registrations and the kernel are untouched.

**Status: DRAFT / EXECUTION HELD.** This document freezes the choices supported
below; the open STOPs are not invented defaults or permission to generate a
candidate. Scope permission was recorded separately. The accountable lead must
freeze the missing identities, data partition and candidate-bound guard contract,
then obtain the required independent re-check before candidate generation.
Private scope/provenance dispositions remain outside the published tree; this
file refers only to **the host product** and contains no fixture or payload text.

## 1. Why, scope and exclusions

H1a tests the frozen kernel against a copy of a real built-in configuration
artifact, with a deterministic matcher. It is an **offline, non-grant,
configuration-artifact integration**, not the LLM prompt/context tier, not
unchanged-artifact transfer and not a product deployment. Prompt/context and tool
routing remain untested. Precedent: `docs/design.md` §4.1 supplies the non-Python
host seam; RRSI §3.1 treats configuration as a harness component
(https://arxiv.org/abs/2609.24972); the scope disposition authorizes copies only.

- Exactly one copied built-in rule pack; no tenant rules or customer traffic.
- No host-product code or policy change, activation, deployment or publication.
- `apply` records the approved content ID only. It neither replaces the champion
  nor publishes rules. This is the existing §4.1 / PR #77 record-only behavior.
- No product sealed set is opened or used. Outputs must **never be evaluated on
  any product sealed set or proposed to the product team without a separate
  disposition**. A kernel `updated` record is not such a disposition.
- Raw public payloads, private source/classes, golden resources, run configuration
  and evidence stay outside the published repository. No grant scope is amended.

## 2. Artifact, proposal source and unchanged execution

### 2.1 Artifact

| Field | Frozen value and precedent |
|---|---|
| Component key | `rules.yml`, the default in `examples/firewall-host/README.md` and PR #77 |
| Component registry | `["c1"]`, the one-component §4.1 quickstart convention |
| Media | `application/yaml`, PR #77 `GET /artifact` |
| Champion | Exact startup bytes of the copied built-in pack; raw SHA-256 and reconstructed `candidate.content_id` both required |
| Candidate | Complete replacement bytes for that one component; no patch format, normalization or reserialization |

The host calls the existing static `load(InputStream, List)` through private-API
reflection, with `ByteArrayInputStream` over the **exact decoded candidate bytes**.
It uses the existing matcher predicates and native `java.util.regex.Pattern`
compilation / `find()` semantics, **not** a tenant RE2/J path. Reflection precedent:
the host team's `PolicySnapshotRuntimeFirewallViewTest.java:478–483`, already
adopted in PR #77. The probe does not reproduce registry phase selection,
decoding, quoted-text processing, posture or the surrounding policy pipeline.

### 2.2 Proposal source: fixed, data-blind authoring; no live proposer

Choose the smaller existing option: **one complete proposal, authored before any
dev data is read, then frozen in the CLI `proposals` array**. Precedent:
`docs/quickstart.md:34–42` supplies one prewritten candidate;
`tests/test_cli.py:94–95` exercises it; `src/rsi_kernel/cli.py:208–226` decodes
host-supplied frozen candidates and consumes that queue. One proposal is a
feasibility probe, not a search-depth or optimization-efficacy claim. The inherited
`max_attempts=3` does not require three proposals or authorize replacing one.

**Author:** a separate bounded writer assigned the role `proposal-author` by the
accountable lead, not this preregistration/guard-source reader. The author receives
only the copied champion and the frozen task/format instructions. It must never
see dev item text, evaluation outcomes, adjudication/holdout items, golden text,
expected outputs or failure hints. Its workspace must not expose the source corpus,
private evidence archive or guard resources. It supplies the complete YAML bytes
once, before evaluation; the lead records author identity, actual call accounting,
freeze time, file SHA-256, content ID and parent champion ID. No post-score repair
or replenishment is allowed. Existing isolation precedent:
`docs/prereg-gdpevo-pilot.md`, **Proposer isolation**; this selection tightens that
existing input boundary to champion-only rather than adding a live proposer.

**STOP H1A-PROPOSAL-FREEZE:** the role choice is fixed, but a concrete author,
access-boundary evidence and proposal bytes do not yet exist. Assign and attest a
data-blind writer only after the preregistration re-check releases generation.
An author already exposed to restricted items or golden text is not eligible.
This document does not assert that source readers have become data-blind.

The alternative, a live or evaluation-fed offline proposer, is **not selected**:
the governing disposition requires a separate proposer/isolation/metering spec.
The existing CLI is not adapted into an iterative model proposer.

### 2.3 Execution and bounds

Use unchanged `rsi-kernel run-campaign`, `accept`, and `status` with `--config
config/campaign.json`, exactly `docs/design.md` §4.1. Deterministic D2 and
`spend=lambda: 0` are fixed in `src/rsi_kernel/cli.py:208–226`. Proposal generation
is outside that CLI and is not falsely covered by its zero spend reading.

- `runs=1`, conditional on §6; precedent `docs/quickstart.md:40`.
- `max_attempts=3`, inherited from `docs/prereg-gdpevo-pilot.md`, **Budget caps**.
  No paper-derived replacement, rescue retry or repeated search is introduced.
- `spend_cap=0` for this model-free CLI, consistent with its fixed spend reading;
  it is not a limit or measurement for the separate authoring job.
- `eval_cap`: **STOP H1A-EVAL-CAP** until the dev count is frozen. Derive the cap
  by the existing prereg **Budget caps** accounting: champion dev evaluations
  plus the registered candidate evaluations, each times `runs`. Do not copy a
  solver-specific cap to an unmeasured corpus.

`accept` evaluates adjudication only and requires matching candidate/evaluator/
data/code hashes before record-only apply. It has **no holdout evaluation or
holdout report** (`cli.py:247–255`). Carving a holdout does not exercise it. No
additional holdout driver, prompt adapter or kernel change is authorized here.

## 3. Public source identities, labels and carve STOP

### 3.1 Eligible inputs

The pinned provenance assessment is a private input to this registration. The
following are public source identities, not permission to publish their payloads.

| Source | Revision | Input / SHA-256 | Role |
|---|---|---|---|
| [Arcanum taxonomy](https://github.com/Arcanum-Sec/arc_pi_taxonomy/tree/e02cf5b6e202f195c6b6c01484e99519f797acc6) | `e02cf5b6e202f195c6b6c01484e99519f797acc6` | `docs/data/taxonomy.json`; `fc26b73a909faf73087dac4829cbd2118eb3f4505db6729dc048bc6fb3e1daa7` | 775 attack examples; structural taxonomy labels; no benign controls |
| [Akto source files](https://github.com/akto-api-security/akto/tree/afa02a80a1c10420301b1d7fb4900b158f316be8/apps/dashboard/src/main/resources/inbuilt_llm_test_yaml_files) | `afa02a80a1c10420301b1d7fb4900b158f316be8` | The 16 distinct selected files below, subject to the mandatory exclusion | Attack templates, not response-validator outcomes |
| [deepset/prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections/tree/4f61ecb038e9c3fb77e21034b22511b523772cdd) | `4f61ecb038e9c3fb77e21034b22511b523772cdd` | `data/train-00000-of-00001-9564e8b05b4757ab.parquet`; `2e10bc7ab30f542c97e4e83e2a5683000b5057d25ec10908784c631d44124c04` | `label=0` only: 343 benign controls |
| Same pinned deepset source | Same | `data/test-00000-of-00001-701d16158af87368.parquet`; `39ac797cabc157eeed58435a08593b2952bb6cb16fc394a2d383f447cc7b246e` | `label=0` only: 56 benign controls; the upstream name does not establish independence |

Arcanum `taxonomy.js` is a duplicate representation and is excluded. `ideas` are
not examples. Primary labels retain all 775 examples, including the contextual
reconnaissance labels in the Intents pillar; their ambiguity is disclosed, not
relabelled after scores. Akto's large near-duplicate malware-template family is
not added. Normalization/extraction steps and cross-source duplicate handling
must be frozen in the data manifest before constructing any item.

### 3.2 Selected Akto manifest and the exclusion arithmetic

The provenance table calls its selection 12 files but actually lists **16**.
Use the enumerated manifest, not the heading. Exclude all **9** files in the full
source inventory that cite the unlicensed second-hand payload source. **Eight**
of those nine are in this 16-file selection, leaving **8 eligible selected files**,
not 16 or 7. The ninth excluded file, `InsecureOutputHandling#2.yml`, was never in
the selection. This follows the recorded licensing exclusion, not a new sampler.
Reference URLs and file hashes were checked without printing payload text.

| Selected filename | SHA-256 | Disposition |
|---|---|---|
| `PromptInjectionBasic.yml` | `9f58c151d951d35280214c6785db8fbb601ce8157f52c84664a7292d32ac5deb` | EXCLUDE |
| `PromptInjectionBasicHello.yml` | `a6a369d4d9d5022c69b152428f58e8060f2eb73ad55a7254011a1a15b4cbfe30` | EXCLUDE |
| `PromptInjectionBasicV2.yml` | `3f53cccc405e3c39cb887445e0187f2b3362e386bafb2d8cd4df86910eab5d07` | EXCLUDE |
| `PromptInjectionSTANTest.yml` | `c6a3b70d66fe145f248f9a2644a9141f4be2490d6f89f3c138793ae843c797a2` | RETAIN |
| `PromptInjectionXSSTest.yml` | `426de66634b42f5b73690082c8552c2c57dbe6856ebef9bfe17c13d9dccdc136` | EXCLUDE |
| `PromptLeakInjection.yml` | `7e07ee0ee584b8467c7ea82b20c6f787509594711f1b9c6333f8517df16cd890` | EXCLUDE |
| `SensitiveDataExposurePassword.yml` | `b035752111ba6b2a087e75411251236fd1fbda3aa7418f862395d659d223d825` | EXCLUDE |
| `LLMEncoding#1.yml` | `7a821cd282b89b6b617913abdeeb8f846cb0d446c91d48b273b528794e109100` | RETAIN |
| `LLMEncoding#2.yml` | `10cac405c1dfccfe53d74177cf207b17d3a48010c04e6f2bd7d38be67e41dc86` | RETAIN |
| `LLMEncoding#4.yml` | `709285dc4eddb595a7f9ef39b5f285916a0f6d6dc7500154e57ee6b66febae7a` | RETAIN |
| `LLMEncoding#5.yml` | `2582b074d341d9fd81faf592ddb8039171e5406e420dca32f564c1c518d491e0` | RETAIN |
| `LLMObfuscation.yml` | `df8daccea5f3a382c5d490d537035e5d55d9655b8061ca0059d248e794e35db0` | EXCLUDE |
| `LLMInsecureOutput#1.yml` | `f430d7e2753749c06eec46155a8ab4a562bc41ee5e8a9b0d0058de7244101a75` | RETAIN |
| `LLMInsecureOutput#2.yml` | `bc5f23a96a2cc41cea3f434e7d9151cc8a263cf750f7cb3cd999a64a66669931` | RETAIN |
| `LLMInsecureOutput#3.yml` | `db0774ee47fe9fdbfd62b06ff5aa51632d5c2706f4989b74cdfc1bed27339f3b` | RETAIN |
| `InsecureOutputHandling#1.yml` | `c05fc5e0b152d8a671d45b904c533ba6c054859a643cc7a6d7d7679d3c670204` | EXCLUDE |

### 3.3 Existing carve, not an invented seeded splitter

Use the existing kernel split authority, `src/rsi_kernel/splits.py:70–88`
(`load_splits`): explicit item IDs, disjoint splits, validated purposes, and
`selection_eligible=true` for dev only. Its precedent is Proteus split-purpose
validation, cited in `docs/design.md` §4 and `splits.py`.

The only existing function named `carve_splits` is
`src/rsi_kernel/adapters/gdpevo/tasks.py:47–62`. It takes validated `FrozenTask`
objects and an explicit `dev_tasks_by_group` map: listed train tasks become dev,
remaining train tasks adjudication, and test tasks holdout. **It accepts no seed,
ratio or counts.** `FrozenTask` also binds a benchmark input and official grader
wrapper; fabricating those for public prompt strings would invent an adapter.
`docs/prereg-gdpevo-pilot.md:37–46` explicitly records its no-seed carving map as
a named local exception, not a portable public-corpus sampling rule.

**STOP H1A-CARVE:** no supported fixed seed or paired public-corpus counts were
found. Accordingly these are explicitly **UNFROZEN**, not zero or implicit:

| Split | Attack count | Paired benign count | Seed / explicit membership |
|---|---|---|---|
| dev | UNFROZEN | UNFROZEN | UNFROZEN |
| adjudication | UNFROZEN | UNFROZEN | UNFROZEN |
| holdout | UNFROZEN | UNFROZEN | UNFROZEN |

No arbitrary seed, ratio, benign reuse or content-derived pairing is supplied.
Before execution the lead must provide documented sampling precedent, or freeze
a **NAMED LOCAL EXCEPTION H1A-PUBLIC-CARVE** with a pre-measurement validation
rule, seed, exact counts, IDs, extraction/deduplication rule and hashes, then load
that explicit map through the existing kernel authority. This draft neither
implements nor validates that exception. The 399 raw benign rows do not establish
that all attack examples can be paired without reuse. Adjudication/holdout
provenance and access boundaries require their own frozen disposition.

All these sources are public, writer-visible research material and therefore
**ADAPTIVE dev material**. Any subsets called adjudication or holdout remain
**non-independent**, even if a particular proposal author cannot access them.
Record actual prior exposure and each reproduce/campaign/adjudication read;
unknown exposure is disclosed as unknown, never assumed zero. No sealed set is
used or created. Source-level overlap with the host product's sealed sets
**cannot be determined** without forbidden provenance access; it is not asserted
absent. Split carving does not repair this limitation.

### 3.4 Attribution and changes

Arcanum is CC-BY-4.0. Preserve credit and source/license links, and **indicate
changes** in the data manifest and any permitted write-up: extraction, selection,
URL decoding or other normalization must be named; unchanged strings must be
identified as unchanged. Precedent: [CC-BY-4.0 §3(a)(1)(A)–(B)]
(https://creativecommons.org/licenses/by/4.0/legalcode.en#s3a).
Arcanum `LICENSE.md` SHA-256:
`92d542f8895f021acab468960fe66d0ec99911dd48b3a7eddee9ea511370cefa`.

Retain Akto's MIT copyright and permission notice with eligible material
([pinned license](https://github.com/akto-api-security/akto/blob/afa02a80a1c10420301b1d7fb4900b158f316be8/LICENSE.md)).
Its MIT file does not cure an unlicensed upstream payload, hence the exclusion.
The deepset card conflicts between top-level Apache-2.0 and nested CC-BY-4.0;
record that conflict and the top-level field relied on, preserve attribution and
indicate changes rather than claiming an unambiguous license. No payload
publication is authorized by this registration.

## 4. Metric, selection and hard ineligibility

For each requested item, `score ∈ {0,1}`:

- attack / `must_match`: 1 if any loaded pack predicate matches, otherwise 0;
- benign / `must_not_match`: 1 if no predicate matches, otherwise 0.

Use the **unweighted item mean** and paired candidate-minus-champion mean delta;
no class/family/source weighting or new threshold. Precedent: PR #77 host
`correct` / `results`; `docs/design.md` §4.1 and the prereg zero-margin rule.
On complete valid results, `mean_delta >= 0`: **ties pass**, for both dev selection
and adjudication retention. No holdout non-regression gate is added.

Schema/load/compile or golden guard failure is instead **HTTP 422 ineligible**,
without fabricated scores. It cannot pass a zero-score-champion tie: the
unchanged `HttpHost` exception reaches `loop.py:181–183` before comparison.
Factory/reflection/I/O and predicate-execution failures are **500 operational**;
malformed transport/identity requests retain the host's 400 behavior. Evidence
classifications follow PR #77 and the [SWE-bench evaluation harness]
(https://www.swebench.com/SWE-bench/guides/evaluation/), not a compensatory score.
The CLI records candidate non-2xx failures as `dev_failure` and may continue its
fixed queue; it does **not** distinguish 422 from 500 in that outcome. Reports
must read the host evidence log. No CLI stop semantics are invented.

## 5. Exact team golden selectors, dependencies and guard STOP

The guard contract is the existing team assertions **unchanged**, not a new
union-of-hits check. Source-only inventory below was read at team source commit
`83f5e8ebb0a23621bf77ba61f11c1a161275681d`. No fixture content was opened.
Only the previously disposed counts are carried: 62 active rules (35 regex,
27 function), 37 English and 17 Chinese case groups, 40 Chinese block-eligibility
negatives and 10 known gaps. These are not assertion, sample, pass or skip counts.

Use the team Surefire class-name selectors, without private package names:
`RuntimeFirewallGoldenFixtureTest,RuntimeFirewallZhGoldenFixtureTest,RuntimeFirewallGoldenInventoryTest`.
The first two are the documented golden classes; the third is the existing
negative-control companion for inventory coverage. Preserve each method and its
assertions. Do not run a sealed-data harness through that companion.

### 5.1 English / shared golden

`RuntimeFirewallGoldenFixtureTest.java` (source SHA-256
`2d07eee5e7a18559acebbbefcb214eb52eabfa90e7950dd7e7737d50b818628d`):

- `everyRegistryRulePassesTheSharedMustMatchAndMustNotMatchCases` (:20–64):
  fixture-version assertions, exact keyword IDs, nonempty positive/negative
  keyword lists, **phase-specific rule-ID** hits/non-hits, optional repeat cases,
  and exact registry coverage excluding the existing Chinese/audit/illegal-site
  partitions. Preserve the missing-repeat-field no-op; do not count it as a test.
- `illegalSitePartitionHasExactCoverageAndDestinationBoundaries` (:67–78):
  phase-specific hits/non-hits and exact illegal-site partition IDs.
- `identityHashesMatchRegistry` (:81–93): nonempty identity array and exact
  `matcherIdentity` / `ruleVersionHash` equality to the fixture.

Resources, relative to the team's test resource root:
`firewall/runtime-firewall-golden-v1.json`,
`firewall/runtime-firewall-keyword-v1.json`,
`firewall/runtime-firewall-illegal-sites-v1.json`, and the Chinese inventory below.
Runtime dependencies: registry, phase-aware matcher, rule identity methods,
Jackson, JUnit 5 and AssertJ; preserve the existing built-in pack and function
matcher dependencies as loaded, not invented substitutions.

### 5.2 Chinese golden, identities and staged skips

`RuntimeFirewallZhGoldenFixtureTest.java` (source SHA-256
`349b06de5dae918f6a520ff78e2eead1de0e381f6a5292a2ff7a563343bba47c`):

- `exactInventoryMetadataAndCombinedGoldenCoverage` (:50–76): ordered
  `SPEC_IDS`, disjoint partitions, complete combined registry coverage, all
  Chinese rules `MONITOR`, `TEXT_AND_DECODED`, null posture lock, exact severity,
  category and `regexp:<expression>/<flags>` matcher identity.
- `stagedGoldenCases` (:79–101): validated sample metadata and exact target
  rule-ID hits/non-hits. Positive views `raw` / `canonical` execute; positives
  `decoded` / `H` are **PENDING until P1**, and `S` **PENDING until P2**, using
  `assumeTrue` (:89–90). Negative checks retain their existing execution path.
  Preserve these skips exactly; no skip is a pass. Counts are read from actual
  execution records, not inferred by opening fixtures.
- `blockEligibilityNegativesHaveNoBlockZhMatch`, `knownGapsDoNotMatchAnyZhRule`:
  preserve metadata validation and existing subset/non-hit assertions. The
  block-eligible Chinese subset is empty at the current monitor-only stage;
  this is not demonstrated blocking capability.
- `wordJoinerCanonicalisationUnchanged`, `zhRulesDoNotBacktrackOnLongWhitespace`,
  `mixedLanguageRewriteMatchesUpstreamOnAllFixtures`: preserve existing
  canonicalization, correctness-timeout smoke and upstream `find()` equivalence.
  Existing timeout/sample-size values are team-test values, not H1a tuning.
- `existingRuleIdsAndHashesUnchanged` (:151–159): exact baseline identity hashes.
  `existingRulesHitSetsUnchangedOnZhNegatives` (:162–170): exact existing-rule hit
  sets, with the test's own exclusions and order.
- `zhRulesContainNoWordBoundary`, `wordBoundaryGuardRejectsLiteralRegexEscape`:
  preserve both the constraint and its existing assertion-failure control.

Resources: `firewall/runtime-firewall-zh-golden-v1.json`,
`firewall/runtime-firewall-zh-baseline-v1.json`, shared English and keyword files.
Dependencies also include JUnit dynamic tests/assumptions/timeouts, native Java
regex and the same registry/matcher path. Do not expose test-source literal
examples or assertion messages to the proposal author.

### 5.3 Inventory negative-control companion

`RuntimeFirewallGoldenInventoryTest.java` (source SHA-256
`ea57a195c05157a4fb84fadad1c1c07e9413c72b11931665d7e0a464ed74a533`)
retains all six methods: `unfixturedRegistryRuleProducesOneFailure`,
`missingChineseRuleProducesOneFailure`, `exactCombinedInventoryProducesNoFailure`,
`missingAuditRuleProducesOneFailure`,
`overlappingAuditAndFrozenInventoriesProduceOneFailure`, and
`keywordInventoryIsRequiredAndDisjointFromFrozenGolden`.
Dependency: `RulePrecisionHarness.goldenInventoryFailures` only (:254–269), with
its exact partition/disjointness checks and English/Chinese resources. The
companion's synthetic omission controls must still fail the guard as specified.
**Do not invoke other harness entry points that read sealed collections.**

### 5.4 Hard guard applicability is an open STOP

**STOP H1A-GUARD-BINDING.** PR #77 loads exact candidate bytes but retains only
`Predicate<String>` objects. Its guard cases have `text` / `expectation` only and
ask whether **any** predicate matches. It cannot represent rule IDs, phases,
identity equality, metadata, canonicalization, dynamic assumptions, timeout smoke
or baseline hit sets. The unchanged team tests instead use a static classpath
registry. Running those tests on the original champion does not prove that the
candidate passed them. Flattening their fixtures would weaken their meaning.

No candidate-bound execution of those exact assertions, returning 422 on guard
failure, has been established. Keep generation/evaluation held until the lead
freezes and independently re-checks that bridge with real evidence. Do not edit
team code, relax identity assertions, return all-zero quality scores, remove
staged checks or claim the synthetic guard proves the real guard. If the exact
identity checks make an edit ineligible, that is an eligibility result, not
permission to change the guard. A real guard failure must return **422** before
any requested score is emitted; a guard-execution infrastructure failure is 500.

## 6. Reproduce-first and ordered pre-run STOPs

PR #77 records `evidence/reproduce-1.json` and `evidence/reproduce-2.json` as
byte-identical, with SHA-256
`d4493ed6ae75afb0963825d7f3660cf50fe58ac94988d7a949f8852f75f0639e`.
The receipt identifies synthetic cases and an **empty synthetic guard**. The
recorded files were rehashed and compared during drafting; this validates that
historical receipt, **not** the real dev setup or golden guard.

`runs=1` is adopted only after a **fresh reproduce-first on the frozen real dev
cases**: same champion bytes, requested IDs/order, host, built classes and input
identities; compare raw response bytes and per-item results exactly. The two
historical reproduction outputs supply the repetition precedent, not a newly
chosen repeat count. A mismatch is STOP, not a retuning or rescue run.

After the open configuration/isolation STOPs and independent re-check are closed,
pre-run checks execute in this order, before the first candidate evaluation:

1. **Host identity.** Use a clean detached run tree at a reviewed `main` commit containing this registration, PR #77, and the separately reviewed candidate-bound guard extension described in §9. Before releasing proposal generation, freeze that commit and the actual kernel, host-source and guard-runner hashes in the run manifest. The PR #77 host-source SHA-256 `3b7e656d3d77184b820dccd4f98024c8a2302d15b451652bdf86160714930cce` identifies the historical predicate-only host, not the required extended execution host. Verify exact candidate-byte loading, media/key, unchanged CLI, and candidate-bound guard execution; any mismatch against the frozen execution manifest is STOP.
2. **Jar build identity.** Record and verify SHA-256 of the actual **built classes
   jar**, not just source HEAD, champion hash, dependency list or launcher class.
   Bind the source revision above, JDK identity and every classpath dependency.
   **STOP H1A-JAR-ID:** the classes-jar digest is not supplied by the synthetic
   reproduction receipt; compute it from `host/classes.jar` before use. A file
   path or predicted hash is not evidence.
3. **Fresh real-dev reproduce-first**, as above, before the first candidate.
4. **Guard selectors verified.** Record exact selectors, test-source/resource
   hashes, candidate binding, assertion-failure controls and executed/pass/fail/
   skip counts. Missing dependencies/selectors or an empty guard are STOP. Preserve
   staged skips, never as passes. §5.4 must already have a reviewed resolution.
5. **Data hashes verified.** Final verification of every pinned raw source,
   extraction output, case file and explicit split manifest, including label
   provenance, paired counts and isolation. A mismatch is STOP.

This order is not permission to use unverified inputs at step 3: their pinned
hashes are checked before reproduction as a prerequisite, then rechecked at the
final data step. No code, data, author boundary, seed, counts, guard or success
rule may change after the freeze without a forward-only amendment and disposition.

## 7. Reporting, exposure and evidence

Report execution status separately from quality/acceptance status:
**configuration-artifact integration demonstrated / not demonstrated**, with the
actual reason and coverage; and the exact CLI campaign/acceptance outcome. An
operational STOP is not a completed negative experiment. `updated` requires
adjudication retention and matching four-hash approval but remains record-only.
If no holdout driver ran, state **holdout not evaluated / no holdout report**.

Carry the existing per-attempt reporting shape from the E1c/S5c addenda:

- frozen champion/proposal/selected content IDs, parent IDs, raw-file hashes and
  host/classes/data/code identities;
- requested/evaluated item counts and per-item champion → candidate **flips**,
  with source/label/item IDs and split, never raw text; mean and paired delta;
- exact dev selection, adjudication retention and approval/apply outcomes;
- host `evidence.jsonl` **call counts** for `ok`, `ineligible`, `operational`,
  bound to actual content IDs and reason classes; these are not item counts.
  Reconcile them with CLI outcomes. A failed evidence append returns 500 and
  cannot log itself, so disclose any such gap from response/process records;
- separate reproduce, candidate, adjudication and guard execution/read counts;
  exact skipped checks, unresolved dependencies and the stage-limited guard;
- actual proposal-author model requests/tokens/failures, CLI solver/D2 calls and
  measured wall time, if available. Do not invent uncertainty intervals or cost.

Required limitations: **private-API reflection; residual adaptive overfitting;
non-independent public-data adjudication/holdout; sealed-set overlap that cannot
be determined; predicate-level rather than full product-pipeline coverage**.
Record actual exposure counts where known and unknown history explicitly. No
independent-confirmation, prompt/context-tier, transfer, product-security or
product-acceptance claim is supported. Outputs have never been evaluated on any
product sealed set and cannot be proposed to the product team without a separate
disposition; preserve that restriction in every downstream summary.

## 8. Cost and completion gates

**Zero model solver calls. Zero model D2 calls.** The unchanged CLI has zero spend
metering. The selected proposal source is one separate bounded-writer authoring
job; its actual model-request count, token usage and cost are **unmeasured**, not
assumed zero or covered by `spend_cap=0`. No live/evaluation-fed proposer runs.
Wall time and real-dev evaluation/build cost are **unmeasured**. Historical
synthetic checks are not a wall-time prediction. Shared resources keep the
existing four-job cap; no infrastructure limit is invented here.

Before execution: resolve H1A-CARVE / H1A-EVAL-CAP, H1A-GUARD-BINDING and concrete
author isolation; record host/jar/data identities; independent re-check; only then
release proposal generation and the ordered pre-run evidence. Any unresolved
STOP keeps the experiment held. No new implementation is part of this draft.

Publication check for this documentation change, not a real-host or golden gate:

```sh
uv run pytest -q tests/test_publication_markers.py
```

The publication guard is the existing repository check, including untracked
non-ignored files. Its result must be recorded from this draft's actual run; it
does not stand in for independent review or the H1a execution gates.

## 9. Lead disposition of the open STOPs (2026-11-06)

**H1A-CARVE: design disposition selected as NAMED LOCAL EXCEPTION H1A-PUBLIC-CARVE; execution STOP remains open.** The exception covers reuse of the 30/20/50 proportions for these public pools, the date-derived seed, and the floor/remainder rounding convention. Before proposal generation, freeze the extraction procedure, canonical input ordering, chosen shuffle implementation and version, exact three-way allocation procedure, counts, membership map and hashes. Validate before evaluation that every eligible deduplicated item is assigned exactly once, split memberships are disjoint, class counts satisfy the frozen floor/remainder rule, and regeneration from the same pinned inputs reproduces the identical membership map. Record the validation result and obtain the independent re-check; until then H1A-CARVE and H1A-EVAL-CAP remain open.
- Method: a seeded uniform random split of each pool, done separately for the attack pool (eligible Arcanum examples plus eligible Akto files, deduplicated by exact string) and the benign pool (deepset label 0, deduplicated by exact string). This is the standard practice: scikit-learn `train_test_split(random_state=…)` and Hugging Face `datasets.Dataset.train_test_split(seed=…)` both document a fixed integer seed for reproducible splits.
- Proportions: dev / adjudication / holdout = 30 / 20 / 50. This is the in-repo GDPevo carve ratio of 3 / 2 / 5 tasks per group (`docs/prereg-gdpevo-pilot.md:37–46`). It is reused as a precedent, not presented as a public standard.
- Seed: `20261106`, the freeze date. Any fixed integer is equally valid; the value is the named local exception, recorded before any data is read for evaluation.
- Rounding: floor for dev and adjudication; holdout takes the remainder.
- Output: an explicit membership map (item id → split) plus per-item sha256, frozen and hashed, then loaded through the existing kernel authority (`src/rsi_kernel/splits.py` `load_splits`). No new carving function is added to the kernel.
- Classes are not paired 1:1. The benign pool is smaller than the attack pool, so the per-class means and counts are reported next to the unweighted mean. No content-derived pairing.
- `eval_cap` follows mechanically from the frozen dev count under the existing **Budget caps** accounting (champion dev + registered candidate evaluations, × `runs`).

**H1A-GUARD-BINDING: design disposition selected; execution STOP remains open.** Run the team's existing tests against the candidate in an offline copy. Binding is resolved only after the separately reviewed host extension proves that those tests load the exact candidate bytes, preserve the existing selectors/assertions/skips, and return 422 before scoring on guard failure, including the zero-score-champion counterexample.
- The hard guard runs the host product's existing golden test classes, unchanged and with their exact selectors, against an offline copy. In that copy the candidate's exact bytes replace the built-in rules resource. Identity, phase and staged-skip assertions are therefore preserved by construction.
- Precedent: the SWE-bench harness evaluates a patch by running the repository's own existing tests (PASS_TO_PASS) on the patched tree (`swebench/harness/run_evaluation.py`, https://github.com/SWE-bench/SWE-bench).
- Outcomes: test failure → 422 (ineligible); infrastructure failure (build tool, I/O) → 500 (operational). Results are cached by content_id so each distinct candidate runs once.
- Host addition: an optional configured guard command plus a resource path, tracked as a separate issue. The team's checkout is never modified. Skipped tests are reported as skipped, never as passed.

**H1A-PROPOSAL-FREEZE: resolved procedurally.** After the independent re-check releases generation, the lead assigns one fresh worker that has seen no H1a dev, adjudication or holdout items, no golden text and no fixture contents. Its only input is the champion pack. It writes exactly one proposal. The proposal bytes are hashed and frozen before the first evaluation, and the worker's brief is retained as the access-boundary attestation.

**Remaining pre-run STOPs (unchanged, execution order):**
1. Host identity.
2. Classes-jar build identity.
3. Data hashes and the frozen membership map.
4. Guard command verified: the unchanged champion passes the real guard, and a known-bad synthetic candidate fails it with 422.
5. Fresh reproduce-first on the frozen dev items.
6. Proposal frozen.
