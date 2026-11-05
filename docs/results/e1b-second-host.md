# E1b: second host (Java) over the dev evaluator contract

Slice S6 of `docs/design.md` §7, issue #7. Measured 2026-11-05 on an Apple-silicon Mac (macOS, Darwin 25.6.0), OpenJDK 21.0.13 (Homebrew `openjdk@21`), CPython 3.13 via uv. There is no pass threshold for "plug-and-play"; this file reports what was needed.

## What was built

| File | Role | Lines |
|---|---|---|
| `examples/java-host/EvaluatorHost.java` | Java dev evaluator host: `POST /evaluate` on loopback, toy keyword task, `GET /count` test probe | 161 total, 134 non-blank non-comment |
| `examples/java-host/http_evaluator.py` | host-side glue: the callable `DevEvaluatorServer` wraps; forwards each batch to the Java host | 30 |
| `tests/integration/test_java_host.py` | compiles and runs the host, drives the unchanged kernel against it | 6 tests |

The toy task: item `d<i>` scores 1.0 when the candidate text contains its keyword (`alpha`, `beta`, `gamma`, `delta`), else 0.0, with feedback `found <kw>` / `missing <kw>`.

## Integration direction

`DevEvaluatorServer` (src/rsi_kernel/evaluator.py) wraps a host-supplied callable `evaluate(candidate_id, item_ids) -> [{item_id, score, feedback}]`, and owns the budget (reserved before the host runs), the dev-split check and the loopback binding. The smallest honest seam is that callable: `HttpEvaluator` posts the same `{"candidate_id", "item_ids"}` body to the Java host and returns its `results`. The kernel's own `/evaluate` stays the only budgeted entry point; the Java host only evaluates what the kernel lets through. Precedent for a non-Python evaluator behind a process boundary: GEPA's curl-based `eval.sh` caller (`src/gepa/oa/engines/autoresearch.py`).

Verified by the tests: per-item results match the toy rule; with cap 2 and four single-item requests the statuses are `200, 200, 429, 429` and the Java host's item counter rises by exactly 2; a non-dev item is refused with 400 and never reaches Java; escaped request strings (`\"`, `\\`, and `\u00e9`, which Python's `json.dumps` sends as a `\u` escape) are decoded by the Java parser (exact results asserted); the host binds 127.0.0.1 even with `-Djava.net.preferIPv6Addresses=true`; the readiness wait is bounded and kills a host that never reports ready. In CI (`CI` set) a missing `javac` fails the run; locally it skips with a reason.

## Integration changes to the kernel

None. SHA-256 of every `src/rsi_kernel/*.py` file is identical before and after the run (checked inside `test_kernel_runs_unchanged_against_java_host`). The PR diff touches no file under `src/` (`git diff --stat cfbf87d -- src/` is empty).

| File | SHA-256 |
|---|---|
| `__init__.py` | `55020ac5ffe0809c0f05a3405536e57ff9841cf79fc3d863e6975fd582c34618` |
| `archive.py` | `421255fc507e8d68d0a7f733faa91a52b7d40a206ffc824d2026d8359937990d` |
| `candidate.py` | `bdba4918f4a0d8b6f575412365cae7ba93a8c8280e7cd039125237b82a3f2b06` |
| `compare.py` | `f779542516094928712a21ae251e34dcc008e124ab250e5ecaab2de9690ecdca` |
| `evaluator.py` | `2d22ca552ab47b65b853db47fcb72dc9808328e1940b01c8f93defa490fa3780` |
| `isolation.py` | `5efb586719c0b32e4352316d993abbab26b9d7acc316de0c0fade2c303bfbe49` |
| `splits.py` | `32177e0b1d52af8523b2e0deb3d0938370aa39af615bfac3af0345d8cf834a55` |

## Dependencies

- Java side: JDK 21 only (`com.sun.net.httpserver.HttpServer`, `java.util`). No Maven, Gradle or JSON library. JSON is a hand-rolled parser for the fixed request shape (marked with a `ponytail:` comment naming its ceiling: strings and string arrays only).
- Python side: standard library only (`urllib.request`, `json`).
- CI: `actions/setup-java` v6.2.0 (temurin 21), pinned to commit `77dd5b2ce225ea11469928ac317850245a74ae78` (resolved from the `v6.2.0` tag via the GitHub API, release published 2026-11-04).

## Setup steps

1. Install JDK 21 and put `javac`/`java` on PATH (locally: `export PATH=/opt/homebrew/opt/openjdk@21/bin:$PATH`).
2. `javac -d <out> examples/java-host/EvaluatorHost.java`
3. `java -cp <out> EvaluatorHost 0` (prints `LISTENING <port>`, binds 127.0.0.1 explicitly).
4. Construct `DevEvaluatorServer(HttpEvaluator("http://127.0.0.1:<port>"), dev_item_ids, cap)` and start it.

The test does steps 2–4 itself and skips with a reason when `javac` is absent.

## Wall time (local, measured)

| Step | Runs | Result |
|---|---|---|
| `javac` compile | 4 | 0.25–0.28 s real |
| JVM start to `LISTENING` | 3 | 0.045–0.054 s |
| `pytest -q tests/integration` (compile + 2 host starts + 8 tests incl. CI-gate subprocess runs + teardown) | 3 | 4.76–4.79 s real |

CI timings are not measured here.

## Not covered

- Only the dev `evaluate` call of the §4 host contract; `get_artifact` and `apply` are not exercised.
- Toy task only; no real product environment (not authorized for this slice).
- The Java host has no auth and relies on its explicit 127.0.0.1 binding, the same assumption as the kernel server.
