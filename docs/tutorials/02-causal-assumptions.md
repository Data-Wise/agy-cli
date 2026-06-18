# Tutorial 2 · Verify Causal Assumptions

**Goal:** Use `agy eval` to check Positivity, Backdoor Exchangeability, SUTVA, and Covariate Balance — with optional propensity score adjustment.

---

## Background

The engine enforces three canonical identification assumptions:

**Positivity (Overlap)**

$$0 < P(W = w \mid X = x) < 1 \quad \forall\, x \in \mathcal{X},\; w \in \mathcal{W}$$

**Backdoor Exchangeability (Unconfoundedness)**

$$Y(w) \perp\!\!\!\perp W \mid X$$

**SUTVA**

$$Y_i(W) = Y_i(W_i) \quad \forall\, i$$

When all three hold, the ATE is nonparametrically identified:

$$\tau_{\text{ATE}} = \mathbb{E}_X\!\left[\mathbb{E}[Y \mid W=1,X] - \mathbb{E}[Y \mid W=0,X]\right]$$

---

## Step 1 — Create a Study Design

```yaml title="study_design.yaml"
treatment: W
outcome: Y
covariates: [age, sex, income]
data: ./observational_data.csv

dag: "age -> W, sex -> W, income -> W, age -> Y, income -> Y, W -> Y"

sutva_responses:
  interference: "no"
  treatment_variation: "no"
```

---

## Step 2 — Run Baseline `eval`

```bash
agy eval study_design.yaml --non-interactive
```

Expected console output:

```
Checking Positivity Assumption...
✔ Positivity check passed. All covariate strata have treatment variation.

Checking Backdoor Exchangeability...
✔ Exchangeability check passed. {age, sex, income} d-separates W ⊥ Y.

Checking SUTVA Assumptions...
✔ SUTVA check passed. No interference, single treatment version.

Checking Covariate Balance (Standardized Mean Difference)...
✗ Covariate Balance VIOLATED. Found imbalanced covariates (SMD > 0.1):
```

---

## Step 3 — Fix Imbalance with Propensity Score Matching

When baseline SMD flags imbalance, re-run with `--method matching`:

```bash
agy eval study_design.yaml --method matching --non-interactive
```

The engine fits a logistic propensity model $\hat{e}(X) = P(W=1 \mid X)$, performs 1:1 nearest-neighbour matching, then re-computes SMD on the matched sample.

Output shows a **pre/post SMD comparison table**:

```
 Covariate │ SMD (Pre) │ SMD (Post) │ Status (Matching)
───────────┼───────────┼────────────┼──────────────────
 age       │  0.3241   │  0.0412    │ Balanced
 sex       │  0.1823   │  0.0209    │ Balanced
 income    │  0.4102   │  0.0887    │ Balanced
```

---

## Step 4 — IPW Weighting (Alternative)

For regression-based workflows, use inverse probability weighting instead:

```bash
agy eval study_design.yaml --method weighting --non-interactive
```

The IPW estimator:

$$\hat{\tau}_{\text{IPW}} = \frac{1}{n}\sum_{i=1}^n \left[\frac{W_i Y_i}{\hat{e}(X_i)} - \frac{(1-W_i)Y_i}{1-\hat{e}(X_i)}\right]$$

where $\hat{e}(X_i) = P(W=1 \mid X_i)$ is the fitted propensity score.

---

## Step 5 — Markdown Report Output

After every `eval` run, `agy` auto-saves a Markdown audit trail:

```
Synthesized Markdown Report saved to: ./agy_report_2024-06-18.md
```

!!! tip "Persistent Audit Trail"
    This report captures all assumption checks, violations, and balance results — useful for appending to a research notebook or committing alongside your analysis code.

---

## Step 6 — Interpret Violations

**Positivity violation:**

```
✗ Positivity VIOLATED. Found strata with no treatment variation:
 age  │ sex │ income │ P(W=1|X)
──────┼─────┼────────┼──────────
 18   │ F   │ low    │ 0.000
```

**Fix:** Trim the dataset to the region of common support, or use a positivity-robust estimator (e.g. targeted MLE).

**Exchangeability violation:**

```
✗ Exchangeability FAILED. Adjustment set {age} does not block all backdoor paths.
```

**Fix:** Re-specify your DAG and covariate set to block all backdoor paths from $W$ to $Y$.

---

## ✅ What's Next

| Ready to... | Go to |
|---|---|
| Draw and compile a DAG | [Tutorial 3 → DAG Compiler](03-dag-compiler.md) |
| Understand SMD in depth | [Tutorial 4 → Covariate Balance](../guides/balance_tutorial.md) |
| Full `eval` CLI flags | [Command Reference](../guides/commands.md) |
