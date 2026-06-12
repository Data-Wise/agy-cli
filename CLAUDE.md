# CLAUDE.md - agy-cli

## Project Overview

**agy-cli** - Core engine for Antigravity (Gemini CLI), featuring domain-specific Plugins, context-activated Skills, interactive Artifacts, and parallel validation Agents.

**Current Version**: v0.1.0
**Status**: Planning / Initializing
**Priority**: P1

## Git Workflow

```text
main (protected) ← PR only, never direct commits
  ↑
dev (integration) ← Plan here, branch from here
  ↑
feature/* (worktrees) ← All implementation work
```

### Constraints

- **CRITICAL**: Always start work from `dev` branch (`git checkout dev`)
- **Never** commit directly to `main`
- **Never** write feature code on `dev` (specs and planning only)
- **Always** verify branch: `git branch --show-current`
- Use git worktrees for development off `dev`: `git worktree add ~/.git-worktrees/agy-cli/<feature> -b feature/<feature> dev`


## Execution and Development

*Placeholder for python/node test and run commands as code is added.*
