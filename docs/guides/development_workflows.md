# Development & CI/CD Workflows

*   **BLUF**: To maintain codebase stability and release consistency, all code modifications must follow the Git worktree structure, pass local pre-commit checks, and pass the dual-environment (Python + R) GitHub Actions CI suite.

---

## 🗺️ Git Branching Policy

We strictly enforce a multi-branch development lifecycle to prevent unreviewed changes from hitting production:

```text
main (protected) ← Pull Request only (No direct commits allowed)
  ↑
dev (integration) ← Integration branch for planning and staging
  ↑
feature/* (worktrees) ← All coding & feature implementation
```

### Git Worktree Setup
Instead of switching branches in a single directory, add dedicated worktrees from `dev`:
```bash
git checkout dev
git worktree add ~/.git-worktrees/agy-cli/my-feature -b feature/my-feature dev
```

---

## ⚓ Pre-Commit Hooks

We use `pre-commit` to catch formatting, syntax, and style errors locally before code is committed to Git.

### Setup Instructions
1. Install pre-commit via Python virtual environment:
   ```bash
   uv pip install pre-commit
   ```
2. Register the hooks with Git:
   ```bash
   pre-commit install
   ```

### Included Checks
*   **Black**: Automatically formats Python code to standard 100-character line lengths.
*   **Ruff**: Instantly lints, checks syntax, and applies import sorting/autofixes.

To run hooks manually across all files:
```bash
pre-commit run --all-files
```

---

## 🚀 GitHub Actions CI/CD Pipelines

Our repository runs two separate automated pipelines in GitHub Actions:

### 1. Pull Request & Commit CI (`ci.yml`)
Triggers on any push or pull request targeting `dev` or `main`.
*   **Environments**: Installs Python 3.10 and R 4.4+.
*   **R Setup**: Installs system requirements (`libcurl4`, `libxml2`, `libssl`) and the target stats packages (`dplyr`, `ggplot2`, `dagitty`, `ggdag`).
*   **Checks**: Runs `black`, `ruff`, and the entire `pytest` suite.

### 2. Version Release & Distribution (`release.yml`)
Triggers only on version tag pushes (`v*`).
*   **Publishing**: Builds Python wheels, uploads distributions, and creates a GitHub Release.
*   **Homebrew Bump**: Downloads the source tarball, calculates the new `sha256` hash, automatically updates `Formula/agy.rb`, and commits the bump directly back to the `dev` branch.
