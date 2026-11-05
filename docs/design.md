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
 │            for memory/skill artifacts Jev D4 advises add/merge/revise/    │
 │            discard here, so the evaluated library IS the admitted one     │
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
| Admit inside propose, then evaluate the resulting library | Evo-Harness: the Evolver writes the batch's harness, which the next batch uses (guide §4). Here the **LLM proposer is the evolver**; Jev only advises its choice at D4. |
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
| D4 | For a proposed memory/skill entry: add / merge-with-X / revise-X / discard? | as listed | discard (conservative) |
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
| T3 | harness code | sandbox only, each control from its own source: container per task and hidden tests excluded from the creator (OpenSkill 2606.06741 README); `--network none` (Docker docs, none driver); allowlist env + per-run prefix (Harness² 742d48f/f1417de, inverted); CPU/memory/file limits as user nobody (RSI-Anything candidate sandbox). Never in the kernel. | after T1 E0 is green |

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
