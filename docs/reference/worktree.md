# Worktree Workflow

**BLUF:** `agy worktree` automates git worktrees for context-isolated feature development — each feature gets its own working directory off `dev`, no stashing, no context switching.

---

## Why Worktrees?

| Without worktrees | With `agy worktree` |
|---|---|
| `git stash` before switching tasks | Each feature lives in its own directory |
| Risk of mixing unrelated changes | Branches are strictly isolated |
| Manual branch + directory setup | One command: `agy worktree add <name>` |
| Easy to lose where you were | Named directories make context obvious |

---

## Lifecycle

```
main
 └── dev
      ├── feature-balance-smd      ← agy worktree add balance-smd
      ├── feature-atlas-v2         ← agy worktree add atlas-v2
      └── feature-rforge-output    ← agy worktree add rforge-output
```

Each worktree maps to a persistent directory **adjacent** to the main repo, with its own branch branched off `dev`.

---

## Commands

### Add a worktree

```bash
agy worktree add balance-smd
```

Output:

```
╭─ Worktree Manager ──────────────────────────────╮
│ ✔ Git worktree successfully added!              │
│                                                 │
│ Name:    balance-smd                            │
│ Branch:  feature-balance-smd                   │
│ Path:    ../agy-cli-balance-smd                │
│                                                 │
│ Run 'cd ../agy-cli-balance-smd && agy' to start │
╰─────────────────────────────────────────────────╯
```

---

### List active worktrees

```bash
agy worktree list
```

Output:

```
 Path                          │ Branch
───────────────────────────────┼───────────────────────
 /Users/dt/agy-cli             │ dev
 /Users/dt/agy-cli-balance-smd │ feature-balance-smd
 /Users/dt/agy-cli-atlas-v2   │ feature-atlas-v2
```

---

### Remove a worktree

When a feature is merged, clean up:

```bash
agy worktree remove balance-smd
```

```
✔ Removed worktree feature-balance-smd and branch feature-balance-smd.
```

This decommissions the directory **and** deletes the local tracking branch.

---

## Typical Workflow

```bash
# 1. Start new feature
agy worktree add my-feature

# 2. Switch to isolated directory
cd ../agy-cli-my-feature

# 3. Do work, commit normally
git add . && git commit -m "feat: add my-feature"

# 4. Push and open PR to dev
git push origin feature-my-feature

# 5. After merge, clean up
agy worktree remove my-feature
```

---

## See Also

- [Worktree Rules Spec](../specs/SPEC-worktree-rules.md) — formal conventions
- [Branch Workflow](../contributing/BRANCH-WORKFLOW.md) — full contribution process
