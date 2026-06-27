# Tutorial 3 · Draw & Compile DAGs

⏱️ **5 minutes** • 🟢 Beginner • ✓ 4 steps

> **TL;DR** (30 seconds)
> - **What:** Compile shorthand edge-notation string representations of Directed Acyclic Graphs (DAGs) into publication-ready R `ggdag` / `dagitty` plots.
> - **Why:** Visualize confounding paths, determine minimal backdoor adjustment sets, and prevent collider bias.
> - **How:** Run `cagy dag "X -> W, X -> Y, W -> Y" -t W -y Y -o my_dag.R`.
> - **Next:** [Asymptotic Theory & EIF](../guides/asymptotic_theory.md)

---

## Step 1 — Basic DAG Compilation

```bash
cagy dag "X -> W, X -> Y, W -> Y" -t W -y Y
```

Outputs R code:

```r
library(dagitty)
library(ggdag)

dag <- dagitty("dag {
    W [exposure]
    Y [outcome]
    X -> W
    X -> Y
    W -> Y
}")

# Plot DAG
ggdag(dag) + theme_dag()
```

---

## Step 2 — Save to File

```bash
cagy dag "X -> W, X -> Y, W -> Y" -t W -y Y -o my_dag.R
Rscript my_dag.R
```

---

## Step 3 — Identify Adjustment Sets

`cagy dag` can also check backdoor adjustment sets. Given the DAG:

$$X \to W,\quad X \to Y,\quad W \to Y$$

The minimal sufficient adjustment set for the effect of $W$ on $Y$ is $\{X\}$, since:

$$Y(w) \perp\!\!\!\perp W \mid X$$

Run:

```bash
cagy dag "X -> W, X -> Y, W -> Y" -t W -y Y --adjustment-sets
```

---

## Step 4 — Complex DAGs (Mediators, Colliders)

```bash
cagy dag "U -> W, U -> Y, X -> W, W -> M, M -> Y" \
    -t W -y Y --unobserved U
```

!!! warning "Collider Bias"
    Conditioning on a collider (a variable caused by both W and Y) **opens** a spurious path.
    `cagy dag` will warn you if your adjustment set contains a collider.

---

## ✅ What's Next

| Ready to... | Go to |
|---|---|
| Verify assumptions on this DAG | [Tutorial 2 → Causal Assumptions](02-causal-assumptions.md) |
| Understand the asymptotic theory | [Asymptotic Theory & EIF](../guides/asymptotic_theory.md) |
| Full CLI options for `cagy dag` | [Command Reference](../guides/commands.md) |
