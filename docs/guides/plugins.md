# Tutorial 5 · Obsidian Vault Audit

**Goal:** Use `cagy obs` to query your local Obsidian SQLite graph — find orphan notes, hub nodes by PageRank, and broken internal links.

---

## Background

When you enable the Obsidian [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) or the built-in **Obsidian Sync**, the app writes a SQLite database (`vault_db.sqlite`) that `cagy obs` queries directly.

The graph is modelled as a directed network $G = (V, E)$ where:

- $V$ = all notes in the vault
- $E$ = all `[[wikilinks]]` between notes
- $k_{in}(v)$ = in-degree (notes pointing **to** $v$)
- $k_{out}(v)$ = out-degree (notes $v$ points **to**)

---

## Step 1 — Find Orphan Notes

Orphans have $k_{in} = 0$ **and** $k_{out} = 0$ — no connections at all.

```bash
cagy obs --db-path ~/Library/Application\ Support/obsidian/vault_db.sqlite orphans
```

Output:

```
 Title              │ Path                       │ Modified At
────────────────────┼────────────────────────────┼─────────────────────
 Draft: SMD notes   │ research/drafts/smd.md     │ 2024-06-01 09:12:00
 Scratch pad        │ inbox/scratch.md            │ 2024-05-28 14:30:22
```

**Action:** Link them into the graph or archive them.

---

## Step 2 — Find Hub Notes

Hubs are high-centrality nodes. Sort by `pagerank` (default), `in_degree`, `out_degree`, or `total_degree`.

```bash
cagy obs --db-path ~/vault.sqlite hubs --sort pagerank --limit 10
```

Output:

```
 Title               │ PageRank │ In  │ Out │ Total
─────────────────────┼──────────┼─────┼─────┼──────
 Causal Inference MOC│  0.1842  │  34 │  12 │  46
 Methods Index       │  0.0931  │  28 │   8 │  36
 Study Design Hub    │  0.0712  │  21 │  15 │  36
```

!!! tip "Map of Contents"
    Hub notes with high `in_degree` are natural **Maps of Content (MOC)** — good candidates for pinning to your dashboard.

---

## Step 3 — Audit Broken Links

Broken links are `[[wikilinks]]` pointing to notes that don't exist.

```bash
cagy obs --db-path ~/vault.sqlite health
```

**Healthy vault:**

```
✔ Vault health check passed. No broken links found.
```

**With broken links:**

```
Broken Links Detected
 Source Note     │ Source Path          │ Target Path              │ Count
─────────────────┼──────────────────────┼──────────────────────────┼──────
 Week 23 Notes   │ journals/week-23.md  │ methods/iv-estimator.md  │  1
```

**Action:** Create the missing note or correct the link path.

---

## Step 4 — Visualize Note Graph

Render your vault note connections as a Mermaid diagram or a nested ASCII tree. You can focus on a single note to map its neighborhood.

### Renders Top Hub Connections (Mermaid Format)
```bash
cagy obs --db-path ~/vault.sqlite graph --format mermaid --limit 5
```

Output:
```text
graph TD
    "MediationVerse Dashboard" --> "medfit"
    "MediationVerse Dashboard" --> "medsim"
    "medsim" --> "medfit"
```

### Renders Neighborhood Indented Tree (ASCII Format)
Focus on a note to trace its outgoing link path recursively up to a custom depth:
```bash
cagy obs --db-path ~/vault.sqlite graph --format ascii --focus "MediationVerse Dashboard" --depth 2
```

Output:
```text
MediationVerse Dashboard
├── medrobust
├── medsim
│   ├── medfit
│   └── RMediation
└── RMediation
```

---

## Step 5 — Find Literature Gaps

Identify isolated theoretical methods or disconnected applications/projects in your literature database. It classifies notes by tags or path substrings.

```bash
cagy obs --db-path ~/vault.sqlite gaps --method-tags "causal-inference,mediation,regression,assumptions" --setting-tags "project,data"
```

Output:
```text
Obsidian Vault Causal/Literature Audit Summary
  • Classified 223 Method notes (matching tags: causal-inference,mediation,regression,assumptions)
  • Classified 98 Setting/Project notes (matching tags: project,data)

                 Isolated Methods (No Application/Project Links)
┏━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Title                   ┃ Path                     ┃ Tags                    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Bounds of Sensitivity   │ Knowledge_Base/20_stati… │ assumptions             │
└─────────────────────────┴──────────────────────────┴─────────────────────────┘
```

---

## Step 6 — Automate Vault Health in CI

Add a vault health check to your weekly review script:

```bash
#!/bin/bash
# vault_health.sh
cagy obs --db-path "$OBSIDIAN_DB" health && \
cagy obs --db-path "$OBSIDIAN_DB" orphans && \
cagy obs --db-path "$OBSIDIAN_DB" gaps
```

```bash
export OBSIDIAN_DB=~/Library/Application\ Support/obsidian/vault_db.sqlite
bash vault_health.sh
```

---

## ✅ What's Next

| Ready to... | Go to |
|---|---|
| Track work sessions with Atlas | [Tutorial 6 → Atlas Session Sync](../tutorials/06-atlas-session.md) |
| Run R package checks | [Tutorial 7 → R Package Harness](rforge_tutorial.md) |
| Full `obs` CLI flags | [Command Reference](commands.md) |
