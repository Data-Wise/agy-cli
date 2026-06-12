# PLAN: Core Causal Inference Engine Implementation

This plan outlines the task-by-task execution steps to implement the core causal inference and R integration features in **agy-cli**.

**Goal:** Implement Python CLI commands and R integration for checking Positivity ($0 < P(W=1|X) < 1$), backdoor Exchangeability ($Y(w) \perp\!\!\perp W \mid X$), and SUTVA assumptions, along with compiling causal DAGs to R code.

**Tech Stack:** Python 3.9+, Click, Rich, NetworkX, R 4.4+, tidyverse, ggdag, dagitty.

---

## File Structure

| File | Status | Responsibility |
|---|---|---|
| `src/agy/core/evaluator.py` | Create | Implements Positivity, Exchangeability, and SUTVA validators. Spawns subprocess R bridges. |
| `src/agy/core/dag_compiler.py` | Create | Parses textual graphs and compiles them to R ggdag/dagitty code. |
| `src/agy/cli.py` | Modify | Connects CLI subcommands `eval` and `dag` to the core layer. |
| `tests/test_evaluator.py` | Create | Unit tests for positivity and exchangeability checks. |
| `tests/test_dag_compiler.py` | Create | Unit tests for DAG text parsing and R code compilation. |

---

## 🛠️ Implementation Steps

### Task 1: R Process Bridge & Positivity Checker
Implement a subprocess wrapper that invokes R to run statistical evaluations, and implement the positivity assumption checker.

*   [ ] **Step 1.1: Implement R Process Bridge in `src/agy/core/evaluator.py`**
    *   Write `RBridge` class that starts an interactive R process via `subprocess.Popen` or similar, runs command strings, and returns stdout/stderr.
*   [ ] **Step 1.2: Implement Positivity Checker**
    *   Add `check_positivity(data_path, treatment, covariates)` function.
    *   Pass the CSV path to R, group by covariates, calculate treatment probability for each group, and flag any strata violating $0 < P(W=1|X) < 1$.
*   [ ] **Step 1.3: Add Positivity Unit Tests**
    *   Create `tests/test_evaluator.py` with mock datasets (one violating positivity, one satisfying it) and assert correct detections.

### Task 2: Backdoor Exchangeability & SUTVA Validator
Implement backdoor path checks using NetworkX in Python and verify conditioning sets.

*   [ ] **Step 2.1: Implement Backdoor Path Checker in `src/agy/core/evaluator.py`**
    *   Load causal graph from input or text and build a NetworkX `DiGraph`.
    *   Write `check_exchangeability(graph, treatment, outcome, covariates)` using NetworkX's d-separation functions to check if covariates $X$ block all backdoor paths:
        $$Y(w) \perp\!\!\perp W \mid X$$
*   [ ] **Step 2.2: Implement SUTVA Questionnaire Validator**
    *   Add `check_sutva(project_path)` which scans study metadata or asks interactive CLI questions (e.g. check for spillover/interference or variant treatment definitions).
*   [ ] **Step 2.3: Add Exchangeability & SUTVA Unit Tests**
    *   Add test cases to `tests/test_evaluator.py` validating d-separation assertions on different DAG structures.

### Task 3: DAG Compiler to R Code
Implement a parser for textual graph configurations and generate ggdag/dagitty R code.

*   [ ] **Step 3.1: Implement Text Parser in `src/agy/core/dag_compiler.py`**
    *   Parse string inputs like `W -> Y, X -> W, X -> Y` into nodes and edges.
*   [ ] **Step 3.2: Implement R Code Generator**
    *   Write `compile_to_r(nodes, edges)` returning standard R code utilizing `dagitty::dagitty()` and `ggdag::ggdag()`.
*   [ ] **Step 3.3: Add DAG Compiler Unit Tests**
    *   Create `tests/test_dag_compiler.py` asserting compiled R strings match expected syntax.

### Task 4: CLI Integration
Hook the CLI commands up to the core business logic.

*   [ ] **Step 4.1: Modify `src/agy/cli.py`**
    *   Update `eval` command to accept `--treatment`, `--outcome`, `--covariates`, and `--data` options and call `evaluator.py`.
    *   Update `dag` command to compile description strings and optionally write them to the specified `--output` R script.
*   [ ] **Step 4.2: Verify with manual CLI checks**
    *   Run `python3 -m src.agy.cli status` to verify Click commands.
