import subprocess
import os
import io
import sys
import pandas as pd
import networkx as nx
from typing import List, Dict, Any, Optional


class RBridge:
    """
    An interactive bridge to R using subprocess.Popen.
    Maintains an active R session and handles running command strings,
    ensuring stdout/stderr are read safely with sentinels.
    """

    def __init__(self):
        self.process = None

    def start(self):
        if self.process is not None:
            return

        # Start R process. --vanilla prevents loading start-up files.
        # Redirect stderr to stdout to read everything sequentially and avoid blocking.
        self.process = subprocess.Popen(
            ["R", "--vanilla", "--quiet", "--slave"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # line buffered
        )

    def run(self, command: str) -> str:
        if self.process is None:
            self.start()

        assert self.process is not None
        assert self.process.stdin is not None
        assert self.process.stdout is not None

        sentinel = "---R_SENTINEL---"
        full_command = f"{command}\ncat('{sentinel}\\n')\nflush(stdout())\n"

        self.process.stdin.write(full_command)
        self.process.stdin.flush()

        output_lines = []
        while True:
            line = self.process.stdout.readline()
            if not line:
                break
            if line.strip() == sentinel:
                break
            output_lines.append(line)

        return "".join(output_lines)

    def close(self):
        if self.process is not None:
            if self.process.stdin is not None:
                try:
                    self.process.stdin.write("q(save='no')\n")
                    self.process.stdin.flush()
                except Exception:
                    pass
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def check_positivity(data_path: str, treatment: str, covariates: List[str]) -> pd.DataFrame:
    """
    Checks the Positivity assumption: 0 < P(W=1|X) < 1.
    Groups by covariates and returns a DataFrame containing violating strata
    (i.e., strata where p_treatment is exactly 0 or 1).
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found at {data_path}")

    # Escape quotes and backslashes for R compatibility
    safe_data_path = os.path.abspath(data_path).replace("\\", "/").replace('"', '\\"')
    safe_treatment = treatment.replace('"', '\\"')
    safe_covariates = [c.replace('"', '\\"') for c in covariates]
    
    covs_formatted = ", ".join(f'"{c}"' for c in safe_covariates)
    covs_vector = f"c({covs_formatted})"
    
    r_script = f"""
library(dplyr)
df <- read.csv("{safe_data_path}")
covs <- {covs_vector}
treatment <- "{safe_treatment}"

if (!treatment %in% colnames(df)) {{
    stop(paste("Treatment column", treatment, "not found"))
}}
for (cov in covs) {{
    if (!cov %in% colnames(df)) {{
        stop(paste("Covariate column", cov, "not found"))
    }}
}}

# Ensure treatment is treated as binary
df[[treatment]] <- as.numeric(df[[treatment]] == 1 | df[[treatment]] == TRUE)

if (length(covs) > 0) {{
    res <- df %>%
      group_by(across(all_of(covs))) %>%
      summarize(
        p_treatment = mean(get(treatment), na.rm = TRUE),
        n = n(),
        n_treated = sum(get(treatment) == 1, na.rm = TRUE),
        n_control = sum(get(treatment) == 0, na.rm = TRUE),
        .groups = "drop"
      ) %>%
      filter(p_treatment == 0 | p_treatment == 1)
}} else {{
    res <- df %>%
      summarize(
        p_treatment = mean(get(treatment), na.rm = TRUE),
        n = n(),
        n_treated = sum(get(treatment) == 1, na.rm = TRUE),
        n_control = sum(get(treatment) == 0, na.rm = TRUE)
      ) %>%
      filter(p_treatment == 0 | p_treatment == 1)
}}

write.csv(res, row.names = FALSE)
"""
    with RBridge() as bridge:
        output = bridge.run(r_script)

    # If there are error messages, parse them
    if "Error" in output or "stop(" in output:
        raise RuntimeError(f"R execution error:\n{output}")

    # Parse CSV output in Python
    try:
        # Filter output to only keep the CSV part (which starts with columns or is structured)
        lines = output.strip().split("\n")
        # Find start of CSV by matching the header containing 'p_treatment'
        csv_start_idx = 0
        for idx, line in enumerate(lines):
            if "p_treatment" in line:
                csv_start_idx = idx
                break

        csv_content = "\n".join(lines[csv_start_idx:])
        if not csv_content.strip():
            return pd.DataFrame()

        df_violations = pd.read_csv(io.StringIO(csv_content))
        return df_violations
    except Exception as e:
        raise RuntimeError(f"Failed to parse R output:\n{output}\nError: {e}")


def check_exchangeability(
    graph: nx.DiGraph, treatment: str, outcome: str, covariates: List[str]
) -> Dict[str, Any]:
    r"""
    Checks backdoor Exchangeability: $Y(w) \perp W \mid X$.
    Uses NetworkX is_d_separator to check:
    1. No covariate is a descendant of the treatment.
    2. Covariates block all backdoor paths (i.e. d-separate treatment and outcome in G_underbar_W).
    """
    # 1. Check if nodes exist in graph
    for node in [treatment, outcome] + covariates:
        if node not in graph:
            return {
                "satisfied": False,
                "reason": f"Node '{node}' is not present in the graph.",
                "descendant_violations": [],
                "backdoor_blocked": False,
            }

    # 2. Check descendant violations (covariates must not be descendants of treatment)
    descendants = nx.descendants(graph, treatment)
    descendant_violations = [cov for cov in covariates if cov in descendants]

    # 3. Check backdoor path blocking
    # Remove all outgoing edges from the treatment node
    graph_backdoor = graph.copy()
    outgoing_edges = list(graph.out_edges(treatment))
    graph_backdoor.remove_edges_from(outgoing_edges)

    # Check d-separation in graph_backdoor
    from networkx.algorithms.d_separation import is_d_separator

    try:
        backdoor_blocked = is_d_separator(graph_backdoor, {treatment}, {outcome}, set(covariates))
    except Exception as e:
        # Fallback or error handling
        backdoor_blocked = False

    satisfied = (len(descendant_violations) == 0) and backdoor_blocked

    reason = ""
    if satisfied:
        reason = "Exchangeability is satisfied: covariates block all backdoor paths and contain no descendants of treatment."
    else:
        reasons = []
        if descendant_violations:
            reasons.append(
                f"Covariates {descendant_violations} are descendants of treatment '{treatment}'."
            )
        if not backdoor_blocked:
            reasons.append(
                f"Covariates {covariates} fail to block all backdoor paths between '{treatment}' and '{outcome}'."
            )
        reason = "Exchangeability violated: " + " ".join(reasons)

    return {
        "satisfied": satisfied,
        "reason": reason,
        "descendant_violations": descendant_violations,
        "backdoor_blocked": backdoor_blocked,
    }


def check_sutva(
    interactive: bool = True, responses: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Validates SUTVA (Stable Unit Treatment Value Assumption) interactively or programmatically.
    Checks for:
    1. Interference / Spillover effects
    2. Treatment version variation
    """
    questions = {
        "interference": (
            "Is there any potential for interaction or spillover effects between study units "
            "(e.g., social contact, geographic proximity, resource sharing)?"
        ),
        "treatment_variation": (
            "Are there multiple versions or variations of the treatment that might have "
            "different effects on the outcome (e.g., dosage levels, program quality differences)?"
        ),
    }

    results = {}
    violations = []

    for key, q in questions.items():
        ans = None
        if responses and key in responses:
            ans = responses[key].strip().lower()
        elif interactive:
            import click

            ans = "yes" if click.confirm(q, default=False) else "no"
        else:
            ans = "no"  # Default in non-interactive mode with no responses

        results[key] = ans
        if ans == "yes":
            violations.append(key)

    satisfied = len(violations) == 0

    if satisfied:
        summary = "SUTVA assumptions are likely satisfied (no interference or treatment variation reported)."
    else:
        reasons = []
        if "interference" in violations:
            reasons.append("Potential interference/spillover effects detected between units.")
        if "treatment_variation" in violations:
            reasons.append("Potential variations/versions of treatment detected.")
        summary = "SUTVA potentially violated: " + " ".join(reasons)

    return {
        "satisfied": satisfied,
        "summary": summary,
        "violations": violations,
        "responses": results,
    }


def check_covariate_balance(data_path: str, treatment: str, covariates: List[str]) -> List[Dict[str, Any]]:
    """
    Checks covariate balance between treated and control groups using Standardized Mean Difference (SMD).
    SMD > 0.1 indicates significant imbalance.
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found at {data_path}")
        
    if not covariates:
        return []

    # Escape quotes and backslashes for R compatibility
    safe_data_path = os.path.abspath(data_path).replace("\\", "/").replace('"', '\\"')
    safe_treatment = treatment.replace('"', '\\"')
    safe_covariates = [c.replace('"', '\\"') for c in covariates]
    
    covs_formatted = ", ".join(f'"{c}"' for c in safe_covariates)
    covs_vector = f"c({covs_formatted})"
    
    r_script = f"""
library(dplyr)
df <- read.csv("{safe_data_path}")
covs <- {covs_vector}
treatment <- "{safe_treatment}"

# Ensure treatment is binary 0/1
df[[treatment]] <- as.numeric(df[[treatment]] == 1 | df[[treatment]] == TRUE)

balance_results <- data.frame(
  covariate = character(),
  mean_treated = numeric(),
  mean_control = numeric(),
  var_treated = numeric(),
  var_control = numeric(),
  smd = numeric(),
  satisfied = logical(),
  stringsAsFactors = FALSE
)

for (cov in covs) {{
  if (!cov %in% colnames(df)) {{
    stop(paste("Covariate column", cov, "not found"))
  }}
  
  treated_vals <- df[[cov]][df[[treatment]] == 1]
  control_vals <- df[[cov]][df[[treatment]] == 0]
  
  m1 <- mean(treated_vals, na.rm = TRUE)
  m0 <- mean(control_vals, na.rm = TRUE)
  v1 <- var(treated_vals, na.rm = TRUE)
  v0 <- var(control_vals, na.rm = TRUE)
  
  if (is.na(v1)) v1 <- 0
  if (is.na(v0)) v0 <- 0
  
  denom <- sqrt((v1 + v0) / 2)
  if (denom == 0) {{
    smd <- 0
  }} else {{
    smd <- abs(m1 - m0) / denom
  }}
  
  satisfied <- smd <= 0.1
  
  balance_results <- rbind(balance_results, data.frame(
    covariate = cov,
    mean_treated = m1,
    mean_control = m0,
    var_treated = v1,
    var_control = v0,
    smd = smd,
    satisfied = satisfied
  ))
}}

write.csv(balance_results, row.names = FALSE)
"""
    with RBridge() as bridge:
        output = bridge.run(r_script)

    if "Error" in output or "stop(" in output:
        raise RuntimeError(f"R execution error in balance check:\n{output}")

    try:
        lines = output.strip().split("\n")
        csv_start_idx = 0
        for idx, line in enumerate(lines):
            if "smd" in line:
                csv_start_idx = idx
                break

        csv_content = "\n".join(lines[csv_start_idx:])
        if not csv_content.strip():
            return []

        df_balance = pd.read_csv(io.StringIO(csv_content))
        return df_balance.to_dict(orient="records")
    except Exception as e:
        raise RuntimeError(f"Failed to parse R balance check output:\n{output}\nError: {e}")


def check_propensity_diagnostics(
    data_path: str, treatment: str, covariates: List[str], method: str
) -> List[Dict[str, Any]]:
    """
    Performs propensity score matching or weighting diagnostics and evaluates
    before/after covariate balance using Standardized Mean Difference (SMD).
    """
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Data file not found at {data_path}")

    if not covariates:
        return []

    if method not in ("matching", "weighting"):
        raise ValueError(f"Invalid adjustment method: {method}")

    # Escape quotes and backslashes for R compatibility
    safe_data_path = os.path.abspath(data_path).replace("\\", "/").replace('"', '\\"')
    safe_treatment = treatment.replace('"', '\\"')
    safe_covariates = [c.replace('"', '\\"') for c in covariates]

    covs_formatted = ", ".join(f'"{c}"' for c in safe_covariates)
    covs_vector = f"c({covs_formatted})"
    safe_method = method.replace('"', '\\"')

    r_script = f"""
library(dplyr)
df <- read.csv("{safe_data_path}")
covs <- {covs_vector}
treatment <- "{safe_treatment}"
method <- "{safe_method}"

# Ensure treatment is binary 0/1
df[[treatment]] <- as.numeric(df[[treatment]] == 1 | df[[treatment]] == TRUE)

# 1. Fit propensity score model
formula_str <- paste(treatment, "~", paste(covs, collapse = " + "))
fit <- glm(as.formula(formula_str), family = binomial, data = df)
df$ps <- predict(fit, type = "response")
df$ps <- pmax(pmin(df$ps, 0.999), 0.001)

# 2. Adjust based on method
if (method == "matching") {{
  treated_indices <- which(df[[treatment]] == 1)
  control_indices <- which(df[[treatment]] == 0)
  
  matched_control <- c()
  available_controls <- control_indices
  
  for (t_idx in treated_indices) {{
    if (length(available_controls) == 0) break
    t_ps <- df$ps[t_idx]
    c_ps <- df$ps[available_controls]
    best_match_idx <- available_controls[which.min(abs(c_ps - t_ps))]
    matched_control <- c(matched_control, best_match_idx)
    available_controls <- setdiff(available_controls, best_match_idx)
  }}
  
  df_post <- df[c(treated_indices, matched_control), ]
  df_post$w_adj <- 1
}} else if (method == "weighting") {{
  df$w_adj <- ifelse(df[[treatment]] == 1, 1 / df$ps, 1 / (1 - df$ps))
  df_post <- df
}} else {{
  df$w_adj <- 1
  df_post <- df
}}

# 3. Calculate balance
balance_results <- data.frame(
  covariate = character(),
  mean_treated_pre = numeric(),
  mean_control_pre = numeric(),
  var_treated_pre = numeric(),
  var_control_pre = numeric(),
  smd_pre = numeric(),
  mean_treated_post = numeric(),
  mean_control_post = numeric(),
  var_treated_post = numeric(),
  var_control_post = numeric(),
  smd_post = numeric(),
  satisfied_post = logical(),
  stringsAsFactors = FALSE
)

# Helper function to compute weighted mean and variance (Cochran formula)
get_weighted_stats <- function(x, w) {{
  m <- sum(w * x) / sum(w)
  sum_w <- sum(w)
  sum_w2 <- sum(w^2)
  if (sum_w == sum_w2) {{
    v <- var(x, na.rm = TRUE)
  }} else {{
    v <- sum(w * (x - m)^2) / (sum_w - sum_w2 / sum_w)
  }}
  if (is.na(v)) v <- 0
  return(c(m, v))
}}

for (cov in covs) {{
  if (!cov %in% colnames(df)) {{
    stop(paste("Covariate column", cov, "not found"))
  }}
  
  # Pre-adjustment (unweighted)
  treated_vals_pre <- df[[cov]][df[[treatment]] == 1]
  control_vals_pre <- df[[cov]][df[[treatment]] == 0]
  
  m1_pre <- mean(treated_vals_pre, na.rm = TRUE)
  m0_pre <- mean(control_vals_pre, na.rm = TRUE)
  v1_pre <- var(treated_vals_pre, na.rm = TRUE)
  v0_pre <- var(control_vals_pre, na.rm = TRUE)
  if (is.na(v1_pre)) v1_pre <- 0
  if (is.na(v0_pre)) v0_pre <- 0
  
  denom_pre <- sqrt((v1_pre + v0_pre) / 2)
  smd_pre <- if (denom_pre == 0) 0 else abs(m1_pre - m0_pre) / denom_pre
  
  # Post-adjustment
  treated_vals_post <- df_post[[cov]][df_post[[treatment]] == 1]
  control_vals_post <- df_post[[cov]][df_post[[treatment]] == 0]
  w_treated <- df_post$w_adj[df_post[[treatment]] == 1]
  w_control <- df_post$w_adj[df_post[[treatment]] == 0]
  
  stats_treated <- get_weighted_stats(treated_vals_post, w_treated)
  stats_control <- get_weighted_stats(control_vals_post, w_control)
  
  m1_post <- stats_treated[1]
  v1_post <- stats_treated[2]
  m0_post <- stats_control[1]
  v0_post <- stats_control[2]
  
  denom_post <- sqrt((v1_post + v0_post) / 2)
  smd_post <- if (denom_post == 0) 0 else abs(m1_post - m0_post) / denom_post
  
  satisfied_post <- smd_post <= 0.1
  
  balance_results <- rbind(balance_results, data.frame(
    covariate = cov,
    mean_treated_pre = m1_pre,
    mean_control_pre = m0_pre,
    var_treated_pre = v1_pre,
    var_control_pre = v0_pre,
    smd_pre = smd_pre,
    mean_treated_post = m1_post,
    mean_control_post = m0_post,
    var_treated_post = v1_post,
    var_control_post = v0_post,
    smd_post = smd_post,
    satisfied_post = satisfied_post
  ))
}}

write.csv(balance_results, row.names = FALSE)
"""
    with RBridge() as bridge:
        output = bridge.run(r_script)

    if "Error" in output or "stop(" in output:
        raise RuntimeError(f"R execution error in propensity diagnostics:\n{output}")

    try:
        lines = output.strip().split("\n")
        csv_start_idx = 0
        for idx, line in enumerate(lines):
            if "smd_pre" in line:
                csv_start_idx = idx
                break

        csv_content = "\n".join(lines[csv_start_idx:])
        if not csv_content.strip():
            return []

        df_balance = pd.read_csv(io.StringIO(csv_content))
        return df_balance.to_dict(orient="records")
    except Exception as e:
        raise RuntimeError(f"Failed to parse R propensity diagnostics output:\n{output}\nError: {e}")

