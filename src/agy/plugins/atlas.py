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
        if ts_str.endswith('Z'):
            ts_str = ts_str[:-1] + '+00:00'
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
                    "description": context_desc or session.get("task") or "Active work session"
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
