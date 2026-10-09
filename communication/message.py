"""Core message data structures and knowledge state taxonomies for ALC communication."""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional
import uuid


class KnowledgeStatus(str, Enum):
    """Epistemic status of a knowledge claim or response."""
    KNOWN = "KNOWN"                  # Directly verified through multiple consistent experiences
    UNKNOWN = "UNKNOWN"              # Concept or relation has not been experienced / is unrecognized
    UNCERTAIN = "UNCERTAIN"          # Sparse or low-confidence evidence (e.g. 1-2 experiences)
    CONTRADICTORY = "CONTRADICTORY"  # Conflicting outcomes experienced (e.g. both positive and negative)
    UNVERIFIED = "UNVERIFIED"        # Testimony received from another agent, not yet tested
    CONFIRMED = "CONFIRMED"          # Testimony that was experimentally tested and verified
    REFUTED = "REFUTED"              # Testimony that was experimentally tested and disproven


class CommType(str, Enum):
    """Pragmatic category of communication."""
    QUERY = "QUERY"                        # Asking a question (e.g. "What is water?", "What did you learn?")
    ANSWER = "ANSWER"                      # Answering a question
    STATEMENT = "STATEMENT"                # Sharing a fact (e.g. "Water restores hydration")
    TEACH = "TEACH"                        # Human teaching a concept or word association
    OBSERVATION = "OBSERVATION"            # Sharing current sensory observation
    WARNING = "WARNING"                    # Alerting about danger (e.g. poison berry)
    DISTRESS = "DISTRESS"                  # Expressing critical biological need (low health/water/food)
    UNKNOWN_RESPONSE = "UNKNOWN_RESPONSE"  # Honest "I don't know" response
    GREETING = "GREETING"                  # Interaction greeting / status check


@dataclass
class Message:
    """Standardized message exchanged between humans, Alpha, and Albedo.
    
    Strict Rule: Messages contain explicit symbolic representations and metadata.
    No hidden state or direct memory pointer is ever passed.
    """
    sender: str                                # "human", "alpha", "albedo", "roselia"
    receiver: str                              # "human", "alpha", "albedo", "roselia", "both", "all"
    tick: int                                  # World tick when message was created
    content: str                               # Human-readable or symbolic text
    comm_type: CommType = CommType.STATEMENT   # Category of message
    status: KnowledgeStatus = KnowledgeStatus.KNOWN  # Epistemic status
    confidence: float = 1.0                    # 0.0 (complete uncertainty) to 1.0 (certainty)
    is_understood: bool = True                 # Whether concepts in message are understood by receiver
    associated_concepts: List[str] = field(default_factory=list)  # Grounded concepts involved
    evidence_count: int = 0                    # Number of supporting episodic memories / visit counts
    supporting_memories: List[Dict[str, Any]] = field(default_factory=list)  # Snippets of evidence
    source: str = "direct_experience"          # "direct_experience", "testimony", "human_teaching", "unknown"
    is_autonomous: bool = False                # True if organism initiated communication autonomously
    message_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize message to dictionary for JSON network transmission."""
        return {
            "id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "tick": self.tick,
            "content": self.content,
            "comm_type": self.comm_type.value if isinstance(self.comm_type, Enum) else str(self.comm_type),
            "status": self.status.value if isinstance(self.status, Enum) else str(self.status),
            "confidence": round(self.confidence, 2),
            "is_understood": self.is_understood,
            "associated_concepts": list(self.associated_concepts),
            "evidence_count": self.evidence_count,
            "source": self.source,
            "is_autonomous": self.is_autonomous,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Deserialize message from dictionary."""
        comm_type_str = data.get("comm_type", CommType.STATEMENT.value)
        status_str = data.get("status", KnowledgeStatus.KNOWN.value)
        try:
            comm_type = CommType(comm_type_str)
        except ValueError:
            comm_type = CommType.STATEMENT
        try:
            status = KnowledgeStatus(status_str)
        except ValueError:
            status = KnowledgeStatus.KNOWN

        return cls(
            sender=data.get("sender", "unknown"),
            receiver=data.get("receiver", "all"),
            tick=data.get("tick", 0),
            content=data.get("content", ""),
            comm_type=comm_type,
            status=status,
            confidence=float(data.get("confidence", 1.0)),
            is_understood=bool(data.get("is_understood", True)),
            associated_concepts=list(data.get("associated_concepts", [])),
            evidence_count=int(data.get("evidence_count", 0)),
            source=data.get("source", "direct_experience"),
            is_autonomous=bool(data.get("is_autonomous", False)),
            message_id=data.get("id", str(uuid.uuid4())[:8]),
            timestamp=float(data.get("timestamp", time.time())),
        )
