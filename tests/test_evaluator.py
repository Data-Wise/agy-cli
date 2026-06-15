import os
import pytest
import pandas as pd
import networkx as nx
from agy.core.evaluator import (
    check_positivity,
    check_exchangeability,
    check_sutva,
    check_covariate_balance,
    check_propensity_diagnostics,
)


def test_check_positivity_satisfied(tmp_path):
    # Create a mock dataset that satisfies positivity:
    # Covariates X=1, X=2 both have treatment W=0 and W=1
    data = pd.DataFrame(
        {
            "X": [1, 1, 1, 1, 2, 2, 2, 2],
            "W": [0, 1, 0, 1, 0, 1, 0, 1],
            "Y": [1.2, 2.3, 1.1, 2.4, 0.9, 1.8, 1.0, 1.9],
        }
    )
    data_file = tmp_path / "data_satisfied.csv"
    data.to_csv(data_file, index=False)

    violations = check_positivity(str(data_file), treatment="W", covariates=["X"])

    # No strata should violate positivity
    assert isinstance(violations, pd.DataFrame)
    assert len(violations) == 0


def test_check_positivity_violated(tmp_path):
    # Create a mock dataset that violates positivity:
    # Stratum X=2 has only treatment W=1
    data = pd.DataFrame(
        {
            "X": [1, 1, 1, 1, 2, 2, 2, 2],
            "W": [0, 1, 0, 1, 1, 1, 1, 1],  # X=2 has only W=1
            "Y": [1.2, 2.3, 1.1, 2.4, 0.9, 1.8, 1.0, 1.9],
        }
    )
    data_file = tmp_path / "data_violated.csv"
    data.to_csv(data_file, index=False)

    violations = check_positivity(str(data_file), treatment="W", covariates=["X"])

    # Stratum X=2 should violate positivity
    assert isinstance(violations, pd.DataFrame)
    assert len(violations) == 1
    assert violations.iloc[0]["X"] == 2
    assert violations.iloc[0]["p_treatment"] == 1.0


def test_check_exchangeability_satisfied():
    # Causal DAG: X -> W, X -> Y, W -> Y (Confounder X blocks backdoor path)
    G = nx.DiGraph()
    G.add_edges_from([("X", "W"), ("X", "Y"), ("W", "Y")])

    result = check_exchangeability(G, treatment="W", outcome="Y", covariates=["X"])

    assert result["satisfied"] is True
    assert result["backdoor_blocked"] is True
    assert len(result["descendant_violations"]) == 0


def test_check_exchangeability_violated_unblocked():
    # Causal DAG: X -> W, X -> Y, W -> Y
    # Covariates = [] (Confounder X is NOT controlled for, backdoor path unblocked)
    G = nx.DiGraph()
    G.add_edges_from([("X", "W"), ("X", "Y"), ("W", "Y")])

    result = check_exchangeability(G, treatment="W", outcome="Y", covariates=[])

    assert result["satisfied"] is False
    assert result["backdoor_blocked"] is False


def test_check_exchangeability_violated_descendant():
    # Causal DAG: W -> M -> Y, X -> W, X -> Y
    # Controlling for M (a descendant/mediator of treatment W)
    G = nx.DiGraph()
    G.add_edges_from([("W", "M"), ("M", "Y"), ("X", "W"), ("X", "Y")])

    result = check_exchangeability(G, treatment="W", outcome="Y", covariates=["X", "M"])

    assert result["satisfied"] is False
    assert "M" in result["descendant_violations"]


def test_check_sutva_satisfied():
    responses = {"interference": "no", "treatment_variation": "no"}
    result = check_sutva(interactive=False, responses=responses)
    assert result["satisfied"] is True
    assert len(result["violations"]) == 0


def test_check_sutva_violated():
    responses = {"interference": "yes", "treatment_variation": "no"}
    result = check_sutva(interactive=False, responses=responses)
    assert result["satisfied"] is False
    assert "interference" in result["violations"]


def test_check_covariate_balance_satisfied(tmp_path):
    # Perfect balance: W=0 and W=1 have identical distributions of X
    data = pd.DataFrame(
        {
            "X": [1.0, 1.0, 2.0, 2.0, 1.0, 1.0, 2.0, 2.0],
            "W": [0, 1, 0, 1, 0, 1, 0, 1],
            "Y": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )
    data_file = tmp_path / "balance_sat.csv"
    data.to_csv(data_file, index=False)

    res = check_covariate_balance(str(data_file), treatment="W", covariates=["X"])
    assert len(res) == 1
    assert res[0]["covariate"] == "X"
    assert res[0]["satisfied"] is True
    assert res[0]["smd"] == 0.0


def test_check_covariate_balance_violated(tmp_path):
    # Imbalanced with non-zero variance:
    # W=1 has mean ~10.0, W=0 has mean ~1.0
    data = pd.DataFrame(
        {
            "X": [1.0, 10.0, 1.1, 10.1, 0.9, 9.9, 1.0, 10.0],
            "W": [0, 1, 0, 1, 0, 1, 0, 1],
            "Y": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )
    data_file = tmp_path / "balance_viol.csv"
    data.to_csv(data_file, index=False)

    res = check_covariate_balance(str(data_file), treatment="W", covariates=["X"])
    assert len(res) == 1
    assert res[0]["satisfied"] is False
    assert res[0]["smd"] > 0.1


def test_check_covariate_balance_missing_column(tmp_path):
    # Missing covariate column X
    data = pd.DataFrame(
        {
            "W": [0, 1, 0, 1],
            "Y": [1.0, 1.0, 1.0, 1.0],
        }
    )
    data_file = tmp_path / "balance_missing.csv"
    data.to_csv(data_file, index=False)

    with pytest.raises(RuntimeError) as exc_info:
        check_covariate_balance(str(data_file), treatment="W", covariates=["X"])
    assert "Covariate column X not found" in str(exc_info.value)


def test_check_propensity_diagnostics_matching(tmp_path):
    # Confounded dataset with overlap: 3 treated, 6 controls.
    # Controls closest to treated units (2.0, 3.0, 4.0) will be matched.
    data = pd.DataFrame(
        {
            "X": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 2.1, 3.1, 4.1],
            "W": [0, 0, 0, 0, 0, 0, 1, 1, 1],
            "Y": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )
    data_file = tmp_path / "propensity_match.csv"
    data.to_csv(data_file, index=False)

    res = check_propensity_diagnostics(str(data_file), treatment="W", covariates=["X"], method="matching")
    assert len(res) == 1
    assert res[0]["covariate"] == "X"
    assert res[0]["smd_pre"] > 0.1
    # Matching must reduce the SMD
    assert res[0]["smd_post"] < res[0]["smd_pre"]


def test_check_propensity_diagnostics_weighting(tmp_path):
    # Confounded dataset with overlap: W=1 (X=2,3,4,5), W=0 (X=1,2,3,4)
    data = pd.DataFrame(
        {
            "X": [1.0, 2.0, 3.0, 4.0, 2.0, 3.0, 4.0, 5.0],
            "W": [0, 0, 0, 0, 1, 1, 1, 1],
            "Y": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
        }
    )
    data_file = tmp_path / "propensity_weight.csv"
    data.to_csv(data_file, index=False)

    res = check_propensity_diagnostics(str(data_file), treatment="W", covariates=["X"], method="weighting")
    assert len(res) == 1
    assert res[0]["covariate"] == "X"
    assert res[0]["smd_pre"] > 0.1
    # Weighting must reduce the SMD
    assert res[0]["smd_post"] < res[0]["smd_pre"]



