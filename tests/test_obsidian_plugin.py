import os
import sqlite3
import pytest
from agy.plugins.obsidian import ObsidianBridge

@pytest.fixture
def mock_db(tmp_path):
    db_file = tmp_path / "test_vault_db.sqlite"
    conn = sqlite3.connect(db_file)
    
    # Create tables
    conn.execute(
        """
        CREATE TABLE notes (
            id TEXT PRIMARY KEY,
            vault_id TEXT,
            path TEXT,
            title TEXT,
            modified_at TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE links (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_note_id TEXT,
            target_note_id TEXT,
            target_path TEXT,
            link_type TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE graph_metrics (
            note_id TEXT PRIMARY KEY,
            pagerank REAL,
            in_degree INTEGER,
            out_degree INTEGER
        )
        """
    )
    
    # Create views
    conn.execute(
        """
        CREATE VIEW orphaned_notes AS
        SELECT n.id, n.vault_id, n.path, n.title, n.modified_at
        FROM notes n
        LEFT JOIN links l_out ON n.id = l_out.source_note_id
        LEFT JOIN links l_in ON n.id = l_in.target_note_id
        WHERE l_out.id IS NULL AND l_in.id IS NULL
        """
    )
    conn.execute(
        """
        CREATE VIEW hub_notes AS
        SELECT n.id, n.vault_id, n.path, n.title, gm.pagerank, gm.in_degree, gm.out_degree, (gm.in_degree + gm.out_degree) as total_degree
        FROM notes n
        JOIN graph_metrics gm ON n.id = gm.note_id
        """
    )
    conn.execute(
        """
        CREATE VIEW broken_links AS
        SELECT n.path as source_path, n.title as source_title, l.target_path, COUNT(*) as broken_count
        FROM links l
        JOIN notes n ON l.source_note_id = n.id
        WHERE l.link_type = 'broken'
        GROUP BY l.source_note_id, l.target_path
        """
    )
    
    # Insert notes
    conn.execute("INSERT INTO notes VALUES ('note1', 'vault-1', 'path1.md', 'Orphan Note', '2026-06-12 12:00:00')")
    conn.execute("INSERT INTO notes VALUES ('note2', 'vault-1', 'path2.md', 'Hub Note', '2026-06-12 12:01:00')")
    conn.execute("INSERT INTO notes VALUES ('note3', 'vault-1', 'path3.md', 'Target Note', '2026-06-12 12:02:00')")
    
    # Insert links (note2 -> note3 is a valid link, note2 -> non-existent is a broken link)
    conn.execute("INSERT INTO links (source_note_id, target_note_id, target_path, link_type) VALUES ('note2', 'note3', 'path3.md', 'internal')")
    conn.execute("INSERT INTO links (source_note_id, target_note_id, target_path, link_type) VALUES ('note2', NULL, 'non-existent.md', 'broken')")
    
    # Insert graph metrics
    conn.execute("INSERT INTO graph_metrics VALUES ('note1', 0.15, 0, 0)")
    conn.execute("INSERT INTO graph_metrics VALUES ('note2', 0.5, 0, 2)")
    conn.execute("INSERT INTO graph_metrics VALUES ('note3', 0.35, 1, 0)")
    
    conn.commit()
    conn.close()
    return str(db_file)

def test_get_orphan_notes(mock_db):
    bridge = ObsidianBridge(db_path=mock_db)
    orphans = bridge.get_orphan_notes()
    assert len(orphans) == 1
    assert orphans[0]["id"] == "note1"
    assert orphans[0]["title"] == "Orphan Note"

def test_get_hub_notes(mock_db):
    bridge = ObsidianBridge(db_path=mock_db)
    
    # Sort by pagerank
    hubs = bridge.get_hub_notes(order_by="pagerank", limit=5)
    assert len(hubs) == 3
    assert hubs[0]["id"] == "note2"  # 0.5
    assert hubs[1]["id"] == "note3"  # 0.35
    assert hubs[2]["id"] == "note1"  # 0.15
    
    # Sort by out_degree
    hubs_out = bridge.get_hub_notes(order_by="out_degree", limit=5)
    assert hubs_out[0]["id"] == "note2"  # out_degree = 2

def test_get_broken_links(mock_db):
    bridge = ObsidianBridge(db_path=mock_db)
    broken = bridge.get_broken_links()
    assert len(broken) == 1
    assert broken[0]["source_title"] == "Hub Note"
    assert broken[0]["target_path"] == "non-existent.md"
    assert broken[0]["broken_count"] == 1

def test_missing_db():
    bridge = ObsidianBridge(db_path="non_existent_file.sqlite")
    assert bridge.get_orphan_notes() == []
    assert bridge.get_hub_notes() == []
    assert bridge.get_broken_links() == []
