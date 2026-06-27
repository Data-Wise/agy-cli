import click
import json
import yaml
import os
import sys
import io
import networkx as nx
from importlib.metadata import version, PackageNotFoundError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

try:
    __version__ = version("agy-cli")
except PackageNotFoundError:
    __version__ = "dev"

from agy.core.dag_compiler import (
    parse_dag_string,
    compile_to_r,
)
from agy.core.sandbox import SandboxVault
from agy.agents.orchestrator import ValidationOrchestrator
from agy.agents.synthesizer import ReportSynthesizer
from agy.core.worktree import WorktreeManager
from pathlib import Path

import logging
from logging.handlers import RotatingFileHandler


def setup_error_logging():
    log_file_env = os.environ.get("AGY_LOG_FILE")
    if log_file_env:
        log_file = os.path.abspath(log_file_env)
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
    else:
        log_dir = os.path.expanduser("~/.config/obs")
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, "obs.log")

    logger = logging.getLogger("agy")
    logger.setLevel(logging.ERROR)

    handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    handler.setFormatter(formatter)

    # Clear existing handlers to allow clean re-configuration in tests or re-runs
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(handler)

    def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("Unhandled exception occurred", exc_info=(exc_type, exc_value, exc_traceback))
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

    sys.excepthook = handle_unhandled_exception


setup_error_logging()

console = Console()


@click.group()
@click.version_option(version=__version__)
def main():
    """cagy - Causal Antigravity CLI workflow engine."""
    pass


@main.command()
@click.option("--verbose", "-v", is_flag=True, help="Show detailed status information.")
def status(verbose):
    """Show the current project status."""
    console.print(
        Panel("[bold green]agy-cli[/bold green] - Active and initialized.", title="Status")
    )


