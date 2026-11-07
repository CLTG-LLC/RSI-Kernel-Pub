# H1b prereg addendum — inventory-preserving rule-pack edit (issue #92)

Forward-only amendment to `docs/prereg-h1a-rule-pack-addendum.md` (H1a), drafted
2026-11-06 before H1b proposal generation or evaluation. Following
`docs/prereg-s5c-addendum.md` and [COS Transparent Changes](https://www.cos.io/initiatives/prereg),
only changes are stated here; everything else is adopted by reference. Earlier
registrations, H1a records and the kernel are untouched.

**Status: DRAFT / EXECUTION HELD.** This document does not release generation or
evaluation. Private records remain outside the published tree; only **the host
product** is named here, and no data or golden text is included.

## 1. Why

H1a's additions-only proposal was ineligible: the frozen guard pins the exact
rule inventory and requires per-rule golden coverage (`docs/results/h1a-rule-pack.md`,
“Interpretation”). It returned 422 before scoring; no improvement or adjudication
retention was demonstrated. H1b asks whether an inventory-preserving edit can
pass that **unchanged** guard and change dev and, if selected, adjudication scores.
Pattern-only admission does not guarantee guard eligibility: identity and behavior
assertions remain binding.

## 2. What changes: the proposal constraint

The author may edit **only the pattern text of existing regex rules**. Rule ids,
count, order, phase, action, flags, metadata, comments and manifest remain
byte-identical; all bytes outside the edited pattern strings remain identical.
No additions, removals or function-rule changes are allowed. The proposal remains
one complete replacement pack, not a new patch format.

**Mechanical admission check, before evaluation:** retain a champion-to-proposal
diff and verify that only existing regex pattern values changed. Any other change
makes the proposal **inadmissible**: report the result, do not evaluate it, and do
not regenerate or repair it. Passing admission does not replace the real guard.

Precedent: H1a §5 and its report's inventory/coverage finding; the one-component
contract in `docs/design.md` §4.1; and the RRSI assessment §4.3, “Single attributable
change” (kept outside the published tree), adopting [RRSI Eq. 9 and Appendix D.2](https://arxiv.org/html/2609.24972v3).
This bounds one component and one proposal; it does not claim that multiple
pattern edits are one semantic atomic edit.

## 3. Author boundary and release order

One **fresh data-blind worker**, separate from this preregistration/guard-source
reader, authors one proposal only. Allowed inputs are the champion pack, frozen
task/format instructions, and the host product's **loader, rule and phase source
files**. These explicitly include the source files H1a's author was attested to
have read (`docs/results/h1a-rule-pack.md`, “Champion and proposal”); that wider
boundary is preregistered here rather than described as champion-only.

No data, evaluation outcomes or failure hints, tests, fixtures, golden text,
expected outputs, private evidence or web datasets are allowed. Retain the actual
access-boundary attestation and H1a's author identity, request accounting,
freeze-time, file-hash, content-id and parent-id reporting requirements.

**Order:** assign the author only **after this preregistration is merged AND an
independent release re-check record exists that releases generation**. Only then
may the proposal be written and frozen. The earlier generation-order lesson, disclosed in the H1a report:
evaluation waiting for release does not cure proposal generation before release.
No post-score repair, replacement or replenishment is permitted.

## 4. Unchanged protocol and new run identity

Adopt H1a and `docs/results/h1a-rule-pack.md` (“Frozen identities” and “Pre-run STOPs
and the release re-check”) by reference, including:

- The owner's recorded scope disposition: an offline copy, non-grant and record-only; no host-product change,
  activation, deployment or publication, and no sealed-set evaluation or proposal
  to the host product's team without a separate disposition.
- The host at its frozen identity, champion, actual built-class manifests,
  dependencies, all **three** golden classes and staged skips, candidate binding,
  carve/membership and input hashes, metric and all disclosed limitations.
- Zero-margin dev selection and adjudication retention (**ties pass**), `runs=1`,
  `max_attempts=3`, and `eval_cap=706` under the same formula:
  champion dev 353 × 1 + one registered candidate dev 353 × 1.
- The frozen CLI path and configuration contract, deterministic D2, spend reading,
  matching four-hash owner approval before record-only apply, fresh reproduce-first
  at the run, and **holdout not evaluated / no holdout report**.

Use a **new run directory, `h1b-run-1`**, with fresh run-bound manifests, receipts
and logs. H1a records are not reused as H1b evidence or edited. Reusing frozen
inputs does not mean reusing a receipt or waiving run-time identity verification.

## 5. Exposure

The same frozen dev items were read again in H1a: **three reproduce passes plus
the campaign champion read**, in addition to the two earlier reproductions
(`docs/results/h1a-rule-pack.md`, “Exposure”). They remain **adaptive**. Prior
exposure outside the documented receipts is **unknown**, not zero. Carry the
report's separate guard/read accounting and uncertainty about that count;
record H1b's actual additional reads separately. No independence claim is made,
including for public-data adjudication or holdout.

## 6. Pre-run STOPs

H1a §6's ordered pre-run STOPs apply unchanged, with identities **re-verified at
run time** against the frozen H1a identities and the new run manifest: host and
build identity, fresh real-dev reproduce-first, exact guard selectors/binding/
controls/skips, and data/membership hashes. Verify inputs before reproduction as
H1a requires. Its §9 dispositions and the report's actual build-manifest evidence
are adopted, not assertions that those checks have already run for H1b.

Additionally, the **admission diff check in §2 must pass before any proposal
evaluation**. A mismatch or unresolved STOP keeps execution held; an inadmissible
proposal is reported without evaluation or regeneration. No guard relaxation,
retuning or rescue run is authorized.

## 7. What is reported

Carry **H1a §7's complete reporting list**, including separate execution and
quality/acceptance status, identities and lineage, requested/evaluated counts,
text-free flips and paired scores where available, CLI outcomes, host call/reason
counts, reproduce/candidate/adjudication/guard reads and skips, author accounting,
wall time if measured, and all disclosures. Add the **admission-check result** and
its retained diff; if inadmissible, state that no proposal evaluation ran. An
operational STOP remains distinct from a completed negative outcome.

Publication check for this documentation change only, not the real-host guard
or independent release re-check:

```sh
uv run pytest -q tests/test_publication_markers.py
```
