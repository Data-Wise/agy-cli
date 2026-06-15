import os
import sys
import yaml
import pytest
import subprocess
from pathlib import Path
from agy.core.worktree import WorktreeManager
from agy.plugins.atlas import AtlasBridge
from agy.cli import setup_error_logging


@pytest.fixture
def temp_git_repo(tmp_path):
    # Initialize a temporary git repository
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"], cwd=str(tmp_path), capture_output=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=str(tmp_path), capture_output=True
    )

    # Create initial commit to establish HEAD branch
    (tmp_path / "init.txt").write_text("initial file")
    subprocess.run(["git", "add", "init.txt"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial commit"], cwd=str(tmp_path), capture_output=True
    )

    # Create dev branch
    subprocess.run(["git", "branch", "dev"], cwd=str(tmp_path), capture_output=True)

    # Create mock .STATUS file
    status_content = (
        "## Project: agy-cli\n"
        "## Progress: 100\n"
        "## Focus: Testing\n"
        "\n"
        "## Links\n"
        "- **Spec**: file:///spec.md\n"
    )
    (tmp_path / ".STATUS").write_text(status_content)

    return tmp_path


def test_dogfood_worktree_venv_cache(temp_git_repo):
    # Setup isolated worktrees directory
    wt_dir = temp_git_repo / "git-worktrees"
    wt_dir.mkdir()

    # Create dummy .venv in the project root
    dummy_venv = temp_git_repo / ".venv"
    dummy_venv.mkdir()
    (dummy_venv / "dummy_bin").write_text("python binary")

    # Initialize WorktreeManager
    manager = WorktreeManager(temp_git_repo)
    manager.worktrees_dir = wt_dir  # Override global path for tests

    # Add worktree
    res = manager.add_worktree("venv-cache-test")
    wt_path = Path(res["path"])
    assert wt_path.exists()

    # Verify .venv symlink was created in the worktree
    dest_venv = wt_path / ".venv"
    assert dest_venv.exists()
    assert dest_venv.is_symlink()
    assert os.readlink(dest_venv) == str(dummy_venv.resolve())


def test_dogfood_atlas_session_lifecycle(tmp_path):
    sessions_file = tmp_path / "sessions.yaml"
    registry_file = tmp_path / "registry.yaml"

    bridge = AtlasBridge(sessions_path=str(sessions_file), registry_path=str(registry_file))

    # 1. Create a session
    res = bridge.create_session(
        project="test-proj", task="Implement tests", description="Writing tests"
    )
    assert res["project"] == "test-proj"
    assert res["task"] == "Implement tests"
    assert res["description"] == "Writing tests"

    # Verify YAML file structure
    sessions_data = yaml.safe_load(open(sessions_file))
    assert len(sessions_data) == 1
    assert sessions_data[0]["project"] == "test-proj"
    assert sessions_data[0]["state"] == "active"

    # 2. Add breadcrumb
    crumb = bridge.add_breadcrumb(text="Touch test_dogfood.py", type_str="file")
    assert crumb["project"] == "test-proj"
    assert crumb["text"] == "Touch test_dogfood.py"

    registry_data = yaml.safe_load(open(registry_file))
    assert len(registry_data["breadcrumbs"]) == 1
    assert registry_data["breadcrumbs"][0]["text"] == "Touch test_dogfood.py"

    # 3. Create a second session (should end the first)
    res2 = bridge.create_session(
        project="second-proj", task="Documentation", description="Write docs"
    )
    assert res2["project"] == "second-proj"

    sessions_data_updated = yaml.safe_load(open(sessions_file))
    assert len(sessions_data_updated) == 2
    assert sessions_data_updated[0]["project"] == "test-proj"
    assert sessions_data_updated[0]["state"] == "ended"
    assert sessions_data_updated[1]["project"] == "second-proj"
    assert sessions_data_updated[1]["state"] == "active"


def test_dogfood_error_logging(tmp_path, monkeypatch):
    log_file = tmp_path / "obs.log"
    monkeypatch.setenv("AGY_LOG_FILE", str(log_file))

    # Setup logger with the environment variable overrides
    setup_error_logging()

    # Manually trigger sys.excepthook to simulate an unhandled error
    try:
        raise ValueError("Simulated unhandled exception for dogfooding tests")
    except ValueError:
        exc_type, exc_val, exc_tb = sys.exc_info()
        # Mock sys.__excepthook__ so it doesn't print to stdout/stderr in test output
        monkeypatch.setattr(sys, "__excepthook__", lambda *args: None)
        sys.excepthook(exc_type, exc_val, exc_tb)

    assert log_file.exists()
    log_content = log_file.read_text()
    assert "ERROR" in log_content
    assert "ValueError: Simulated unhandled exception for dogfooding tests" in log_content