@main.command()
@click.argument("study_design_file", type=click.Path(exists=True), required=False)
@click.option("--treatment", "-t", type=str, help="Treatment (exposure) variable name.")
@click.option("--outcome", "-o", type=str, help="Outcome variable name.")
@click.option("--covariates", "-c", type=str, help="Comma-separated list of covariate names.")
@click.option(
    "--data", "-d", type=click.Path(exists=True), help="Path to observational data CSV file."
)
@click.option(
    "--dag-str", "-g", type=str, help="Causal DAG text description (e.g. 'W -> Y, X -> W, X -> Y')."
)
@click.option(
    "--interactive/--non-interactive", default=True, help="Run interactive SUTVA prompts."
)
@click.option(
    "--method",
    type=click.Choice(["none", "matching", "weighting"]),
    default="none",
    help="Propensity score adjustment method for diagnostics.",
)
def eval(study_design_file, treatment, outcome, covariates, data, dag_str, interactive, method):
    """Evaluate observational study assumptions (Positivity, Exchangeability, SUTVA)."""

    # 1. Load study design file if provided
    design = {}
    if study_design_file:
        try:
            with open(study_design_file, "r") as f:
                if study_design_file.endswith(".json"):
                    design = json.load(f)
                else:
                    design = yaml.safe_load(f)
        except Exception as e:
            console.print(f"[bold red]Error loading study design file:[/bold red] {e}")
            sys.exit(1)

    # 2. Extract settings, prioritizing CLI options over file values
    data_path = data or design.get("data")
    if data_path and not os.path.isabs(data_path) and study_design_file:
        design_dir = os.path.dirname(os.path.abspath(study_design_file))
        data_path = os.path.join(design_dir, data_path)
    treatment_var = treatment or design.get("treatment")
    outcome_var = outcome or design.get("outcome")

    # Parse covariates
    covs_list = []
    covs_raw = covariates or design.get("covariates")
    if covs_raw:
        if isinstance(covs_raw, list):
            covs_list = [str(c).strip() for c in covs_raw]
        else:
            covs_list = [c.strip() for c in str(covs_raw).split(",") if c.strip()]

    dag_desc = dag_str or design.get("dag")
    method_val = method if method != "none" else (design.get("method") or "none")

    console.print(
        Panel.fit(
            "[bold blue]Causal Inference Assumption Validator[/bold blue]", border_style="blue"
        )
    )

    # 3. Parse DAG if provided
    graph = None
    if dag_desc:
        try:
            nodes, edges = parse_dag_string(dag_desc)
            graph = nx.DiGraph()
            graph.add_nodes_from(nodes)
            graph.add_edges_from(edges)
        except Exception as e:
            console.print(f"[bold red]Failed to parse DAG description:[/bold red] {e}")

    # 4. Instantiate and run orchestrator
    sutva_responses = design.get("sutva_responses")
    is_stdin_tty = sys.stdin.isatty()
    run_interactively = interactive and is_stdin_tty and not sutva_responses

    orchestrator = ValidationOrchestrator(
        data_path=data_path,
        treatment=treatment_var,
        outcome=outcome_var,
        covariates=covs_list,
        graph=graph,
        dag_desc=dag_desc,
        interactive=run_interactively,
        sutva_responses=sutva_responses,
        method=method_val,
    )

    results = orchestrator.run_all()

    # 5. Output results to stdout (preserving exact strings for test assertions)
    # Positivity
    pos = results.get("positivity", {})
    if pos.get("skipped"):
        console.print(f"\n[yellow]⚠ Skipping Positivity check ({pos.get('reason')}).[/yellow]")
    elif pos.get("error"):
        console.print(
            f"\n[bold red]Positivity check failed with error:[/bold red] {pos.get('error')}"
        )
    else:
        console.print("\n[bold]Checking Positivity Assumption...[/bold]")
        if pos.get("satisfied"):
            console.print(
                "[bold green]✔ Positivity check passed.[/bold green] All covariate strata have treatment variation."
            )
        else:
            console.print(
                "[bold red]✗ Positivity assumption VIOLATED.[/bold red] Found strata with no treatment variation:"
            )
            # Create Rich table for violations
            violations = pos.get("violations", [])
            if violations:
                table = Table(show_header=True, header_style="bold red")
                for col in violations[0].keys():
                    table.add_column(col)
                for row in violations:
                    table.add_row(*[str(val) for val in row.values()])
                console.print(table)

    # Exchangeability
    exc = results.get("exchangeability", {})
    if exc.get("skipped"):
        console.print(f"\n[yellow]⚠ Skipping Exchangeability check ({exc.get('reason')}).[/yellow]")
    elif exc.get("error"):
        console.print(
            f"\n[bold red]Exchangeability check failed with error:[/bold red] {exc.get('error')}"
        )
    else:
        console.print("\n[bold]Checking Backdoor Exchangeability...[/bold]")
        if exc.get("satisfied"):
            console.print(
                f"[bold green]✔ Exchangeability check passed.[/bold green] {exc.get('reason')}"
            )
        else:
            console.print(
                f"[bold red]✗ Exchangeability check FAILED.[/bold red] {exc.get('reason')}"
            )

    # SUTVA
    sut = results.get("sutva", {}).get("result", {})
    if results.get("sutva", {}).get("skipped"):
        console.print("\n[yellow]⚠ Skipping SUTVA check.[/yellow]")
    else:
        console.print("\n[bold]Checking SUTVA Assumptions...[/bold]")
        if sut.get("satisfied"):
            console.print(f"[bold green]✔ SUTVA check passed.[/bold green] {sut.get('summary')}")
        else:
            console.print(f"[bold red]✗ SUTVA check FAILED.[/bold red] {sut.get('summary')}")

    # Covariate Balance
    bal = results.get("balance", {})
    if bal.get("skipped"):
        console.print(
            f"\n[yellow]⚠ Skipping Covariate Balance check ({bal.get('reason')}).[/yellow]"
        )
    elif bal.get("error"):
        console.print(
            f"\n[bold red]Covariate Balance check failed with error:[/bold red] {bal.get('error')}"
        )
    else:
        console.print("\n[bold]Checking Covariate Balance (Standardized Mean Difference)...[/bold]")
        if bal.get("satisfied"):
            console.print(
                "[bold green]✔ Covariate Balance check passed.[/bold green] All covariates are balanced (SMD <= 0.1)."
            )
        else:
            console.print(
                "[bold red]✗ Covariate Balance check VIOLATED.[/bold red] Found imbalanced covariates (SMD > 0.1):"
            )

        balance_rows = bal.get("balance", [])
        if balance_rows:
            adj_method = bal.get("method", "none")
            if adj_method in ("matching", "weighting"):
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Covariate")
                table.add_column("SMD (Pre)")
                table.add_column("SMD (Post)")
                table.add_column(f"Status ({adj_method.capitalize()})")

                for row in balance_rows:
                    status_str = (
                        "[green]Balanced[/green]"
                        if row.get("satisfied_post")
                        else "[red]Imbalanced[/red]"
                    )
                    table.add_row(
                        row.get("covariate"),
                        f"{row.get('smd_pre', 0.0):.4f}",
                        f"{row.get('smd_post', 0.0):.4f}",
                        status_str,
                    )
                console.print(table)
            else:
                table = Table(show_header=True, header_style="bold magenta")
                table.add_column("Covariate")
                table.add_column("Mean (Treated)")
                table.add_column("Mean (Control)")
                table.add_column("SMD")
                table.add_column("Status")

                for row in balance_rows:
                    status_str = (
                        "[green]Balanced[/green]"
                        if row.get("satisfied_post")
                        else "[red]Imbalanced[/red]"
                    )
                    table.add_row(
                        row.get("covariate"),
                        f"{row.get('mean_treated_pre', 0.0):.4f}",
                        f"{row.get('mean_control_pre', 0.0):.4f}",
                        f"{row.get('smd_pre', 0.0):.4f}",
                        status_str,
                    )
                console.print(table)

    # 6. Save Markdown Report
    try:
        synthesizer = ReportSynthesizer(Path.cwd())
        meta = {
            "treatment": treatment_var,
            "outcome": outcome_var,
            "covariates": covs_list,
            "data": data_path,
            "dag": dag_desc,
        }
        report_path = synthesizer.synthesize(results, meta)
        console.print(f"\n[dim]Synthesized Markdown Report saved to: {report_path}[/dim]")
    except Exception as e:
        console.print(f"\n[yellow]⚠ Failed to synthesize markdown report: {e}[/yellow]")


