from typing import List, Tuple, Set


def parse_dag_string(dag_str: str) -> Tuple[List[str], List[Tuple[str, str]]]:
    """
    Parses a causal graph description string like 'W -> Y, X -> W, X -> Y'.
    Allows commas, newlines, and chained relations like 'X -> W -> Y'.
    Returns a sorted list of unique nodes and a list of directed edges.
    """
    edges: List[Tuple[str, str]] = []
    nodes: Set[str] = set()

    # Split by comma or newline
    parts = dag_str.replace("\n", ",").split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # If no edge sign, it might be an isolated node definition
        if "->" not in part:
            node = part.strip()
            if node:
                nodes.add(node)
            continue

        # Handle edges
        nodes_in_path = [n.strip() for n in part.split("->")]
        # Filter out empty strings
        nodes_in_path = [n for n in nodes_in_path if n]

        for i in range(len(nodes_in_path) - 1):
            src = nodes_in_path[i]
            dst = nodes_in_path[i + 1]
            edges.append((src, dst))
            nodes.add(src)
            nodes.add(dst)

    return sorted(list(nodes)), edges


def compile_to_r(
    nodes: List[str], edges: List[Tuple[str, str]], treatment: str = None, outcome: str = None
) -> str:
    """
    Compiles list of nodes and edges to R code using dagitty and ggdag.
    Optionally labels treatment and outcome exposures/outcomes.
    """
    dag_lines = []
    for src, dst in edges:
        dag_lines.append(f"  {src} -> {dst}")

    # Handle single/isolated nodes
    for node in nodes:
        # Check if the node is not in any edge to prevent clutter
        if not any(node in edge for edge in edges):
            dag_lines.append(f"  {node}")

    dagitty_str = "\n".join(dag_lines)

    r_code = f"""library(dagitty)
library(ggdag)
library(ggplot2)

# Define DAG using dagitty
dag <- dagitty('dag {{
{dagitty_str}
}}')
"""

    if treatment:
        r_code += f'exposure(dag) <- "{treatment}"\n'
    if outcome:
        r_code += f'outcome(dag) <- "{outcome}"\n'

    r_code += """
# Plot DAG
p <- ggdag(dag) + 
  theme_dag() +
  labs(title = "Causal Directed Acyclic Graph (DAG)")

print(p)
"""
    return r_code
