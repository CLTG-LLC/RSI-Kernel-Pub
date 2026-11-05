# Contributing

This repo follows [GitHub Flow](https://docs.github.com/en/get-started/using-github/github-flow) with an issue for every task.

## 1. Issue first

- One issue per task or per reproducible bug. Use the templates in `.github/ISSUE_TEMPLATE/`.
- The issue body names the repo-relative paths it will change. Those paths must fall inside the boundary in [docs/review-paths.md](docs/review-paths.md).
- Labels (kept small): `bug` / `enhancement` / `documentation`, plus `severity::1`–`4` for bugs. There are no workflow-state labels; the PR shows state. On GitHub, `::` is plain text, so remove the old severity label when changing it.
- Larger features get a design section in `docs/` and a checklist in the issue body, ticked as slices land.

## 2. Branch

- Branch from `main`: `feature/<issue#>-<short-slug>` for features, `fix/<issue#>-<short-slug>` for bugs, e.g. `feature/12-add-replay-log`.

## 3. Commits

- Follow [Conventional Commits 1.0.0](https://www.conventionalcommits.org/en/v1.0.0/): `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`, `ci:`.
- Tests come first: show the failing test, then the change that makes it pass.

## 4. Pull request

- Open a pull request into `main` using the template.
- Write `Closes #<issue>` in the description so that merging closes the issue ([linking a PR to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue)).
- Before merge:
  - CI is green on the exact PR head SHA. While Actions are disabled on this repo, run the workflow's commands on a clean checkout of that SHA: `CI=true uv sync --locked && CI=true uv run pytest -q` (JDK 21 on `PATH`), and record the result in the PR;
  - one independent review by a reviewer on a different model from the writer;
  - one fix round, then a re-check.
  - The reviewed diff is frozen by its SHA. If the head moves, the review is void.
  - The review is recorded in the PR.

## 5. Merge

- Squash-merge, so `main` keeps one Conventional-Commit commit per issue ([merge methods](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/configuring-pull-request-merges/about-merge-methods-on-github)).
- The accountable lead merges after the gates pass. Workers never commit, push or merge.
- Delete the branch after merge.
- Push only through a git credential helper; never put a token in argv or a URL. Verify each push with `git ls-remote` against local HEAD.

## 6. Data and secrets

- Never commit keys, tokens, customer data, or sealed or evaluation datasets.
- Secrets come from the environment at run time only.
- External decision-model services receive only the fixed, content-free request envelope (see `docs/design.md`).
