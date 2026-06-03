"""Lightweight tracking for sandboxed web extraction events."""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List

# Default to a path under the system temp dir rather than a hardcoded, world-
# writable /tmp location (avoids symlink/race issues on shared hosts).
HISTORY_PATH = os.environ.get(
    "TORON_WEB_HISTORY", os.path.join(tempfile.gettempdir(), "toron_web_history.json")
)


@dataclass
class WebHistoryEntry:
    session_id: str
    url: str
    extracted_data: Dict[str, Any]
    timestamp: str
    user_approval_id: str


class WebHistory:
    def __init__(self, path: str = HISTORY_PATH) -> None:
        self.path = path
        self._load()

    def _load(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as handle:
                    self.entries: List[WebHistoryEntry] = [
                        WebHistoryEntry(**entry) for entry in json.load(handle)
                    ]
            except (json.JSONDecodeError, OSError):
                self.entries = []
        else:
            self.entries = []

    def _persist(self) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        serialized = [asdict(entry) for entry in self.entries]
        with open(self.path, "w", encoding="utf-8") as handle:
            json.dump(serialized, handle, indent=2)

    def log_extraction(self, session_id: str, url: str, extracted_data: Dict[str, Any], user_approval_id: str) -> None:
        entry = WebHistoryEntry(
            session_id=session_id,
            url=url,
            extracted_data=extracted_data,
            timestamp=datetime.utcnow().isoformat() + "Z",
            user_approval_id=user_approval_id,
        )
        self.entries.append(entry)
        self._persist()

    def list_history(self) -> List[WebHistoryEntry]:
        return list(self.entries)


def get_history() -> WebHistory:
    return WebHistory()
