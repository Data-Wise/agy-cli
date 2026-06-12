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
feature/* (worktrees) ← All implementation work
```

### Constraints

- **CRITICAL**: Never commit directly to `main`
- **Always** branch from `main` to `feature/*`
- **Always** verify branch: `git branch --show-current`
- Use git worktrees for development: `git worktree add ~/.git-worktrees/agy-cli/<feature> -b feature/<feature> main`

## Execution and Development

*Placeholder for python/node test and run commands as code is added.*
