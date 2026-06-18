# Tutorial 5 · Obsidian Vault Audit

**Goal:** Use `agy obs` to query your local Obsidian SQLite graph — find orphan notes, hub nodes by PageRank, and broken internal links.

---

## Background

When you enable the Obsidian [Local REST API](https://github.com/coddingtonbear/obsidian-local-rest-api) or the built-in **Obsidian Sync**, the app writes a SQLite database (`vault_db.sqlite`) that `agy obs` queries directly.

The graph is modelled as a directed network $G = (V, E)$ where:

- $V$ = all notes in the vault
- $E$ = all `[[wikilinks]]` between notes
- $k_{in}(v)$ = in-degree (notes pointing **to** $v$)
- $k_{out}(v)$ = out-degree (notes $v$ points **to**)

---

## Step 1 — Find Orphan Notes

Orphans have $k_{in} = 0$ **and** $k_{out} = 0$ — no connections at all.

```bash
agy obs --db-path ~/Library/Application\ Support/obsidian/vault_db.sqlite orphans
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
agy obs --db-path ~/vault.sqlite hubs --sort pagerank --limit 10
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
agy obs --db-path ~/vault.sqlite health
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

## Step 4 — Automate Vault Health in CI

Add a vault health check to your weekly review script:

```bash
#!/bin/bash
# vault_health.sh
agy obs --db-path "$OBSIDIAN_DB" health && \
agy obs --db-path "$OBSIDIAN_DB" orphans
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
