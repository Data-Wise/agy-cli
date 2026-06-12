# SPEC: Worktree Rules & Management for agy-cli

This specification defines the worktree rules for **agy-cli**, governing both how developers build `agy-cli` and how the `agy` CLI manages worktrees for causal inference projects.

---

## 🎯 Executive Summary (BLUF)
*   **Verdict:** Yes, we should implement the same persistent worktree rules as `craft`.
*   **Core Rationale:** Persistent worktrees (`~/.git-worktrees/agy-cli/<branch>`) enforce clean context isolation, prevent stash loss, support parallel project states, and align with the multi-branch ($\text{main} \leftarrow \text{dev} \leftarrow \text{feature/*}$) Git workflow.

---

## 🚀 Persistent vs. Native Isolation

| Feature | Persistent Worktrees (`agy-cli`) | Native Agent Isolation (`isolation: "worktree"`) |
|---|---|---|
| **Location** | `~/.git-worktrees/agy-cli/<branch>` | `.gemini/worktrees/<hash>` |
| **Lifetime** | Long-lived (until PR merge and explicit cleanup) | Ephemeral (cleaned automatically after agent run) |
| **Workspace Cwd** | Persistent folder you can `cd` into and inspect | Hidden, managed internally by Antigravity |
| **Context Scope** | Human-guided development & stats execution | Single-agent parallel execution isolation |

---

## 🏗️ Worktree Lifecycle Rules

### 1. Planning & Authorization (Always on `dev`)
Before a worktree is created, you must check in a spec to the `dev` branch:
1. Write `docs/specs/SPEC-<feature>.md`.
2. Commit to the `dev` branch.
3. Verify local branch is clean.

### 2. Creation Protocol
To start work on a feature, create the worktree off `dev`:
```bash
git worktree add ~/.git-worktrees/agy-cli/feature-<name> -b feature/<name> dev
```

Upon creation, the orchestrator:
*   Automatically appends the worktree path to the local [.STATUS](file:///Users/dt/projects/dev-tools/agy-cli/.STATUS) file.
*   Enforces that the implementation session is started in the worktree directory:
    ```bash
    cd ~/.git-worktrees/agy-cli/feature-<name> && agy
    ```

### 3. Implementation Constraints (Inside Worktree)
*   **Context Isolation:** Never run cross-project operations inside the worktree without explicit project paths.
*   **Atomic Commits:** Follow conventional commits (`feat:`, `fix:`, etc.).
*   **Tests:** Run all tests locally before staging.

### 4. Cleanup & Decommissioning
Once the PR is merged to `dev`:
1. Remove the worktree:
   ```bash
   git worktree remove ~/.git-worktrees/agy-cli/feature-<name>
   ```
2. Delete the local feature branch:
   ```bash
   git branch -d feature/<name>
   ```
3. Update [.STATUS](file:///Users/dt/projects/dev-tools/agy-cli/.STATUS) to remove the tracking entry.
