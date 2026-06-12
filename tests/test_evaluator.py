import os
import pytest
import pandas as pd
import networkx as nx
from agy.core.evaluator import (
    check_positivity,
    check_exchangeability,
    check_sutva,
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
