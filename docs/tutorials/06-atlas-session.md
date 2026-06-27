# Tutorial 5 · Atlas Session Sync

**Goal:** Use `cagy atlas` to start work sessions, track breadcrumbs, and review your activity trail — an ADHD-friendly context log for long research workflows.

---

## What Is Atlas?

Atlas is `agy`'s session synchronizer. It bridges your CLI workflow with a persistent breadcrumb trail so you can answer "what was I doing?" at any point.

- **Sessions** — named work contexts (project + task + duration)
- **Breadcrumbs** — timestamped log entries tied to a session
- **Trail** — ordered history of recent activity

---

## Setup

Atlas uses two YAML files you point to at runtime:

| File | Purpose |
|---|---|
| `sessions.yaml` | Stores active and past work sessions |
| `registry.yaml` | Stores breadcrumb log entries |

Generate both with a sandbox:

```bash
cagy sandbox generate ./atlas-test
# → creates atlas/sessions.yaml + atlas/registry.yaml
```

Or create them manually — both start as empty YAML files (`{}`).

!!! tip "Shortcut"
    Export paths as shell aliases to avoid typing `--sessions-path` every time:
    ```bash
    export AGY_SESSIONS=~/atlas/sessions.yaml
    export AGY_REGISTRY=~/atlas/registry.yaml
    alias agya="agy atlas --sessions-path $AGY_SESSIONS --registry-path $AGY_REGISTRY"
    ```

---

## Step 1 — Start a Session

```bash
cagy atlas --sessions-path ~/atlas/sessions.yaml \
    start-session \
    --project "mediation-study" \
    --task "Fit propensity model" \
    --desc "Running IPW on RCT dataset v3"
```

Output:

```
✔ Started active session 'sess_abc123' for project 'mediation-study'.
```

---

## Step 2 — Check Session Status

Mid-work, check elapsed time and current task:

```bash
cagy atlas --sessions-path ~/atlas/sessions.yaml status
```

Output:

```
╭─ Active Atlas Session ──────────────────────╮
│ Project:     mediation-study                │
│ Task:        Fit propensity model           │
│ Duration:    00:42:17                       │
│ Description: Running IPW on RCT dataset v3  │
╰─────────────────────────────────────────────╯
```

---

## Step 3 — Log Breadcrumbs

Log a breadcrumb after each meaningful action:

```bash
cagy atlas --registry-path ~/atlas/registry.yaml \
    log-crumb "Ran eval on RCT dataset — positivity passed" \
    --type command \
    --project mediation-study
```

```bash
cagy atlas --registry-path ~/atlas/registry.yaml \
    log-crumb "Found SMD > 0.1 for income — switching to matching" \
    --type note \
    --project mediation-study
```

Breadcrumb `--type` options: `command`, `note`, `file`, `decision`.

---

## Step 4 — Review the Trail

```bash
cagy atlas --registry-path ~/atlas/registry.yaml trail --limit 10
```

Output:

```
 Timestamp           │ Type    │ Project          │ Description
─────────────────────┼─────────┼──────────────────┼────────────────────────────────
 2024-06-18 14:02:11 │ note    │ mediation-study  │ Found SMD > 0.1 for income
 2024-06-18 13:47:33 │ command │ mediation-study  │ Ran eval on RCT dataset
 2024-06-18 13:20:00 │ command │ dag-spec         │ Compiled DAG to R — dag_v2.R
```

---

## ✅ What's Next

| Ready to... | Go to |
|---|---|
| Run R package checks | [Tutorial 7 → R Package Harness](../guides/rforge_tutorial.md) |
| Audit your Obsidian vault | [Tutorial 5 → Obsidian Vault Audit](../guides/plugins.md) |
| Full `atlas` flags | [Command Reference](../guides/commands.md) |