@main.command()
@click.argument("description", type=str)
@click.option("--output", "-o", type=click.Path(), help="Output R script file.")
@click.option("--treatment", "-t", type=str, help="Treatment (exposure) variable name.")
@click.option("--outcome", "-y", type=str, help="Outcome variable name.")
def dag(description, output, treatment, outcome):
    """Compile textual causal graph description to R ggdag/dagitty code."""
    try:
        nodes, edges = parse_dag_string(description)
        r_code = compile_to_r(nodes, edges, treatment, outcome)

        if output:
            with open(output, "w") as f:
                f.write(r_code)
            console.print(
                Panel(
                    f"[bold green]✔ Successfully compiled to R script:[/bold green]\n{output}",
                    title="DAG Compiler",
                )
            )
        else:
            console.print(Panel(r_code, title="Compiled R Code"))
    except Exception as e:
        console.print(f"[bold red]DAG Compilation failed:[/bold red] {e}")
        sys.exit(1)


@main.group(name="obs")
@click.option("--db-path", type=click.Path(exists=True), help="Path to Obsidian SQLite database.")
@click.pass_context
def obs_group(ctx, db_path):
    """Obsidian knowledge bridge commands."""
    ctx.ensure_object(dict)
    from agy.plugins.obsidian import ObsidianBridge

    ctx.obj["bridge"] = ObsidianBridge(db_path=db_path)


@obs_group.command(name="orphans")
@click.pass_context
def obs_orphans(ctx):
    """List orphan notes (in-degree and out-degree are 0)."""
    bridge = ctx.obj["bridge"]
    orphans = bridge.get_orphan_notes()
    if not orphans:
        console.print("[green]No orphan notes found.[/green]")
        return

    table = Table(title="Orphan Notes")
    table.add_column("Title", style="cyan")
    table.add_column("Path", style="magenta")
    table.add_column("Modified At", style="green")
    for note in orphans:
        table.add_row(
            note.get("title") or "Untitled",
            note.get("path") or "",
            note.get("modified_at") or "Unknown",
        )
    console.print(table)


@obs_group.command(name="hubs")
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of hub notes to display.")
@click.option(
    "--sort",
    "-s",
    type=click.Choice(["pagerank", "out_degree", "in_degree", "total_degree"]),
    default="pagerank",
    help="Field to sort by.",
)
@click.pass_context
def obs_hubs(ctx, limit, sort):
    """List hub notes (high centrality/connections)."""
    bridge = ctx.obj["bridge"]
    hubs = bridge.get_hub_notes(order_by=sort, limit=limit)
    if not hubs:
        console.print("[yellow]No hub notes found.[/yellow]")
        return

    table = Table(title=f"Hub Notes (Sorted by {sort})")
    table.add_column("Title", style="cyan")
    table.add_column("Path", style="magenta")
    table.add_column("PageRank", style="green")
    table.add_column("In-Degree", style="blue")
    table.add_column("Out-Degree", style="blue")
    table.add_column("Total Degree", style="yellow")
    for note in hubs:
        table.add_row(
            note.get("title") or "Untitled",
            note.get("path") or "",
            f"{note.get('pagerank', 0.0):.4f}",
            str(note.get("in_degree", 0)),
            str(note.get("out_degree", 0)),
            str(note.get("total_degree", 0)),
        )
    console.print(table)


