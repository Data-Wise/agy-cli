import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List


class ReportSynthesizer:
    """
    Synthesizes the results of parallel validation checks into a clean,
    well-formatted Markdown report.
    """

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)

    def synthesize(self, results: Dict[str, Any], meta: Dict[str, Any]) -> Path:
        """
        Creates and writes the Markdown report to <output_dir>/.agy/report.md.
        """
        agy_dir = self.output_dir / ".agy"
        agy_dir.mkdir(parents=True, exist_ok=True)
        report_path = agy_dir / "report.md"

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_duration = results.get("total_duration", 0.0)

        # Retrieve check outcomes
        pos = results.get("positivity", {})
        exc = results.get("exchangeability", {})
        sut = results.get("sutva", {}).get("result", {})
        bal = results.get("balance", {})

        # Status emojis
        status_pos = "✔" if pos.get("satisfied") else "✗"
        if pos.get("skipped"):
            status_pos = "⚠ (Skipped)"
        elif pos.get("error"):
            status_pos = "🔥 (Error)"

        status_exc = "✔" if exc.get("satisfied") else "✗"
        if exc.get("skipped"):
            status_exc = "⚠ (Skipped)"
        elif exc.get("error"):
            status_exc = "🔥 (Error)"

        status_sut = "✔" if sut.get("satisfied") else "✗"
        if results.get("sutva", {}).get("skipped"):
            status_sut = "⚠ (Skipped)"
        elif results.get("sutva", {}).get("error"):
            status_sut = "🔥 (Error)"

        status_bal = "✔" if bal.get("satisfied") else "✗"
        if bal.get("skipped"):
            status_bal = "⚠ (Skipped)"
        elif bal.get("error"):
            status_bal = "🔥 (Error)"

        content = []
        content.append("# Causal Validation Report")
        content.append(f"*   **Generated At:** {now_str}")
        content.append(f"*   **Total Check Duration:** {total_duration:.4f} seconds\n")

        content.append("## 📊 Summary Dashboard")
        content.append(f"*   **Positivity:** {status_pos}")
        content.append(f"*   **Exchangeability:** {status_exc}")
        content.append(f"*   **SUTVA:** {status_sut}")
        content.append(f"*   **Covariate Balance (SMD):** {status_bal}\n")

        content.append("---")
        content.append("## 🔍 Study Settings")
        content.append(f"*   **Treatment (W):** `{meta.get('treatment', 'N/A')}`")
        content.append(f"*   **Outcome (Y):** `{meta.get('outcome', 'N/A')}`")
        content.append(f"*   **Covariates (X):** `{meta.get('covariates', [])}`")
        content.append(f"*   **Dataset Path:** `{meta.get('data', 'N/A')}`")
        content.append(f"*   **Causal DAG:** `{meta.get('dag', 'N/A')}`\n")

        content.append("---")

        # 1. Positivity details
        content.append("## 1. Positivity Check")
        if pos.get("skipped"):
            content.append(f"*   *Check Skipped:* {pos.get('reason')}")
        elif pos.get("error"):
            content.append(f"*   *Check Failed with Execution Error:* `{pos.get('error')}`")
        elif pos.get("satisfied"):
            content.append("*   [bold green]Passed:[/bold green] All covariate strata have sufficient treatment variation ($0 < P(W=1|X) < 1$).")
        else:
            content.append("*   [bold red]Violated:[/bold red] Found strata with no treatment variation:")
            violations = pos.get("violations", [])
            if violations:
                headers = list(violations[0].keys())
                header_row = " | ".join(headers)
                divider_row = " | ".join(["---"] * len(headers))
                content.append(f"\n| {header_row} |")
                content.append(f"| {divider_row} |")
                for row in violations:
                    val_row = " | ".join(str(row[h]) for h in headers)
                    content.append(f"| {val_row} |")
            content.append("")
        content.append("")

        # 2. Exchangeability details
        content.append("## 2. Backdoor Exchangeability Check")
        if exc.get("skipped"):
            content.append(f"*   *Check Skipped:* {exc.get('reason')}")
        elif exc.get("error"):
            content.append(f"*   *Check Failed with Execution Error:* `{exc.get('error')}`")
        elif exc.get("satisfied"):
            content.append(f"*   **Passed:** {exc.get('reason')}")
        else:
            content.append(f"*   **Violated:** {exc.get('reason')}")
            desc_v = exc.get("descendant_violations", [])
            if desc_v:
                content.append(f"    *   *Descendant Violations:* Covariates {desc_v} are downstream descendants of treatment.")
            if not exc.get("backdoor_blocked"):
                content.append("    *   *Backdoor Paths:* Backdoor paths are not fully blocked/d-separated by adjusted covariates.")
        content.append("")

        # 3. SUTVA details
        content.append("## 3. SUTVA Check")
        if results.get("sutva", {}).get("skipped"):
            content.append("*   *Check Skipped.*")
        elif sut.get("satisfied"):
            content.append(f"*   **Passed:** {sut.get('summary')}")
        else:
            content.append(f"*   **Violated:** {sut.get('summary')}")
            for viol in sut.get("violations", []):
                content.append(f"    *   Detected SUTVA violation type: `{viol}`")
        content.append("")

        # 4. Covariate Balance details
        content.append("## 4. Covariate Balance Check (SMD)")
        if bal.get("skipped"):
            content.append(f"*   *Check Skipped:* {bal.get('reason')}")
        elif bal.get("error"):
            content.append(f"*   *Check Failed with Execution Error:* `{bal.get('error')}`")
        elif bal.get("satisfied"):
            content.append("*   **Passed:** All covariates are balanced ($SMD \\le 0.1$).")
            self._append_balance_table(content, bal.get("balance", []), bal.get("method", "none"))
        else:
            content.append("*   **Violated:** One or more covariates are imbalanced ($SMD > 0.1$). Details below:")
            self._append_balance_table(content, bal.get("balance", []), bal.get("method", "none"))
        content.append("")

        with open(report_path, "w") as f:
            f.write("\n".join(content))

        return report_path

    def _append_balance_table(self, content: List[str], balance_rows: List[Dict[str, Any]], method: str = "none"):
        if not balance_rows:
            return
        if method in ("matching", "weighting"):
            headers = ["Covariate", "Mean T (Pre)", "Mean C (Pre)", "SMD (Pre)", "Mean T (Post)", "Mean C (Post)", "SMD (Post)", "Status"]
            header_row = " | ".join(headers)
            divider_row = " | ".join(["---"] * len(headers))
            content.append(f"\n| {header_row} |")
            content.append(f"| {divider_row} |")
            for row in balance_rows:
                status = "Balanced" if row.get("satisfied_post") else "Imbalanced"
                m1_pre = f"{row.get('mean_treated_pre', 0.0):.4f}"
                m0_pre = f"{row.get('mean_control_pre', 0.0):.4f}"
                smd_pre = f"{row.get('smd_pre', 0.0):.4f}"
                m1_post = f"{row.get('mean_treated_post', 0.0):.4f}"
                m0_post = f"{row.get('mean_control_post', 0.0):.4f}"
                smd_post = f"{row.get('smd_post', 0.0):.4f}"
                content.append(
                    f"| `{row.get('covariate')}` | {m1_pre} | {m0_pre} | {smd_pre} | {m1_post} | {m0_post} | {smd_post} | {status} |"
                )
        else:
            headers = ["Covariate", "Mean (Treated)", "Mean (Control)", "Var (Treated)", "Var (Control)", "SMD", "Status"]
            header_row = " | ".join(headers)
            divider_row = " | ".join(["---"] * len(headers))
            content.append(f"\n| {header_row} |")
            content.append(f"| {divider_row} |")
            for row in balance_rows:
                status = "Balanced" if row.get("satisfied_post") else "Imbalanced"
                smd_val = f"{row.get('smd_pre', 0.0):.4f}"
                m1 = f"{row.get('mean_treated_pre', 0.0):.4f}"
                m0 = f"{row.get('mean_control_pre', 0.0):.4f}"
                v1 = f"{row.get('var_treated_pre', 0.0):.4f}"
                v0 = f"{row.get('var_control_pre', 0.0):.4f}"
                content.append(
                    f"| `{row.get('covariate')}` | {m1} | {m0} | {v1} | {v0} | {smd_val} | {status} |"
                )
