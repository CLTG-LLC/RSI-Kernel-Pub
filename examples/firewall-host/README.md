# Offline firewall-pack evaluator

A generic JDK-only host for the frozen HTTP contract in
[`design.md §4.1`](../../docs/design.md#41-frozen-host-contract-for-non-python-hosts).
It reuses [`examples/java-host`](../java-host/EvaluatorHost.java), with no kernel
changes or product dependency in this repository. Run only against an offline
built copy; this is a feasibility probe, not an integration or activation.

## Run

```sh
javac -d /your/offline/host-classes examples/firewall-host/FirewallHost.java
java -cp /your/offline/host-classes FirewallHost /your/offline/host.properties 0
```

The host prints `LISTENING <port>` and binds **127.0.0.1 only**, including when the
JVM prefers IPv6. The optional port defaults to the JDK's ephemeral port (`0`).
All paths resolve relative to the properties file. Keep real configuration,
artifacts, evidence and any private fixtures outside this repository.

```properties
classpath=classes:dependency.jar
loader_class=example.RuleLoader
matcher_factory=example.MatcherCatalog#defaults
champion_path=champion.yml
cases_path=cases.json
guard_cases_path=guards.json
evidence_path=evidence.jsonl
# Optional; the default artifact component name is rules.yml.
component_name=rules.yml
```

`classpath` uses the platform's path separator and lists class directories or
jars explicitly, not Java launcher wildcards. The evidence directory must exist.
The matcher factory is a **public static zero-argument method returning List**.
The loader has a **static `load(InputStream, List)`** method; returned rule objects
must expose a public **`matcher()` returning `Predicate<String>`**.

**private-API reflection, offline copy only.** The precedent is the loader's own
`PolicySnapshotRuntimeFirewallViewTest.java:478–483`: `Class.forName(...)`,
`getDeclaredMethod("load", InputStream.class, List.class)`, `setAccessible(true)`,
then invocation with `ByteArrayInputStream`. The host passes the exact decoded
candidate bytes, not normalized or reserialized YAML. It calls the existing
rule predicates, including their native `java.util.regex` compilation and
`find()` semantics; it does **not** reproduce a surrounding registry, phase
selection, decoding, quoted-text processing, posture, or policy pipeline.
Private API compatibility is therefore checked by the local reproduction, not
promised across product upgrades. Named modules may require explicit access;
reflection failures are operational errors, not weaker eligibility checks.

## Cases and guard

Both JSON files are objects keyed by item ID, with this synthetic shape:

```json
{
  "d0": {"text": "synthetic-alpha", "expectation": "must_match"},
  "d1": {"text": "synthetic-ordinary", "expectation": "must_not_match"}
}
```

A case is correct if any loaded rule predicate hits for `must_match`, or none
hits for `must_not_match`. Correct cases score `1`, incorrect cases `0`.
Requested results keep request order; feedback is only `correct`/`incorrect`.
The guard file uses the same shape; **every** guard case must be correct before
any requested score is returned. `{}` explicitly means no guard cases for a
synthetic smoke, not evidence that a real golden gate ran. Guard text and
exception messages never appear in responses or evidence. Split ownership stays
with the kernel; the host does not select or carve splits.

## Optional repository-test command

Following the [SWE-bench evaluation harness](https://www.swebench.com/SWE-bench/guides/evaluation/),
the host can run an offline repository's existing tests on the patched tree.
Configure all four keys together:

```properties
guard_command=["./run-existing-tests", "--offline"]
guard_working_directory=offline-copy
guard_resource_path=offline-copy/resources/rules.yml
guard_timeout_seconds=<explicit-positive-seconds>
```

`guard_command` is a **JSON argv array**, not a shell command string; it must
contain an executable and may contain arguments. The JDK's
[`ProcessBuilder`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ProcessBuilder.html)
runs it directly, without adding a shell. Executable paths are interpreted by
process-launch rules, not relative to the properties file; use an absolute
executable or `./...` relative to the guard working directory. Properties-file
escaping still applies: double any JSON backslashes. Both configured filesystem
paths resolve relative to the properties file. The resource must be an existing
regular file inside the working directory, including after resolving symlinks.
Use only a disposable offline copy; never configure a live checkout.

`guard_timeout_seconds` is required, with **no default**. It accepts finite positive
seconds (including fractions) representable as JDK nanoseconds. Missing keys,
invalid argv, invalid paths, or an invalid timeout prevent startup.

For each distinct, verified candidate content ID, the host atomically replaces
the resource with the **exact candidate bytes** using a same-directory temporary
file and atomic rename, then runs the command in the configured directory.
Exit `0` passes; any non-zero exit returns **422 `guard_failed`**. Launch failures,
timeouts, or resource IO failures return **500 `guard_unavailable`**. On timeout,
the host captures the command's descendants, forcibly stops them and the root,
and waits for their exit before restoration, using the configured timeout again
as the termination-wait bound. A failed termination wait is operational, not a
pass. The descendant snapshot follows the JDK's
[`ProcessHandle`](https://docs.oracle.com/en/java/javase/21/docs/api/java.base/java/lang/ProcessHandle.html)
API; it is not isolation against a hostile process that spawns after the snapshot.
Before installing the candidate, the host captures the original resource mode
and timestamps in memory; the champion bytes are already held in memory. Only
after the command finishes does a `finally` block create a same-directory temporary
file from those bytes and attributes and atomically restore it before the response,
even if the guard deletes or modifies the destination. No restore temporary file
is present in the resource directory while the command runs. Unrecoverable
filesystem errors return `500 guard_unavailable`. Guard results, including failures,
are cached by content ID for this host process; scoring still uses each call's
requested items. Restart the host after changing the command or offline tree.

Restoration preserves the original source timestamps, so the build output may still hold
the previous candidate after a guard run. A content-based copy step recopies it on the next
run: `maven-resources-plugin` 3.4.0 and later use content-based change detection by default, so no
overwrite flag is needed. Since 3.5.0, this strategy is configurable through `changeDetection` (default:
`content`; https://maven.apache.org/plugins/maven-resources-plugin/resources-mojo.html#changeDetection).
Build tools that decide by timestamp only need their own documented forced-recopy option
in the guard command. The host never edits the product's build files.

Standard output and error are discarded and never echoed into responses or
evidence. With a command configured, each evidence record also includes
`guard_status` (`passed`, `guard_failed`, `guard_unavailable`, or `not_run` for
invalid requests) and `skipped_tests: "unknown"`: discarded output cannot provide
a trustworthy skipped-test count. Without a command configured, evaluation and
evidence retain their existing behavior. The command guard supplements rather
than replaces the native loader and golden-case checks.

## HTTP and evidence

| Route | Reply |
|---|---|
| `GET /artifact` | `200 {media_type: "application/yaml", components: {name: base64}}`; fixed startup champion snapshot |
| `POST /evaluate` | `{candidate_id, item_ids, components}` → `200 {results: [{item_id, score, feedback}]}` |
| `POST /apply` | `{candidate_id}` → `200 {applied: [...]}`; in-memory record only, no write or activation |

Exactly one configured component is required. Its content identity is recomputed
using [`candidate.content_id`](../../src/rsi_kernel/candidate.py): sorted names,
8-byte big-endian byte lengths, SHA-256. A mismatch, missing component, wrong
shape or unknown item returns `400`; wrong methods return `405`, path suffixes
`404`. Unlike the old synthetic evaluator seam, bytes are always required.

* **422 ineligible**: `IllegalStateException` thrown by the loader, a loader regex
  compilation failure, a golden-case failure (`GoldenGuardFailure`), or a
  configured test command's non-zero exit (`guard_failed`).
* **500 operational**: factory/reflection/IO failures and predicate execution
  faults, even an `IllegalStateException` outside the loader invocation; an
  unavailable or timed-out test command returns `guard_unavailable`.
* Errors contain only `{error, reason_class}`, never exception messages or text.

Each evaluation call appends one JSONL record:

```json
{"content_id":"...","status":"ok","reason_class":"none"}
```

Statuses are `ok`, `ineligible`, `operational`. Invalid transport requests are
logged as `operational`; an identity is empty when no bytes could be decoded,
and otherwise reflects **actual decoded bytes**, not the claimed ID. No case,
guard or candidate text is logged. If evidence cannot be written, the response
is `500 EvidenceWriteFailure`; it is impossible to append to a broken destination,
so repair it before rerunning. No success is returned without evidence.

The failure/score separation follows the
[SWE-bench evaluation harness](https://www.swebench.com/SWE-bench/guides/evaluation/).
The frozen kernel's non-2xx exception path (`loop.py`, candidate evaluation)
rejects ineligible candidates before comparing scores: a guard-failing candidate
cannot win a zero-score tie. A **valid** zero-score candidate remains a legitimate
tie; this host does not change that rule or add a score threshold.

This is the trusted local-example boundary already documented in design §4.1:
unbounded bodies, a fixed-shape JSON parser, serial evaluation, no authentication,
no regex isolation or loader/predicate execution deadline (the optional command
has its own required timeout). Do not expose it as a shared service
or run arbitrary candidates. The synthetic fixture only tests tiny regexes.

## Verify

```sh
CI=true uv run pytest -q tests/integration/test_firewall_host.py
CI=true uv sync --locked -q && CI=true uv run pytest -q
```

Use JDK 21 on `PATH`. Missing `javac` skips locally but fails in CI, mirroring
`test_java_host.py`. Tests compile a synthetic package-private loader, exercise
exact-byte reflection, scores, guard rejection through the unchanged CLI,
operational failures, identity-bound evidence, record-only apply, and a synthetic
repository-test command's exact bytes, restoration, cache, timeout, launch failure,
configuration validation, and output suppression. Real
built-copy reproduction is local only, outside CI and outside this repository;
never import real golden, sealed, evaluation or PII fixtures into public tests.
