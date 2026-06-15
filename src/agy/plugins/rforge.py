import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional


class RForgeBridge:
    """
    In-process bridge to R packages, automating devtools checking,
    unit testing, and Roxygen2 documentation compiling.
    """

    def __init__(self, pkg_dir: Optional[str] = None):
        self.pkg_dir = Path(pkg_dir or os.getcwd())

    def is_r_package(self) -> bool:
        """
        Verifies if the target directory contains an R package (has a DESCRIPTION file).
        """
        return (self.pkg_dir / "DESCRIPTION").exists()

    def check_package(self) -> Dict[str, Any]:
        """
        Runs devtools::check(document = FALSE) on the package.
        """
        if not self.is_r_package():
            return {
                "success": False,
                "error": f"No DESCRIPTION file found. '{self.pkg_dir}' is not an R package.",
                "stdout": "",
                "stderr": "",
            }
        
        pkg_path_str = str(self.pkg_dir).replace('\\', '/')
        r_cmd = f"devtools::check(pkg = '{pkg_path_str}', document = FALSE)"
        return self._run_r_cmd(r_cmd)

    def test_package(self) -> Dict[str, Any]:
        """
        Runs devtools::test() on the package.
        """
        if not self.is_r_package():
            return {
                "success": False,
                "error": f"No DESCRIPTION file found. '{self.pkg_dir}' is not an R package.",
                "stdout": "",
                "stderr": "",
            }
        
        pkg_path_str = str(self.pkg_dir).replace('\\', '/')
        r_cmd = f"devtools::test(pkg = '{pkg_path_str}')"
        return self._run_r_cmd(r_cmd)

    def document_package(self) -> Dict[str, Any]:
        """
        Runs devtools::document() on the package.
        """
        if not self.is_r_package():
            return {
                "success": False,
                "error": f"No DESCRIPTION file found. '{self.pkg_dir}' is not an R package.",
                "stdout": "",
                "stderr": "",
            }
        
        pkg_path_str = str(self.pkg_dir).replace('\\', '/')
        r_cmd = f"devtools::document(pkg = '{pkg_path_str}')"
        return self._run_r_cmd(r_cmd)

    def _run_r_cmd(self, r_code: str) -> Dict[str, Any]:
        cmd = ["R", "--vanilla", "--quiet", "-e", r_code]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return {
            "success": res.returncode == 0,
            "stdout": res.stdout,
            "stderr": res.stderr,
            "returncode": res.returncode,
            "error": None if res.returncode == 0 else "R execution failed.",
        }
