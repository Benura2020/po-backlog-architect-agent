from typing import Protocol, List, Optional, Dict, Any
from datetime import datetime
import uuid


class TrackerItem(Dict[str, Any]):
    """Dict representing a tracker record (e.g. Jira issue or Azure DevOps item)."""
    pass


class Tracker(Protocol):
    def list_items(self) -> List[Dict[str, Any]]: ...
    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]: ...
    def create_item(self, payload: Dict[str, Any], tags: List[str], status: str = "NOT_READY") -> Dict[str, Any]: ...
    def add_comment(self, item_id: str, comment: str) -> bool: ...


class MockTracker:
    def __init__(self):
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._comments: Dict[str, List[Dict[str, Any]]] = {}

    def list_items(self) -> List[Dict[str, Any]]:
        return list(self._storage.values())

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self._storage.get(item_id)

    def create_item(self, payload: Dict[str, Any], tags: List[str], status: str = "NOT_READY") -> Dict[str, Any]:
        item_id = payload.get("id") or f"MOCK-{uuid.uuid4().hex[:6].upper()}"
        record = {
            "id": item_id,
            "title": payload.get("title", "Untitled"),
            "description": payload.get("description", ""),
            "acceptance_criteria": payload.get("acceptance_criteria", ""),
            "tags": tags,
            "status": status,  # Gated status floor enforced by caller
            "created_at": datetime.utcnow().isoformat()
        }
        self._storage[item_id] = record
        return record

    def add_comment(self, item_id: str, comment: str) -> bool:
        if item_id not in self._storage:
            return False
        if item_id not in self._comments:
            self._comments[item_id] = []
        self._comments[item_id].append({
            "comment": comment,
            "timestamp": datetime.utcnow().isoformat()
        })
        return True
