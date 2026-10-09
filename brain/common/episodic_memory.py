"""Episodic memory store with Prioritized Experience Replay (PER) for ALC.

Strict Rule: Epistemic store of direct experiences (obs, action, outcome).
No hardcoded rules; records chronological sensory consequences.
Supports proportional TD-error prioritized replay with importance sampling.
"""

from collections import deque
import math
import random
from typing import Any, Dict, List, Optional, Tuple


def state_to_key(state: Tuple) -> Any:
    """Serialize nested state tuple."""
    import json
    return json.dumps(state)


def key_to_state(key: Any) -> Tuple:
    """Deserialize nested state tuple."""
    import json
    def _to_tuples(item):
        if isinstance(item, list):
            return tuple(_to_tuples(x) for x in item)
        return item
    return _to_tuples(json.loads(key))


class EpisodicMemory:
    """Ring buffer storing episodic experiences with prioritized sampling."""

    def __init__(self, capacity: int = 3000, alpha: float = 0.6, eps: float = 1e-4):
        self.capacity = capacity
        self.alpha = alpha  # Prioritization exponent
        self.eps = eps      # Small constant to guarantee non-zero sampling probability
        self.buffer: List[Dict[str, Any]] = []
        self.priorities: List[float] = []
        self.max_priority: float = 1.0
        self.total_experiences: int = 0

    def add(
        self,
        state: Tuple,
        action: int,
        need_delta: Dict[str, float],
        next_state: Tuple,
        events: List[int],
        alive: bool,
        initial_td_error: Optional[float] = None,
    ) -> None:
        """Store a single transition experience with appropriate initial priority."""
        # Calculate surprise / biological magnitude
        food_gain = abs(need_delta.get("food", 0.0))
        water_gain = abs(need_delta.get("water", 0.0))
        health_delta = abs(need_delta.get("health", 0.0))
        bio_surprise = (food_gain * 2.0 + water_gain * 2.0 + health_delta * 3.0)
        
        if not alive:
            bio_surprise += 10.0

        if initial_td_error is not None:
            priority = max(abs(initial_td_error) + bio_surprise, self.eps)
        else:
            priority = max(self.max_priority, bio_surprise, 1.0)

        experience = {
            "state": state,
            "action": action,
            "need_delta": dict(need_delta),
            "next_state": next_state,
            "events": tuple(events),
            "alive": alive,
        }

        if len(self.buffer) < self.capacity:
            self.buffer.append(experience)
            self.priorities.append(priority)
        else:
            # Overwrite oldest (ring buffer behavior)
            idx = self.total_experiences % self.capacity
            self.buffer[idx] = experience
            self.priorities[idx] = priority

        self.max_priority = max(self.max_priority, priority)
        self.total_experiences += 1

    def sample_recent(self, n: int) -> List[Dict[str, Any]]:
        """Retrieve the N most recent experiences (chronological order)."""
        count = min(n, len(self.buffer))
        return list(self.buffer[-count:])

    def sample_prioritized(
        self,
        batch_size: int,
        beta: float = 0.4,
    ) -> Tuple[List[Dict[str, Any]], List[int], List[float]]:
        """Sample a batch of experiences proportional to TD-error / surprise priority.
        
        Returns:
            (batch_experiences, sample_indices, importance_sampling_weights)
        """
        n = len(self.buffer)
        if n == 0:
            return [], [], []

        k = min(batch_size, n)
        # Compute sampling probabilities: P(i) = p_i^alpha / sum(p_k^alpha)
        scaled_priorities = [p ** self.alpha for p in self.priorities]
        total_p = sum(scaled_priorities)
        if total_p == 0:
            probs = [1.0 / n] * n
        else:
            probs = [sp / total_p for sp in scaled_priorities]

        # Draw indices with replacement based on probabilities
        indices = random.choices(range(n), weights=probs, k=k)
        experiences = [self.buffer[i] for i in indices]

        # Importance sampling weights: w_i = (N * P(i))^(-beta) / max(w)
        weights = [(n * probs[i]) ** (-beta) for i in indices]
        max_w = max(weights) if weights else 1.0
        norm_weights = [w / max_w for w in weights]

        return experiences, indices, norm_weights

    def update_priorities(self, indices: List[int], td_errors: List[float]) -> None:
        """Update priorities for sampled experiences based on new TD-errors."""
        for idx, td in zip(indices, td_errors):
            if idx < len(self.priorities):
                new_p = abs(td) + self.eps
                self.priorities[idx] = new_p
                self.max_priority = max(self.max_priority, new_p)

    def get_all(self) -> List[Dict[str, Any]]:
        """Return all experiences in memory."""
        return list(self.buffer)

    def size(self) -> int:
        return len(self.buffer)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize memory metadata and samples."""
        serialized_buf = []
        for exp in self.buffer:
            serialized_buf.append({
                "state": state_to_key(exp["state"]),
                "action": exp["action"],
                "need_delta": exp["need_delta"],
                "next_state": state_to_key(exp["next_state"]),
                "events": list(exp["events"]),
                "alive": exp["alive"],
            })
        return {
            "capacity": self.capacity,
            "alpha": self.alpha,
            "total_experiences": self.total_experiences,
            "max_priority": self.max_priority,
            "buffer": serialized_buf,
            "priorities": self.priorities,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restore episodic memory from dictionary."""
        self.capacity = data.get("capacity", self.capacity)
        self.alpha = data.get("alpha", self.alpha)
        self.total_experiences = data.get("total_experiences", 0)
        self.max_priority = data.get("max_priority", 1.0)
        self.buffer.clear()
        self.priorities.clear()

        for exp in data.get("buffer", []):
            self.buffer.append({
                "state": key_to_state(exp["state"]),
                "action": exp["action"],
                "need_delta": exp["need_delta"],
                "next_state": key_to_state(exp["next_state"]),
                "events": tuple(exp.get("events", [])),
                "alive": exp.get("alive", True),
            })
        self.priorities = list(data.get("priorities", []))
