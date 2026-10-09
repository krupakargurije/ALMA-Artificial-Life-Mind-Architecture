"""CommunicationChannel: Central message bus and research logging hub for ALC.

Strict Rule: Absolute memory isolation between Alpha and Roselia.
Agents interact ONLY through explicit serialized Message instances.
Every message is logged for research analysis.
"""

from collections import deque
import json
import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from communication.message import Message


class CommunicationChannel:
    """Central message routing and empirical research logging hub."""

    def __init__(self, log_path: Optional[str] = "experiments/communication_log.jsonl"):
        self.log_path = log_path
        self._lock = threading.Lock()

        # Inboxes per participant: "alpha", "albedo", "roselia", "human"
        self._inboxes: Dict[str, deque] = {
            "alpha": deque(),
            "albedo": deque(),
            "roselia": deque(),
            "human": deque(),
        }

        # Persistent history ring buffer for UI and research
        self._history: List[Message] = []
        self._listeners: List[Callable[[Message], None]] = []

        if self.log_path:
            os.makedirs(os.path.dirname(os.path.abspath(self.log_path)), exist_ok=True)

    def subscribe(self, callback: Callable[[Message], None]) -> None:
        """Register a callback for all dispatched messages (e.g. WebSocket broadcast)."""
        with self._lock:
            self._listeners.append(callback)

    def send(self, message: Message) -> None:
        """Route a message to its intended destination inboxes and record in history."""
        with self._lock:
            self._history.append(message)

            rec = message.receiver.lower()
            if rec in ["albedo", "roselia"]:
                self._inboxes["albedo"].append(message)
                self._inboxes["roselia"].append(message)
            elif rec in self._inboxes:
                self._inboxes[rec].append(message)
            elif rec in ["both", "all"]:
                # Deliver to all agents
                for key in ["alpha", "albedo", "roselia"]:
                    if key != message.sender.lower():
                        self._inboxes[key].append(message)
                if message.sender.lower() != "human":
                    self._inboxes["human"].append(message)

            # Persist to JSONL log
            self._append_to_file(message)

            # Notify subscribers
            for cb in self._listeners:
                try:
                    cb(message)
                except Exception as e:
                    print(f"[CommChannel] Error in subscriber callback: {e}")

    def fetch_inbox(self, participant: str) -> List[Message]:
        """Retrieve and clear all pending messages for participant."""
        with self._lock:
            p = participant.lower()
            if p not in self._inboxes:
                return []
            msgs = list(self._inboxes[p])
            self._inboxes[p].clear()
            return msgs

    def get_history(self, limit: int = 100) -> List[Message]:
        """Return the most recent messages."""
        with self._lock:
            return list(self._history[-limit:])

    def _append_to_file(self, message: Message) -> None:
        """Append message record to research log."""
        if not self.log_path:
            return
        try:
            line = json.dumps(message.to_dict()) + "\n"
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"[CommChannel] Failed to write research log: {e}")
