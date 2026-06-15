import os
import sqlite3
import yaml
import pytest
from pathlib import Path
from click.testing import CliRunner

from agy.core.sandbox import SandboxVault
from agy.cli import main


def test_sandbox_vault_satisfied_generation(tmp_path):
    vault_dir = tmp_path / "satisfied_vault"
    sandbox = SandboxVault(vault_dir)
    results = sandbox.build(violations=False)

    assert Path(results["path"]).exists()
    assert Path(results["db_path"]).exists()
    assert Path(results["data_path"]).exists()
    assert Path(results["design_path"]).exists()
    assert Path(results["sessions_path"]).exists()
    assert Path(results["registry_path"]).exists()

    # Check Markdown files exist
    assert (vault_dir / "notes" / "orphan_causal.md").exists()
    assert (vault_dir / "notes" / "confounder_hub.md").exists()
    assert (vault_dir / "notes" / "target_outcome.md").exists()

    # Check DB structure and content
    conn = sqlite3.connect(results["db_path"])
    cursor = conn.cursor()
    
    # Check that views return valid rows
    cursor.execute("SELECT id FROM orphaned_notes")
    orphans = cursor.fetchall()
    assert len(orphans) == 1
    assert orphans[0][0] == "note1"

    cursor.execute("SELECT id FROM hub_notes")
    hubs = cursor.fetchall()
    assert len(hubs) == 3

    cursor.execute("SELECT * FROM broken_links")
    broken = cursor.fetchall()
    assert len(broken) == 0  # No violations means no broken links

    conn.close()

    # Check study design
    with open(results["design_path"], "r") as f:
        design = yaml.safe_load(f)
    assert design["treatment"] == "W"
    assert design["outcome"] == "Y"
    assert "X" in design["covariates"]
    assert design["sutva_responses"]["interference"] == "no"


def test_sandbox_vault_violated_generation(tmp_path):
    vault_dir = tmp_path / "violated_vault"
    sandbox = SandboxVault(vault_dir)
    results = sandbox.build(violations=True)

    # Check DB has a broken link
    conn = sqlite3.connect(results["db_path"])
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM broken_links")
    broken = cursor.fetchall()
    assert len(broken) == 1
    assert broken[0][2] == "notes/broken_target.md"
    conn.close()

    # Check study design
    with open(results["design_path"], "r") as f:
        design = yaml.safe_load(f)
    assert design["covariates"] == ["X"]  # Covariate X adjusted, but positivity / exchangeability still fail
    assert design["sutva_responses"]["interference"] == "yes"  # SUTVA violation


def test_cli_sandbox_generate(tmp_path):
    vault_dir = tmp_path / "cli_vault"
    runner = CliRunner()
    
    # Generate satisfied vault
    result = runner.invoke(main, ["sandbox", "generate", str(vault_dir)])
    assert result.exit_code == 0
    assert "Sandbox Vault successfully generated!" in result.output
    assert (vault_dir / "vault_db.sqlite").exists()
    assert (vault_dir / "study_design.yaml").exists()

    # Check we can run Obsidian plugin command against it
    result_obs = runner.invoke(main, ["obs", "--db-path", str(vault_dir / "vault_db.sqlite"), "orphans"])
    assert result_obs.exit_code == 0
    assert "Orphan Causal Note" in result_obs.output

    # Check we can run Atlas plugin command against it
    sessions_path = vault_dir / "atlas" / "sessions.yaml"
    registry_path = vault_dir / "atlas" / "registry.yaml"
    result_atlas = runner.invoke(
        main,
        [
            "atlas",
            "--sessions-path",
            str(sessions_path),
            "--registry-path",
            str(registry_path),
            "status",
        ],
    )
    assert result_atlas.exit_code == 0
    assert "agy-sandbox" in result_atlas.output
    assert "Integration Testing" in result_atlas.output

    # Check we can run eval command against study design (satisfied case)
    result_eval = runner.invoke(main, ["eval", str(vault_dir / "study_design.yaml"), "--non-interactive"])
    assert result_eval.exit_code == 0
    assert "Positivity check passed" in result_eval.output
    assert "Exchangeability check passed" in result_eval.output
    assert "SUTVA check passed" in result_eval.output
    assert "Covariate Balance check VIOLATED" in result_eval.output
    assert "X" in result_eval.output
    assert "Balanced" not in result_eval.output


