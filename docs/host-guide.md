# Host integration guide

## What the host provides

Provide three calls. The kernel does not replace your evaluator or activate a version without approval. ([docs/design.md:119-127](design.md#L119-L127), [src/rsi_kernel/loop.py:214-225](../src/rsi_kernel/loop.py#L214-L225))

- **`get_artifact() → Candidate`** returns the current champion as data-only components. `Candidate.id` hashes the component names and bytes; it is not a version label you choose. ([docs/design.md:123](design.md#L123), [src/rsi_kernel/candidate.py:26-49](../src/rsi_kernel/candidate.py#L26-L49))
- **`evaluate(candidate, example_ids) → per-item results`** runs dev evaluation. Return item identity, score and feedback for reflection. The loop passes champion dev results to the proposer. ([docs/design.md:124](design.md#L124), [docs/design.md:133](design.md#L133), [src/rsi_kernel/loop.py:134](../src/rsi_kernel/loop.py#L134))
- **`apply(approved_candidate_hash)`** handles an approved hash. Start record-only: both GDPevo adapters record the decision without swapping artifact bytes. ([src/rsi_kernel/adapters/gdpevo/adapter.py:112-117](../src/rsi_kernel/adapters/gdpevo/adapter.py#L112-L117), [src/rsi_kernel/adapters/gdpevo_memory/adapter.py:44-48](../src/rsi_kernel/adapters/gdpevo_memory/adapter.py#L44-L48))

## What stays in the kernel

- **Split carving.** Freeze assignments in kernel configuration, not host selection logic. The loader rejects overlaps and allows selection eligibility only for dev. GDPevo's carving helper uses explicit dev task lists, remaining train tasks for adjudication, and test tasks for holdout. It does not choose a random split ratio. ([docs/design.md:127](design.md#L127), [src/rsi_kernel/splits.py:46-85](../src/rsi_kernel/splits.py#L46-L85), [src/rsi_kernel/adapters/gdpevo/tasks.py:47-63](../src/rsi_kernel/adapters/gdpevo/tasks.py#L47-L63))
- **Budget and paired comparison.** `run_campaign` reserves item evaluations before calling the host. It compares candidates with the champion, applies the supplied non-regression rule, and selects the passing candidate with the highest mean delta. Bounds and rules are injected, not chosen by the driver. ([src/rsi_kernel/loop.py:90-117](../src/rsi_kernel/loop.py#L90-L117), [src/rsi_kernel/loop.py:144-165](../src/rsi_kernel/loop.py#L144-L165))
- **Acceptance and approval.** `accept` evaluates one frozen candidate outside the loop. It uses private paired adjudication and the supplied retention rule. The approval callback must return matching candidate, evaluator and data hashes before `apply` runs; it is not a built-in human approval screen. ([src/rsi_kernel/loop.py:196-225](../src/rsi_kernel/loop.py#L196-L225))
- **Holdout once.** Holdout is optional. A completed acceptance evaluation closes the campaign against another adjudication/holdout call. A crash before the closure record leaves it open: this is not crash-safe exactly-once execution. ([src/rsi_kernel/loop.py:200-213](../src/rsi_kernel/loop.py#L200-L213))
- **Decision log.** The envelope admits registered choices and numeric dev state, not candidate text. The decider records the envelope, answer and any fallback; replay uses recorded answers. Supply a persistent log stream. ([src/rsi_kernel/decision/envelope.py:61-91](../src/rsi_kernel/decision/envelope.py#L61-L91), [src/rsi_kernel/decision/log.py:1-7](../src/rsi_kernel/decision/log.py#L1-L7), [src/rsi_kernel/decision/log.py:62-104](../src/rsi_kernel/decision/log.py#L62-L104))

## Non-Python hosts: the Java worked example

Keep the kernel unchanged. Register `HttpEvaluator(java_base_url)` as the callable in `DevEvaluatorServer`, with frozen dev IDs and an item cap. The bridge forwards reserved batches to Java's `POST /evaluate`. ([tests/integration/test_java_host.py:122-131](../tests/integration/test_java_host.py#L122-L131), [examples/java-host/http_evaluator.py:23-30](../examples/java-host/http_evaluator.py#L23-L30))

The JSON request has `candidate_id` and `item_ids`. Java returns a `results` array with `item_id`, `score` and `feedback`, in request order. The kernel wrapper adds `budget: {cap, used}` and checks that returned IDs match the requested order. ([examples/java-host/EvaluatorHost.java:4-9](../examples/java-host/EvaluatorHost.java#L4-L9), [src/rsi_kernel/evaluator.py:90](../src/rsi_kernel/evaluator.py#L90), [src/rsi_kernel/evaluator.py:115-139](../src/rsi_kernel/evaluator.py#L115-L139))

The kernel endpoint rejects invalid or non-dev requests with HTTP 400, exhausted budgets with 429, and host failures with 502. A failed host call still spends its reservation. The endpoint has no authentication and binds only to loopback. ([src/rsi_kernel/evaluator.py:71-90](../src/rsi_kernel/evaluator.py#L71-L90), [src/rsi_kernel/evaluator.py:98-106](../src/rsi_kernel/evaluator.py#L98-L106), [src/rsi_kernel/evaluator.py:118-130](../src/rsi_kernel/evaluator.py#L118-L130))

The full host contract (console control plus `get_artifact`/`evaluate`/`apply` callbacks with real artifact bytes) is frozen in [design §4.1](design.md); the same Java host implements it. Without `components`, `/evaluate` still treats `candidate_id` as toy keyword text for the S6 seam. ([examples/java-host/EvaluatorHost.java:59-70](../examples/java-host/EvaluatorHost.java#L59-L70), [docs/results/e1b-second-host.md:60-64](results/e1b-second-host.md#L60-L64))

## Host isolation duties

**Supply solver isolation yourself.** The current GDPevo adapter calls an injected solver; it does not launch a solver sandbox. It stages input files without grader files, then grades the prediction outside that solver call using the frozen `eval.sh`. The grader gets a minimal environment with judge access disabled. Offline grading still needs a host-enforced network boundary: this subprocess call does not create one. ([src/rsi_kernel/adapters/gdpevo/adapter.py:134-160](../src/rsi_kernel/adapters/gdpevo/adapter.py#L134-L160))

**Keep credentials out of the sandbox.** The proposer launcher disables networking and mounts dev data read-only plus a writable output directory. It forwards explicitly supplied environment values; it does not identify or remove secrets from them. GDPevo blocks source/private-store mounts and requires judge access off for the proposer and solver. These proposer controls do not prove solver isolation. ([src/rsi_kernel/isolation.py:40-56](../src/rsi_kernel/isolation.py#L40-L56), [src/rsi_kernel/adapters/gdpevo/adapter.py:104-121](../src/rsi_kernel/adapters/gdpevo/adapter.py#L104-L121), [src/rsi_kernel/adapters/gdpevo/runtime.py:1-27](../src/rsi_kernel/adapters/gdpevo/runtime.py#L1-L27))

## Integration checklist

- [ ] Return a data-only, content-addressed champion. ([src/rsi_kernel/candidate.py:12-49](../src/rsi_kernel/candidate.py#L12-L49))
- [ ] Freeze disjoint dev, adjudication and holdout assignments. ([src/rsi_kernel/splits.py:46-85](../src/rsi_kernel/splits.py#L46-L85))
- [ ] Return ordered per-item dev scores and feedback through the budgeted evaluator. ([src/rsi_kernel/evaluator.py:81-90](../src/rsi_kernel/evaluator.py#L81-L90), [src/rsi_kernel/evaluator.py:132-139](../src/rsi_kernel/evaluator.py#L132-L139))
- [ ] Supply campaign bounds, non-regression and retention rules. ([src/rsi_kernel/loop.py:90-98](../src/rsi_kernel/loop.py#L90-L98), [src/rsi_kernel/loop.py:196-201](../src/rsi_kernel/loop.py#L196-L201))
- [ ] Isolate the solver, exclude sandbox credentials, disable judge access, and grade outside the solver. ([src/rsi_kernel/adapters/gdpevo/adapter.py:134-160](../src/rsi_kernel/adapters/gdpevo/adapter.py#L134-L160), [src/rsi_kernel/isolation.py:49-56](../src/rsi_kernel/isolation.py#L49-L56), [src/rsi_kernel/adapters/gdpevo/runtime.py:17-27](../src/rsi_kernel/adapters/gdpevo/runtime.py#L17-L27))
- [ ] Wire hash-bound approval and record-only apply; keep holdout outside selection. ([src/rsi_kernel/loop.py:196-225](../src/rsi_kernel/loop.py#L196-L225), [src/rsi_kernel/adapters/gdpevo/adapter.py:112-117](../src/rsi_kernel/adapters/gdpevo/adapter.py#L112-L117))
- [ ] Persist the decision log and verify recorded-answer replay. ([src/rsi_kernel/decision/log.py:1-7](../src/rsi_kernel/decision/log.py#L1-L7), [src/rsi_kernel/decision/log.py:79-104](../src/rsi_kernel/decision/log.py#L79-L104))

## Worked examples

- [GDPevo SKILL.md adapter](../src/rsi_kernel/adapters/gdpevo/adapter.py): text-only artifact, dev checks and record-only apply. ([src/rsi_kernel/adapters/gdpevo/adapter.py:31-38](../src/rsi_kernel/adapters/gdpevo/adapter.py#L31-L38), [src/rsi_kernel/adapters/gdpevo/adapter.py:108-132](../src/rsi_kernel/adapters/gdpevo/adapter.py#L108-L132))
- [GDPevo memory/skill-library adapter](../src/rsi_kernel/adapters/gdpevo_memory/adapter.py): renders the library and verifies staged skill bytes before and after the solver. ([src/rsi_kernel/adapters/gdpevo_memory/adapter.py:23-48](../src/rsi_kernel/adapters/gdpevo_memory/adapter.py#L23-L48))
- [Java evaluator host](../examples/java-host/EvaluatorHost.java), [HTTP bridge](../examples/java-host/http_evaluator.py), and [run instructions](results/e1b-second-host.md): dev evaluation only. ([docs/results/e1b-second-host.md:35-48](results/e1b-second-host.md#L35-L48), [docs/results/e1b-second-host.md:60-64](results/e1b-second-host.md#L60-L64))
