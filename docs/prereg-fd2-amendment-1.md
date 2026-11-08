# FD2 amendment 1: fidelity reference set when a native reference is unobtainable (pre-campaign, forward-only)

Recorded 2026-11-08, **before any FD2 noise-floor, solver-smoke or campaign solve**.
It follows COS **Transparent Changes** (https://www.cos.io/initiatives/prereg) and the
in-repo amendment precedent (`docs/prereg-e2-amendment-1.md`). The original
`docs/prereg-fd2-swebench-live.md` (**FD2 prereg**) remains the frozen historical record.

## 1. What happened

- The native x64 gold smoke (FD2 prereg §8 step 3) ran twice on the public CI runner,
  using the identical shared script (`tools/fd2/gold_smoke.sh`) and the frozen 8-instance
  selection.
- In both runs, 7 of 8 instances resolved under gold in 3 of 3 runs.
- In each native smoke execution, `tursodatabase__turso-8102` (rust) was attempted
  once and aborted with `low_disk`. The script did not execute repetitions 2–3;
  it recorded zero-second `low_disk` entries for them. No completed grading
  outcome was obtained.
- On the legacy image store (the runner was switched because the containerd store "uses
  more disk space than the legacy storage drivers",
  https://docs.docker.com/engine/storage/containerd/), its instance image is
  79,995,319,078 bytes unpacked.
- In native run 42454404566, the runner recorded 115,429,388,288 bytes free before
  the first instance and 34,579,771,392 bytes free before turso's first evaluation.
  That evaluation was aborted after 491 s by the `low_disk` watchdog, whose
  configured guard was 2,147,483,648 bytes. These are measurements from this
  prepared runner, not a general hosted-runner capacity guarantee.
- The project's GitHub plan does not provide larger hosted runners.

This is an operational STOP, not a fidelity result. No turso outcome exists on either
host.

## 2. What changes

1. **Fidelity reference set.** FD2 prereg §4(a) requires the host to reproduce "the native
   x64 runner's per-instance resolved outcomes **exactly**". This is now read together with
   §8 step 3, which already says "non-3/3 instances excluded and reported".
   - The fidelity comparison runs over the instances that have a native 3/3 reference.
     There are 7: one per language split except rust.
   - Any mismatch on those 7 remains a STOP for the host, not a tolerance.
   - `tursodatabase__turso-8102` is excluded from the native reference and reported,
     with its reason `low_disk` and the measured sizes above.
2. **turso remains in the carve.** It is a single holdout instance. Like every included
   instance, it is subject to the frozen gold-validity rule on the campaign host (FD2
   prereg §3): it must resolve under gold in all three runs, or it is excluded and
   reported. No rule for it changes.
3. **Campaign-host disk allocation** is an operational setting. It is raised so that
   instances of this size can run on the host. Its value is recorded with the other
   host settings under §4. It is not part of any comparison.

## 3. What does not change

Everything else in the FD2 prereg is unchanged:
- pool, carve, seed and item lists (`docs/prereg-fd2-items.json`);
- the frozen 3/3 gold-validity rule;
- metric, runs, selection, the zero-margin retention rule and the estimator;
- the report-only noise floor;
- the budgets-amendment limits.

Apart from the fidelity-reference scope change in §2 item 1, no threshold, gate,
measurement or analysis rule is changed. The frozen eight-instance smoke selection
rule is unchanged; the fidelity comparison uses its seven native 3/3 references.

## 4. Why this is not outcome-driven

No FD2 solver output, score or campaign result exists when this amendment is recorded.
The change concerns host capacity on the reference runner, measured from gold-patch
evaluation only, and it applies before any comparison on the campaign host is run.

Publication check for this documentation change:

```sh
uv run pytest -q tests/test_publication_markers.py
```
