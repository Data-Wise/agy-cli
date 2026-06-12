# Branch Workflow - agy-cli

## Overview

agy-cli uses a **three-tier branch strategy** for safe, organized development.

```text
feature/* ──► dev ──► main
hotfix/*       │        │
    │          │        │
    └── PR ────┘        │
               └── PR ──┘
```

---

## Branch Structure

### 1. `main` - Production
- **Purpose:** Stable, production-ready code.
- **Updates:** Release PRs from `dev` only.
- **Protection:** Protected branch. No direct commits.

### 2. `dev` - Integration
- **Purpose:** Integration branch for all development.
- **Updates:** Feature PRs from `feature/*`, `fix/*`, `docs/*`.
- **Protection:** No direct feature code commits. Direct commits allowed only for planning/spec docs and status file updates.
- **Testing:** All changes must pass checks before merge.

### 3. `feature/*` - Development
- **Purpose:** Individual features, fixes, improvements.
- **Created from:** `dev` branch.
- **Merged to:** `dev` branch (via PR).
- **Naming:** `feature/description`, `fix/bug-name`, `docs/topic`.

---

## Mandatory Workflow Protocol (Agent Development)

When working on agy-cli, follow these **strict** steps to maintain code quality and branch integrity.

### 1. Planning Phase (Always on `dev`)
1. Analyze requirements on `dev` branch.
2. Create implementation plan.
3. Document plan in spec file (`docs/specs/SPEC-*.md`).
4. Commit plan to `dev` branch.
5. **Wait for user approval** before starting implementation.

### 2. Worktree Creation (Isolation)
After plan approval, create an isolated worktree for implementation:
```bash
git worktree add ~/.git-worktrees/agy-cli-<feature-name> -b feature/<feature-name> dev
```

**Worktree Location Convention:**
- `~/.git-worktrees/agy-cli-<feature-name>`

**Critical Rule:**
- **Stop here.** Do not start implementation from the planning session. Start a new session in the worktree directory.

### 3. Atomic Development (In Worktree)
- Use **Conventional Commits** format (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`).
- Run all unit tests before committing.

### 4. Integration (feature/* → dev)
1. Fetch latest dev and rebase feature:
   ```bash
   git fetch origin dev
   git rebase origin/dev
   ```
2. Run full test suite.
3. Push feature branch and create PR to `dev`:
   ```bash
   git push -u origin feature/<feature-name>
   gh pr create --base dev --title "feat: feature name" --body "..."
   ```

### 5. Release (dev → main)
1. Create release PR:
   ```bash
   gh pr create --base main --head dev --title "Release vX.Y.Z" --body "Release notes..."
   ```
2. Tag release after merge:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push --tags
   ```
