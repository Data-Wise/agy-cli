import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional
import networkx as nx

from agy.core.evaluator import (
    check_positivity,
    check_exchangeability,
    check_sutva,
    check_covariate_balance,
    check_propensity_diagnostics,
)


class ValidationOrchestrator:
    """
    Orchestrates causal validation checks (Positivity, Exchangeability, SUTVA)
    in parallel using background threads to optimize execution speed.
    """

    def __init__(
        self,
        data_path: Optional[str] = None,
        treatment: Optional[str] = None,
        outcome: Optional[str] = None,
        covariates: Optional[List[str]] = None,
        graph: Optional[nx.DiGraph] = None,
        dag_desc: Optional[str] = None,
        interactive: bool = False,
        sutva_responses: Optional[Dict[str, str]] = None,
        method: str = "none",
    ):
        self.data_path = data_path
        self.treatment = treatment
        self.outcome = outcome
        self.covariates = covariates or []
        self.graph = graph
        self.dag_desc = dag_desc
        self.interactive = interactive
        self.sutva_responses = sutva_responses
        self.method = method

    def run_all(self) -> Dict[str, Any]:
        """
        Runs the validations concurrently.
        Positivity and Exchangeability run in background threads,
        while SUTVA is executed on the main thread (for stdin tty handling).
        """
        start_time = time.time()
        results = {}

        # 1. Run non-interactive checks in thread pool
        with ThreadPoolExecutor(max_workers=3) as executor:
            positivity_future = None
            exchangeability_future = None
            balance_future = None

            # Dispatch Positivity
            if self.data_path and self.treatment:
                positivity_future = executor.submit(
                    self._run_positivity
                )

            # Dispatch Exchangeability
            if self.graph and self.treatment and self.outcome:
                exchangeability_future = executor.submit(
                    self._run_exchangeability
                )

            # Dispatch Covariate Balance
            if self.data_path and self.treatment and self.covariates:
                balance_future = executor.submit(
                    self._run_balance
                )

            # 2. Run SUTVA on main thread (handles interactive click.confirm)
            sutva_start = time.time()
            sutva_res = check_sutva(interactive=self.interactive, responses=self.sutva_responses)
            results["sutva"] = {
                "result": sutva_res,
                "duration": time.time() - sutva_start,
            }

            # 3. Retrieve background task results
            if positivity_future:
                results["positivity"] = positivity_future.result()
            else:
                results["positivity"] = {
                    "skipped": True,
                    "reason": "Missing data or treatment variable definition.",
                }

            if exchangeability_future:
                results["exchangeability"] = exchangeability_future.result()
            else:
                results["exchangeability"] = {
                    "skipped": True,
                    "reason": "Missing graph or treatment/outcome variables.",
                }

            if balance_future:
                results["balance"] = balance_future.result()
            else:
                results["balance"] = {
                    "skipped": True,
                    "reason": "Missing data, treatment, or covariates.",
                }

        results["total_duration"] = time.time() - start_time
        return results

    def _run_positivity(self) -> Dict[str, Any]:
        start = time.time()
        try:
            assert self.data_path is not None
            assert self.treatment is not None
            violations_df = check_positivity(self.data_path, self.treatment, self.covariates)
            duration = time.time() - start
            return {
                "satisfied": violations_df.empty,
                "violations": violations_df.to_dict(orient="records"),
                "duration": duration,
                "error": None,
            }
        except Exception as e:
            return {
                "satisfied": False,
                "violations": [],
                "duration": time.time() - start,
                "error": str(e),
            }

    def _run_exchangeability(self) -> Dict[str, Any]:
        start = time.time()
        try:
            assert self.graph is not None
            assert self.treatment is not None
            assert self.outcome is not None
            res = check_exchangeability(self.graph, self.treatment, self.outcome, self.covariates)
            duration = time.time() - start
            return {
                "satisfied": res["satisfied"],
                "reason": res["reason"],
                "descendant_violations": res.get("descendant_violations", []),
                "backdoor_blocked": res.get("backdoor_blocked", False),
                "duration": duration,
                "error": None,
            }
        except Exception as e:
            return {
                "satisfied": False,
                "reason": f"Execution error: {e}",
                "descendant_violations": [],
                "backdoor_blocked": False,
                "duration": time.time() - start,
                "error": str(e),
            }

    def _run_balance(self) -> Dict[str, Any]:
        start = time.time()
        try:
            assert self.data_path is not None
            assert self.treatment is not None
            if self.method in ("matching", "weighting"):
                balance_data = check_propensity_diagnostics(
                    self.data_path, self.treatment, self.covariates, self.method
                )
                satisfied = all(row.get("satisfied_post", True) for row in balance_data)
            else:
                raw_balance = check_covariate_balance(self.data_path, self.treatment, self.covariates)
                balance_data = []
                for row in raw_balance:
                    balance_data.append({
                        "covariate": row.get("covariate"),
                        "mean_treated_pre": row.get("mean_treated"),
                        "mean_control_pre": row.get("mean_control"),
                        "var_treated_pre": row.get("var_treated"),
                        "var_control_pre": row.get("var_control"),
                        "smd_pre": row.get("smd"),
                        "mean_treated_post": row.get("mean_treated"),
                        "mean_control_post": row.get("mean_control"),
                        "var_treated_post": row.get("var_treated"),
                        "var_control_post": row.get("var_control"),
                        "smd_post": row.get("smd"),
                        "satisfied_post": row.get("satisfied"),
                    })
                satisfied = all(row.get("satisfied", True) for row in raw_balance)
                
            duration = time.time() - start
            return {
                "satisfied": satisfied,
                "balance": balance_data,
                "duration": duration,
                "error": None,
                "method": self.method,
            }
        except Exception as e:
            return {
                "satisfied": False,
                "balance": [],
                "duration": time.time() - start,
                "error": str(e),
                "method": self.method,
            }

