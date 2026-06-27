# Causal Inference Assumptions Verification

To draw causal inferences from observational data, three primary assumptions must hold: **Positivity**, **Exchangeability**, and **SUTVA**. The `cagy eval` command automates checking these assumptions.

---

## 1. Positivity (Overlap)

### Mathematical Definition
For all covariate strata $X$ where $P(X) > 0$, the probability of receiving any treatment level $W$ must be strictly bounded between $0$ and $1$:
$$0 < P(W = w \mid X = x) < 1$$

### Verification Protocol
The engine groups the dataset by the covariates specified in the study design and calculates the proportion of treated units in each stratum. If a stratum is found where the proportion is exactly $0$ or $1$, a positivity violation is flagged.

---

## 2. Backdoor Exchangeability (Unconfoundedness)

### Mathematical Definition
Given covariate set $X$, the potential outcomes $Y(w)$ must be conditionally independent of treatment assignment $W$:
$$Y(w) \perp\!\!\perp W \mid X$$

### Verification Protocol
Using a graphical Directed Acyclic Graph (DAG), backdoor exchangeability is checked by testing if:
1. No covariate in $X$ is a descendant of treatment $W$ (checking that $X$ does not lie on the causal path or act as a mediator).
2. The set $X$ d-separates $W$ and $Y$ in the backdoor graph $\underline{G}_W$ (where outgoing edges from $W$ are deleted).

---

## 3. Stable Unit Treatment Value Assumption (SUTVA)

### Mathematical Definition
The treatment assignment of any unit $i$ does not affect the potential outcome of another unit $j$ (no interference), and there is only a single version of the treatment:
$$Y_i(W) = Y_i(W_i)$$

### Verification Protocol
Because SUTVA cannot be verified purely from data matrices, `cagy eval` uses structured survey questionnaire profiles (`sutva_responses` inside the design file) or prompts the user interactively in the terminal to evaluate:
*   **Interference/Spillover:** Social, geographical, or resource contacts between units.
*   **Treatment Variation:** Multiple unmeasured dosages or quality variations.

---

## 💻 R Compiler Integration (`cagy dag`)

You can compile textual DAG descriptions (e.g. `X -> W, X -> Y, W -> Y`) to clean R scripts using:
```bash
cagy dag "X -> W, X -> Y, W -> Y" -t W -y Y -o my_dag.R
```
This compiles to the following R structure:
```R
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
