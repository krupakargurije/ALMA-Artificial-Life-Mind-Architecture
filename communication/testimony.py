"""Testimony record and verification system for inter-agent teaching.

Strict Rule: Communicated claims are never automatically accepted as ground truth.
A receiving agent records testimony as UNVERIFIED, assigns prior confidence,
and can empirically test the hypothesis in the environment before updating its model.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional
import uuid

from communication.message import KnowledgeStatus


@dataclass
class TestimonyClaim:
    """A factual claim received from another agent or human."""
    claim_id: str
    sender: str                               # Who made the claim (e.g. "Alpha", "human")
    tick_received: int                        # Simulation tick when received
    subject: str                              # Concept/object (e.g. "water", "fruit", "poison")
    action: Optional[int]                     # Action ID tested (e.g. DRINK, EAT)
    expected_effect: Dict[str, float]         # Claimed need delta (e.g. {"water": 35.0})
    raw_message: str                          # Original text
    status: KnowledgeStatus = KnowledgeStatus.UNVERIFIED  # UNVERIFIED -> CONFIRMED / REFUTED
    confidence: float = 0.5                   # Initial trust prior
    test_count: int = 0                       # How many times receiver tested this claim
    verified_tick: Optional[int] = None       # Tick when empirical verification occurred

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.claim_id,
            "sender": self.sender,
            "tick_received": self.tick_received,
            "subject": self.subject,
            "action": self.action,
            "expected_effect": self.expected_effect,
            "raw_message": self.raw_message,
            "status": self.status.value,
            "confidence": self.confidence,
            "test_count": self.test_count,
            "verified_tick": self.verified_tick,
        }


class TestimonyBuffer:
    """Stores unverified and verified testimony claims for an individual organism."""

    def __init__(self, owner: str = "agent"):
        self.owner = owner
        self.claims: Dict[str, TestimonyClaim] = {}

    def add_claim(
        self,
        sender: str,
        tick: int,
        subject: str,
        action: Optional[int],
        expected_effect: Dict[str, float],
        raw_message: str,
        initial_confidence: float = 0.5,
    ) -> TestimonyClaim:
        """Record a new unverified claim received via communication."""
        cid = str(uuid.uuid4())[:8]
        claim = TestimonyClaim(
            claim_id=cid,
            sender=sender,
            tick_received=tick,
            subject=subject,
            action=action,
            expected_effect=expected_effect,
            raw_message=raw_message,
            status=KnowledgeStatus.UNVERIFIED,
            confidence=initial_confidence,
        )
        self.claims[cid] = claim
        return claim

    def get_unverified_claims(self) -> List[TestimonyClaim]:
        """Return claims that have not yet been tested."""
        return [c for c in self.claims.values() if c.status == KnowledgeStatus.UNVERIFIED]

    def find_claim_for_action(self, action: int) -> Optional[TestimonyClaim]:
        """Find an unverified claim relating to a specific action."""
        for c in self.claims.values():
            if c.status == KnowledgeStatus.UNVERIFIED and c.action == action:
                return c
        return None

    def evaluate_test(
        self,
        claim_id: str,
        realized_delta: Dict[str, float],
        tick: int,
    ) -> KnowledgeStatus:
        """Empirically evaluate a claim against realized consequences."""
        if claim_id not in self.claims:
            return KnowledgeStatus.UNKNOWN

        claim = self.claims[claim_id]
        claim.test_count += 1
        claim.verified_tick = tick

        # Check if realized outcome supports the claimed effect
        confirmed = True
        for need, claimed_val in claim.expected_effect.items():
            realized = realized_delta.get(need, 0.0)
            if claimed_val > 0 and realized <= 0:
                confirmed = False
                break
            elif claimed_val < 0 and realized >= 0:
                confirmed = False
                break

        if confirmed:
            claim.status = KnowledgeStatus.CONFIRMED
            claim.confidence = 1.0
        else:
            claim.status = KnowledgeStatus.REFUTED
            claim.confidence = 0.0

        return claim.status

    def to_dict(self) -> Dict[str, Any]:
        """Serialize testimony buffer claims."""
        return {
            "owner": self.owner,
            "claims": [
                {
                    "claim_id": c.claim_id,
                    "sender": c.sender,
                    "tick": c.tick,
                    "subject": c.subject,
                    "action": c.action,
                    "expected_effect": c.expected_effect,
                    "raw_message": c.raw_message,
                    "confidence": c.confidence,
                    "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                    "test_count": c.test_count,
                    "verified_tick": c.verified_tick,
                }
                for c in self.claims.values()
            ],
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Restore testimony buffer from serialized dictionary."""
        self.owner = data.get("owner", self.owner)
        self.claims.clear()
        for item in data.get("claims", []):
            status_val = item.get("status", "unverified")
            for ks in KnowledgeStatus:
                if ks.value == status_val:
                    st = ks
                    break
            else:
                st = KnowledgeStatus.UNVERIFIED

            claim = TestimonyClaim(
                claim_id=item["claim_id"],
                sender=item["sender"],
                tick=item["tick"],
                subject=item["subject"],
                action=item.get("action"),
                expected_effect=item.get("expected_effect", {}),
                raw_message=item.get("raw_message", ""),
                confidence=item.get("confidence", 0.5),
                status=st,
                test_count=item.get("test_count", 0),
                verified_tick=item.get("verified_tick"),
            )
            self.claims[claim.claim_id] = claim
