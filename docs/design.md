# How we build it: harness-level RSI loop with a SystemOne decision model

Design principles:
- a standalone kernel, independent of any host product;
- the harness is improved first; changing the model is optional and out of scope here;
- the hosted `jev-latest` SystemOne model is used for testing, with swappable offline backends later (§3).

All interpretation is **INFERENCE**. Choices without direct precedent are marked **NAMED LOCAL EXCEPTION**. Each precedent below is cited by public paper, repository or vendor document.

---

## 1. What we are building

A small, product-independent **improvement loop** for an agent's *harness*: context/prompts, memory, skills, tool descriptions, then tool routing, with harness code later. The model stays frozen.

A host product plugs in through a thin adapter (§4). Inside the loop:
- an LLM proposer writes data-only edits;
- a fast **SystemOne decision model** (Jev) makes a few bounded structured choices, using **content-free state** (§3).

Promotion is never decided by the loop. A paired check on a sealed adjudication split, plus a human approval, decides it (§2).

In the guide's terms (Agent = Model + Harness), this is **teacher-update, harness-artifact RSI, offline first**.

## 2. The loop (v1)

```
 Host (frozen model + champion harness version)
   │ dev traces + outcomes  (research: public/synthetic test bed only)
   ▼
 ┌──────────────── L1: improvement loop ─────────────────────────────────────┐
 │ 1 TARGET   Jev D2: which component to change (content-free state)         │
 │            baseline = round-robin over components                         │
 │ 2 PROPOSE  in the isolated proposer runtime: reflective mutation          │
 │            (GEPA ProposalFn-style library call) writes the edit;          │
 │            memory adapter: validate + exact-dedupe the draft as "add";    │
 │            paired dev evaluation, not a D4 veto, decides selection (#45)   │
 │            → one Candidate hash                                           │
 │ 3 DEV EVAL budgeted (reserve before running), paired vs champion,         │
 │            dev-side non-regression check                                  │
 │ 4 SELECT   best dev candidate, frozen (hash)                              │
 │ 5 LOG      append-only outcome log; exact-hash duplicate suppression of   │
 │            candidates that showed a DEV regression (dev view only)        │
 │ STOP       bounded attempts + per-campaign spend cap (rule, not model)    │
 │            evaluator calls: hard reserved ceiling; proposer, evaluated-   │
 │            agent and Jev calls (failed ones included): metered, campaign  │
 │            halts at the first check past the cap                          │
 └──────────────────────────────────┬─────────────────────────────────────────┘
                                    ▼
 ACCEPT (outside the loop): sealed adjudication split, paired per scene,
 host-registered rule → human approval bound to hashes → host record-only
 → enforce → rollback.                     Holdout: reported once per campaign.
```

**Deliberately not in v1.** Each item returns only with its own evidence:
- **A pre-screen.** RSI-Anything's own dev selection set its world-model weight to 0.
- **A self-updated strategy library.** A loop-written library with no evaluator is an unverified L2. In its controlled study, VERSE 2610.02616 found that optimizer self-evolution failed without execution-based verification. The AIDE² outlier filter, written by the loop itself, broke silently. Optional L2 means changing the improver itself, which is a different thing.
- **A Jev failure taxonomy (D1).** No registered taxonomy exists, and writing one now would be invention.
- **Jev stop/escalate (D6).** Stopping is a budget and attempt rule. Precedents: GEPA's 429 signal, penguin-harness bounded steps.

