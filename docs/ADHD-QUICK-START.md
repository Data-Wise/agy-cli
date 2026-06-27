# 🧠 ADHD Quick Start

> Get started with `cagy` in **under 2 minutes**

---

## ⏱️ First 30 Seconds

The absolute essentials to get running:

```bash
brew tap data-wise/tap && brew install agy  # Install the causal engine
cagy status                                 # Verify Python, R, and database status
```

---

## ⏱️ Next 5 Minutes

Once the basics work, run your first evaluation or draw a DAG:

### 1. Run Causal Assumptions Eval
Create a design configuration:
```yaml title="study_design.yaml"
treatment: W
outcome: Y
covariates: [age, sex, income]
data: ./my_data.csv
```
Run the audit:
```bash
cagy eval study_design.yaml --method matching
```

### 2. Draw & Compile a DAG
Compile shorthand notation into an R `ggdag` plotting script:
```bash
cagy dag "X -> W, X -> Y, W -> Y" -t W -y Y -o my_dag.R
```

### 3. Audit local Obsidian vault
Find orphan notes, central hub notes, and broken links:
```bash
cagy obs --db-path ~/vault.sqlite hubs
```

---

## 🆘 Stuck? Run These

If something is not working:

*   **View CLI help:** `cagy --help` or `cagy <command> --help`
*   **Check logs:** Unhandled errors are automatically logged to `~/.config/obs/obs.log`
*   **Reset session:** Reset active Atlas workspaces via `cagy atlas status`

---

## 🎯 ADHD-Friendly Features

This project is optimized for ADHD developers to minimize cognitive load:

*   ⏱️ **Time Estimates:** Estimates listed on every tutorial and reference page.
*   > **TL;DR Boxes:** 30-second bulleted summaries at the top of all documentation pages.
*   🎨 **Visual Cues:** Uses clear status icons (✔ / ✗) and Rich console panels.
*   📊 **Workflow Diagrams:** Integrated Mermaid illustrations for visual mapping.
*   🚀 **Zero Friction:** Sub-10ms startup times with entirely in-process executions.

---

## 📚 Next Steps

| Ready to... | Go to |
|---|---|
| Run step-by-step guides | [Tutorials Index](tutorials/index.md) |
| Read CLI commands | [Command Reference Guide](guides/commands.md) |
| Audit local vaults | [Tutorial 5 · Obsidian Vault Audit](guides/plugins.md) |
