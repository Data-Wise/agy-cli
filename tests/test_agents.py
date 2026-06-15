import networkx as nx

from agy.agents.orchestrator import ValidationOrchestrator
from agy.agents.synthesizer import ReportSynthesizer
from agy.core.sandbox import SandboxVault


def test_validation_orchestrator_satisfied(tmp_path):
    # Setup sandbox
    vault = SandboxVault(tmp_path / "sandbox")
    res = vault.build(violations=False)

    graph = nx.DiGraph()
    graph.add_nodes_from(["X", "W", "Y"])
    graph.add_edges_from([("X", "W"), ("X", "Y"), ("W", "Y")])

    orchestrator = ValidationOrchestrator(
        data_path=res["data_path"],
        treatment="W",
        outcome="Y",
        covariates=["X"],
        graph=graph,
        dag_desc="X -> W, X -> Y, W -> Y",
        interactive=False,
        sutva_responses={"interference": "no", "treatment_variation": "no"},
    )

    results = orchestrator.run_all()

    # Verify duration keys and outcomes
    assert "total_duration" in results
    assert results["positivity"]["satisfied"] is True
    assert results["exchangeability"]["satisfied"] is True
    assert results["sutva"]["result"]["satisfied"] is True
    assert results["balance"]["satisfied"] is False  # Confounded raw data is imbalanced (SMD > 0.1)


def test_validation_orchestrator_violated(tmp_path):
    # Setup sandbox with violations
    vault = SandboxVault(tmp_path / "sandbox_viol")
    res = vault.build(violations=True)

    # DAG contains unadjusted backdoor path Z
    graph = nx.DiGraph()
    graph.add_nodes_from(["X", "W", "Y", "Z"])
    graph.add_edges_from([("X", "W"), ("X", "Y"), ("W", "Y"), ("Z", "W"), ("Z", "Y")])

    orchestrator = ValidationOrchestrator(
        data_path=res["data_path"],
        treatment="W",
        outcome="Y",
        covariates=["X"],
        graph=graph,
        dag_desc="X -> W, X -> Y, W -> Y, Z -> W, Z -> Y",
        interactive=False,
        sutva_responses={"interference": "yes", "treatment_variation": "no"},
    )

    results = orchestrator.run_all()

    assert results["positivity"]["satisfied"] is False  # Positivity violated (W=X)
    assert (
        results["exchangeability"]["satisfied"] is False
    )  # Exchangeability violated (Z unblocked)
    assert results["sutva"]["result"]["satisfied"] is False  # SUTVA violated (interference)
    assert (
        results["balance"]["satisfied"] is True
    )  # Deterministic treatment W=X has var=0, SMD=0 (Balanced)


def test_report_synthesizer(tmp_path):
    synthesizer = ReportSynthesizer(tmp_path)
    results = {
        "total_duration": 0.123,
        "positivity": {"satisfied": True, "violations": []},
        "exchangeability": {"satisfied": True, "reason": "blocked backdoor paths"},
        "sutva": {"result": {"satisfied": True, "summary": "no interference"}},
        "balance": {
            "satisfied": True,
            "balance": [
                {
                    "covariate": "X",
                    "mean_treated_pre": 0.5,
                    "mean_control_pre": 0.48,
                    "var_treated_pre": 1.0,
                    "var_control_pre": 1.0,
                    "smd_pre": 0.02,
                    "satisfied_post": True,
                }
            ],
        },
    }
    meta = {
        "treatment": "W",
        "outcome": "Y",
        "covariates": ["X"],
        "data": "data.csv",
        "dag": "X -> W, X -> Y, W -> Y",
    }

    report_path = synthesizer.synthesize(results, meta)
    assert report_path.exists()
    assert report_path.name == "report.md"

    content = report_path.read_text()
    assert "# Causal Validation Report" in content
    assert "**Positivity:** ✔" in content
    assert "**Exchangeability:** ✔" in content
    assert "**SUTVA:** ✔" in content
    assert "Covariate Balance (SMD)" in content
    assert "`X` | 0.5000 | 0.4800 | 1.0000 | 1.0000 | 0.0200 | Balanced" in content
