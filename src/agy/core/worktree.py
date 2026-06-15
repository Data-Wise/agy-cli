import os
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any


class WorktreeManager:
    """
    Manages git worktrees for agy-cli features, enforcing persistent isolation rules
    and synchronizing active worktrees with the project .STATUS file.
    """

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.status_file = self.project_root / ".STATUS"
        self.worktrees_dir = Path(os.path.expanduser("~/.git-worktrees/agy-cli"))

    def add_worktree(self, name: str) -> Dict[str, Any]:
        """
        Creates a new worktree off the dev branch.
        """
        clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
        branch_name = f"feature/{clean_name}"
        worktree_path = self.worktrees_dir / f"feature-{clean_name}"

        # Run git worktree add ~/.git-worktrees/agy-cli/feature-<name> -b feature/<name> dev
        cmd = [
            "git",
            "worktree",
            "add",
            str(worktree_path),
            "-b",
            branch_name,
            "dev",
        ]
        res = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
        )

        if res.returncode != 0:
            raise RuntimeError(f"Failed to create worktree: {res.stderr.strip()}")

        # Semantic caching of .venv
        src_venv = self.project_root / ".venv"
        dest_venv = worktree_path / ".venv"
        if src_venv.exists() and not dest_venv.exists():
            try:
                os.symlink(src_venv.resolve(), dest_venv)
            except Exception:
                pass

        self._track_in_status(str(worktree_path), add=True)

        return {
            "name": clean_name,
            "branch": branch_name,
            "path": str(worktree_path),
        }

    def remove_worktree(self, name: str) -> Dict[str, Any]:
        """
        Removes the specified worktree and force deletes its branch.
        """
        clean_name = re.sub(r"[^a-zA-Z0-9_-]", "", name)
        branch_name = f"feature/{clean_name}"
        worktree_path = self.worktrees_dir / f"feature-{clean_name}"

        # 1. Run git worktree remove
        cmd_remove = ["git", "worktree", "remove", str(worktree_path)]
        res_remove = subprocess.run(
            cmd_remove,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
        )
        if res_remove.returncode != 0:
            # Fallback in case directory was manually deleted but not unregistered
            cmd_prune = ["git", "worktree", "prune"]
            subprocess.run(cmd_prune, cwd=str(self.project_root))

        # 2. Delete the local feature branch
        cmd_branch = ["git", "branch", "-D", branch_name]
        subprocess.run(cmd_branch, cwd=str(self.project_root))

        self._track_in_status(str(worktree_path), add=False)

        return {
            "name": clean_name,
            "branch": branch_name,
            "path": str(worktree_path),
        }

    def list_worktrees(self) -> List[Dict[str, str]]:
        """
        Lists registered git worktrees.
        """
        cmd = ["git", "worktree", "list"]
        res = subprocess.run(
            cmd,
            cwd=str(self.project_root),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            return []

        worktrees = []
        lines = res.stdout.strip().split("\n")
        for line in lines:
            if not line.strip():
                continue
            parts = line.split()
            path = parts[0]
            # Git output format is typically: <path> <commit-hash> [<branch-name>]
            branch = ""
            for part in parts:
                if part.startswith("[") and part.endswith("]"):
                    branch = part[1:-1]
                    break
            worktrees.append({"path": path, "branch": branch})

        return worktrees

    def _track_in_status(self, path: str, add: bool = True):
        """
        Updates the local .STATUS file tracking list.
        """
        if not self.status_file.exists():
            return

        with open(self.status_file, "r") as f:
            content = f.read()

        # Parse sections
        lines = content.split("\n")
        tracking_idx = -1
        for idx, line in enumerate(lines):
            if line.strip() == "## Active Worktrees":
                tracking_idx = idx
                break

        # Generate new tracking block
        current_tracked = []
        if tracking_idx != -1:
            # Read existing tracking lines
            scan_idx = tracking_idx + 1
            while scan_idx < len(lines) and (lines[scan_idx].startswith("- ") or not lines[scan_idx].strip()):
                if lines[scan_idx].startswith("- "):
                    current_tracked.append(lines[scan_idx][2:].strip())
                scan_idx += 1
            # Remove old tracking block lines
            del lines[tracking_idx:scan_idx]

        if add:
            if path not in current_tracked:
                current_tracked.append(path)
        else:
            if path in current_tracked:
                current_tracked.remove(path)

        # Re-insert tracking block if there are tracked worktrees
        if current_tracked:
            tracking_lines = ["## Active Worktrees"]
            for p in current_tracked:
                tracking_lines.append(f"- {p}")
            tracking_lines.append("")
            # Find the best insertion point (right before Links, or at the end)
            links_idx = -1
            for idx, line in enumerate(lines):
                if line.strip() == "## Links":
                    links_idx = idx
                    break
            if links_idx != -1:
                lines[links_idx:links_idx] = tracking_lines
            else:
                lines.extend(tracking_lines)

        # Write status file back
        with open(self.status_file, "w") as f:
            f.write("\n".join(lines))