@obs_group.command(name="health")
@click.pass_context
def obs_health(ctx):
    """Check vault graph health (e.g. broken links)."""
    bridge = ctx.obj["bridge"]
    broken = bridge.get_broken_links()
    if not broken:
        console.print(
            "[bold green]✔ Vault health check passed. No broken links found.[/bold green]"
        )
        return

    table = Table(title="Broken Links Detected", show_header=True, header_style="bold red")
    table.add_column("Source Note", style="cyan")
    table.add_column("Source Path", style="magenta")
    table.add_column("Target Path", style="yellow")
    table.add_column("Count", style="red")
    for link in broken:
        table.add_row(
            link.get("source_title") or "Untitled",
            link.get("source_path") or "",
            link.get("target_path") or "",
            str(link.get("broken_count", 1)),
        )
    console.print(table)


@obs_group.command(name="graph")
@click.option("--focus", "-f", type=str, help="Focus note title or path to traverse from.")
@click.option("--depth", "-d", type=int, default=2, help="Traversal depth from focus note.")
@click.option("--limit", "-l", type=int, default=30, help="Maximum hub notes to include when not focusing.")
@click.option(
    "--format",
    type=click.Choice(["mermaid", "ascii"]),
    default="mermaid",
    help="Output format."
)
@click.option("--out-file", "-o", type=click.Path(), help="Path to write the graph visualization.")
@click.pass_context
def obs_graph(ctx, focus, depth, limit, format, out_file):
    """Render Obsidian note connections as Mermaid or ASCII tree."""
    bridge = ctx.obj["bridge"]
    res = bridge.get_vault_graph(focus=focus, depth=depth, limit=limit)
    nodes = res["nodes"]
    edges = res["edges"]
    focus_node = res["focus_node"]

    if not nodes:
        if focus:
            console.print(f"[yellow]Focus note '{focus}' not found or has no connections.[/yellow]")
        else:
            console.print("[yellow]No notes found in graph.[/yellow]")
        return

    output_str = ""
    if format == "mermaid":
        lines = ["graph TD"]
        seen_edges = set()
        for e in edges:
            s, t = e["source_title"], e["target_title"]
            edge_key = (s, t)
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                lines.append(f'    "{s}" --> "{t}"')
        
        # Ensure all selected nodes are listed to show orphans if any
        for n in nodes:
            title = n["title"] or "Untitled"
            has_edge = False
            for e in edges:
                if e["source_title"] == title or e["target_title"] == title:
                    has_edge = True
                    break
            if not has_edge:
                lines.append(f'    "{title}"')

        output_str = "\n".join(lines)
    else:
        old_stdout = sys.stdout
        sys.stdout = mystdout = io.StringIO()
        
        # Build adjacency mapping
        adj = {}
        for n in nodes:
            adj[n["title"]] = []
        for e in edges:
            s, t = e["source_title"], e["target_title"]
            if s in adj and t in adj:
                adj[s].append(t)

        visited = set()
        def dfs(curr, prefix=""):
            if curr in visited:
                return
            visited.add(curr)
            children = adj.get(curr, [])
            for i, child in enumerate(children):
                is_last = (i == len(children) - 1)
                branch = "└── " if is_last else "├── "
                print(f"{prefix}{branch}{child}")
                next_prefix = prefix + ("    " if is_last else "│   ")
                dfs(child, next_prefix)

        if focus_node:
            print(focus_node["title"])
            dfs(focus_node["title"])
        else:
            for n in nodes:
                title = n["title"]
                if title not in visited:
                    if adj.get(title) or not any(title in children for children in adj.values()):
                        print(title)
                        dfs(title)
        
        sys.stdout = old_stdout
        output_str = mystdout.getvalue()

    if out_file:
        try:
            with open(out_file, "w") as f:
                f.write(output_str)
            console.print(f"[green]✔ Graph successfully saved to: {out_file}[/green]")
        except Exception as e:
            console.print(f"[bold red]Failed to write out-file:[/bold red] {e}")
    else:
        if format == "mermaid":
            console.print(Panel(output_str, title="Mermaid Graph Visualization", border_style="cyan"))
        else:
            console.print(Panel(output_str, title="ASCII Graph Tree", border_style="cyan"))


