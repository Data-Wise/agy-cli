# Covariate Balance Tutorial (Standardized Mean Difference)

**BLUF:** Standardized Mean Difference ($SMD$) measures covariate balance between treated and control groups. Any covariate with $SMD > 0.1$ is flagged as imbalanced.

---

## 📐 Mathematical Formulation

For a given covariate $X$, the Standardized Mean Difference ($SMD$) between the treated group ($W=1$) and the control group ($W=0$) is defined as:

$$SMD = \frac{\bar{X}_1 - \bar{X}_0}{\sqrt{\frac{s_1^2 + s_0^2}{2}}}$$

Where:
*   $\bar{X}_1$ and $\bar{X}_0$ are the sample means of the covariate in the treated and control groups.
*   $s_1^2$ and $s_0^2$ are the sample variances of the covariate in the treated and control groups.

---

## 🚨 Balance Decision Rules

*   **Balanced:** $SMD \le 0.1$. The covariate distributions are sufficiently similar.
*   **Imbalanced:** $SMD > 0.1$. The distributions differ significantly, requiring adjustment (e.g., matching or weighting).

---

## 🔍 Diagnostics & Overlap Estimation

Propensity score models are estimated via logistic regression:

$$e(X) = P(W = 1 \mid X)$$

Estimated in R using:
```R
fit <- glm(W ~ X1 + X2, family = binomial, data = df)
ps <- predict(fit, type = "response")
```

Evaluating propensity score overlap ensures that:

$$0 < e(X) < 1$$

Which satisfies the **Positivity** assumption.

---

## 🛠️ Adjustment Methods

When raw covariate balance is violated, we can adjust using one of the following methods via the `--method` option:

### 1. Propensity Score Matching (`--method matching`)
*   **Mechanism:** Performs 1:1 nearest neighbor greedy matching without replacement.
*   **Result:** Outputs standard covariate means, variances, and Standardized Mean Differences ($SMD$) calculated on the matched subgroup.

### 2. Inverse Probability Weighting (`--method weighting`)
*   **Mechanism:** Computes weights $w_i$ for each unit $i$:
    
    $$w_i = \frac{W_i}{e(X_i)} + \frac{1 - W_i}{1 - e(X_i)}$$
    
*   **Weighted Mean:**
    
    $$\bar{X}_{g, w} = \frac{\sum_{i: W_i = g} w_i X_i}{\sum_{i: W_i = g} w_i}$$
    
*   **Weighted Variance (Cochran's Variance with Reliability Weights):**
    
    $$s^2_{g, w} = \frac{\sum_{i: W_i = g} w_i (X_i - \bar{X}_{g, w})^2}{\sum_{i: W_i = g} w_i - \frac{\sum_{i: W_i = g} w_i^2}{\sum_{i: W_i = g} w_i}}$$
    
*   **Weighted Standardized Mean Difference:**
    
    $$SMD_w = \frac{\bar{X}_{1, w} - \bar{X}_{0, w}}{\sqrt{\frac{s^2_{1, w} + s^2_{0, w}}{2}}}$$

---

## 💻 CLI Walkthrough

### 1. Unadjusted (Baseline) Evaluation
To evaluate raw covariate balance:
```bash
agy eval -t W -o Y -c X -d ./data.csv -g "X -> W, X -> Y, W -> Y" --non-interactive
```
The CLI prints the unadjusted $SMD$ table:
```text
Checking Covariate Balance (Standardized Mean Difference)...
✗ Covariate Balance check VIOLATED. Found imbalanced covariates (SMD > 0.1):

┌───────────┬────────────────┬────────────────┬────────┬────────────┐
│ Covariate │ Mean (Treated) │ Mean (Control) │ SMD    │ Status     │
├───────────┼────────────────┼────────────────┼────────┼────────────┤
│ X         │ 0.7000         │ 0.3000         │ 0.8718 │ Imbalanced │
└───────────┴────────────────┴────────────────┴────────┴────────────┘
```

### 2. Propensity Score Matching Evaluation
To check balance on matched subgroups:
```bash
agy eval -t W -o Y -c X -d ./data.csv -g "X -> W, X -> Y, W -> Y" --non-interactive --method matching
```
The CLI output compares before and after adjustment:
```text
Checking Covariate Balance (Standardized Mean Difference)...
✗ Covariate Balance check VIOLATED. Found imbalanced covariates (SMD > 0.1):

┌───────────┬───────────┬────────────┬───────────────────┐
│ Covariate │ SMD (Pre) │ SMD (Post) │ Status (Matching) │
├───────────┼───────────┼────────────┼───────────────────┤
│ X         │ 0.8718    │ 0.1500     │ Imbalanced        │
└───────────┴───────────┴────────────┴───────────────────┘
```

### 3. Inverse Probability Weighting Evaluation
To check balance on the weighted sample:
```bash
agy eval -t W -o Y -c X -d ./data.csv -g "X -> W, X -> Y, W -> Y" --non-interactive --method weighting
```
The CLI output displays the weighted comparison:
```text
Checking Covariate Balance (Standardized Mean Difference)...
✔ Covariate Balance check passed. All covariates are balanced (SMD <= 0.1).

┌───────────┬───────────┬────────────┬────────────────────┐
│ Covariate │ SMD (Pre) │ SMD (Post) │ Status (Weighting) │
├───────────┼───────────┼────────────┼────────────────────┤
│ X         │ 0.8718    │ 0.0234     │ Balanced           │
└───────────┴───────────┴────────────┴────────────────────┘
```

### 📄 Markdown Report Output
All validation results are synthesized to `.agy/report.md`. For adjusted methods (`matching` / `weighting`), the output format includes side-by-side means:

| Covariate | Mean T (Pre) | Mean C (Pre) | SMD (Pre) | Mean T (Post) | Mean C (Post) | SMD (Post) | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `X` | 0.7000 | 0.3000 | 0.8718 | 0.5123 | 0.5012 | 0.0234 | Balanced |


