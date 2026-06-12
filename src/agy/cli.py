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


if __name__ == "__main__":
    main()
