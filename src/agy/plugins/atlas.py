import os
import datetime
import yaml
from typing import List, Dict, Any, Optional


class AtlasBridge:
    """Reader and parser for Atlas state registries and active sessions."""

    def __init__(self, sessions_path: Optional[str] = None, registry_path: Optional[str] = None):
        self.sessions_path = sessions_path or os.environ.get("ATLAS_SESSIONS_PATH")
        if not self.sessions_path:
            self.sessions_path = os.path.expanduser("~/.atlas/sessions.yaml")

        self.registry_path = registry_path or os.environ.get("ATLAS_REGISTRY_PATH")
        if not self.registry_path:
            self.registry_path = os.path.expanduser("~/.atlas/registry.yaml")

    def _parse_iso_timestamp(self, ts_str: str) -> Optional[datetime.datetime]:
        if not ts_str:
            return None
        # Replace Z with +00:00 for Python 3.9/3.10 compatibility
        if ts_str.endswith("Z"):
            ts_str = ts_str[:-1] + "+00:00"
        try:
            return datetime.datetime.fromisoformat(ts_str)
        except ValueError:
            return None

    def _load_yaml_file(self, file_path: str) -> Any:
        if not os.path.exists(file_path):
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return None

    def get_active_session(self) -> Optional[Dict[str, Any]]:
        """Extract active session name, duration, and context description."""
        data = self._load_yaml_file(self.sessions_path)
        if not data:
            return None

        # Standard sessions file is a list of sessions
        sessions = data if isinstance(data, list) else data.get("sessions", [])
        if not isinstance(sessions, list):
            return None

        for session in sessions:
            if not isinstance(session, dict):
                continue
            if session.get("state") == "active":
                start_time_str = session.get("startTime")
                duration = 0.0
                if start_time_str:
                    start_time = self._parse_iso_timestamp(start_time_str)
                    if start_time:
                        if start_time.tzinfo is not None:
                            now = datetime.datetime.now(datetime.timezone.utc)
                        else:
                            now = datetime.datetime.utcnow()
                        duration = (now - start_time).total_seconds()

                context = session.get("context") or {}
                # Handle case where context is a string or dict
                context_desc = ""
                if isinstance(context, dict):
                    context_desc = context.get("description") or context.get("summary") or ""
                elif isinstance(context, str):
                    context_desc = context

                return {
                    "id": session.get("id"),
                    "project": session.get("project") or "unknown",
                    "task": session.get("task") or "Work session",
                    "startTime": start_time_str,
                    "duration": duration,
                    "context": context,
                    "description": context_desc or session.get("task") or "Active work session",
                }
        return None

    def get_breadcrumbs(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Extract recent breadcrumbs from registry.yaml."""
        data = self._load_yaml_file(self.registry_path)
        if not data:
            return []

        breadcrumbs = data.get("breadcrumbs") if isinstance(data, dict) else None
        if not isinstance(breadcrumbs, list):
            return []

        # Return up to limit recent breadcrumbs
        return breadcrumbs[:limit]

    def get_captured_inbox_items(self) -> List[Dict[str, Any]]:
        """Extract captured inbox items (status == inbox)."""
        data = self._load_yaml_file(self.registry_path)
        if not data:
            return []

        captures = data.get("captures") if isinstance(data, dict) else None
        if not isinstance(captures, list):
            return []

        inbox_items = []
        for item in captures:
            if not isinstance(item, dict):
                continue
            if item.get("status") == "inbox":
                inbox_items.append(item)
        return inbox_items

    def _save_yaml_file(self, file_path: str, data: Any):
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f)
            return True
        except Exception:
            return False

    def create_session(self, project: str, task: str, description: str) -> Dict[str, Any]:
        """
        Creates and starts a new active session, ending all other active sessions.
        """
        data = self._load_yaml_file(self.sessions_path)
        if data is None or not isinstance(data, list):
            sessions = []
        else:
            sessions = data

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        # 1. End any currently active session
        for session in sessions:
            if isinstance(session, dict) and session.get("state") == "active":
                session["state"] = "ended"
                session["endTime"] = now_str
                session["outcome"] = "completed"

        # 2. Add new session
        import uuid

        session_id = f"session-{uuid.uuid4().hex[:8]}"
        new_session = {
            "id": session_id,
            "project": project,
            "task": task,
            "startTime": now_str,
            "endTime": None,
            "state": "active",
            "outcome": None,
            "context": {"description": description},
        }
        sessions.append(new_session)

        # 3. Save file
        self._save_yaml_file(self.sessions_path, sessions)

        return {
            "id": session_id,
            "project": project,
            "task": task,
            "startTime": now_str,
            "description": description,
        }

    def add_breadcrumb(
        self, text: str, type_str: str = "command", project: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Adds a new breadcrumb to the registry trail.
        """
        data = self._load_yaml_file(self.registry_path)
        if data is None or not isinstance(data, dict):
            registry = {"breadcrumbs": [], "captures": []}
        else:
            registry = data

        if "breadcrumbs" not in registry or not isinstance(registry["breadcrumbs"], list):
            registry["breadcrumbs"] = []

        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        # Resolve project name
        proj_name = project
        if not proj_name:
            active = self.get_active_session()
            proj_name = active.get("project") if active else "N/A"

        import uuid

        crumb_id = f"crumb-{uuid.uuid4().hex[:8]}"
        new_crumb = {
            "id": crumb_id,
            "text": text,
            "type": type_str,
            "project": proj_name,
            "timestamp": now_str,
        }

        # Prepend to breadcrumbs for LIFO order
        registry["breadcrumbs"].insert(0, new_crumb)

        # Save registry back
        self._save_yaml_file(self.registry_path, registry)

        return new_crumb