@obs_group.command(name="gaps")
@click.option(
    "--method-tags",
    "-m",
    default="causal-inference,mediation,regression,assumptions,MLE",
    help="Comma-separated list of tags to identify Method notes."
)
@click.option(
    "--setting-tags",
    "-s",
    default="project,data,application",
    help="Comma-separated list of tags to identify Setting/Project notes."
)
@click.option("--method-path", type=str, help="Relative path substring to filter Method notes.")
@click.option("--setting-path", type=str, help="Relative path substring to filter Setting notes.")
@click.pass_context
def obs_gaps(ctx, method_tags, setting_tags, method_path, setting_path):
    """Find literature gaps by auditing unconnected methods vs settings."""
    bridge = ctx.obj["bridge"]
    m_tags = [t.strip() for t in method_tags.split(",") if t.strip()]
    s_tags = [t.strip() for t in setting_tags.split(",") if t.strip()]

    res = bridge.get_literature_gaps(
        method_tags=m_tags,
        setting_tags=s_tags,
        method_path=method_path,
        setting_path=setting_path
    )

    console.print(
        f"\n[bold green]Obsidian Vault Causal/Literature Audit Summary[/bold green]\n"
        f"  • Classified [cyan]{res['methods_count']}[/cyan] Method notes (matching tags: {method_tags})\n"
        f"  • Classified [magenta]{res['settings_count']}[/magenta] Setting/Project notes (matching tags: {setting_tags})\n"
    )

    # 1. Table for isolated methods
    table_m = Table(title="Isolated Methods (No Application/Project Links)", show_header=True, header_style="bold red")
    table_m.add_column("Title", style="cyan")
    table_m.add_column("Path", style="magenta")
    table_m.add_column("Tags", style="green")

    for m in res["isolated_methods"]:
        table_m.add_row(m.get("title") or "Untitled", m.get("path") or "", m.get("tags") or "")

    # 2. Table for isolated settings
    table_s = Table(title="Isolated Settings/Projects (No Method Links)", show_header=True, header_style="bold red")
    table_s.add_column("Title", style="magenta")
    table_s.add_column("Path", style="cyan")
    table_s.add_column("Tags", style="green")

    for s in res["isolated_settings"]:
        table_s.add_row(s.get("title") or "Untitled", s.get("path") or "", s.get("tags") or "")

    if res["isolated_methods"]:
        console.print(table_m)
    else:
        console.print("[green]✔ No isolated Method notes found. All methods are linked to applications.[/green]")

    console.print()

    if res["isolated_settings"]:
        console.print(table_s)
    else:
        console.print("[green]✔ No isolated Setting/Project notes found. All projects are linked to methods.[/green]")


@main.group(name="atlas")
@click.option("--sessions-path", type=click.Path(exists=True), help="Path to Atlas sessions YAML.")
@click.option("--registry-path", type=click.Path(exists=True), help="Path to Atlas registry YAML.")
@click.pass_context
def atlas_group(ctx, sessions_path, registry_path):
    """Atlas state synchronizer commands."""
    ctx.ensure_object(dict)
    from agy.plugins.atlas import AtlasBridge

    ctx.obj["bridge"] = AtlasBridge(sessions_path=sessions_path, registry_path=registry_path)


@atlas_group.command(name="status")
@click.pass_context
def atlas_status(ctx):
    """Show active session status."""
    bridge = ctx.obj["bridge"]
    session = bridge.get_active_session()
    captures = bridge.get_captured_inbox_items()

    if not session:
        panel_content = "[yellow]No active session.[/yellow]\n"
        if captures:
            panel_content += f"\n[bold]Captured Inbox Items:[/bold] {len(captures)}"
        console.print(Panel(panel_content, title="Atlas Status"))
        return

    duration_secs = session.get("duration", 0)
    hours, remainder = divmod(int(duration_secs), 3600)
    minutes, seconds = divmod(remainder, 60)
    duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    panel_content = (
        f"[bold]Project:[/bold] {session.get('project')}\n"
        f"[bold]Task:[/bold] {session.get('task')}\n"
        f"[bold]Duration:[/bold] {duration_str}\n"
        f"[bold]Description:[/bold] {session.get('description')}"
    )
    if captures:
        panel_content += f"\n\n[bold]Captured Inbox Items:[/bold] {len(captures)}"

    console.print(Panel(panel_content, title="Active Atlas Session", border_style="green"))