| Step | Precedent |
|---|---|
| Two levels, retention on a hidden score | AIDE² arXiv 2609.26457: public score guides the inner loop, private score decides retention; held-out MLE-Bench Lite paired +0.053. The fixed per-evaluation allowance and the paired +0.053 (p=0.0024) figure are **blog-reported** (Weco blog post); +0.053 was not located in the paper text, so it stays unverified against the paper. |
| Teacher update, not self-update | Guide §4: self-update can persist misdiagnoses. Recuris: a fixed meta-agent edits skill memory after validation. |
| Draft candidate inside propose, then evaluate before selection | Memory adapter ([#45](https://github.com/CLTG-LLC/RSI-Kernel/issues/45)): validated, non-duplicate drafts become isolated candidates without a D4 veto; the existing paired dev rule decides selection. Precedents: [Voyager arXiv 2305.16291 §2.3](https://arxiv.org/abs/2305.16291), [Recursa arXiv 2611.04035 §5.1](https://arxiv.org/abs/2611.04035), and [GEPA arXiv 2507.19457](https://arxiv.org/abs/2507.19457). |
| Dev-side non-regression | Growing Harness 2609.26760, Self-Harness 2606.09498, HarnessEvolve 2609.00829, DarwinX 2608.07545 and SkillEvoReg 2609.30861 all describe regression / non-regression gates. |
| Duplicate suppression | **v1 simplification:** exact-hash suppression of candidates that showed a dev regression. Operational failures and inconclusive evaluations are not suppressed. Suppression applies **only within the same frozen campaign/evaluation context** (same champion, dev split and evaluator hashes) and is cleared when any of them changes. This is a simplified form of SkillSmith 2606.01314 version-scoped nogoods (scoped to component versions and invalidated when versions change); the full mechanism is not claimed. |
| Noise floor | Phantom Gains 2608.20290: an unchanged-control arm. Separately, FinEvo-Bench's state-reset control measures gain from retained experience, which is a different construct. |
| Release | SageMaker Model Registry approval status; MOSS 2605.22794: consent-gated swap and health-probe rollback. |

## 3. Jev (SystemOne) in v1

**Contract:** `state + questions{name:{type:"choice", instructions, criteria}} → answers{name:{choice}}`. This is the SystemOne choice-question shape; the kernel rejects any answer outside the asked choices (`src/rsi_kernel/decision/envelope.py`).

**Fixed request envelope.** The kernel builds the *whole* outbound request from a template held in the repo:
- **Instructions and criteria:** constant strings committed in the repo.
- **Options:** fixed operation enums (`add / merge / revise / discard`, `cheap / strong`, `none`) plus **kernel-issued opaque IDs** for components and memory/skill entries (e.g. `c3`, `e17`). D4 choices are generated from those IDs with fixed templates. Candidate text is never used as an option label or criterion. One contract test each for D2, D4 and D5.
- **State:** numeric fields only, read from the **dev-only public view**. That means per-component dev pass/fail counts, dev paired score deltas, attempt counts and budget used.
- **Not sent:** hashes, trace text, prompts, or any customer or test-bed content.
- **Unknown fields:** rejected before sending.

This applies the data-minimisation principle: GDPR Art. 5(1)(c), and OWASP LLM02:2025 Sensitive Information Disclosure mitigations. The envelope schema itself is a **NAMED LOCAL EXCEPTION**, validated by tests.

**Tests (S2):**
- A synthetic canary string placed in traces and candidates never appears in any outbound request. This covers state, options, criteria, instructions and error paths.
- Changing adjudication/holdout outcomes leaves every outbound Jev request and every later loop decision unchanged.

**No private-result path:** Jev requests and duplicate suppression read only dev outcomes. Adjudication/holdout outcomes and their logs never enter the loop view (§2), and a campaign is closed once its candidate goes to adjudication. Any decision that needs content requires an **offline backend**.

**Decisions (advisory, logged):**

| # | Question | Options | Baseline / fallback |
|---|---|---|---|
| D2 | Which component should change next? | registered component ids + "none" | round-robin component selection, GEPA's own default round-robin component selector |
| D4 (legacy) | Retained for historical records and in-process compatibility; not called by memory adapter draft admission ([#45](https://github.com/CLTG-LLC/RSI-Kernel/issues/45)). Drafts are evaluated first, then judged by the existing paired dev rule (§2). | add / merge-with-X / revise-X / discard | discard (legacy only) |
| D5 (optional) | Send this proposal to the cheap or strong proposer model? | cheap / strong | strong |

**Never decided by Jev:** acceptance, release, labels, the evaluator, permissions, or stopping.

**Replay:**
- Every Jev call is an **ordered** record of sequence number, backend, model id, the exact request envelope (an immutable snapshot) and the answer, plus response headers where available.
- Timeouts and malformed answers are logged as fallback decisions.
- Replay re-reads these records and never re-queries. Precedent: RSI-Anything re-derives decisions from recorded predictions.
- This is **deterministic replay** of recorded records, not live repeatability of the whole loop, which stays a separate measurement.

**Backends (one port):**

| Backend | Use |
|---|---|
| `jev-latest` (Experiential Labs `POST /v1/systemone`) | testing now |
| deterministic baseline | always available; it is what Jev must beat |
| NeoHorse-Jev-4B (TokenRhythm, Apache-2.0, prefill-only, probabilities, local vLLM/SGLang) | first offline backend, added when a decision needs content or reproducibility |

Benchmark figures for all backends are vendor-reported. The **NeoHorse-Jev-4B README** (not Experiential Labs) states that multilingual and calibration evaluation are not yet available. We measure Jev against the deterministic baseline ourselves.

## 4. Host adapter contract (minimal)

| Call | Purpose | Precedent |
|---|---|---|
| `get_artifact() → Candidate` | current champion harness artifact (data only) | GEPA `Candidate`, Proteus adapter |
| `evaluate(candidate, example_ids) → per-item results` | dev evaluation only, run by the host or test-bed harness | GEPA `evaluate`, Shinka evaluator |
| `apply(approved_candidate_hash)` | the host activates an approved version (record-only first) | Reef manual activation, MOSS consent-gated swap |

Splits are **carved by the kernel config, not the host**. Proteus validates split purposes at config load (`recipes/config.py:146-154`); we add an `adjudication` purpose. For a test bed that ships only exploration plus strict held-out, the kernel splits exploration into dev and adjudication, and uses the strict held-out set as holdout. The carving rule is frozen in pre-registration.

### 4.1 Frozen host contract for non-Python hosts (issue #52)

Synthetic Java integration only (`examples/java-host`), not a product integration. Transport is the S6 HTTP bridge, the smallest existing choice; no custom RPC. MCP is offered only as the optional extra below (#50), over the same functions.

**Java → Python control.** Console entry `rsi-kernel` ([PyPA console_scripts](https://packaging.python.org/en/latest/specifications/entry-points/), `src/rsi_kernel/cli.py`). Each subcommand reads `--config <file.json>` and prints exactly one JSON object on stdout; logs go to stderr. Exit codes: 0 success, 1 runtime or config error, 2 usage error (argparse's standard code); stdout is empty on any error.

| Subcommand | Calls | stdout |
|---|---|---|
| `run-campaign --config C` | `loop.run_campaign` | `{outcome, stop_reason, attempts, evaluator_items_used, champion_id, selected_id}` |
| `accept --config C [--approval A]` | `loop.accept` | `{outcome, candidate_id}`; `outcome` ∈ `loop.OUTCOMES`. Blocks at the approval step until `A` exists (see below) |
| `status --config C` | none (reads state) | `{campaign, acceptance, approval_request}` |

Config `C`: `campaign_id`, `host_url`, `store` (campaign state and the public/private archive), `component_ids`, `evaluator_hash`, `code_hash`, `splits` (the `splits.load_splits` shape), `bounds` `{max_attempts, spend_cap, eval_cap, runs}`, `proposals` (frozen candidates, see artifact encoding below). `campaign_id` must be one filename component; the resolved state file (symlinks followed) must sit directly in `store`. One champion snapshot is fetched per invocation and is the only one the kernel sees; `accept` rejects a host whose champion changed since the campaign. The retention and non-regression rule is the GDPevo prereg rule, `mean_delta >= 0`. The decider is fixed to the deterministic backend, and `spend` is fixed at 0: this synthetic contract does no spend metering.

Approval `A` is an `ApprovalRecord` JSON `{candidate_hash, evaluator_hash, data_hash, code_hash, approver}`; without `--approval` it is `<store>/approval.json`. Before any callback, `accept` rejects `<store>/approval-request.json` and the default `<store>/approval.json` if they resolve outside the store (the state file's check); an explicit `--approval` is the caller's own path. The kernel never creates it. Order (issue #60, the GDPevo pilot's request-then-wait flow, `src/rsi_kernel/approval.py`):

1. `accept` runs adjudication. With no candidate, or a failed adjudication, it returns `no_improvement` or `failed_gate` and files nothing.
2. Otherwise it writes the `ApprovalRequest` `{campaign_id, candidate_hash, evaluator_hash, data_hash, code_hash}` to `<store>/approval-request.json`; `status.approval_request` reports the same hashes.
3. It then waits, polling once a second with no timeout (the operator stops the process), until `A` exists.
4. The owner writes `A` from those hashes, and `accept` continues: a matching record gives `updated` and calls `apply`; a present but malformed or mismatched record gives `not_updated`. Both files are published atomically, a sibling temp file then [`os.replace`](https://docs.python.org/3/library/os.html#os.replace), because `accept` reads `A` as soon as its name appears and a partial file counts as malformed.

The campaign is marked adjudicated in step 1 (`loop.accept`), before the wait, so the adjudication split is spent once: stopping `accept` during the wait leaves no outcome, and a later `accept` for that campaign raises `CampaignClosed`. Write `A` rather than restarting.

**Python → Java callbacks** (§4 calls over HTTP on loopback). `host_url` must be plain `http` to 127.0.0.1 or ::1 (numeric only; names such as localhost are rejected because they go to the resolver), matching the Java bind; redirects are not followed and environment proxies are ignored (the `decision/backends.py` opener pattern). An artifact is `{media_type, components: {name: base64(bytes)}}`; its identity is `candidate.content_id` over the decoded bytes.

| Call | HTTP | Body / reply |
|---|---|---|
| `get_artifact()` | `GET /artifact` | reply: champion artifact |
| `evaluate(candidate, ids)` | `POST /evaluate` | `{candidate_id, item_ids, components}` → `{results: [{item_id, score, feedback}]}` in request order. The host recomputes `content_id` and answers 400 on mismatch. |
| `apply(hash)` | `POST /apply` | `{candidate_id}`; record-only, as the GDPevo adapters |

Without `components`, `/evaluate` keeps the S6 evaluator-seam shape that `DevEvaluatorServer` forwards.

The Java example is a trusted local example, not a hardened service for arbitrary input: request sizes are unbounded and its JSON parser is not fully RFC 8259 validating.

#### MCP surface (issue #50, optional extra)

A second thin entry over the same three B1 functions, for MCP hosts. It is not a product transport: the Java host remains on the HTTP bridge above, and callbacks — `get_artifact`, `evaluate`, `apply` — never travel over MCP.

| Item | Value |
|---|---|
| Transport | stdio, [MCP 2025-11-25 transports §stdio](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports); newline-delimited JSON-RPC, stdout carries protocol messages only, logs on stderr (verified against the spec text, fetched 2026-11-06) |
| SDK | official `mcp` 2.3.0, `MCPServer` (`src/rsi_kernel/mcp_server.py`); optional extra `[mcp]`, MIT |
| Console script | `rsi-kernel-mcp` ([PyPA console_scripts](https://packaging.python.org/en/latest/specifications/entry-points/)); without the extra it prints how to install it and exits 1 |
| Tools | exactly `run_campaign`, `accept`, `status` |
| Tool arguments | `config` (the same config file `--config` takes); `accept` also `approval` (the `--approval` file) |
| Tool result | the same JSON object the matching subcommand prints; an expected failure (bad config, host error, stale state) is an MCP tool error |

**Rejected input spends nothing.** The config contract is checked once, before any host callback or evaluation, by the shared `cli._preflight`; each check reuses the kernel's own validator (`EnvelopeBuilder` id registry, `splits.load_splits`, `evaluator.Budget`'s cap rule, `loop._validate_runs`) rather than restating it, so the CLI and MCP reject the same configs. It rejects only values the kernel would reject much later, so accepted values keep their exact kernel semantics — `max_attempts: -1` still yields `no_improvement` and `1.0` still yields `selected`. The guarantee covers **rejected input only**: a runtime failure after execution has begun — a host error, a malformed evaluation row, a decision-backend failure — may already have consumed evaluator items while leaving the campaign state absent or unchanged.

The SDK name changed in v2: `FastMCP` is now `MCPServer` ([migration guide](https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver)). There is no approval-creation tool and no shell or filesystem tool, so MCP cannot mint an approval: `accept` reads a record the host or owner wrote and gives `not_updated` if it does not match. The `accept` tool call waits for the owner's approval file exactly as the CLI does (steps 2–4 above), so it may block for as long as the owner takes. MCP allows a long-running request, but clients **SHOULD** set request timeouts and cancel on expiry ([MCP 2025-11-25 lifecycle §Timeouts](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle#timeouts)); a host that cannot hold one call open that long should run `rsi-kernel accept` from the CLI instead.

```sh
pip install 'rsi-kernel[mcp]'
rsi-kernel-mcp          # then connect any MCP client over stdio
```

## 5. Build vs reuse

- **Build:** the thin kernel in the new repo. Not forking Proteus (about 42.6k LOC, agent-shaped) or Reef (its improver reads gate tasks).
- **Reuse (library, MIT):** GEPA's concrete proposer, `InstructionProposalSignature` + `run_proposal` (`src/gepa/strategies/instruction_proposal.py`:138,147, lead-verified), called standalone inside the proposer runtime. It needs reflection records and a model callable.
  - **Input mapping:** per-item dev results from the host's `evaluate` (input, output, feedback), so the adapter's `evaluate` must return per-item feedback.
  - **Output:** the new text for one registered component. An empty answer or no change means "no candidate".
  - (`adapter.py:49-97` `ProposalFn` is only the protocol.) Also reuse its `EvalServer`/`BudgetTracker` classes where they fit, adding our own up-front reservation (GEPA's budget tracker can overshoot). We do **not** run GEPA's optimizer loop, to avoid two loops over one budget. "GEPA proposer calling our endpoint" is INFERENCE; validate it in S1.
- **Port as patterns (lead-verified lines):**
  - Reef paired comparison, `evaluators.py:60-81`: **pair alignment only**. Reef drops a pair when either side is missing. We instead treat a missing, corrupt or mismatched result as a **failure that blocks acceptance** (§2). Tests: missing on the candidate side only, mismatched task/run identity, suppressed observation.
  - penguin-harness snapshots, version numbers and closed failure codes.
  - Harness² allowlist environment and per-rollout prefixes.
  - RSI-Anything gain-and-cost dev selection, `rsi.py:53`, and its frozen protocol.
  - ShinkaEvolve public/private metrics.

## 6. Artifact tiers

| Tier | Artifacts | Isolation | When |
|---|---|---|---|
| T1 | prompts/context bundle, memory entries, skills, tool descriptions | proposer container, no protected mounts | first: **one** adapter (prompt/context), second only after a measured result |
| T2 | tool routing among approved tools | same | next |
| T3 | harness code | sandbox only, each control from its own source: container per task and hidden tests excluded from the creator (OpenSkill 2606.06741 README); `--network none` (Docker docs, none driver); allowlist env + per-run prefix (Harness² 742d48f/f1417de, inverted); CPU/memory/file limits as the non-root invoking uid:gid (Docker run User; issue #59). Never in the kernel. | after T1 E0 is green |

### T3 harness-code contract (issue #49)

- **Editable:** exactly one UTF-8 `solver.py`, replaced as a whole file, never a
  diff. **NAMED LOCAL REPRESENTATION SOLVER-PROMPT-SCRIPT:** the trusted
  `SOLVER_COMMAND` dispatch invokes `python3 /harness/solver.py` in a separate
  per-task container. stdin is the trusted task prompt (UTF-8); stdout must be
  exactly one JSON object `{"prompt": "non-empty Codex task prompt"}`. stderr is
  diagnostic only. The script may read `/work/input`, `/work/skill` and
  `/work/environment_access.md`; it cannot supply runtime options or scores.
  The host validates that object and passes only its string after the `--`
  option terminator in the code tier's trusted Codex invocation. The shared S4
  command stays unchanged. Positional prompt precedent:
  [Codex 0.166.0 cli.rs:81–85](https://github.com/openai/codex/blob/rust-v0.166.0/codex-rs/exec/src/cli.rs#L81-L85).
  This is solver prompt logic, not arbitrary replacement
  of the provider/agent runner. Full-file rewrite precedent:
  [OpenEvolve configuration.md:74](https://github.com/algorithmicsuperintelligence/openevolve/blob/0fa8c4de9faff5d11e2f819557c6b14e0add3a23/docs/configuration.md#L74).
- **Trusted:** command dispatch and Codex invocation, frozen SKILL.md, model,
  provider/runtime config, images, input staging, official grading, metering,
  and timeout. Candidate code runs before, and in a different container from,
  Codex configuration and sessions: it cannot forge the trusted session meter.
  No candidate directory, score file or grader/evaluator/gold is mounted in the
  Codex container. The external grader still uses `--network none`.
- **Mapping:** only `{"solver.py": <source>}` with `text/plain` is admitted;
  text/plain remains a byte transport, not executable permission in the kernel.
  The code adapter alone stages it to the fixed `/harness/solver.py`. Other keys,
  extra keys, path traversal and symlinked staging paths are rejected before
  execution. Both content identity and the parent's exact singleton tuple are
  checked against the frozen champion; an unchanged root champion has no parent.
- **Isolation:** both candidate-code and trusted-agent containers use the invoking
  host process's numeric `uid:gid` (`os.getuid()` / `os.getgid()`); a root host UID
  causes `STOP root_host_uid` before staging commands, never a root fallback.
  This keeps private bind-mounted outputs host-readable on native Linux Docker
  (issue #59; [Docker run User](https://docs.docker.com/engine/containers/run/#user)).
  `/work` retains its private `0700` staging mode; cross-user chmods are unnecessary.
  Explicit CPU, memory and file-size limits bind the untrusted candidate-code
  container only. Both containers remain non-root, with dropped capabilities and
  no-new-privileges; the trusted agent has no CPU, memory or file-size limits
  imposed by `CodeLimits`. See `docs/prereg-e1c-amendment-1.md` for the post-smoke,
  pre-campaign operational amendment; the frozen resource values are unchanged.
  Candidate code has a read-only filesystem with disposable `/tmp`, no writable
  host mounts, and `--network none`: it needs no service calls to transform stdin
  into a prompt. Only the trusted agent joins the existing internal task/model
  forwarder network, so candidate Python cannot bypass Codex metering.
  The code tier's trusted PIPE collector bounds stdout and stderr independently
  to the existing frozen `file_bytes` allowance (RLIMIT_FSIZE alone cannot bound
  pipes). Overflow kills, verifies stopped, and removes the owned container;
  sizes are checked again before text decoding/JSON parsing. The data-only
  Docker runner and shared command retain their existing behaviour.
  Docker controls follow [Docker run resource, user, ulimit and security options](https://docs.docker.com/reference/cli/docker/container/run/).
  **NAMED LOCAL EXCEPTION T3-RESOURCE-VALUES:** `cpus`, `memory_bytes` and
  `file_bytes` are required frozen parameters, with no defaults. Any supplied
  values remain local exceptions pending workload feasibility measurement;
  **NAMED LOCAL EXCEPTION T3-SYNTHETIC-VALUES:** the tiny-container checks use
  1 CPU, 268435456 memory bytes and 1048576 file bytes. Successful execution
  validates only this synthetic fixture, not GDPevo capacity. Limits, fixed
  SKILL.md identity and timeout are included in the frozen execution identity,
  checked again before final evaluation. No PID limit
  is added: [SWE-bench container creation:103–125](https://github.com/SWE-bench/SWE-bench/blob/02e7a74ffd0b707aab73d203fe87bdc7c76afc8e/swebench/harness/run_evaluation.py#L103-L125)
  establishes no such workload values. On timeout kill, verify stopped, then
  remove only that owned container; retain evidence and other scoped resources.
- **Driver:** `gdpevo_code` reuses S4 `Hooks`, paired dev retention, record-only
  apply and the existing isolated proposer. No live run is authorized by these
  synthetic implementation tests. Checks: exact-key/path/symlink and parent
  denial, non-root/resource flags, trusted-score authority, scoped timeout
  removal, synthetic reference/change grading, and unchanged data-only adapters.

## 7. Build slices (one GitHub issue per slice)

1. **S0+S1, together.** Contracts, plus wrapping GEPA's EvalServer/BudgetTracker pieces with:
   - our split purposes;
   - the reservation;
   - the allowlist container;
   - E0 denial tests: a hostile proposer is denied, and evaluator invocations are counted.

   RED/GREEN first.
2. **S2 (parallel).** SystemOne port: the `jev-latest` backend, the deterministic baseline, the fixed request envelope with canary and private-outcome-invariance tests, ordered log replay, and off-list rejection.
3. **S3.** One T1 text-only `SKILL.md` adapter on **GDPevo** @5082a777 (Apache-2.0; issue #3; [pinned tree](https://github.com/Prism-Shadow/GDPevo/tree/5082a777379156a048881e94940d640702e5e09a)). Its official per-task `eval/eval.sh` graders are executable; the host injects solver attempts, carves train tasks into dev/adjudication, and reserves test tasks for holdout. Admitting exactly `SKILL.md` is a **NAMED LOCAL RESTRICTION**, not an upstream package invariant. The proposer mounts staged dev inputs only, cannot mount the source repository or adjudication inputs, and receives only projected score/correct feedback; upstream judge access is disabled for both proposer and solver. GEPA's standalone proposer is pinned at 3d344691. GDPevo shares the index's org and public test answers introduce pretraining-contamination risk. Solver-image readiness, provider compatibility, verifier CPU cost and our model-call cost remain unmeasured. S3Gym (arXiv 2608.31100) has no public release and remains a future candidate, not a paper reconstruction.
4. **S4 single-adapter pilot** on GDPevo. This is **not** E1a; classifier-style acceptance fields (1% FPR, attack scenes, F1) do not carry over.
   - **GDPevo-specific pre-registration (`docs/prereg-gdpevo-pilot.md`), frozen before any fitting:**
     - explicit per-group train task assignments to dev / adjudication; upstream test tasks reserved for holdout;
     - task pairing, with bootstrap clustered by task group;
     - native evaluator score;
     - retention rule;
     - uncertainty method;
     - unchanged-control protocol.
   - **Report:**
     - paired dev and adjudication results;
     - Jev vs the deterministic baseline at D2;
     - cost;
     - exposure log.
   - **D4 is not reported** until a memory/skill artifact exercises it.
5. **S5:** a second harness artifact (memory or skill library), which exercises D4 and turns S4 into the two-artifact E1a.
6. **S6:** E1b second-host integration.

Campaign driver (issue #15): `src/rsi_kernel/loop.py` runs the §2 loop (`run_campaign`) and the one-shot `accept` step on any §4 adapter; bounds and rules are injected from the prereg.

Neither S5 nor S6 is claimed until it runs.

Durations: needs measurement.
