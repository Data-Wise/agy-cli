import pytest
from agy.core.dag_compiler import parse_dag_string, compile_to_r


def test_parse_dag_string_simple():
    nodes, edges = parse_dag_string("W -> Y, X -> W, X -> Y")
    assert sorted(nodes) == ["W", "X", "Y"]
    assert len(edges) == 3
    assert ("W", "Y") in edges
    assert ("X", "W") in edges
    assert ("X", "Y") in edges


def test_parse_dag_string_chained():
    nodes, edges = parse_dag_string("X -> W -> Y")
    assert sorted(nodes) == ["W", "X", "Y"]
    assert len(edges) == 2
    assert ("X", "W") in edges
    assert ("W", "Y") in edges


def test_parse_dag_string_newlines_and_spaces():
    nodes, edges = parse_dag_string("""
        W -> Y
        X -> W
        X -> Y
    """)
    assert sorted(nodes) == ["W", "X", "Y"]
    assert len(edges) == 3
    assert ("W", "Y") in edges
    assert ("X", "W") in edges
    assert ("X", "Y") in edges


def test_parse_dag_string_isolated_nodes():
    nodes, edges = parse_dag_string("A, B, W -> Y")
    assert sorted(nodes) == ["A", "B", "W", "Y"]
    assert len(edges) == 1
    assert ("W", "Y") in edges


def test_compile_to_r_basic():
    nodes = ["W", "X", "Y"]
    edges = [("X", "W"), ("X", "Y"), ("W", "Y")]
    r_code = compile_to_r(nodes, edges)

    assert "library(dagitty)" in r_code
    assert "library(ggdag)" in r_code
    assert "dag <- dagitty('dag {" in r_code
    assert "X -> W" in r_code
    assert "X -> Y" in r_code
    assert "W -> Y" in r_code
    assert "ggdag(dag)" in r_code


def test_compile_to_r_with_exposure_and_outcome():
    nodes = ["W", "X", "Y"]
    edges = [("X", "W"), ("X", "Y"), ("W", "Y")]
    r_code = compile_to_r(nodes, edges, treatment="W", outcome="Y")

    assert 'exposure(dag) <- "W"' in r_code
    assert 'outcome(dag) <- "Y"' in r_code
