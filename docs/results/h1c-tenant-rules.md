# H1c: tenant-layer rule artifact

This report covers H1c under `docs/prereg-h1c-tenant-rules-addendum.md` (the
**H1c prereg**, issue #100) and `docs/prereg-h1c-amendment-1.md` (**amendment 1**).
Amendment 1 §6 requires one report for both runs. As in H1b, only the differences
from `docs/results/h1a-rule-pack.md` and `docs/results/h1b-rule-pack.md` are stated.
Host, data pins, carve, metric, bounds and limitations are adopted from those
reports by reference. The artifact is one tenant rule list (`c1`) for the host
product's documented tenant rule layer; the champion is the empty list. Tier:
configuration-artifact integration; prompt/context remains untested.

Status (H1a prereg §7, reported separately):

- **Execution: completed, no operational STOP**, in both runs.
- **Run 1: proposal ineligible.** The host returned 422 `TenantParseEmpty` before
  scoring; `no_improvement`. The cause is the lead's author brief, which omitted the
  rule key layout. This is a disclosed lead deviation, not evidence about the
  quality of tenant rules.
- **Run 2: proposal eligible, selected on an exact dev tie.** Both arms scored
  attack 15/234 and benign 119/119, mean delta 0.0, 0 flips. Selected under the
  preregistered zero-margin rule (ties pass).
- **Accept: exact adjudication tie, retained.** Both arms scored attack 13/156 and
  benign 79/79, 0 flips. Zero-margin retention passed; outcome `updated`
  (record-only; no snapshot publication; monitor posture not exercised).
- **Zero measured improvement on dev and on adjudication.** This is a retained
  tie, not an improvement.
- **Holdout not evaluated / no holdout report.**

## Order of events

The order followed the release records.

| Step | Record |
|---|---|
| Feasibility on the offline copy, public APIs only (synthetic probes) | R-253 |
| H1c prereg merged | `1dca137` (#102), R-257 |
| Host tenant mode merged after two security fixes (below) | `881f6d3` (#103), R-265 |
| Pre-generation checks (a)–(e): ALL-PASS | R-267 (identity count corrected to 54/54 in R-268) |
| Independent release re-check (f) | GENERATION-RELEASE, R-268 |
| Run 1 author assigned, proposal frozen | R-269, R-270 |
| Run 1 | `h1c-run-1`, R-271 |
| Amendment 1 merged | `9a5fb09` (#105), R-274 |
| Independent release re-check; fresh author assigned | R-275 |
| Run 2 proposal frozen | R-276 |
| Run 2 and accept | `h1c-run-2`, R-277, R-278 |

## Host tenant mode and its security history

The host mode substitutes the candidate list into a frozen policy envelope
(`c83f39f4…`, 0444) and parses and compiles it through the product's public APIs.
Built-in rules are unchanged. Review of #103 found that candidate bytes could escape
the list slot (R-261). A containment check was added, mapped to 500
`TenantContainment`. An independent re-check then found a YAML 1.1 line-break gap
(R-265). That gap was closed by rejecting those characters before parsing. The final
fix was applied by the lead after the single re-check, as R-265 discloses.

## Pre-generation checks (H1c prereg §3)

| Check | Result |
|---|---|
| (a) Identity | 54/54 recomputed and matched: H1a kernel `83268e4` (sources `897fd9fe…`), H1c host `881f6d3` (source `d9d43022…`, classes `0f7670b7…`), offline classes `7076d7c7…` (1,593 files), built-in resource `404cd8c4…`, envelope, champion `0907b0c9…` (content_id `2a981d52…`), dev cases (353 dev ids, 0 others) |
| (b) Built-in guard at startup | Fixture 3/0/0, Zh 139 with 0 failures and 4 staged skips, Inventory 6/0/0; 0 `.guard-*` strays |
| (c) Empty-list continuity | One 353-item dev call, HTTP 200, body `717638f74dea71a8427fc10f3abd20e92289d03022673316a694e8e6ec451b54`, byte-identical to the H1b reproduction |
| (d) Candidate dependence (synthetic only) | Two synthetic cases; scores change with the candidate list (empty, two hit rules, one miss rule) |
| (e) Admission probes (synthetic only) | 31 rules, duplicate id, invalid regex, 513-code-point pattern and over-budget program: all 422. Boundary controls (30 rules, 512 code points): 200. Containment violation: 500 `TenantContainment` |

**All five 422s came through the parser-empty path.** The compiler-exception path to
422 was not exercised. The prereg §2 counts both as admission.

**Guard coverage.** The guard runs once, at startup, on the unchanged built-in
resource. It does not test candidate tenant rules. No golden non-regression claim
is made for the composed policy (H1c prereg §2).

## Proposals and authors

Pattern text is not reproduced here.

| | Run 1 | Run 2 |
|---|---|---|
| Proposal | `proposal-1.yml` sha256 `5c4322c13bda5d850dcf0f9095de2cc429843e52893f0f284c8a086c3305dc5f`, content_id `4978d75f…9b66`, 11 rules, frozen 0444 at 2026-11-07 19:08:12 CST | `proposal-2.yml` sha256 `91b47b5abada10243caf12ea551ae187c09021fcdbb5824c906073138f487464`, content_id `98deb5baa17d580c6d3e5c91ff9fd0ccee50e276c08adf6bbcf0899660770a53`, 14 rules, frozen 0444 at 2026-11-07 19:47:43 CST |
| Author | Fresh data-blind Opus (`proposal-author`); 4 tool calls by its own count; attested reads within the §4 boundary | Fresh data-blind GPT-6.1-Sol, a different author; 12 tool calls by its own count, including 1 rejected read; attested 9 allowed reads. It received the run 1 inputs plus the amendment 1 key layout, and no run 1 information |
| Parent content_id | `2a981d52d766c0fff03c41cc159be4a2ff5b6b6c670202728edb3b3cfdf0af98` | `2a981d52d766c0fff03c41cc159be4a2ff5b6b6c670202728edb3b3cfdf0af98` |
| Format | Flat `expression`/`flags` on each rule. The brief omitted the `matcher` layout, which was known from the feasibility probe (R-270) | `matcher` layout present on every rule (R-276) |

## Run-time verification

Each run used a new directory and an owned copy of the offline build. No earlier
receipt was reused.

- **Identities:** 75/75 recomputed and matched in each run (the 54 pre-generation
  checks plus run bindings and the proposal hash and mode).
- **Startup guard:** the same counts as (b) in each run; 0 strays.
- **Reproduce-first:** one empty-champion pass per run, body `717638f7…`
  byte-identical. Attack 15/234, benign 119/119, mean **0.3796**.

## Result

**Run 1** `run-campaign.stdout.json`, exit 0:

```json
{"attempts": 3, "champion_id": "2a981d52d766c0fff03c41cc159be4a2ff5b6b6c670202728edb3b3cfdf0af98", "evaluator_items_used": 706, "outcome": "no_improvement", "selected_id": null, "stop_reason": "attempts"}
```

Attempt 1 was `dev_failure`: host `ineligible`/`TenantParseEmpty`, which the frozen
host maps to 422. The CLI did not retain the raw 422 response. No proposal item was
scored. Attempts 2 and 3 were `no_candidate`. Host evidence: `ok` 2, `ineligible` 1,
`operational` 0. 353 item scores were produced, all for the champion; 706 is the
reservation, as in H1a.

**Run 2** `run-campaign.stdout.json`, exit 0:

```json
{"attempts": 3, "champion_id": "2a981d52d766c0fff03c41cc159be4a2ff5b6b6c670202728edb3b3cfdf0af98", "evaluator_items_used": 706, "outcome": "selected", "selected_id": "98deb5baa17d580c6d3e5c91ff9fd0ccee50e276c08adf6bbcf0899660770a53", "stop_reason": "attempts"}
```

| Dev (353) | Attack | Benign | Mean | Flips (gained/lost) |
|---|---|---|---|---|
| Champion (empty) | 15/234 | 119/119 | 0.3796 | |
| Proposal 2 | 15/234 | 119/119 | 0.3796 | 0/0 attack, 0/0 benign |

Attempt 1 was `dev_pass` with mean delta 0.0; attempts 2 and 3 were `no_candidate`.
Host evidence: `ok` 3, 0 ineligible, 0 operational. All 706 scores were produced.

**Accept** (`h1c-run-2/accept/`). The host was restarted with adjudication-only
cases: 235 ids (156 attack, 79 benign), 0 dev and 0 holdout ids. Only the cases path
changed in the host configuration. The startup guard passed with the same counts and
0 strays.

| Adjudication (235) | Attack | Benign | Mean | Flips (gained/lost) |
|---|---|---|---|---|
| Champion (empty) | 13/156 | 79/79 | 0.3915 | |
| Proposal 2 | 13/156 | 79/79 | 0.3915 | 0/0 attack, 0/0 benign |

Accept host evidence: 2 `ok` calls, one for champion `2a981d52…` and one for proposal `98deb5ba…`, both reason class `none`; 0 `ineligible`, 0 `operational`. These are calls, not item counts.

**Approval.** Zero-margin retention passed, and `accept` wrote an approval request
(sha256 `0a5a423e…2e04`): candidate `98deb5ba…`, code `897fd9fe…`, data `2df04406…`,
evaluator `66a08dc2…`. The lead checked these hashes against the run configuration
and the selected candidate. It then wrote `approval.json` (sha256 `5cc8f42e…b2a8`,
approver Billy) under the owner's standing grant R-248, and logged it in R-278.
`accept` returned `{"candidate_id": "98deb5ba…", "outcome": "updated"}`. The
campaign record now holds that acceptance. The accept worker stopped on a provider
error after launch; the lead completed verification (R-278).

## Interpretation

- **Demonstrated:** the integration path through the product's public tenant APIs.
  Admission rejects malformed lists before scoring, an eligible list is scored, and
  continuity with H1a is exact (`717638f7…` byte-identical).
- **Not demonstrated:** any improvement. Proposal 2 changed no item score on dev or
  adjudication. It was retained only because ties pass.
- **A plausible reason, not verified:** the run 2 author stated that it anchored
  every pattern to the start of the input. No further claim is made about why the
  effect was zero.
- Run 1 says nothing about tenant-rule quality; its proposal was never scored.

## Integrity

After each run and the accept: proposals unchanged and 0444, built-in resource
`404cd8c4…` in source and target, offline classes `7076d7c7…`, 0 strays, frozen code
trees clean. The own host was stopped by PID with SIGTERM.

## Exposure

| Read | Count |
|---|---|
| Pre-generation continuity (c) | 1 full dev read |
| Run 1 | +2 dev reads (reproduce-first, campaign champion) |
| Run 2 | +3 dev reads (reproduce-first, campaign champion, campaign candidate) |
| Accept | +2 adjudication reads (470 item exposures) |
| Holdout | 0 |
| Probes (d), (e) | Synthetic cases only |

Built-in guard executions: 2 pre-generation startups (continuity and synthetic-probe hosts), 1 in run 1, 1 in run 2, and 1 for accept: 5 total. Candidate tenant-rule guard executions: 0. Each reported suite result includes four skipped `stagedGoldenCases` invocations; these are not passes.

These add to H1a's and H1b's recorded exposure. Dev and adjudication are adaptive
data. Prior exposure outside the documented receipts is unknown, not zero. No
independence claim is made.

## Cost

Model solver calls 0. Model D2 calls 0; the recorded D2 backend and model are deterministic. Two authoring jobs: run 1 reported 4 tool calls; run 2
reported 12, including 1 rejected read. Tool calls are not model requests. Tokens
and model-request counts were not measured. Recorded wall times: run 1 directory
567 s (startup, continuity, campaign and shutdown 21 s); run 2 directory 162 s
(33 s); accept supervisor elapsed time through the pre-approval summary, 5.3 s (includes host startup, guard and scoring; excludes approval completion). Reviews are not metered.

## Sources

Private run-relative paths; none is published.

- `h1c-feasibility/run.log`
- `h1c-build/envelope.yml`, `prerun/` (`RESULTS.md`, `IDENTITIES.md`, `c/`, `d/`),
  `proposal/` (hashes and freeze times only)
- `h1c-run-1/` and `h1c-run-2/` (`RUN.txt`, `IDENTITIES.txt`,
  `run-campaign.stdout.json`, `score-summary.json`, `host/`, `store/`, `post-run.json`)
- `h1c-run-2/accept/` (`score-summary.json`, `cases-identity.json`,
  `host-evidence.jsonl`, `startup-guard.json`, `host.properties.diff.txt`),
  `store/approval-request.json`, `store/approval.json`
- Decision records R-246 to R-280

## Not covered

- No improvement claim on any split, and no significance or power claim.
- No holdout evaluation or holdout report, and no sealed-set result.
- No product release, activation or snapshot publication. Nothing has been
  proposed to the host product's team. These outputs have never been evaluated on
  any product sealed set and cannot be proposed to the host product's team without
  a separate disposition.
- No golden non-regression claim for the composed policy, and the compiler-exception
  admission path was not exercised.
