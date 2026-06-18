import subprocess
import pytest
from pathlib import Path

from agy.core.worktree import WorktreeManager


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
        "## Progress: 95\n"
        "## Focus: Testing\n"
        "\n"
        "## Links\n"
        "- **Spec**: file:///spec.md\n"
    )
    (tmp_path / ".STATUS").write_text(status_content)

    return tmp_path


def test_worktree_manager_lifecycle(temp_git_repo):
    # Setup isolated worktrees directory
    wt_dir = temp_git_repo / "git-worktrees"
    wt_dir.mkdir()

    # Initialize WorktreeManager
    manager = WorktreeManager(temp_git_repo)
    manager.worktrees_dir = wt_dir  # Override global path for tests

    # 1. Add worktree
    res = manager.add_worktree("test-feature")
    assert res["name"] == "test-feature"
    assert res["branch"] == "feature/test-feature"
    assert Path(res["path"]).exists()

    # Verify tracking in .STATUS
    status_text = (temp_git_repo / ".STATUS").read_text()
    assert "## Active Worktrees" in status_text
    assert res["path"] in status_text

    # 2. List worktrees
    wts = manager.list_worktrees()
    paths = [wt["path"] for wt in wts]
    assert any(res["path"] in p for p in paths)

    # 3. Remove worktree
    manager.remove_worktree("test-feature")
    assert not Path(res["path"]).exists()

    # Verify removed from tracking in .STATUS
    status_text_removed = (temp_git_repo / ".STATUS").read_text()
    assert "## Active Worktrees" not in status_text_removed