@atlas_group.command(name="trail")
@click.option(
    "--limit", "-l", type=int, default=10, help="Maximum number of breadcrumbs to display."
)
@click.pass_context
def atlas_trail(ctx, limit):
    """Display active or recent breadcrumbs."""
    bridge = ctx.obj["bridge"]
    crumbs = bridge.get_breadcrumbs(limit=limit)
    if not crumbs:
        console.print("[yellow]No breadcrumbs found.[/yellow]")
        return

    table = Table(title="Recent Breadcrumbs (Trail)")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Project", style="green")
    table.add_column("Description", style="white")

    for crumb in crumbs:
        table.add_row(
            crumb.get("timestamp") or "Unknown",
            crumb.get("type") or "note",
            crumb.get("project") or "N/A",
            crumb.get("text") or "",
        )
    console.print(table)


@atlas_group.command(name="start-session")
@click.option("--project", "-p", required=True, help="Project name.")
@click.option("--task", "-t", required=True, help="Task description.")
@click.option("--desc", "-d", default="Active work session", help="Detailed session description.")
@click.pass_context
def atlas_start_session(ctx, project, task, desc):
    """Start a new active Atlas session."""
    bridge = ctx.obj["bridge"]
    try:
        res = bridge.create_session(project, task, desc)
        console.print(
            f"[bold green]✔ Started active session '{res['id']}' for project '{res['project']}'.[/bold green]"
        )
    except Exception as e:
        console.print(f"[bold red]Failed to start session:[/bold red] {e}")
        sys.exit(1)


@atlas_group.command(name="log-crumb")
@click.argument("text")
@click.option(
    "--type", "-t", "type_str", default="command", help="Type of breadcrumb (e.g. command, note)."
)
@click.option("--project", "-p", help="Associated project name.")
@click.pass_context
def atlas_log_crumb(ctx, text, type_str, project):
    """Log a breadcrumb trail item to the registry."""
    bridge = ctx.obj["bridge"]
    try:
        res = bridge.add_breadcrumb(text, type_str, project)
        console.print(f"[bold green]✔ Logged breadcrumb '{res['id']}': {res['text']}[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to log breadcrumb:[/bold red] {e}")
        sys.exit(1)


@main.group(name="sandbox")
def sandbox_group():
    """Sandbox vault management commands."""
    pass


@sandbox_group.command(name="generate")
@click.argument("path", type=click.Path())
@click.option(
    "--violations", is_flag=True, help="Inject positivity, exchangeability, and SUTVA violations."
)
def sandbox_generate(path, violations):
    """Generate a temporary sandbox vault at the specified path for testing."""
    from pathlib import Path

    try:
        vault_path = Path(path)
        sandbox = SandboxVault(vault_path)
        results = sandbox.build(violations=violations)

        # Present clean ADHD-friendly Rich output
        panel_content = (
            f"[bold green]✔ Sandbox Vault successfully generated![/bold green]\n\n"
            f"[bold]Location:[/bold] {results['path']}\n"
            f"[bold]Obsidian DB:[/bold] {results['db_path']}\n"
            f"[bold]Causal Data:[/bold] {results['data_path']}\n"
            f"[bold]Study Design:[/bold] {results['design_path']}\n"
            f"[bold]Atlas Sessions:[/bold] {results['sessions_path']}\n"
            f"[bold]Atlas Registry:[/bold] {results['registry_path']}\n\n"
            f"[dim]Violations injected: {violations}[/dim]"
        )
        console.print(Panel(panel_content, title="Sandbox Generator", border_style="green"))
    except Exception as e:
        console.print(f"[bold red]Failed to generate sandbox vault:[/bold red] {e}")
        sys.exit(1)


@main.group(name="worktree")
def worktree_group():
    """Git worktree isolation workflow helper commands."""
    pass


