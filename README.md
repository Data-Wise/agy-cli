# agy-cli: Antigravity Causal Inference Engine & Workflow Manager

* **BLUF:** A fast ($T < 10\text{ms}$ startup), ADHD-friendly Python command line tool and R process bridge to compile causal Directed Acyclic Graphs (DAGs) and validate observational study assumptions.

---

## 🎯 Core Observational Study Pillars Verified

* **Positivity Assumption:**
  * **Rule:** $0 < P(W=1 \mid X) < 1$ for all strata defined by covariates $X$.
  * **Check:** Automatically identifies and outputs any covariate strata where treatment probability is exactly $0$ or $1$.
* **Backdoor Exchangeability Assumption:**
  * **Rule:** $Y(w) \perp\!\!\perp W \mid X$.
  * **Check:** Verifies that no covariate in $X$ is a descendant of the treatment $W$, and asserts that $X$ blocks all backdoor paths between $W$ and $Y$ via d-separation in the graph $G_{\underline{W}}$.
* **SUTVA (Stable Unit Treatment Value Assumption):**
  * **Rule:** $Y_i(W) = Y_i(W_i)$ (no interference/spillover and no hidden variations of treatment).
  * **Check:** Diagnoses potential violations interactively or via configuration responses.

---

## 🚀 Installation & Environment Setup

This project uses Python 3.10+ and requires R (with `dplyr`, `ggdag`, and `dagitty` installed).

```bash
# Create virtual environment and install packages
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

---

## 💻 CLI Commands & Usage

### 1. Show Status
Verify package initialization and active environment status:
```bash
agy status
```

### 2. Compile Textual DAGs to R Code
Convert textual representations of causal graphs into executable R code utilizing `dagitty` and `ggdag`:
```bash
agy dag "W -> Y, X -> W, X -> Y" --treatment W --outcome Y
```
* Use `-o <path>` to save the generated code to an R script file directly.

### 3. Evaluate Study Assumptions
Validate positivity, exchangeability, and SUTVA on a study:
```bash
agy eval \
  --data tests/mock_data.csv \
  --treatment W \
  --outcome Y \
  --covariates "X1,X2" \
  --dag-str "W -> Y, X1 -> W, X2 -> Y" \
  --non-interactive
```
* **Study Design Configuration:** You can alternatively pass a path to a JSON or YAML study design file:
```bash
agy eval path/to/study_design.json
```

---

## 🧪 Running Unit Tests

Execute the complete test suite (CLI interface, DAG compilation, and statistical assumption validators):
```bash
uv run pytest
```
