# E1d amendment 1: approver under the owner's standing grant (pre-final, forward-only)

Recorded 2026-11-07, while the E1d optimise phase is running and **before any E1d final-phase
solve, observation, approval request or acceptance record exists**. This follows COS
**Transparent Changes** (https://www.cos.io/initiatives/prereg) and the in-repo amendment
precedent (`docs/prereg-e1c-amendment-1.md`, `docs/prereg-h1c-amendment-1.md`). The original
`docs/prereg-e1d-addendum.md` (**E1d prereg**) remains the frozen historical record.

## 1. What changes

E1d prereg §2.2 requires "hash-bound owner approval **per request** (no standing approval)".
The owner's recorded standing grant for this lane predates that text: it lets the lead approve
a record-only apply when the preregistered retention gate passes. The H1c and E2
preregistrations already state this (`docs/prereg-h1c-tenant-rules-addendum.md` §5,
`docs/prereg-e2-skill-groups.md` §6). This amendment aligns E1d with them.

For E1d only, the full phrase "hash-bound owner approval per request (no standing approval)" in E1d prereg §2.2 is superseded by:

> Approval stays hash-bound per request to the candidate, evaluator, data and code hashes.
> Under the owner's recorded standing grant, the lead may approve a record-only apply when
> retention passes; each approval is logged with its request hashes and the grant.

## 2. What does not change

Everything else in E1d prereg is unchanged, including the champions, code pin, caps,
zero-margin retention (ties pass), the adjudication gate, holdout reported and not gated,
the final-phase shape, record-only `apply(hash)`, exposure and reporting. No threshold,
gate, measurement or analysis rule changes. A request that fails to match its frozen
hashes is still not approved.

## 3. Why this is not outcome-driven

No final-phase data exists when this is recorded: there is no `final/` directory, approval
request or acceptance record for E1d. The change concerns only who signs a record-only
approval, not whether retention passes.

Publication check for this documentation change:

```sh
uv run pytest -q tests/test_publication_markers.py
```
