# Review path boundary

This adapts the team's repository review-path standard (v1.0, 2026-10-21) to this repo. It decides which findings may become issues. It does not limit what reviews may read.

## Paths that may receive issues

| Path | Meaning |
| --- | --- |
| `src/**` | kernel and adapters, including scripts |
| `tests/**` | tests |
| `examples/**` | example hosts and their host-side glue |
| `docs/**` | project documentation |
| `.github/**` | CI workflows and templates |
| `pyproject.toml`, `uv.lock` | build and dependency configuration |

Generated and dependency directories do not get their own issues; record the problem against the source that produces them. This covers `.venv/`, `dist/`, `build/`, `**/__pycache__/`, `.pytest_cache/` and run outputs under `runs/`.

## Paths that do not become issues

| Path | Reason |
| --- | --- |
| `research/**` | copied research notes, not product code |
| root `README.md`, `CONTRIBUTING.md` | repo-level notes; changes go through ordinary PRs |

## Rules

1. One issue records one reproducible problem or one task, and its body names the repo-relative paths to change.
2. Open an issue only when every file to change is inside the paths that may receive issues.
3. A finding that touches both lists points only at the in-boundary files.
4. Issues opened against excluded paths are closed with the note "outside the review path boundary".