def test_cli_sandbox_generate_violations(tmp_path):
    # Setup _violations vault
    vault_dir = tmp_path / "cli_vault_violations"
    runner = CliRunner()
    
    # Generate violated vault
    result = runner.invoke(main, ["sandbox", "generate", str(vault_dir), "--violations"])
    assert result.exit_code == 0
    assert "Sandbox Vault successfully generated!" in result.output

    # Check that Obsidian health command spots the broken link
    result_obs = runner.invoke(main, ["obs", "--db-path", str(vault_dir / "vault_db.sqlite"), "health"])
    assert result_obs.exit_code == 0
    assert "broken_target" in result_obs.output

    # Check that eval spots the violations
    result_eval = runner.invoke(main, ["eval", str(vault_dir / "study_design.yaml"), "--non-interactive"])
    # The eval command outputs the violations to stdout. Click return code is 0 as evaluations run normally even with statistical violations
    assert result_eval.exit_code == 0
    assert "Positivity assumption VIOLATED" in result_eval.output
    assert "Exchangeability check FAILED" in result_eval.output
    assert "SUTVA check FAILED" in result_eval.output
    assert "Covariate Balance check passed" in result_eval.output


def test_cli_eval_propensity_matching(tmp_path):
    vault_dir = tmp_path / "matching_vault"
    runner = CliRunner()
    
    # Generate satisfied vault
    result = runner.invoke(main, ["sandbox", "generate", str(vault_dir)])
    assert result.exit_code == 0
    
    # Clean up any existing report first
    report_path = Path.cwd() / ".agy" / "report.md"
    if report_path.exists():
        report_path.unlink()

    # Run eval with matching
    result_eval = runner.invoke(main, ["eval", str(vault_dir / "study_design.yaml"), "--non-interactive", "--method", "matching"])
    assert result_eval.exit_code == 0
    # Output should print the pre/post balance table containing before/after SMDs
    assert "SMD (Pre)" in result_eval.output
    assert "SMD (Post)" in result_eval.output
    assert "Status (Matching)" in result_eval.output

    # Check generated report contents
    assert report_path.exists()
    report_content = report_path.read_text()
    assert "Mean T (Pre)" in report_content
    assert "Mean C (Pre)" in report_content
    assert "Mean T (Post)" in report_content
    assert "Mean C (Post)" in report_content
    assert "SMD (Pre)" in report_content
    assert "SMD (Post)" in report_content


def test_cli_eval_propensity_weighting(tmp_path):
    vault_dir = tmp_path / "weighting_vault"
    runner = CliRunner()
    
    # Generate satisfied vault
    result = runner.invoke(main, ["sandbox", "generate", str(vault_dir)])
    assert result.exit_code == 0
    
    # Clean up any existing report first
    report_path = Path.cwd() / ".agy" / "report.md"
    if report_path.exists():
        report_path.unlink()

    # Run eval with weighting
    result_eval = runner.invoke(main, ["eval", str(vault_dir / "study_design.yaml"), "--non-interactive", "--method", "weighting"])
    assert result_eval.exit_code == 0
    assert "SMD (Pre)" in result_eval.output
    assert "SMD (Post)" in result_eval.output
    assert "Status (Weighting)" in result_eval.output

    # Check generated report contents
    assert report_path.exists()
    report_content = report_path.read_text()
    assert "Mean T (Pre)" in report_content
    assert "Mean C (Pre)" in report_content
    assert "Mean T (Post)" in report_content
    assert "Mean C (Post)" in report_content
    assert "SMD (Pre)" in report_content
    assert "SMD (Post)" in report_content



