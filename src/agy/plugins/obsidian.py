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
                            match = re.search(
                                r'^OBS_DB=["\']?([^"\']+)["\']?', content, re.MULTILINE
                            )
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
                    cursor = conn.execute(
                        "SELECT id, title, path, vault_id, modified_at FROM orphaned_notes"
                    )
                    return [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Fallback to raw query if view doesn't exist
                    cursor = conn.execute("""
                        SELECT n.id, n.title, n.path, n.vault_id, n.modified_at
                        FROM notes n
                        LEFT JOIN links l_out ON n.id = l_out.source_note_id
                        LEFT JOIN links l_in ON n.id = l_in.target_note_id
                        WHERE l_out.id IS NULL AND l_in.id IS NULL
                        """)
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
                    cursor = conn.execute(
                        "SELECT source_path, source_title, target_path, broken_count FROM broken_links"
                    )
                    return [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    # Fallback to raw query if view doesn't exist
                    cursor = conn.execute("""
                        SELECT n.path as source_path, n.title as source_title, l.target_path, COUNT(*) as broken_count
                        FROM links l
                        JOIN notes n ON l.source_note_id = n.id
                        WHERE l.link_type = 'broken' OR l.target_note_id IS NULL
                        GROUP BY l.source_note_id, l.target_path
                        """)
                    return [dict(row) for row in cursor.fetchall()]
        except FileNotFoundError:
            return []

    def get_vault_graph(self, focus: str = None, depth: int = 2, limit: int = 30) -> Dict[str, Any]:
        """
        Returns nodes and links from the Obsidian vault.
        If focus is provided, traverses the neighborhood up to the specified depth.
        If focus is not provided, returns connections among the top `limit` hub notes.
        """
        try:
            with self.get_connection() as conn:
                # 1. Fetch all notes and build lookup maps
                cursor = conn.execute("SELECT id, title, path FROM notes")
                notes = [dict(row) for row in cursor.fetchall()]
                note_map = {n["id"]: n for n in notes}
                
                # Fetch all internal/valid links
                cursor = conn.execute(
                    "SELECT source_note_id, target_note_id FROM links WHERE link_type != 'broken' AND target_note_id IS NOT NULL"
                )
                links = [dict(row) for row in cursor.fetchall()]

                # Build adjacency list for traversal (undirected for neighborhood search)
                adj = {}
                for n in notes:
                    adj[n["id"]] = set()
                for l in links:
                    src, tgt = l["source_note_id"], l["target_note_id"]
                    if src in adj and tgt in adj:
                        adj[src].add(tgt)
                        adj[tgt].add(src)

                selected_note_ids = set()

                if focus:
                    # Find note matching focus string (exact or substring of title/path)
                    focus_id = None
                    focus_lower = focus.lower()
                    # First try exact match
                    for nid, n in note_map.items():
                        if (n.get("title") or "").lower() == focus_lower or (n.get("path") or "").lower() == focus_lower:
                            focus_id = nid
                            break
                    # Fallback to substring
                    if not focus_id:
                        for nid, n in note_map.items():
                            if focus_lower in (n.get("title") or "").lower() or focus_lower in (n.get("path") or "").lower():
                                focus_id = nid
                                break

                    if not focus_id:
                        return {"nodes": [], "edges": [], "focus_node": None}

                    # BFS traversal up to depth
                    queue = [(focus_id, 0)]
                    visited = {focus_id}
                    while queue:
                        curr_id, curr_depth = queue.pop(0)
                        selected_note_ids.add(curr_id)
                        if curr_depth < depth:
                            for neighbor in adj.get(curr_id, []):
                                if neighbor not in visited:
                                    visited.add(neighbor)
                                    queue.append((neighbor, curr_depth + 1))
                    
                    focus_node = note_map[focus_id]
                else:
                    # No focus note: select top `limit` hubs sorted by PageRank
                    try:
                        cursor = conn.execute(
                            "SELECT note_id FROM graph_metrics ORDER BY pagerank DESC LIMIT ?", (limit,)
                        )
                        selected_note_ids = {row["note_id"] for row in cursor.fetchall()}
                    except sqlite3.OperationalError:
                        # Fallback if graph_metrics table is empty or doesn't exist
                        # Just sort by degree count from links table
                        degrees = {}
                        for n in notes:
                            degrees[n["id"]] = 0
                        for l in links:
                            src, tgt = l["source_note_id"], l["target_note_id"]
                            if src in degrees: degrees[src] += 1
                            if tgt in degrees: degrees[tgt] += 1
                        sorted_ids = sorted(degrees.keys(), key=lambda k: degrees[k], reverse=True)
                        selected_note_ids = set(sorted_ids[:limit])
                    
                    focus_node = None

                # Construct nodes list and edges list
                result_nodes = [note_map[nid] for nid in selected_note_ids if nid in note_map]
                result_edges = []
                for l in links:
                    src, tgt = l["source_note_id"], l["target_note_id"]
                    if src in selected_note_ids and tgt in selected_note_ids:
                        result_edges.append({
                            "source_title": note_map[src]["title"],
                            "target_title": note_map[tgt]["title"]
                        })

                return {
                    "nodes": result_nodes,
                    "edges": result_edges,
                    "focus_node": focus_node
                }
        except FileNotFoundError:
            return {"nodes": [], "edges": [], "focus_node": None}

    def get_literature_gaps(self, method_tags: List[str], setting_tags: List[str], method_path: str = None, setting_path: str = None) -> Dict[str, Any]:
        """
        Classifies notes as either Methods or Settings/Applications and
        identifies those that are isolated (have no links between methods and settings).
        """
        try:
            with self.get_connection() as conn:
                # 1. Fetch all notes and links
                try:
                    cursor = conn.execute("""
                        SELECT n.id, n.title, n.path, GROUP_CONCAT(t.tag) as tags
                        FROM notes n
                        LEFT JOIN note_tags nt ON n.id = nt.note_id
                        LEFT JOIN tags t ON nt.tag_id = t.id
                        GROUP BY n.id
                    """)
                    notes = [dict(row) for row in cursor.fetchall()]
                except sqlite3.OperationalError:
                    cursor = conn.execute("SELECT id, title, path, tags FROM notes")
                    notes = [dict(row) for row in cursor.fetchall()]
                note_map = {n["id"]: n for n in notes}

                cursor = conn.execute(
                    "SELECT source_note_id, target_note_id FROM links WHERE link_type != 'broken' AND target_note_id IS NOT NULL"
                )
                links = [dict(row) for row in cursor.fetchall()]

                # Build undirected link adjacency
                adj = {}
                for n in notes:
                    adj[n["id"]] = set()
                for l in links:
                    src, tgt = l["source_note_id"], l["target_note_id"]
                    if src in adj and tgt in adj:
                        adj[src].add(tgt)
                        adj[tgt].add(src)

                # Lowercase tag filters
                m_tags = [t.lower().strip() for t in method_tags]
                s_tags = [t.lower().strip() for t in setting_tags]

                methods = []
                settings = []

                for n in notes:
                    path = n["path"] or ""
                    tags_str = n["tags"] or ""
                    # Split comma-separated tags
                    note_tags = [t.lower().strip() for t in tags_str.split(",") if t.strip()]

                    is_method = False
                    is_setting = False

                    # Check by path match
                    if method_path and method_path.lower() in path.lower():
                        is_method = True
                    if setting_path and setting_path.lower() in path.lower():
                        is_setting = True

                    # Check by tags
                    if any(t in note_tags for t in m_tags):
                        is_method = True
                    if any(t in note_tags for t in s_tags):
                        is_setting = True

                    # If a note matches both, prioritize/deduplicate
                    if is_method and is_setting:
                        if method_path and method_path.lower() in path.lower():
                            is_setting = False
                        elif setting_path and setting_path.lower() in path.lower():
                            is_method = False
                        else:
                            is_setting = False

                    if is_method:
                        methods.append(n)
                    elif is_setting:
                        settings.append(n)

                method_ids = {m["id"] for m in methods}
                setting_ids = {s["id"] for s in settings}

                # Find isolated methods: method notes with no links to any setting note
                isolated_methods = []
                for m in methods:
                    connected_to_setting = False
                    for neighbor in adj.get(m["id"], []):
                        if neighbor in setting_ids:
                            connected_to_setting = True
                            break
                    if not connected_to_setting:
                        isolated_methods.append(m)

                # Find isolated settings: setting notes with no links to any method note
                isolated_settings = []
                for s in settings:
                    connected_to_method = False
                    for neighbor in adj.get(s["id"], []):
                        if neighbor in method_ids:
                            connected_to_method = True
                            break
                    if not connected_to_method:
                        isolated_settings.append(s)

                return {
                    "methods_count": len(methods),
                    "settings_count": len(settings),
                    "isolated_methods": isolated_methods,
                    "isolated_settings": isolated_settings
                }
        except FileNotFoundError:
            return {
                "methods_count": 0,
                "settings_count": 0,
                "isolated_methods": [],
                "isolated_settings": []
            }
