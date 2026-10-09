"""Base Brain interface specification for ALC.

Strict rule: Brains must only perceive opaque Observations and emit opaque action IDs.
No world internals, no pretrained weights, and no solution-encoding reward shortcuts.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class Brain(ABC):
    """Abstract base class for all ALC agent brains."""

    @abstractmethod
    def reset_episode(self) -> None:
        """Reset transient episode state (e.g. per-life buffers).
        
        Crucial: This is NOT a knowledge reset. Accumulated memory, models,
        and learned weights persist across episodes/lives.
        """
        raise NotImplementedError

    @abstractmethod
    def observe(self, obs: Dict[str, Any]) -> None:
        """Receive local opaque observation from the environment."""
        raise NotImplementedError

    @abstractmethod
    def act(self) -> int:
        """Select and return an opaque integer action ID."""
        raise NotImplementedError

    @abstractmethod
    def learn(self, outcome: Dict[str, Any]) -> None:
        """Update internal state/model using the consequences of the chosen action."""
        raise NotImplementedError

    @abstractmethod
    def save(self, path: str) -> None:
        """Persist brain state/knowledge to disk."""
        raise NotImplementedError

    @abstractmethod
    def load(self, path: str) -> None:
        """Load persisted brain state/knowledge from disk."""
        raise NotImplementedError

    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """Return diagnostic metrics for logging and inspector panel visualization."""
        raise NotImplementedError
