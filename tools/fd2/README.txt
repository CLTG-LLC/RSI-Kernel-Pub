FD2 MultiLang gold-only smoke

The manually dispatched GitHub Actions workflow selects the newest instance in
c, cpp, cs, go, java, js, rust and ts (ties use the lowest instance_id), then
runs each instance's gold patch three times on an ubuntu x64 runner. Repeats
use distinct output directories and one worker. Each image is pulled once and
rewritten to repository@sha256:<digest> before its three runs. Only that
instance's containers and exact image are removed afterward; cleanup failure
stops before the next instance. It uploads only a JSON summary of IDs, splits, timestamps, booleans,
numbers and image digests. No logs, patches, test output or test names are
uploaded. The last step exits zero and prints PASS only if all 24 runs resolve.

Frozen inputs:
- Dataset: SWE-bench-Live/MultiLang
  Revision: eb09c2e5db6e4c5a95e01c903c8fd1d5da33c4f3
- Harness: https://github.com/microsoft/SWE-bench-Live
  Commit: 091279261203b243386adf256b2b107656013dbf

Dispatch from a checkout of the public repository:

  gh workflow run fd2-gold-smoke.yml -R <public repo>

The workflow verifies all eight Parquet SHA-256 values against the frozen
receipt, then writes only the selected full rows to a runner-only JSONL. That
file includes the gold and test fields needed by the harness; it is never
printed or uploaded. Harness stdout and stderr are redirected to runner-only
files and are never printed or uploaded. The harness accepts this JSONL through
its local-dataset input, so grading remains on the exact frozen revision. See
the harness README
and evaluation/README.md at that commit for its Python setup, gold mode, image
and rebuild behavior.

Local metadata-only selection (no Docker or evaluation):

  uv run --with huggingface_hub --with pyarrow python tools/fd2/select_smoke.py

Local selection test:

  uv run pytest -q tests/test_fd2_select_smoke.py
