# H1c prereg addendum — tenant-layer rule artifact (issue #100)

Forward-only amendment to `docs/prereg-h1a-rule-pack-addendum.md` (H1a), drafted
2026-11-07 before H1c proposal generation or evaluation. As in
`docs/prereg-h1b-rule-pack-addendum.md` (H1b), only changes are stated; everything
else is adopted by reference. Earlier registrations, H1a/H1b records and the kernel
are untouched.

**Status: DRAFT / EXECUTION HELD.** This document does not release generation or
evaluation. Only **the host product** is named; no data or golden text is included.

## 1. Why

H1a's additions-only proposal failed the frozen inventory/coverage checks. H1b's
tested pattern edit failed identity/hash and hit-set checks
(`docs/results/h1b-rule-pack.md`, “Interpretation”). These two rejected proposals
do not establish that every built-in-pack edit is impossible.

H1c instead targets the product's documented customer path for additional rules:
the tenant rule layer (the host product's tenant-rule design and testing handover;
exact file and line references are kept in the private decision record, not in this
published repository).
[Amazon Macie custom data identifiers](https://docs.aws.amazon.com/macie/latest/user/custom-data-identifiers.html) are only an analogous product precedent.
Scope R-193 is extended by R-248 to a tenant-layer `custom_rules` artifact on the
same offline copy: non-grant, offline, record-only. There is no host-product code
or policy change, activation or publication.

## 2. What changes: the artifact

The component is **one candidate tenant rule list (`c1`)**; the champion is the
**empty list**. The list is placed in a **frozen policy envelope**, then parsed and
compiled as a whole section through the product's public APIs, driven by the host's
tenant-rule mode (#101). Built-in rules are unchanged. For every item, evaluation
uses the unchanged built-in predicates plus the compiled tenant-rule predicates.
H1a's metric applies to that combined set: attack scores 1 if any predicate matches;
benign scores 1 if none matches.

**Admission (422).** A parse-empty result or a documented admission failure
(rule count, duplicate id, unsupported syntax, pattern length, compiled program
size) is mapped to 422 and the proposal is inadmissible. It is reported, not evaluated,
regenerated or repaired. Any other error is 500 operational, as in H1a: an operational failure, not a quality result. Claims cover
compile/program-size constraints and predicate-level execution only, not runtime
budget enforcement. Feasibility was shown on the offline copy with public access
only (scope: parse, whole-list compile, predicate).

**Guard coverage.** The unchanged golden suite is a built-in-registry regression
check only. It runs once, on the unchanged built-in resource, and does not test
candidate tenant rules. **No golden non-regression claim is made for the composed
policy.** Candidate admission and paired dev evaluation are separate checks.

**Tier label:** configuration-artifact integration; prompt/context remains untested.

## 3. Pre-generation STOPs

In order, each a STOP; any failure keeps execution held:

- **(a) Identity.** Host and build identity re-verified against the frozen H1a
  identities, plus the new host commit carrying the tenant-rule mode.
- **(b) Built-in guard.** Startup built-in guard pass on the unchanged resource.
- **(c) Empty-list continuity.** Ordered per-item response bytes equal H1a's
  reproduction (`717638f7…`, H1a report) under identical predicates, inputs, metric
  and serialization. This verifies only that H1a's evaluator is preserved.
- **(d) Candidate dependence.** Synthetic non-empty positive/negative probes show
  candidate-dependent loading and scoring.
- **(e) Admission probes.** Over-limit count, duplicate id, invalid regex, pattern
  length and program size each return 422.
- **(f) Release.** An independent release re-check record releases generation.

Only then may the author be assigned.

## 4. Author boundary

As H1b §3, with this input set: the champion (empty list), the frozen envelope, the
product's tenant-rule limits, and the tenant validator, compiler and regex source
files. The author is told the limits from source: 30 rules, 512 code points per
pattern, and the compiled program-size budget. No data, outcomes, tests, fixtures,
golden text, or H1a/H1b proposals or results. **One** fresh data-blind author and
**one** proposal, frozen before evaluation; no repair, replacement or
replenishment.

## 5. Unchanged protocol

Adopt H1a and H1b §4 by reference: carve and membership hashes, metric, `runs=1`,
`max_attempts=3`, `eval_cap=706` by the same formula (champion dev 353 × 1 + one
candidate dev 353 × 1), zero-margin dev selection and adjudication retention
(**ties pass**), and **holdout not evaluated / no holdout report**. Apply stays
record-only with **no snapshot publication**; the monitor posture is not claimed
as exercised. Approval stays hash-bound per request. Under the R-248 standing
grant the lead may approve a record-only apply when retention passes; that approval
is still logged. Use a **new run directory, `h1c-run-1`**; H1a/H1b records are not
reused as H1c evidence.

## 6. Exposure

The same adaptive dev items are reused. H1a's and H1b's recorded reads carry over
(H1a and H1b reports, “Exposure”); prior exposure outside receipts is unknown, not
zero. Record H1c's reads, including continuity and probe runs, separately. No
independence claim is made.

## 7. What is reported

H1b §7 in full, plus: admission-probe results, the continuity evidence for §3(c),
the candidate-dependence probes, and the guard-coverage limitation of §2. If the
proposal is inadmissible, state that no proposal evaluation ran. An operational STOP
remains distinct from a completed negative outcome.

Publication check for this documentation change only, not the real-host checks or
release re-check:

```sh
uv run pytest -q tests/test_publication_markers.py
```
