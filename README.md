# RSI-Kernel

A small, product-independent improvement loop for an agent's **harness**: its context and prompts, memory, skills and tool descriptions, then tool routing, and later harness code. The model stays frozen.

A host product plugs in through a thin adapter. Inside the loop:

- an LLM proposer writes data-only edits;
- a structured decision model (SystemOne contract; `jev-latest` for testing) makes bounded advisory choices on content-free state.

**Promotion is never decided by the loop.** A paired check on a sealed adjudication split, followed by human approval, decides it.

Status: design stage. See `docs/design.md` and the open issues.
See the [host integration guide](docs/host-guide.md).

## Working in this repo

See [CONTRIBUTING.md](CONTRIBUTING.md). In short: one issue per task, one branch per issue, and a pull request that closes the issue after independent review.
