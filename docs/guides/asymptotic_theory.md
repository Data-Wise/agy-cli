# Asymptotic Theory & Influence Functions

*   **BLUF**: Semiparametric estimation allows causal effect inference without assuming parametric models for the entire data-generating distribution. The **efficient influence function (EIF)** provides the semiparametric efficiency bound and guides the construction of doubly robust estimators.

---

## 📐 Mathematical Formulation

### 1. First-Order Asymptotics & Influence Functions
An estimator $\hat{\theta}_n$ of a parameter $\theta_0$ is **asymptotically linear** if there exists a function $\psi(O)$ (the influence function) such that:

$$\sqrt{n}(\hat{\theta}_n - \theta_0) = \frac{1}{\sqrt{n}}\sum_{i=1}^n \psi(O_i) + o_p(1)$$

Where:
*   $O_i = (X_i, W_i, Y_i)$ represents the observed data for unit $i$.
*   $E[\psi(O)] = 0$ and $E[\psi(O)\psi(O)^T] < \infty$.
*   The asymptotic variance of $\hat{\theta}_n$ is given by $Var(\psi(O))$.

### 2. Efficient Influence Function (EIF) for ATE
For the Average Treatment Effect ($ATE = \psi_{ATE}$):

$$ATE = E[Y(1) - Y(0)]$$

Under positivity, exchangeability, and SUTVA, the EIF is:

$$\psi_{ATE}(Y, W, X) = \frac{W(Y - \mu_1(X))}{e(X)} - \frac{(1-W)(Y - \mu_0(X))}{1-e(X)} + \mu_1(X) - \mu_0(X) - ATE$$

Where:
*   $e(X) = P(W = 1 \mid X)$ is the propensity score model.
*   $\mu_w(X) = E[Y \mid W = w, X]$ is the outcome regression model.

### 3. Semiparametric Efficiency Bound
*   **Definition**: The variance of the EIF, $Var(\psi_{ATE}(O))$, defines the lowest possible asymptotic variance that any regular asymptotically linear estimator can achieve.
*   **Double Robustness**: Estimators built on the EIF (e.g., TMLE or AIPW) remain consistent if either $e(X)$ or $\mu_w(X)$ is correctly specified.

---

## 🛠️ Implementation in R (tidyverse & targets)

To estimate semiparametric causal effects with influence functions in a reproducible pipeline, configure a `targets` workflow:

```R
library(targets)
library(tidyverse)

# Define target pipeline
tar_pipeline <- list(
  tar_target(
    raw_data,
    read_csv("data/causal_data.csv")
  ),
  tar_target(
    fit_models,
    {
      # Propensity score (logistic)
      ps_fit <- glm(W ~ X, family = binomial, data = raw_data)
      ps <- predict(ps_fit, type = "response")
      
      # Outcome regression (OLS)
      mu_fit <- lm(Y ~ W + X, data = raw_data)
      mu1 <- predict(mu_fit, newdata = mutate(raw_data, W = 1))
      mu0 <- predict(mu_fit, newdata = mutate(raw_data, W = 0))
      
      list(ps = ps, mu1 = mu1, mu0 = mu0)
    }
  ),
  tar_target(
    eif_estimate,
    {
      W <- raw_data$W
      Y <- raw_data$Y
      ps <- fit_models$ps
      mu1 <- fit_models$mu1
      mu0 <- fit_models$mu0
      
      # Doubly robust ATE using EIF components
      aipw_terms <- (W * (Y - mu1) / ps) - ((1 - W) * (Y - mu0) / (1 - ps)) + mu1 - mu0
      ate <- mean(aipw_terms)
      
      # Calculate standard error using EIF variance
      eif <- aipw_terms - ate
      se <- sd(eif) / sqrt(length(eif))
      
      data.frame(ate = ate, se = se)
    }
  )
)
```
