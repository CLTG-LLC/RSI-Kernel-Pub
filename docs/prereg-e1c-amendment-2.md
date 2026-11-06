# E1c amendment 2: calibration-replay defect fix (post-smoke, pre-campaign operational amendment)

Recorded 2026-11-06, after the fresh smoke of amendment 1 passed and before any campaign solve.
This follows COS **Transparent Changes** (https://www.cos.io/initiatives/prereg) and amendment 1 §5:
"Any subsequent change needs its own explicit operational amendment before another run."

## 1. What happened

- Under amendment 1, at code pin `faa00e48`, the fresh live T3 smoke **passed**: `1 passed in 196.97s`,
  and the agent was not OOM-killed. Evidence: `e1c-smoke-2/attempts/gdp-9839b680`. Exposure: one more dev
  solve of `task_group_001/train/001`.
- The campaign then stopped, for all three groups, at **pre-run STOP 3 (calibration replay)**.
  `_docker_replay` in `src/rsi_kernel/adapters/gdpevo/pilot.py` staged a placeholder `SKILL.md` candidate
  through `solver._stage`. The T3 `CodeDockerSolver._stage` admits only the `solver.py` component, so it
  raised `ValueError`.
- No model call, solve or campaign record was made. Each group has one calibration evidence directory.
  The stopped run directory is preserved as `pilot-005-attempt-2-prerun-stop`.
- This is a code defect, not a quality failure. The existing tests replaced the real replay with fakes,
  so the defect was not caught.

## 2. Change

The calibration replay calls the base `DockerSolver._stage` explicitly. Replay needs only the trusted
task image and grader inputs (`group_dir`, `task_path`), and it never stages candidate code.

Unchanged:
- `validate_code`;
- the trusted manifest and hash checks in base staging;
- the T3 candidate path.

A regression test runs the real `_docker_replay` against both a real `DockerSolver` and a real
`CodeDockerSolver` with external calls stubbed. RED before the fix: `ValueError`. GREEN after.

Not changed:
- the frozen values, the frozen rule, the carve, caps, metric, retention or approval;
- amendment 1's resource scope;
- the smoke assertions.

## 3. New pin, fresh smoke and run identity

- **Code pin:** the first `main` commit containing this amendment and the fix. Record both identity
  hashes before the next solve; identity drift is a STOP.
- **Fresh live T3 smoke at the new pin:** it must show exactly `1 passed`. A failure is a STOP and
  requires amendment 3.
- **Run directory:** `pilot-005`, because no campaign solve has run. Evidence from the stopped attempt and
  from both earlier smokes is kept separately and is never overwritten.
- **Exposure:** recorded before the first campaign solve. It is the S4b terminal counts, plus the three
  smoke solves (the failed one, the passing one, and this fresh one), each one dev solve of
  `task_group_001/train/001`.

Every screen stays adaptive. No independence claim is made.
