import click
import json
import yaml
import os
import sys
import networkx as nx
import pandas as pd
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from agy.core.evaluator import (
    check_positivity,
    check_exchangeability,
    check_sutva,
)
from agy.core.dag_compiler import (
    parse_dag_string,
    compile_to_r,
)

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """agy - Antigravity CLI workflow engine."""
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
def eval(study_design_file, treatment, outcome, covariates, data, dag_str, interactive):
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

    console.print(
        Panel.fit(
            "[bold blue]Causal Inference Assumption Validator[/bold blue]", border_style="blue"
        )
    )

    # 3. Check Positivity
    if data_path and treatment_var:
        console.print("\n[bold]Checking Positivity Assumption...[/bold]")
        try:
            violations_df = check_positivity(data_path, treatment_var, covs_list)
            if violations_df.empty:
                console.print(
                    "[bold green]✔ Positivity check passed.[/bold green] All covariate strata have treatment variation."
                )
            else:
                console.print(
                    "[bold red]✗ Positivity assumption VIOLATED.[/bold red] Found strata with no treatment variation:"
                )
                table = Table(show_header=True, header_style="bold red")
                for col in violations_df.columns:
                    table.add_column(col)
                for _, row in violations_df.iterrows():
                    table.add_row(*[str(val) for val in row])
                console.print(table)
        except Exception as e:
            console.print(f"[bold red]Positivity check failed with error:[/bold red] {e}")
    else:
        console.print(
            "\n[yellow]⚠ Skipping Positivity check (requires --data/data and --treatment/treatment).[/yellow]"
        )

    # 4. Check Backdoor Exchangeability
    if dag_desc and treatment_var and outcome_var:
        console.print("\n[bold]Checking Backdoor Exchangeability...[/bold]")
        try:
            nodes, edges = parse_dag_string(dag_desc)
            graph = nx.DiGraph()
            graph.add_nodes_from(nodes)
            graph.add_edges_from(edges)

            result = check_exchangeability(graph, treatment_var, outcome_var, covs_list)
            if result["satisfied"]:
                console.print(
                    f"[bold green]✔ Exchangeability check passed.[/bold green] {result['reason']}"
                )
            else:
                console.print(
                    f"[bold red]✗ Exchangeability check FAILED.[/bold red] {result['reason']}"
                )
        except Exception as e:
            console.print(f"[bold red]Exchangeability check failed with error:[/bold red] {e}")
    else:
        console.print(
            "\n[yellow]⚠ Skipping Exchangeability check (requires DAG description/dag, --treatment/treatment, and --outcome/outcome).[/yellow]"
        )

    # 5. Check SUTVA
    console.print("\n[bold]Checking SUTVA Assumptions...[/bold]")
    sutva_responses = design.get("sutva_responses")
    is_stdin_tty = sys.stdin.isatty()
    run_interactively = interactive and is_stdin_tty and not sutva_responses

    try:
        sutva_res = check_sutva(interactive=run_interactively, responses=sutva_responses)
        if sutva_res["satisfied"]:
            console.print(f"[bold green]✔ SUTVA check passed.[/bold green] {sutva_res['summary']}")
        else:
            console.print(f"[bold red]✗ SUTVA check FAILED.[/bold red] {sutva_res['summary']}")
    except Exception as e:
        console.print(f"[bold red]SUTVA check failed with error:[/bold red] {e}")


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
        table.add_row(note.get("title") or "Untitled", note.get("path") or "", note.get("modified_at") or "Unknown")
    console.print(table)


@obs_group.command(name="hubs")
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of hub notes to display.")
@click.option("--sort", "-s", type=click.Choice(["pagerank", "out_degree", "in_degree", "total_degree"]), default="pagerank", help="Field to sort by.")
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
            str(note.get("total_degree", 0))
        )
    console.print(table)


@obs_group.command(name="health")
@click.pass_context
def obs_health(ctx):
    """Check vault graph health (e.g. broken links)."""
    bridge = ctx.obj["bridge"]
    broken = bridge.get_broken_links()
    if not broken:
        console.print("[bold green]✔ Vault health check passed. No broken links found.[/bold green]")
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
            str(link.get("broken_count", 1))
        )
    console.print(table)


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
@click.option("--limit", "-l", type=int, default=10, help="Maximum number of breadcrumbs to display.")
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
            crumb.get("text") or ""
        )
    console.print(table)


if __name__ == "__main__":
    main()
