import os
import sqlite3
import re
from typing import List, Dict, Any

class ObsidianBridge:
    """Database connector and query executor for Obsidian vaults."""

    def __init__(self, db_path: str = None):
        if db_path:
            self.db_path = db_path
        else:
            # Try to read from environment variable first
            self.db_path = os.environ.get("OBSIDIAN_DB_PATH")
            if not self.db_path:
                # Try to parse obsidian-cli-ops config for a custom database path or defaults
                config_path = os.path.expanduser("~/.config/obs/config")
                self.db_path = os.path.expanduser("~/.config/obs/vault_db.sqlite")
                if os.path.exists(config_path):
                    try:
                        with open(config_path, "r") as f:
                            content = f.read()
                            # In case db path is defined in config file in the future
                            match = re.search(r'^OBS_DB=["\']?([^"\']+)["\']?', content, re.MULTILINE)
                            if match:
                                self.db_path = os.path.expanduser(match.group(1))
                    except Exception:
                        pass

    def get_connection(self) -> sqlite3.Connection:
        """Returns a connection to the SQLite database."""
        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Obsidian database not found at: {self.db_path}")
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def get_orphan_notes(self) -> List[Dict[str, Any]]:
        """Query notes with in-degree = 0 and out-degree = 0."""
        try:
            with self.get_connection() as conn:
                # Try querying the orphaned_notes view first
                try:
                    cursor = conn.execute("SELECT id, title, path, vault_id, modified_at FROM orphaned_notes")
                    return [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Fallback to raw query if view doesn't exist
                    cursor = conn.execute(
                        """
                        SELECT n.id, n.title, n.path, n.vault_id, n.modified_at
                        FROM notes n
                        LEFT JOIN links l_out ON n.id = l_out.source_note_id
                        LEFT JOIN links l_in ON n.id = l_in.target_note_id
                        WHERE l_out.id IS NULL AND l_in.id IS NULL
                        """
                    )
                    return [dict(row) for row in cursor.fetchall()]
        except FileNotFoundError:
            return []

    def get_hub_notes(self, order_by: str = "pagerank", limit: int = 10) -> List[Dict[str, Any]]:
        """Query notes with high out-degree or PageRank metrics."""
        try:
            with self.get_connection() as conn:
                # We want to support ordering by pagerank or out_degree
                # To prevent SQL injection, validate order_by input
                valid_columns = {"pagerank", "out_degree", "in_degree", "total_degree"}
                if order_by not in valid_columns:
                    order_by = "pagerank"

                query = f"""
                    SELECT n.id, n.title, n.path, n.vault_id, 
                           gm.pagerank, gm.in_degree, gm.out_degree,
                           (gm.in_degree + gm.out_degree) as total_degree
                    FROM notes n
                    JOIN graph_metrics gm ON n.id = gm.note_id
                    ORDER BY {order_by} DESC
                    LIMIT ?
                """
                cursor = conn.execute(query, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except FileNotFoundError:
            return []

    def get_broken_links(self) -> List[Dict[str, Any]]:
        """Query links pointing to non-existent target notes."""
        try:
            with self.get_connection() as conn:
                # Try querying broken_links view first
                try:
                    cursor = conn.execute("SELECT source_path, source_title, target_path, broken_count FROM broken_links")
                    return [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Fallback to raw query if view doesn't exist
                    cursor = conn.execute(
                        """
                        SELECT n.path as source_path, n.title as source_title, l.target_path, COUNT(*) as broken_count
                        FROM links l
                        JOIN notes n ON l.source_note_id = n.id
                        WHERE l.link_type = 'broken' OR l.target_note_id IS NULL
                        GROUP BY l.source_note_id, l.target_path
                        """
                    )
                    return [dict(row) for row in cursor.fetchall()]
        except FileNotFoundError:
            return []
