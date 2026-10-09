"""Autonomous communication decision engine for ALC organisms.

Strict Rule: No hard-coded scripted dialogues.
Decisions to initiate communication emerge from internal drives:
1. Novel Discovery: First or major positive causal discovery -> wants to share with peer
2. Danger Warning: Significant damage suffered -> warns peer to protect them
3. Biological Distress: Critical hydration or health depletion -> signals human/peer for help
4. Novelty/Curiosity: Reaching a milestone of exploration or encounter with new entity
A cooldown mechanism prevents excessive spam.
"""

from typing import Any, Dict, List, Optional, Tuple

from communication.message import CommType, KnowledgeStatus, Message


class AutonomousCommDecisionEngine:
    """Evaluates when an agent should autonomously initiate communication."""

    def __init__(
        self,
        agent_name: str,
        cooldown_ticks: int = 25,
    ):
        self.agent_name = agent_name
        self.cooldown_ticks = cooldown_ticks
        self.last_comm_tick: int = -999

        # Track what has already been shared to avoid repetitive broadcasting
        self.shared_discoveries: set = set()

    def evaluate(
        self,
        tick: int,
        outcome: Dict[str, Any],
        current_obs: Optional[Dict[str, Any]],
        peer_name: str,
    ) -> Optional[Message]:
        """Evaluate if an autonomous message should be dispatched on this tick."""
        if tick - self.last_comm_tick < self.cooldown_ticks:
            return None

        need_delta = outcome.get("need_delta", {})
        obs_next = outcome.get("obs_next", {})
        events = obs_next.get("events", [])
        self_needs = obs_next.get("self", {})

        # ── 1. DANGER WARNING: Poison or severe damage ──────────────────────
        health_delta = need_delta.get("health", 0.0)
        if health_delta < -15.0 or 7 in events:  # 7 = EVENT_ATE_POISON
            key = "danger_damage"
            if key not in self.shared_discoveries:
                self.shared_discoveries.add(key)
                self.last_comm_tick = tick
                return Message(
                    sender=self.agent_name,
                    receiver=peer_name,
                    tick=tick,
                    content=f"Warning! I took severe damage ({health_delta:.0f} health). Avoid harmful berries!",
                    comm_type=CommType.WARNING,
                    status=KnowledgeStatus.KNOWN,
                    confidence=1.0,
                    evidence_count=1,
                    source="direct_experience",
                    is_autonomous=True,
                )

        # ── 2. HIGH BENEFIT DISCOVERY: Water or food found ──────────────────
        water_delta = need_delta.get("water", 0.0)
        if water_delta > 15.0 or 8 in events:  # 8 = EVENT_DRANK_WATER
            key = "discovery_water"
            if key not in self.shared_discoveries:
                self.shared_discoveries.add(key)
                self.last_comm_tick = tick
                return Message(
                    sender=self.agent_name,
                    receiver=peer_name,
                    tick=tick,
                    content=f"I discovered that drinking water restores hydration (+{water_delta:.0f} water)!",
                    comm_type=CommType.STATEMENT,
                    status=KnowledgeStatus.KNOWN,
                    confidence=0.9,
                    evidence_count=1,
                    source="direct_experience",
                    is_autonomous=True,
                )

        food_delta = need_delta.get("food", 0.0)
        if food_delta > 15.0 or 6 in events:  # 6 = EVENT_ATE_FOOD
            key = "discovery_food"
            if key not in self.shared_discoveries:
                self.shared_discoveries.add(key)
                self.last_comm_tick = tick
                return Message(
                    sender=self.agent_name,
                    receiver=peer_name,
                    tick=tick,
                    content=f"I discovered that eating fruit restores food (+{food_delta:.0f} nourishment)!",
                    comm_type=CommType.STATEMENT,
                    status=KnowledgeStatus.KNOWN,
                    confidence=0.9,
                    evidence_count=1,
                    source="direct_experience",
                    is_autonomous=True,
                )

        # ── 3. CRITICAL DISTRESS: Low water/health -> signal to Human ───────
        cur_water = self_needs.get("water", 100.0)
        cur_health = self_needs.get("health", 100.0)
        if cur_water < 20.0 or cur_health < 25.0:
            key = f"distress_{tick // 100}"
            if key not in self.shared_discoveries:
                self.shared_discoveries.add(key)
                self.last_comm_tick = tick
                return Message(
                    sender=self.agent_name,
                    receiver="human",
                    tick=tick,
                    content=f"I am in physiological distress! Water: {cur_water:.0f}%, Health: {cur_health:.0f}%.",
                    comm_type=CommType.DISTRESS,
                    status=KnowledgeStatus.KNOWN,
                    confidence=1.0,
                    evidence_count=1,
                    source="direct_experience",
                    is_autonomous=True,
                )

        return None
