# Development & CI Workflows

**BLUF:** All changes go through `feature/* → dev → main`. CI runs Python + R checks on every push. Releases are fully automated on version tags.

---

## Git Branching Policy

```text
main (protected)       ← PR only, no direct commits
  ↑
dev (integration)      ← Staging + planning branch
  ↑
feature/* (worktrees)  ← All feature development
```

Use `agy worktree` to manage feature branches:

```bash
agy worktree add my-feature     # creates feature/my-feature off dev
agy worktree list               # see active worktrees
agy worktree remove my-feature  # clean up after merge
```

See [Worktree Workflow](../reference/worktree.md) for the full guide.

---

## Pre-Commit Hooks

Catch formatting and lint errors **before** they hit CI.

```bash
# Install
uv pip install pre-commit
pre-commit install

# Run manually
pre-commit run --all-files
```

| Hook | What it does |
|---|---|
| `black` | Auto-formats Python to 100-char line width |
| `ruff` | Lints, checks syntax, sorts imports |

---

## GitHub Actions Pipelines

### CI (`ci.yml`)

Triggers on push or PR to `dev` or `main`.

```
Python 3.12 + R 4.4+
  → black + ruff
  → pytest (full suite)
  → R: install dagitty, ggdag, dplyr, ggplot2
```

Run locally before pushing:

```bash
uv run pytest tests/ -v
pre-commit run --all-files
```

### Docs (`docs.yml`)

Triggers on push to `main`. Builds MkDocs and deploys to `gh-pages`.

```bash
# Preview locally
uv run mkdocs serve

# Build
uv run mkdocs build --strict
```

### Release (`release.yml`)

Triggers on `v*` tag push. Fully automated:

1. Build Python wheel + sdist
2. Upload to PyPI
3. Create GitHub Release
4. Calculate new `sha256`, update `Formula/agy.rb`, commit Homebrew bump to `dev`

```bash
# Tag and push to trigger release
git tag v0.2.0
git push origin v0.2.0
```

---

## ✅ What's Next

| Ready to... | Go to |
|---|---|
| Set up git worktrees | [Worktree Reference](../reference/worktree.md) |
| Read branch conventions | [Branch Workflow](../contributing/BRANCH-WORKFLOW.md) |
| Understand the release spec | [Implementation Roadmap](../specs/SPEC-agy-cli-roadmap.md) |
