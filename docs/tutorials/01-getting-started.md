# Tutorial 1 · Installation & Quick Start

**Goal:** Install `agy`, verify the environment, run your first command. ~5 min.

---

## Step 1 — Install

=== "Homebrew (Recommended)"

    ```bash
    brew tap data-wise/tap
    brew install agy
    ```

    !!! note "First time?"
        Run `brew update` before tapping if you haven't in a while.

=== "Source / uv"

    ```bash
    git clone git@github.com:Data-Wise/agy-cli.git
    cd agy-cli
    uv sync --all-extras
    ```

---

## Step 2 — Verify Installation

```bash
cagy status
```

Expected output:

```
✓  agy-cli vX.Y.Z
✓  Python 3.12+
✓  R bridge: available
✓  Obsidian plugin: not configured
```

---

## Step 3 — Run a Minimal Eval

Create a minimal study design file:

```yaml title="study_design.yaml"
treatment: W
outcome: Y
covariates: [age, sex, income]
```

Then run:

```bash
cagy eval study_design.yaml
```

`agy` will output assumption check results for **Positivity**, **Exchangeability**, and **SUTVA**.

---

## Step 4 — Explore the CLI

```bash
cagy --help
```

---

## ✅ What's Next

| Ready to... | Go to |
|---|---|
| Verify causal assumptions in depth | [Tutorial 2 → Causal Assumptions](02-causal-assumptions.md) |
| Draw a DAG | [Tutorial 3 → DAG Compiler](03-dag-compiler.md) |
| See all CLI flags | [Command Reference](../guides/commands.md) |
