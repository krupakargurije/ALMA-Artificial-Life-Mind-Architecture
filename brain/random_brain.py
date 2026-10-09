"""Random Brain baseline implementation for ALC.

Strict rule: Brain operates strictly over opaque observations and action IDs.
No world internals, no pretrained models, no hardcoded semantic knowledge.
"""

import json
import random
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from brain.interface import Brain
from sim.actions import ALL_ACTIONS


class RandomBrain(Brain):
    """Baseline brain that selects actions uniformly at random."""

    def __init__(
        self,
        action_set: Sequence[int] = ALL_ACTIONS,
        seed: int = 42,
    ):
        self.action_set = tuple(action_set)
        self.seed = seed
        self.rng = random.Random(seed)

        # Transient state
        self.current_obs: Optional[Dict[str, Any]] = None
        self.last_action: Optional[int] = None
        self.episode_steps: int = 0

        # Persistent baseline statistics
        self.total_steps: int = 0
        self.action_counts: Dict[int, int] = {a: 0 for a in self.action_set}
        # Set of hashed (compact_obs, action, event_tuple)
        self.distinct_transitions: Set[Tuple[int, int, Tuple[int, ...]]] = set()

    def reset_episode(self) -> None:
        """Reset transient episode state upon respawn (knowledge persists)."""
        self.current_obs = None
        self.last_action = None
        self.episode_steps = 0

    def observe(self, obs: Dict[str, Any]) -> None:
        """Receive local opaque observation."""
        self.current_obs = obs

    def act(self) -> int:
        """Select an opaque action uniformly at random."""
        action = self.rng.choice(self.action_set)
        self.last_action = action
        self.action_counts[action] = self.action_counts.get(action, 0) + 1
        self.episode_steps += 1
        self.total_steps += 1
        return action

    def _hash_obs_view(self, obs: Optional[Dict[str, Any]]) -> int:
        """Hash the 7x7 view and holding status into a compact integer state representation."""
        if obs is None:
            return 0
        view = obs.get("view", [])
        holding = obs.get("self", {}).get("holding")
        flat = tuple(cell for row in view for cell in row)
        return hash((flat, holding))

    def learn(self, outcome: Dict[str, Any]) -> None:
        """Record experience transition (obs, action, outcome)."""
        obs_hash = self._hash_obs_view(self.current_obs)
        action = self.last_action if self.last_action is not None else -1
        events = tuple(outcome.get("obs_next", {}).get("events", []))
        self.distinct_transitions.add((obs_hash, action, events))

    def save(self, path: str) -> None:
        """Persist brain state to JSON."""
        state = {
            "seed": self.seed,
            "total_steps": self.total_steps,
            "action_counts": self.action_counts,
            "num_distinct_transitions": len(self.distinct_transitions),
            "rng_state": self.rng.getstate(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def load(self, path: str) -> None:
        """Load persisted brain state from JSON."""
        with open(path, "r", encoding="utf-8") as f:
            state = json.load(f)
        self.seed = state["seed"]
        self.total_steps = state["total_steps"]
        self.action_counts = {int(k): v for k, v in state["action_counts"].items()}
        if "rng_state" in state:
            raw = state["rng_state"]
            # Python rng state format: (version, tuple_of_ints, gauss_next)
            rng_tuple = (raw[0], tuple(raw[1]), raw[2])
            self.rng.setstate(rng_tuple)

    def stats(self) -> Dict[str, Any]:
        """Return diagnostic metrics for logger and inspector panel."""
        return {
            "total_steps": self.total_steps,
            "episode_steps": self.episode_steps,
            "distinct_transitions": len(self.distinct_transitions),
            "action_counts": dict(self.action_counts),
        }
