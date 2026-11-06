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
  compilation failure, or a guard failure (`GoldenGuardFailure`).
* **500 operational**: factory/reflection/IO failures and predicate execution
  faults, even an `IllegalStateException` outside the loader invocation.
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
no regex isolation or execution deadline. Do not expose it as a shared service
or run arbitrary candidates. The synthetic fixture only tests tiny regexes.

## Verify

```sh
CI=true uv run pytest -q tests/integration/test_firewall_host.py
CI=true uv sync --locked -q && CI=true uv run pytest -q
```

Use JDK 21 on `PATH`. Missing `javac` skips locally but fails in CI, mirroring
`test_java_host.py`. Tests compile a synthetic package-private loader, exercise
exact-byte reflection, scores, guard rejection through the unchanged CLI,
operational failures, identity-bound evidence, and record-only apply. Real
built-copy reproduction is local only, outside CI and outside this repository;
never import real golden, sealed, evaluation or PII fixtures into public tests.
