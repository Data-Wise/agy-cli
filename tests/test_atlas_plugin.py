import os
import yaml
import pytest
import datetime
from agy.plugins.atlas import AtlasBridge

@pytest.fixture
def mock_atlas_files(tmp_path):
    sessions_file = tmp_path / "sessions.yaml"
    registry_file = tmp_path / "registry.yaml"

    # Define mock sessions data (one ended, one active)
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    active_start = now_utc - datetime.timedelta(minutes=45)
    active_start_str = active_start.isoformat().replace("+00:00", "Z")

    sessions_data = [
        {
            "id": "session-ended",
            "project": "old-project",
            "task": "Review PRs",
            "startTime": "2026-06-12T10:00:00Z",
            "endTime": "2026-06-12T10:30:00Z",
            "state": "ended",
            "outcome": "completed"
        },
        {
            "id": "session-active",
            "project": "flow-cli",
            "task": "Work session",
            "startTime": active_start_str,
            "endTime": None,
            "state": "active",
            "outcome": None,
            "context": {
                "description": "Implementing plugin integrations"
            }
        }
    ]

    registry_data = {
        "breadcrumbs": [
            {
                "id": "crumb-1",
                "text": "First breadcrumb",
                "type": "note",
                "project": "flow-cli",
                "timestamp": "2026-06-12T14:00:00Z"
            },
            {
                "id": "crumb-2",
                "text": "Second breadcrumb",
                "type": "command",
                "project": "flow-cli",
                "timestamp": "2026-06-12T14:15:00Z"
            }
        ],
        "captures": [
            {
                "id": "cap-1",
                "text": "triaged item",
                "type": "idea",
                "status": "done",
                "project": "flow-cli",
                "createdAt": "2026-06-12T13:00:00Z"
            },
            {
                "id": "cap-2",
                "text": "inbox item 1",
                "type": "idea",
                "status": "inbox",
                "project": "flow-cli",
                "createdAt": "2026-06-12T13:10:00Z"
            },
            {
                "id": "cap-3",
                "text": "inbox item 2",
                "type": "task",
                "status": "inbox",
                "project": "flow-cli",
                "createdAt": "2026-06-12T13:15:00Z"
            }
        ]
    }

    with open(sessions_file, "w") as f:
        yaml.safe_dump(sessions_data, f)

    with open(registry_file, "w") as f:
        yaml.safe_dump(registry_data, f)

    return str(sessions_file), str(registry_file)

def test_get_active_session(mock_atlas_files):
    sessions_path, registry_path = mock_atlas_files
    bridge = AtlasBridge(sessions_path=sessions_path, registry_path=registry_path)

    active = bridge.get_active_session()
    assert active is not None
    assert active["project"] == "flow-cli"
    assert active["task"] == "Work session"
    assert active["description"] == "Implementing plugin integrations"
    # Duration should be approximately 45 minutes (2700 seconds)
    assert 2600 < active["duration"] < 2800

def test_get_active_session_none(tmp_path):
    # Empty sessions file
    sessions_file = tmp_path / "sessions_empty.yaml"
    with open(sessions_file, "w") as f:
        yaml.safe_dump([], f)
        
    bridge = AtlasBridge(sessions_path=str(sessions_file))
    assert bridge.get_active_session() is None

def test_get_breadcrumbs(mock_atlas_files):
    sessions_path, registry_path = mock_atlas_files
    bridge = AtlasBridge(sessions_path=sessions_path, registry_path=registry_path)

    crumbs = bridge.get_breadcrumbs(limit=1)
    assert len(crumbs) == 1
    assert crumbs[0]["text"] == "First breadcrumb"

    crumbs_all = bridge.get_breadcrumbs()
    assert len(crumbs_all) == 2

def test_get_captured_inbox_items(mock_atlas_files):
    sessions_path, registry_path = mock_atlas_files
    bridge = AtlasBridge(sessions_path=sessions_path, registry_path=registry_path)

    inbox = bridge.get_captured_inbox_items()
    assert len(inbox) == 2
    assert inbox[0]["text"] == "inbox item 1"
    assert inbox[1]["text"] == "inbox item 2"

def test_missing_files():
    bridge = AtlasBridge(sessions_path="missing_sessions.yaml", registry_path="missing_registry.yaml")
    assert bridge.get_active_session() is None
    assert bridge.get_breadcrumbs() == []
    assert bridge.get_captured_inbox_items() == []
