# FD2 amendment 2: split solving and grading hosts after the host-fidelity STOP (prospective for solver outcomes; responds to an observed host-fidelity result)

Recorded 2026-11-08, after the host-fidelity gold smoke stopped and **before any FD2
noise-floor, solver-smoke or campaign solve**. It follows COS **Transparent Changes**
(https://www.cos.io/initiatives/prereg) and the in-repo amendment precedents
(`docs/prereg-e2-amendment-1.md`, `docs/prereg-fd2-amendment-1.md`). The original
`docs/prereg-fd2-swebench-live.md` (**FD2 prereg**) and amendment 1 remain the frozen
historical record.

## 1. What happened

- **Host-fidelity smoke (FD2 prereg §4(a), §8 step 4)** ran on the Apple Silicon
  development host ("the Mac") with the identical shared script
  (`tools/fd2/gold_smoke.sh`) and the frozen 8-instance selection, from
  2026-11-08 09:57Z to 12:07Z.
  - Code `8dc4fa8`; harness `0912792` with RepoLaunch submodule `c4b623d`.
  - Docker Desktop 4.94.0, engine 29.8.2, Rosetta amd64 emulation, containerd image
    store, 18 CPUs, 8,317,267,968 bytes of VM memory, about 1.8 TiB of VM disk.
  - The upstream per-instance estimate is "4 CPUs with 16 GB RAM"
    (`evaluation/README.md` line 68 at the harness commit). The VM memory is below
    that estimate. This is a capacity hypothesis only, not a demonstrated cause of
    the results below.
- **Per-instance outcomes against the native references.** The native references are
  public-mirror runs 42445136512 and 42454404566 (amendment 1: 7 of 8 instances at
  3/3; turso `low_disk`).

  | Instance | Mac (resolved / 3) | Native reference | Comparison |
  |---|---|---|---|
  | `xroche__httrack-893` (c) | 0/3; the same PASS_TO_PASS test failed in each run | 3/3 | **mismatch** |
  | `FastLED__FastLED-3781` (cpp) | 2/3; run 1 had 76 of 82 PASS_TO_PASS tests failing | 3/3 | **mismatch** |
  | `elsa-workflows__elsa-core-7898` (cs) | 3/3 | 3/3 | match |
  | `github__gh-aw-27242` (go) | 3/3 | 3/3 | match |
  | `floci-io__floci-2031` (java) | 3/3 | 3/3 | match |
  | `notionnext-org__NotionNext-4338` (js) | 3/3 | 3/3 | match |
  | `mnfst__manifest-1635` (ts) | not run | 3/3 | not executed |
  | `tursodatabase__turso-8102` (rust) | stopped at image pull ("short read", truncated registry download) | `low_disk`, no outcome | outside the reference set (amendment 1) |

  manifest was not reached because the script stopped at turso's image pull. That
  stop is operational; neither instance has a gold result on the Mac.
- **Two mismatches.** Under FD2 prereg §4 ("any mismatch is a STOP for this host, not
  a tolerance") and §8 step 4, this is a STOP for the Mac as grading host.

The STOP stands and is preserved, with both mismatches recorded. **The Mac never grades
again.** There is no Mac grading rerun and no re-qualification of the Mac as a grading
host. Re-running fidelity after a failed comparison would be a rescue that the prereg
forbids. Successive configuration tweaks would also open a "garden of forking paths"
(Gelman & Loken 2013,
http://www.stat.columbia.edu/~gelman/research/unpublished/p_hacking.pdf).

## 2. Owner decisions (2026-11-08)

The lead recommended (1) the Mac as solving host only and (2) publishing grading
payloads through the public mirror. The owner approved both gates on 2026-11-08, in
these words:

> "I said no need for me, og with your recom"

1. **Scoped solving-only exception.** The Mac, which failed as grading host, may act
   only as the solving host. This approval is recorded here before any solve or
   publication. Without it, FD2 would STOP: changing the grading host does not remove
   this requirement.
2. **Publication channel.** Grading payloads are published through the public mirror,
   within the payload classes and timing in §3 item 4. Without this approval the split
   host design would be unavailable.

## 3. What changes

1. **Host roles (FD2 prereg §4 and §8 step 4).**
   - **Solving host:** the Mac. It runs the solver containers, the proposer and the
     kernel. The admission key never leaves it.
   - **Grading host:** a standard hosted runner on the public mirror, image
     `ubuntu-26.04`. It makes no model call and uses no repository secret. The runner
     image build (`ImageOS`, `ImageVersion`, provisioner) is recorded for **every**
     job.
   - **Runner-image drift rule, set prospectively.** The provider states: "We typically
     deploy weekly updates to the software on the runner images"
     (https://github.com/actions/runner-images). A job selects an OS label, not an
     immutable image build. The build is therefore
     recorded per job and reported, grouped by build. Like the Docker image store in
     FD2 prereg §4, it is recorded only and is not part of any comparison.
   - Precedent for splitting generation from evaluation: the pinned harness evaluates
     agent-predicted patches separately (`evaluation/README.md`, "Evaluation of
     agent-predicted patches", lines 97–115); SWE-bench `run_evaluation
     --predictions_path` and sb-cli cloud evaluation (https://www.swebench.com/sb-cli/)
     do the same.
   - For the grading host, FD2 prereg §4(a) is superseded by item 2: qualification
     is the binding of the two native references to the adopted evaluator
     configuration, not a re-run comparison.
   - FD2 prereg §4 conditions (b) and (c) now apply to this pair of hosts: the solver
     smoke passes with remote grading, and gold validity holds on the grading host
     (item 3).
2. **Frozen evaluator identity, before any execution.** The two native runs are
   reference evidence only for **their recorded evaluator configuration**. Before
   gold validity, the solver smoke or any campaign grade, each of these is frozen and
   hashed:
   - the grading code (the grading workflow, `tools/fd2/gold_smoke.sh` and the
     remote-grader bridge);
   - the harness commit and RepoLaunch submodule commit;
   - a **harness dependency lock**. This is new. It resolves FD2 prereg §2's
     "dependency lock hash: PENDING-adapter-pin" and replaces the unlocked
     `python -m pip install -e . ./launch/` in `.github/workflows/fd2-gold-smoke.yml`;
   - the dataset revision and parquet hashes;
   - the per-instance image digests;
   - the grading argv template;
   - the parser file hashes.

   These feed the `evaluator_hash` of FD2 prereg §2. A hash mismatch on any frozen
   input is a STOP.

   If the two references cannot be bound to the adopted evaluator configuration (for
   example, because their dependency resolution differs from the new lock),
   grading-host qualification remains incomplete. It is reported as such, and
   execution stops before the solver smoke. Recording the incompleteness does not
   satisfy the gate. Execution proceeds only after the applicable qualification
   requirement has been satisfied and recorded, or an explicit owner waiver has been
   recorded. No new per-job gold gate is added.
3. **Gold validity on the grading host (FD2 prereg §3, §8 step 5).**
   - The whole frozen included set (222 instances) is attempted on the grading host,
     one instance per job, with the identical `gold_smoke.sh` under the frozen lock.
     Nothing is pre-excluded; turso is attempted like every other instance.
   - The frozen 3/3 rule applies uniformly.
   - Completed outcomes, aborted attempts with their reason (for example `low_disk`)
     and unexecuted repetitions are recorded distinctly.
   - A documented per-instance capacity abort is an **operational exclusion**,
     reported with its reason.
   - A job that never started, or whose result is missing, means **gold validity is
     incomplete**. It is not an exclusion.
   - The surviving instance, repository and language counts are reported.
   - Disclosure: the excluded set may differ from what the Mac's larger disk would
     have produced. That difference is a consequence of the host change.
4. **Publication boundary (FD2 prereg §7).** The private store stays authoritative for
   every score, approval and report.
   - **Payload classes published**, each at the time it is graded: dev, adjudication
     and holdout prediction patches, with their instance and run identity; the
     harness's `results.json` and `report.json`, including the per-test outcomes the
     harness itself writes; and adjudication noise-floor outputs, which are therefore
     published **before the campaign closes**.
   - The workflow publishes only what grading needs: the prediction in, and
     `results.json` and `report.json` out. It logs no per-test detail beyond the
     harness's own.
   - **Never published:** credentials, solver or proposer traces, and private-store
     content.
   - The proposer runs with `--network none` and the solver's only egress is the
     forwarder to the model proxy (FD2 prereg §4), so neither can read the public
     channel. The proposer still receives `{item_id, score, correct}` for dev only.
   - A marker scan (the `tests/test_publication_markers.py` logic) runs over each
     payload before upload. It is **supplemental only** and is not proof of
     confidentiality.
5. **Remote-grading result binding and failure semantics (FD2 prereg §6).**
   - Every request and artifact is bound to the prediction digest, the instance and
     run identity, the workflow commit, the evaluator identity (item 2) and the
     workflow-run ID. A mismatch on any binding is a STOP.
   - Dispatch failure, queue expiry, cancellation, job timeout, missing artifact and
     silent termination each give `None`, which blocks the pair under FD2 prereg §6.
     The actual reason is kept verbatim.
   - There is no redispatch, no rerun and no late-result substitution. The bridge
     terminates only the remote run it owns, by run ID.
   - **Deadline.** A dispatch-to-result deadline is set before the solver smoke. It is
     built from the 6 h hosted-job limit (https://docs.github.com/en/actions/reference/limits),
     the queue-plus-job times measured in the gold-validity matrix, and an allowance
     for queueing and retrieval. The provider documents no hosted-runner queue limit,
     so the allowance is a **NAMED LOCAL EXCEPTION**. The budgets amendment freezes
     the final deadline policy.
6. **Concurrency.** The 4-job cap of FD2 prereg §4 stays a **local** cap on Mac
   solves. Remote grading concurrency is capped by the documented Free-plan limit of
   20 concurrent hosted jobs, which is shared across the organisation
   (https://docs.github.com/en/actions/reference/limits).
7. **Amendment 1, item 3 (disk allocation)** now applies to the solving host.
8. **Campaign code pin (FD2 prereg §2 and §8 step 1).** The original code-pin
   selection rule is superseded by the first `main` commit containing this amendment
   and the merged FD2 split-host grading implementation, including the
   dependency-locked grading workflow and remote-grader bridge. That commit is
   frozen in a clean detached run tree before gold validity or the solver smoke.
   The git SHA, full and kernel-only code hashes are recorded; subsequent code drift
   remains a STOP. The historical host-fidelity smoke and native-reference pins
   remain unchanged evidence.

## 4. What does not change

Everything else in the FD2 prereg and amendment 1 is unchanged:
- pool, carve, seed and item lists (`docs/prereg-fd2-items.json`);
- the frozen 3/3 gold-validity rule and its repetition count;
- metric, runs, selection, the zero-margin retention rule and the estimator;
- missing-result accounting: every `None` blocks the pair and is never imputed;
- retention and approval;
- the report-only noise floor;
- solver and proposer isolation;
- the budgets-amendment limits;
- the fidelity reference set of amendment 1.

Apart from the disclosed changes in §3, no threshold, gate, measurement or analysis rule
is changed.

## 5. Drafting exposure disclosure

While this amendment was drafted, a drafting worker printed the first 1,500 bytes of
the smoke's frozen grading-data file. That output included part of the gold patch for
`xroche__httrack-893`. No test patch, problem statement or other instance's content
was read. This is disclosed and kept, following `docs/prereg-e2-amendment-1.md` §3:

- `xroche__httrack-893` is outside the carve: `docs/prereg-fd2-items.json` excludes it
  as `july_outside_holdout`. It is never solved or scored in FD2. Other instances of
  its repository are in the adjudication split; none of their content was read.
- No candidate is authored by the lead or a worker. Candidates come from the frozen
  proposer and solver path, which receives no gold patch.
- The exposure reconciliation (FD2 prereg §8 step 8) records this incident separately
  from solve counts.

## 6. Prospective for solver outcomes, not outcome-independent

No FD2 solver output, score or campaign result exists when this amendment is recorded,
so it is prospective for solver outcomes. It does, however, respond to an observed
host-fidelity result: the Mac grading STOP. It is therefore disclosed as a response to
that result and is not presented as outcome-independent.

Publication check for this documentation change:

```sh
uv run --locked pytest -q tests/test_publication_markers.py
```
