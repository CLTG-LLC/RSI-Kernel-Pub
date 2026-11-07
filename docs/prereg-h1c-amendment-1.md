# H1c amendment 1: corrected author format instruction (post-run, forward-only)

Recorded 2026-11-07, after H1c run 1 and before any further proposal is generated.
This follows COS **Transparent Changes** (https://www.cos.io/initiatives/prereg) and the
in-repo E1c amendments (`docs/prereg-e1c-amendment-1.md`, `docs/prereg-e1c-amendment-2.md`).
The original `docs/prereg-h1c-tenant-rules-addendum.md` (**H1c prereg**) remains the frozen
historical record. Its run 1 stands as recorded and is reported, not replaced.

## 1. What happened

- Every pre-generation STOP in H1c prereg §3 passed, an independent release record released
  generation, and one data-blind author wrote one proposal, which was frozen read-only.
- In run 1, the host returned **422 `TenantParseEmpty`** for that proposal before any score:
  the host product's parser rejected the list. The campaign closed `no_improvement`. The
  champion reproduced byte-identically, and there were no operational failures.
- **Cause: an incomplete frozen format instruction from the lead.** The author brief gave the
  limits and the containment rules but not the rule key layout. Each rule carries its pattern
  under a `matcher` mapping (`type`, `expression`, `flags`). The proposal placed `expression`
  and `flags` directly on the rule. The layout was known before run 1: the pre-run feasibility
  probe used it. The author's input boundary did not include the file that defines it.

Run 1 is a completed run with an ineligible proposal, caused by the brief. It is **not**
evidence about the quality of tenant rules, and it is not an operational STOP.

## 2. What changes

The only change to the author's task/format inputs is the explicit rule key layout below.
Separately, this amendment authorizes one additional proposal and campaign under the limited
supersession stated below. The layout:

```yaml
    - id: <unique id>
      phase: <phase>
      severity: <severity>
      posture: <posture>
      description: <text>
      matcher:
        type: regex
        expression: <pattern>
        flags: <flags>
```

For run 2 only, this amendment supersedes H1c prereg §2's prohibition on regeneration after
inadmissibility and §4's one-proposal/no-replacement rule to authorize one additional proposal
from a fresh data-blind author. It replaces §5's run directory with `h1c-run-2`. Run 1 remains
closed and reported unchanged. No repair, replacement or replenishment is permitted within
run 2. All other provisions of H1c prereg §2–§7 remain unchanged: artifact, champion, frozen
envelope, admission and 500 mapping, guard coverage, tier label, the author's input boundary
(plus this instruction), metric, `runs=1`, `max_attempts=3`, `eval_cap` 706, zero-margin
selection and retention, record-only apply, holdout not evaluated, exposure and reporting.

## 3. Why this is not a post-score repair

- The run 1 proposal is not edited, repaired or re-evaluated. A **new, fresh** data-blind
  author writes one new proposal.
- The new author receives no run 1 information: no outcome, no proposal text, no host response.
  The only change to its inputs is the key layout above, which was fixed before run 1.
- The run 1 proposal was never scored, so no dev score informs the new proposal.

## 4. Order and STOPs

1. This amendment is merged.
2. An independent release re-check confirms that the H1c prereg §3 identities still hold at run
   time and that no new proposal exists, and records a release.
3. Only then is the fresh author assigned. The new proposal is frozen read-only before
   evaluation, with no repair or replacement.
4. The run uses a **new run directory, `h1c-run-2`**, with fresh identity, startup-guard and
   reproduce-first checks per H1c prereg §3(a)–(c). Run 1 receipts are not reused.

If the new proposal is ineligible for any reason, report it. No further amendment of this kind
is authorized by this document.

## 5. Exposure

Run 1 added **2 full dev reads** (the reproduce-first check and the campaign champion read) on
top of the H1c prereg §6 accounting, which already carries H1a and H1b. The pre-generation
continuity check added one more. Run 2 adds its own reads, reported separately. Dev stays
adaptive; no independence claim is made.

## 6. Reporting

The H1c report covers both runs: run 1 with this cause, and run 2 under H1c prereg §7. The
identities of the two proposals and authors are reported separately.

Publication check for this documentation change:

```sh
uv run pytest -q tests/test_publication_markers.py
```
