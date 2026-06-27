import sqlite3
import pytest
from agy.plugins.obsidian import ObsidianBridge


@pytest.fixture
def mock_extended_db(tmp_path):
    db_file = tmp_path / "test_extended_vault_db.sqlite"
    conn = sqlite3.connect(db_file)

    # Create tables
    conn.execute("""
        CREATE TABLE notes (
            id TEXT PRIMARY KEY,
            vault_id TEXT,
            path TEXT,
            title TEXT,
            tags TEXT,
            modified_at TIMESTAMP
        )
        """)
    conn.execute("""
        CREATE TABLE links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_note_id TEXT,
            target_note_id TEXT,
            target_path TEXT,
            link_type TEXT
        )
        """)
    conn.execute("""
        CREATE TABLE graph_metrics (
            note_id TEXT PRIMARY KEY,
            pagerank REAL,
            in_degree INTEGER,
            out_degree INTEGER
        )
        """)

    # Insert notes
    # Methods (tagged 'mediation' or 'regression')
    conn.execute(
        "INSERT INTO notes VALUES ('note_med', 'v1', 'Research/10_methods/mediation.md', 'Mediation Method', 'mediation,R', '2026-06-12 12:00:00')"
    )
    conn.execute(
        "INSERT INTO notes VALUES ('note_reg', 'v1', 'Research/10_methods/regression.md', 'Regression Method', 'regression', '2026-06-12 12:01:00')"
    )
    # Settings (tagged 'project' or 'data')
    conn.execute(
        "INSERT INTO notes VALUES ('note_proj1', 'v1', 'Research/20_projects/diabetes.md', 'Diabetes Project', 'project,data', '2026-06-12 12:02:00')"
    )
    conn.execute(
        "INSERT INTO notes VALUES ('note_proj2', 'v1', 'Research/20_projects/heart.md', 'Heart Project', 'project', '2026-06-12 12:03:00')"
    )
    # Unrelated note
    conn.execute(
        "INSERT INTO notes VALUES ('note_unrelated', 'v1', 'misc.md', 'Misc Note', 'misc', '2026-06-12 12:04:00')"
    )

    # Insert links: note_med is linked to note_proj1. note_reg and note_proj2 are isolated.
    conn.execute(
        "INSERT INTO links (source_note_id, target_note_id, target_path, link_type) VALUES ('note_med', 'note_proj1', 'Research/20_projects/diabetes.md', 'internal')"
    )

    # Insert graph metrics
    conn.execute("INSERT INTO graph_metrics VALUES ('note_med', 0.4, 0, 1)")
    conn.execute("INSERT INTO graph_metrics VALUES ('note_proj1', 0.3, 1, 0)")
    conn.execute("INSERT INTO graph_metrics VALUES ('note_reg', 0.1, 0, 0)")
    conn.execute("INSERT INTO graph_metrics VALUES ('note_proj2', 0.1, 0, 0)")
    conn.execute("INSERT INTO graph_metrics VALUES ('note_unrelated', 0.1, 0, 0)")

    conn.commit()
    conn.close()
    return str(db_file)


def test_get_vault_graph_without_focus(mock_extended_db):
    bridge = ObsidianBridge(db_path=mock_extended_db)
    res = bridge.get_vault_graph(limit=2)
    nodes = res["nodes"]
    edges = res["edges"]
    focus = res["focus_node"]

    assert focus is None
    # Limit to top 2 pagerank (note_med, note_proj1)
    assert len(nodes) == 2
    assert {n["id"] for n in nodes} == {"note_med", "note_proj1"}
    assert len(edges) == 1
    assert edges[0]["source_title"] == "Mediation Method"
    assert edges[0]["target_title"] == "Diabetes Project"


def test_get_vault_graph_with_focus(mock_extended_db):
    bridge = ObsidianBridge(db_path=mock_extended_db)
    res = bridge.get_vault_graph(focus="Mediation Method", depth=1)
    nodes = res["nodes"]
    edges = res["edges"]
    focus = res["focus_node"]

    assert focus["id"] == "note_med"
    # depth=1 from note_med reaches note_proj1
    assert len(nodes) == 2
    assert {n["id"] for n in nodes} == {"note_med", "note_proj1"}
    assert len(edges) == 1


def test_get_literature_gaps(mock_extended_db):
    bridge = ObsidianBridge(db_path=mock_extended_db)
    res = bridge.get_literature_gaps(
        method_tags=["mediation", "regression"],
        setting_tags=["project", "data"]
    )

    # Classifications
    assert res["methods_count"] == 2
    assert res["settings_count"] == 2

    # isolated_methods: note_reg is isolated (no links to note_proj1 or note_proj2)
    # note_med is linked to note_proj1 (setting), so it is not isolated.
    assert len(res["isolated_methods"]) == 1
    assert res["isolated_methods"][0]["id"] == "note_reg"

    # isolated_settings: note_proj2 is isolated (no links to note_med or note_reg)
    # note_proj1 is linked to note_med (method), so it is not isolated.
    assert len(res["isolated_settings"]) == 1
    assert res["isolated_settings"][0]["id"] == "note_proj2"
