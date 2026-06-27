# Tutorials

Step-by-step walkthroughs from zero to full causal research workflows with `cagy`. Each tutorial is self-contained — start anywhere, no dead ends.

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg } **1 · Get Started**

    ---

    Install `cagy`, verify your environment, run your first command. ~5 min.

    [:octicons-arrow-right-24: Start here](01-getting-started.md)

-   :material-check-all:{ .lg } **2 · Causal Assumptions**

    ---

    `cagy eval` — verify Positivity, Exchangeability, SUTVA. Fix balance with matching or IPW weighting.

    [:octicons-arrow-right-24: Run eval](02-causal-assumptions.md)

-   :material-graph:{ .lg } **3 · DAG Compiler**

    ---

    Compile edge-notation DAGs to `ggdag`/`dagitty` R code. Check adjustment sets and collider bias.

    [:octicons-arrow-right-24: Compile a DAG](03-dag-compiler.md)

-   :material-scale-balance:{ .lg } **4 · Covariate Balance**

    ---

    Understand SMD, balance tables, and the $\text{SMD} > 0.1$ flagging threshold.

    [:octicons-arrow-right-24: Measure balance](../guides/balance_tutorial.md)

-   :material-book-open-variant:{ .lg } **5 · Obsidian Vault Audit**

    ---

    Query your Obsidian SQLite graph — find orphan notes, hub nodes by PageRank, broken links.

    [:octicons-arrow-right-24: Audit vault](../guides/plugins.md)

-   :material-map-marker-path:{ .lg } **6 · Atlas Session Sync**

    ---

    Start work sessions, log breadcrumbs, review your activity trail. ADHD-friendly context log.

    [:octicons-arrow-right-24: Sync sessions](06-atlas-session.md)

-   :material-language-r:{ .lg } **7 · R Package Harness**

    ---

    Run `devtools::check/test/document` from CLI. Validate your R package without leaving the terminal.

    [:octicons-arrow-right-24: Validate R package](../guides/rforge_tutorial.md)

-   :material-flask-outline:{ .lg } **8 · Sandbox Vaults**

    ---

    Generate test vaults with injected violations to stress-test the validation engine.

    [:octicons-arrow-right-24: Generate sandbox](../guides/sandbox.md)

</div>

---

!!! tip "ADHD-Friendly Design"
    Every tutorial ends with a **What's Next** table. No dead ends.
