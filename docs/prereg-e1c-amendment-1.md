# E1c amendment 1 — post-smoke, pre-campaign operational amendment (issue #83)

Amended 2026-11-06 under the COS **Transparent Changes** rule for
preregistration amendments (<https://www.cos.io/initiatives/prereg>). This is
**not pre-data**: the first live T3 smoke has already run and failed. No E1c
campaign solve ran. The original `docs/prereg-e1c-harness-code-addendum.md`
(hereafter **E1c prereg**) remains untouched as the historical frozen record.
This amendment is forward-only and governs the subsequent smoke and campaign.

## 1. Trigger and evidence

The first smoke used code pin `af2054c`, the seed `solver.py`, and
`task_group_001/train/001`. The trusted agent container exited 137 at 34.9 s;
Docker recorded an `oom` event for that owned container under the frozen
`memory_bytes = 45088768`. The OOM event, not exit 137 alone, establishes the
resource classification. The allowance was insufficient for the workload.
**No claim is made about which subprocess caused the OOM.**

The failed smoke remains an **operational STOP**, not a failed dev comparison
or a negative campaign result. Its exposure remains **1 dev solve, g001
train/001, 43,739 tokens**. Preserve the failed smoke's logs, container evidence,
identity and exposure record; do not overwrite them or reuse them as passing
evidence. No campaign solve ran after that STOP.

## 2. Supersession and scope

This amendment supersedes the agent-limit scope in E1c prereg **§3.3–§3.5,
§6, §8 and §9**, and replaces **§5's code-pin rule** as stated in §5 below.
The old statement that both solver containers carry the resource limits is
historical, not the amended execution contract.

- The **untrusted candidate-code container only** receives the frozen
  `--cpus`, `--memory`, `--memory-swap` and per-file `--ulimit fsize` values.
  Its `CodeLimits.docker_argv()` options and logic-container invocation are
  unchanged.
- **Both containers remain non-root**, using the invoking host's numeric
  `uid:gid`; a root host UID remains `STOP root_host_uid`, before external
  staging commands. Both retain `--cap-drop ALL` and
  `--security-opt no-new-privileges`.
- The **trusted agent** receives `CodeLimits.agent_argv()` through the production
  `CodeDockerSolver._solver_options`; it receives no CPU, memory, memory-swap or
  file-size limit from `CodeLimits`.
- Candidate-code `--network none`, read-only filesystem, disposable `/tmp`,
  protected mounts, prompt-as-positional-data boundary, trusted grading and
  metering, independently bounded stdout/stderr collection and scoped timeout
  removal are unchanged. The trusted agent's internal task/model-forwarder
  network and separation from candidate code are unchanged.

The agent's unbounded `RLIMIT_FSIZE` under these options does **not** remove
E1c prereg §4's measured assertion that retained `sessions` files are below
`file_bytes`. That smoke assertion remains unchanged.

## 3. Frozen values and their evidential limit

**NAMED LOCAL EXCEPTION T3-RESOURCE-VALUES** remains the classification.
The run configuration values are unchanged:

| Parameter | Frozen value |
|---|---|
| `cpus` | `0.05` |
| `memory_bytes` | `45088768` |
| `file_bytes` | `784957` |

The rule bytes at `pilot-config/t3-measure/FROZEN-RULE.md` are unchanged;
sha256 remains
`7dbaacadfab97eb2ed4728bb88980e7e8403a73c6569a6cdcffb06ac8e6f2eb8`.
The original sample population, rule, computed values and measurement table
are preserved, not recalculated or retuned.

The rule uses the p95 of one-second Docker stats samples, not per-interval
memory peaks. The recorded S5b agent memory p95 was 36.7 MiB and the sampled
maximum was 44.5 MiB. That diagnostic sampling cannot establish the peak memory
requirement or identify the responsible subprocess. These values now bind a
**lighter workload**, the candidate prompt-code container, not the trusted
Codex workload. They are still local exceptions, **validated only by the
end-to-end smoke**, not standard workload limits or established GDPevo capacity.
The failed smoke did not validate them. A fresh passing smoke is required for
the amended scope.

## 4. Precedents and hardening disposition

- **Existing S4/S5b trusted-agent creation:**
  `src/rsi_kernel/adapters/gdpevo/solver_docker.py:512–522` creates the agent
  without CPU, memory or file-size resource flags. The amendment adopts that
  resource scope without removing T3's existing security hardening.
- **SWE-bench local Docker path only:**
  [run_evaluation.py:116–142 at 02e7a74ffd0b707aab73d203fe87bdc7c76afc8e](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/swebench/harness/run_evaluation.py#L116-L142)
  sets no CPU or memory limits in its local Docker container creation. This
  citation does **not** cover SWE-bench's Modal backend and is not a precedent
  for dropping capabilities or other T3 controls.
- **Docker default:** [Resource constraints](https://docs.docker.com/engine/containers/resource_constraints/)
  states, "By default, a container has no resource constraints". Omitting
  resource flags uses that native behavior; it does not assert whole-host fit.
- **Lead tie-break on hardening:** the pre-amendment `docs/design.md:238`
  stated that dropped capabilities and no-new-privileges "remain unchanged".
  Documented in-repo design takes precedence over locally deriving an agent
  option list that drops those controls. Keep both controls on the agent: the
  smallest change addressing the failed allowance changes resource scope, not
  security hardening.

## 5. New pin, preserved smoke and STOP rule

The code pin is **the first main commit containing this amendment**. That
commit must contain the resource-scope code change, both regression-test
updates and the `docs/design.md` wording together with this amendment. Use a
clean detached run tree at that commit and record its SHA, full code hash and
kernel-only hash before the next solve, as in E1c prereg §5. Identity drift
remains a STOP.

The full test suite and publication guard must pass before the lead runs a
**fresh live T3 smoke** at the new pin. Keep every assertion in
`tests/adapters/test_gdpevo_code_live.py` and E1c prereg **§4** unchanged:
non-root uid:gid, logic-container removal, byte-identical seed prompt, sessions
file-size check, successful execution and trusted grading. It must show exactly
**`1 passed`**; a skip or failed test does not count. Preserve the other §4
pre-run STOPs, including input/image manifests and calibration replay.

**A second smoke failure is a STOP and requires amendment 2.** It does not
select Option B (a new peak-measurement protocol) by default, authorize a
retune, or permit a campaign to start. Any subsequent change needs its own
explicit operational amendment before another run.

The run directory remains **`pilot-005`**, because no campaign solve ran.
Preserve its failed-smoke evidence and write the next smoke's evidence as a
separate attempt, never by overwriting or recycling the failed record.

## 6. Exposure, reporting, failure semantics and ordering

E1c prereg §6's terminal S4b exposure reconciliation is unchanged. Add the
failed smoke's actual exposure stated in §1 and the fresh smoke's actual
exposure, regardless of outcome, before the first campaign solve. Every screen
remains adaptive; no independence or fresh-split claim is made.

Keep **separate T3 reporting** under E1c prereg §8. Removing the former
agent-resource mismatch does not make this a controlled T3-versus-S4
comparison: T3 rows remain campaign records, not pooled with S4, S4b or S5b.
Report the amended candidate-only resource scope, unchanged frozen values and
rule hash, both code identities, smoke outcomes, exposure, resource-event
classification evidence and unclassified failures. Capability, changed-candidate
evaluation and retained improvement remain distinct claims.

E1c prereg **§7's failure semantics remain unchanged**: operational STOP is
not quality failure; invalid final evidence blocks acceptance; resource events
need owned-container evidence; exit 137 alone is not OOM. Caps, carve, metric,
retention and hash-bound owner approval remain unchanged; `apply()` stays
record-only.

E1c prereg §9's ordering remains unchanged: S4b and its final phase finish
first, with no overlapping E1c solve; E1c groups start `001 → 002 → 003` under
the existing four-job cap. Only the candidate-code container now carries the
frozen resource limits; the trusted agent and other solve containers do not.
No whole-VM capacity bound, reserve or new concurrency limit is inferred.
