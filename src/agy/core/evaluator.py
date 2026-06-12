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
