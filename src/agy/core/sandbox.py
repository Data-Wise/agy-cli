import sqlite3
import yaml
import numpy as np
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any


class SandboxVault:
    """
    Automates generating a temporary sandbox vault directory structure,
    populating mock SQLite databases, creating datasets, and writing
    configuration files for integration testing.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.notes_dir = self.path / "notes"
        self.data_dir = self.path / "data"
        self.atlas_dir = self.path / "atlas"

    def build(self, violations: bool = False) -> Dict[str, Any]:
        """
        Builds the entire sandbox structure.
        """
        # Create directories
        self.path.mkdir(parents=True, exist_ok=True)
        self.notes_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.atlas_dir.mkdir(parents=True, exist_ok=True)

        # 1. Generate Markdown Notes
        notes = [
            {
                "id": "note1",
                "title": "Orphan Causal Note",
                "filename": "orphan_causal.md",
                "content": "# Orphan Causal Note\nNo links here.",
            },
            {
                "id": "note2",
                "title": "Confounder Hub Note",
                "filename": "confounder_hub.md",
                "content": "# Confounder Hub Note\nLinks to [[target_outcome]] and [[broken_target]].",
            },
            {
                "id": "note3",
                "title": "Target Outcome Note",
                "filename": "target_outcome.md",
                "content": "# Target Outcome Note\nNo links.",
            },
        ]
        self._write_markdown_notes(notes)

        # 2. Generate SQLite DB
        db_path = self.path / "vault_db.sqlite"
        self._create_sqlite_db(db_path, violations)

        # 3. Generate Causal CSV Data
        data_path = self.data_dir / "causal_data.csv"
        self._create_causal_data(data_path, violations)

        # 4. Generate Study Design Config
        design_path = self.path / "study_design.yaml"
        self._create_study_design(design_path, data_path, violations)

        # 5. Generate Atlas Files
        sessions_path = self.atlas_dir / "sessions.yaml"
        registry_path = self.atlas_dir / "registry.yaml"
        self._create_atlas_files(sessions_path, registry_path)

        return {
            "path": str(self.path),
            "db_path": str(db_path),
            "data_path": str(data_path),
            "design_path": str(design_path),
            "sessions_path": str(sessions_path),
            "registry_path": str(registry_path),
        }

    def _write_markdown_notes(self, notes: List[Dict[str, str]]):
        for note in notes:
            filepath = self.notes_dir / note["filename"]
            with open(filepath, "w") as f:
                f.write(note["content"])

    def _create_sqlite_db(self, db_path: Path, violations: bool):
        conn = sqlite3.connect(db_path)

        # Create Tables
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

        # Create standard views expected by ObsidianBridge
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

        # Insert Mock Notes
        conn.execute(
            "INSERT INTO notes VALUES ('note1', 'vault-sandbox', 'notes/orphan_causal.md', 'Orphan Causal Note', '2026-06-14 12:00:00')"
        )
        conn.execute(
            "INSERT INTO notes VALUES ('note2', 'vault-sandbox', 'notes/confounder_hub.md', 'Confounder Hub Note', '2026-06-14 12:01:00')"
        )
        conn.execute(
            "INSERT INTO notes VALUES ('note3', 'vault-sandbox', 'notes/target_outcome.md', 'Target Outcome Note', '2026-06-14 12:02:00')"
        )

        # Insert Mock Links
        # Link note2 -> note3 (internal)
        conn.execute(
            "INSERT INTO links (source_note_id, target_note_id, target_path, link_type) VALUES ('note2', 'note3', 'notes/target_outcome.md', 'internal')"
        )

        # If violations are enabled, create a broken link note2 -> broken_target.md
        if violations:
            conn.execute(
                "INSERT INTO links (source_note_id, target_note_id, target_path, link_type) VALUES ('note2', NULL, 'notes/broken_target.md', 'broken')"
            )

        # Insert Graph Metrics
        conn.execute("INSERT INTO graph_metrics VALUES ('note1', 0.15, 0, 0)")
        out_degree = 2 if violations else 1
        conn.execute(f"INSERT INTO graph_metrics VALUES ('note2', 0.55, 0, {out_degree})")
        conn.execute("INSERT INTO graph_metrics VALUES ('note3', 0.30, 1, 0)")

        conn.commit()
        conn.close()

    def _create_causal_data(self, data_path: Path, violations: bool):
        np.random.seed(42)
        n = 200
        x = np.random.binomial(1, 0.5, n)  # Binary Confounder

        if violations:
            # Violation of Positivity:
            # If x == 0, treatment w is always 0. If x == 1, treatment w is always 1.
            # Thus, strata has no treatment variation.
            w = x.copy()
        else:
            # Satisfied Positivity:
            # Treatment probability depends on x, but is strictly inside (0, 1)
            # e.g., P(W=1|X=0) = 0.3, P(W=1|X=1) = 0.7
            p_w = 0.3 + 0.4 * x
            w = np.random.binomial(1, p_w)

        # Outcome Y depends on W and X
        y = 2.5 * w + 1.2 * x + np.random.normal(0, 0.5, n)

        df = pd.DataFrame({"X": x, "W": w, "Y": y})
        df.to_csv(data_path, index=False)

    def _create_study_design(self, design_path: Path, data_path: Path, violations: bool):
        # We write relative path to the data file
        relative_data_path = f"data/{data_path.name}"

        if violations:
            # Violations design:
            # 1. Positivity: we adjust for X, but in the data W = X (p_treatment is 0 or 1).
            # 2. Exchangeability: we adjust for X, but backdoor path via Z is unblocked.
            design = {
                "treatment": "W",
                "outcome": "Y",
                "covariates": ["X"],
                "data": relative_data_path,
                "dag": "X -> W, X -> Y, W -> Y, Z -> W, Z -> Y",
                "sutva_responses": {
                    "interference": "yes",  # SUTVA violation
                    "treatment_variation": "no",
                },
            }
        else:
            # Satisfied design
            design = {
                "treatment": "W",
                "outcome": "Y",
                "covariates": ["X"],
                "data": relative_data_path,
                "dag": "X -> W, X -> Y, W -> Y",
                "sutva_responses": {"interference": "no", "treatment_variation": "no"},
            }

        with open(design_path, "w") as f:
            yaml.safe_dump(design, f)

    def _create_atlas_files(self, sessions_path: Path, registry_path: Path):
        sessions_data = [
            {
                "id": "session-sandbox-1",
                "project": "agy-sandbox",
                "task": "Integration Testing",
                "startTime": "2026-06-14T21:00:00Z",
                "state": "active",
                "context": {"description": "Verifying sandbox generator code"},
            }
        ]

        registry_data = {
            "breadcrumbs": [
                {
                    "id": "crumb-sandbox-1",
                    "text": "Created sandbox directory",
                    "type": "command",
                    "project": "agy-sandbox",
                    "timestamp": "2026-06-14T21:05:00Z",
                }
            ],
            "captures": [
                {"id": "cap-sandbox-1", "text": "Triaged sandbox item", "status": "inbox"}
            ],
        }

        with open(sessions_path, "w") as f:
            yaml.safe_dump(sessions_data, f)

        with open(registry_path, "w") as f:
            yaml.safe_dump(registry_data, f)
