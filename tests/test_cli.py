import os
import json
import pytest
from click.testing import CliRunner
from agy.cli import main


def test_cli_status():
    runner = CliRunner()
    result = runner.invoke(main, ["status"])
    assert result.exit_code == 0
    assert "Active and initialized." in result.output


def test_cli_dag_stdout():
    runner = CliRunner()
    result = runner.invoke(main, ["dag", "W -> Y, X -> W, X -> Y", "-t", "W", "-y", "Y"])
    assert result.exit_code == 0
    assert "library(dagitty)" in result.output
    assert 'exposure(dag) <- "W"' in result.output
    assert 'outcome(dag) <- "Y"' in result.output


def test_cli_dag_file(tmp_path):
    output_file = tmp_path / "dag.R"
    runner = CliRunner()
    result = runner.invoke(main, ["dag", "W -> Y", "-o", str(output_file)])
    assert result.exit_code == 0
    assert "Successfully compiled to R script" in result.output
    assert output_file.exists()

    content = output_file.read_text()
    assert "W -> Y" in content


def test_cli_eval_skip_options():
    runner = CliRunner()
    result = runner.invoke(main, ["eval", "--non-interactive"])
    assert result.exit_code == 0
    # Positivity and exchangeability should be skipped since no data/dag is provided
    assert "Skipping Positivity check" in result.output
    assert "Skipping Exchangeability check" in result.output
    # SUTVA should run non-interactively
    assert "SUTVA check passed" in result.output


def test_cli_eval_design_file(tmp_path):
    # Create a mock study design JSON file
    design = {
        "treatment": "W",
        "outcome": "Y",
        "covariates": ["X"],
        "dag": "X -> W, X -> Y, W -> Y",
        "sutva_responses": {"interference": "no", "treatment_variation": "no"},
    }

    design_file = tmp_path / "study_design.json"
    with open(design_file, "w") as f:
        json.dump(design, f)

    runner = CliRunner()
    result = runner.invoke(main, ["eval", str(design_file), "--non-interactive"])
    assert result.exit_code == 0

    # Positivity should be skipped because no data is provided
    assert "Skipping Positivity check" in result.output
    # Exchangeability should run and pass
    assert "Exchangeability check passed" in result.output
    # SUTVA should run and pass
    assert "SUTVA check passed" in result.output
