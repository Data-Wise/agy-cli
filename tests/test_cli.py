import os
import json
import sqlite3
import yaml
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


def test_cli_obs_commands(tmp_path):
    # Setup mock sqlite DB
    db_file = tmp_path / "test_cli_vault_db.sqlite"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE notes (id TEXT PRIMARY KEY, vault_id TEXT, path TEXT, title TEXT, modified_at TIMESTAMP)")
    conn.execute("CREATE TABLE links (id INTEGER PRIMARY KEY AUTOINCREMENT, source_note_id TEXT, target_note_id TEXT, target_path TEXT, link_type TEXT)")
    conn.execute("CREATE TABLE graph_metrics (note_id TEXT PRIMARY KEY, pagerank REAL, in_degree INTEGER, out_degree INTEGER)")
    
    # Insert one orphan note
    conn.execute("INSERT INTO notes VALUES ('note1', 'vault-1', 'path1.md', 'Orphan Note', '2026-06-12 12:00:00')")
    # Insert one hub note
    conn.execute("INSERT INTO notes VALUES ('note2', 'vault-1', 'path2.md', 'Hub Note', '2026-06-12 12:01:00')")
    conn.execute("INSERT INTO graph_metrics VALUES ('note2', 0.8, 1, 1)")
    # Insert one broken link
    conn.execute("INSERT INTO links (source_note_id, target_note_id, target_path, link_type) VALUES ('note2', NULL, 'missing.md', 'broken')")
    conn.commit()
    conn.close()

    runner = CliRunner()
    
    # Test orphans command
    result = runner.invoke(main, ["obs", "--db-path", str(db_file), "orphans"])
    assert result.exit_code == 0
    assert "Orphan Note" in result.output
    
    # Test hubs command
    result = runner.invoke(main, ["obs", "--db-path", str(db_file), "hubs"])
    assert result.exit_code == 0
    assert "Hub Note" in result.output
    
    # Test health command
    result = runner.invoke(main, ["obs", "--db-path", str(db_file), "health"])
    assert result.exit_code == 0
    assert "missing.md" in result.output


def test_cli_atlas_commands(tmp_path):
    sessions_file = tmp_path / "sessions.yaml"
    registry_file = tmp_path / "registry.yaml"
    
    yaml.safe_dump([
        {
            "id": "session-1",
            "project": "flow-cli",
            "task": "Work session",
            "startTime": "2026-06-12T14:00:00Z",
            "state": "active",
            "context": {"description": "Implementing plugin integrations"}
        }
    ], open(sessions_file, "w"))
    
    yaml.safe_dump({
        "breadcrumbs": [{"text": "First breadcrumb", "type": "note", "project": "flow-cli", "timestamp": "2026-06-12T14:00:00Z"}],
        "captures": [{"text": "inbox item", "status": "inbox"}]
    }, open(registry_file, "w"))

    runner = CliRunner()
    
    # Test status command
    result = runner.invoke(main, ["atlas", "--sessions-path", str(sessions_file), "--registry-path", str(registry_file), "status"])
    assert result.exit_code == 0
    assert "flow-cli" in result.output
    assert "Implementing plugin integrations" in result.output
    
    # Test trail command
    result = runner.invoke(main, ["atlas", "--sessions-path", str(sessions_file), "--registry-path", str(registry_file), "trail"])
    assert result.exit_code == 0
    assert "First breadcrumb" in result.output