@worktree_group.command(name="add")
@click.argument("name")
def worktree_add(name):
    """Add a persistent feature worktree off the dev branch."""
    from pathlib import Path

    try:
        manager = WorktreeManager(Path.cwd())
        res = manager.add_worktree(name)
        panel_content = (
            f"[bold green]✔ Git worktree successfully added![/bold green]\n\n"
            f"[bold]Name:[/bold] {res['name']}\n"
            f"[bold]Branch:[/bold] {res['branch']}\n"
            f"[bold]Path:[/bold] {res['path']}\n\n"
            f"[dim]Run 'cd {res['path']} && cagy' to begin feature development.[/dim]"
        )
        console.print(Panel(panel_content, title="Worktree Manager", border_style="green"))
    except Exception as e:
        console.print(f"[bold red]Error adding worktree:[/bold red] {e}")
        sys.exit(1)


@worktree_group.command(name="list")
def worktree_list():
    """List currently active/registered git worktrees."""
    from pathlib import Path

    try:
        manager = WorktreeManager(Path.cwd())
        wts = manager.list_worktrees()
        if not wts:
            console.print("[yellow]No worktrees found.[/yellow]")
            return

        table = Table(title="Active Git Worktrees")
        table.add_column("Path", style="cyan")
        table.add_column("Branch", style="magenta")
        for wt in wts:
            table.add_row(wt["path"], wt["branch"] or "N/A")
        console.print(table)
    except Exception as e:
        console.print(f"[bold red]Error listing worktrees:[/bold red] {e}")
        sys.exit(1)


@worktree_group.command(name="remove")
@click.argument("name")
def worktree_remove(name):
    """Remove a worktree and clean up the tracking branch."""
    from pathlib import Path

    try:
        manager = WorktreeManager(Path.cwd())
        res = manager.remove_worktree(name)
        console.print(
            f"[bold green]✔ Removed worktree feature-{res['name']} and branch {res['branch']}.[/bold green]"
        )
    except Exception as e:
        console.print(f"[bold red]Error removing worktree:[/bold red] {e}")
        sys.exit(1)


@main.group(name="rforge")
@click.option("--pkg-dir", type=click.Path(exists=True), help="Path to R package directory.")
@click.pass_context
def rforge_group(ctx, pkg_dir):
    """R Package Validation Harness commands."""
    ctx.ensure_object(dict)
    from agy.plugins.rforge import RForgeBridge

    ctx.obj["bridge"] = RForgeBridge(pkg_dir=pkg_dir)


@rforge_group.command(name="check")
@click.pass_context
def rforge_check(ctx):
    """Run devtools::check() on the local package."""
    bridge = ctx.obj["bridge"]
    console.print("[bold]Running package check...[/bold]")
    res = bridge.check_package()
    if res["success"]:
        console.print("[bold green]✔ Package check passed successfully.[/bold green]")
    else:
        console.print("[bold red]✗ Package check failed.[/bold red]")
        if res.get("stderr"):
            console.print(f"Error:\n{res['stderr']}")
        else:
            console.print(f"Stdout:\n{res['stdout']}")
        sys.exit(res.get("returncode", 1))


@rforge_group.command(name="test")
@click.pass_context
def rforge_test(ctx):
    """Run devtools::test() on the local package."""
    bridge = ctx.obj["bridge"]
    console.print("[bold]Running package unit tests...[/bold]")
    res = bridge.test_package()
    if res["success"]:
        console.print("[bold green]✔ Package unit tests passed.[/bold green]")
        console.print(res["stdout"])
    else:
        console.print("[bold red]✗ Package unit tests failed.[/bold red]")
        console.print(res["stdout"])
        if res.get("stderr"):
            console.print(res["stderr"])
        sys.exit(res.get("returncode", 1))


@rforge_group.command(name="document")
@click.pass_context
def rforge_document(ctx):
    """Run devtools::document() on the local package."""
    bridge = ctx.obj["bridge"]
    console.print("[bold]Compiling Roxygen2 documentation...[/bold]")
    res = bridge.document_package()
    if res["success"]:
        console.print("[bold green]✔ Documentation compiled successfully.[/bold green]")
    else:
        console.print("[bold red]✗ Documentation compilation failed.[/bold red]")
        if res.get("stderr"):
            console.print(res["stderr"])
        sys.exit(res.get("returncode", 1))


if __name__ == "__main__":
    main()
