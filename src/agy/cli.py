import click
from rich.console import Console
from rich.panel import Panel

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
    console.print(Panel("[bold green]agy-cli[/bold green] - Active and initialized.", title="Status"))

@main.command()
@click.argument("study_design_file", type=click.Path(exists=True), required=False)
def eval(study_design_file):
    """Evaluate observational study assumptions (Positivity, Exchangeability, SUTVA)."""
    console.print("[yellow]Assumption check placeholder...[/yellow]")

@main.command()
@click.argument("description", type=str)
@click.option("--output", "-o", type=click.Path(), help="Output R script file.")
def dag(description, output):
    """Compile textual causal graph description to R ggdag/dagitty code."""
    console.print(f"[green]Compiling graph description:[/green] {description}")

if __name__ == "__main__":
    main()
