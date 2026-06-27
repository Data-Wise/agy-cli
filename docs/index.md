# agy-cli

<div class="hero-badges" markdown>
[![Build](https://github.com/Data-Wise/agy-cli/actions/workflows/ci.yml/badge.svg)](https://github.com/Data-Wise/agy-cli/actions/workflows/ci.yml)
[![Docs](https://github.com/Data-Wise/agy-cli/actions/workflows/docs.yml/badge.svg)](https://data-wise.github.io/agy-cli/)
[![Version](https://img.shields.io/badge/version-0.2.1-22c55e?logo=semver&logoColor=white)](https://github.com/Data-Wise/agy-cli/releases)
[![Python](https://img.shields.io/badge/python-3.12%2B-4f46e5?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-7c3aed)](https://github.com/Data-Wise/agy-cli/blob/main/LICENSE)
[![Homebrew](https://img.shields.io/badge/homebrew-data--wise%2Ftap-f97316?logo=homebrew&logoColor=white)](https://github.com/Data-Wise/homebrew-tap)
</div>

> **Causal inference CLI for stats researchers** — verify assumptions, compile DAGs to R, audit Obsidian vaults, run R package checks.

---

## 🎯 BLUF

| Property | Value |
|---|---|
| **Startup** | $T < 10\text{ms}$ — entirely in-process |
| **Assumptions** | Auto-verifies Positivity, Backdoor Exchangeability, SUTVA |
| **Plugins** | Obsidian SQLite graphs · Atlas session sync · R devtools bridge |
| **Report** | Auto-saves Markdown audit trail after every `eval` run |

---

## ⚡ Quick Start

=== "Homebrew (Recommended)"

    ```bash
    brew tap data-wise/tap
    brew install agy
    cagy status
    ```

=== "Source / uv"

    ```bash
    git clone git@github.com:Data-Wise/agy-cli.git
    cd agy-cli
    uv sync --all-extras
    uv run cagy status
    ```

---

## 🧩 Core Commands

<div class="grid cards" markdown>

-   :material-check-circle:{ .lg } **Assumptions Eval**

    ---

    Verify Positivity, Backdoor Exchangeability, and SUTVA. Supports propensity score matching and IPW weighting.

    ```bash
    cagy eval study_design.yaml --method matching
    ```

-   :material-graph:{ .lg } **DAG Compiler**

    ---

    Compile edge-notation DAG strings to ready-to-run `ggdag`/`dagitty` R code.

    ```bash
    cagy dag "W -> Y, X -> W, X -> Y" \
        -t W -y Y -o dag.R
    ```

-   :material-book-open-variant:{ .lg } **Obsidian Vault Audit**

    ---

    Query your local Obsidian SQLite graph — find orphan notes, hub nodes by PageRank, and broken links.

    ```bash
    cagy obs --db-path ~/vault.sqlite hubs \
        --sort pagerank --limit 10
    ```

-   :material-language-r:{ .lg } **R Package Harness**

    ---

    Run `devtools::check`, `devtools::test`, and `devtools::document` directly from the CLI.

    ```bash
    cagy rforge --pkg-dir ./mypackage check
    ```

</div>

---

## 📐 Causal Framework

The engine enforces the three canonical identification assumptions:

**1. Positivity (Overlap)**

$$0 < P(W = w \mid X = x) < 1 \quad \forall\, x \in \mathcal{X},\; w \in \mathcal{W}$$

**2. Backdoor Exchangeability (Unconfoundedness)**

$$Y(w) \perp\!\!\!\perp W \mid X$$

**3. SUTVA**

$$Y_i(W) = Y_i(W_i) \quad \forall\, i$$

When all three hold, the ATE is nonparametrically identified:

$$\tau_{\text{ATE}} = \mathbb{E}_X\!\left[\mathbb{E}[Y \mid W=1, X] - \mathbb{E}[Y \mid W=0, X]\right]$$

---

## 📚 Documentation Map

| Section | What's inside |
|---|---|
| [Tutorial 1 — Get Started](tutorials/01-getting-started.md) | Install, verify, run first command |
| [Tutorial 2 — Causal Assumptions](tutorials/02-causal-assumptions.md) | `eval`, matching, weighting, report output |
| [Tutorial 3 — DAG Compiler](tutorials/03-dag-compiler.md) | Edge notation, adjustment sets, colliders |
| [Tutorial 4 — Covariate Balance](guides/balance_tutorial.md) | SMD tables, balance diagnostics |
| [Tutorial 5 — Obsidian & Atlas](guides/plugins.md) | `obs` + `atlas` plugin commands |
| [Tutorial 6 — R Package Harness](guides/rforge_tutorial.md) | `rforge` check/test/document |
| [Command Reference](guides/commands.md) | Full CLI flags, options, exit codes |
| [Asymptotic Theory & EIF](guides/asymptotic_theory.md) | Influence functions, semiparametric efficiency |

---

## 🔗 Links

[![GitHub](https://img.shields.io/badge/GitHub-Data--Wise%2Fagy--cli-181717?logo=github)](https://github.com/Data-Wise/agy-cli)
[![Homebrew Tap](https://img.shields.io/badge/Tap-data--wise%2Ftap-f97316?logo=homebrew)](https://github.com/Data-Wise/homebrew-tap)
[![Issues](https://img.shields.io/github/issues/Data-Wise/agy-cli?color=7c3aed)](https://github.com/Data-Wise/agy-cli/issues)
