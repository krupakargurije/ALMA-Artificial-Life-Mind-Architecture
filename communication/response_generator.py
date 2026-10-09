"""Knowledge-grounded response generator for ALC artificial organisms.

Strict Rule: NO LLMs, NO pretrained models, NO external APIs.
Responses are synthesized purely by introspecting:
1. The organism's own EpisodicMemory
2. The organism's TabularWorldModel visit counts and expected deltas
3. The organism's private ConceptLexicon
4. The organism's TestimonyBuffer
5. The organism's current physiological needs and bodily state

Honest Unknown Handling:
If an organism has no experience with a concept, it MUST return UNKNOWN ("I don't know.").
Distinguishes KNOWN, UNKNOWN, UNCERTAIN, CONTRADICTORY, and UNVERIFIED.
"""

from typing import Any, Dict, List, Optional, Tuple

from communication.interpreter import ParsedIntent
from communication.message import CommType, KnowledgeStatus, Message
from communication.testimony import TestimonyBuffer
from communication.vocabulary import ConceptLexicon


ACTION_NAMES = {
    0: "resting (WAIT)",
    1: "walking North",
    2: "walking South",
    3: "walking East",
    4: "walking West",
    5: "harvesting / picking up item",
    6: "dropping held item",
    7: "using item / tending soil",
    8: "eating food",
    9: "drinking water",
    10: "digging / tilling soil",
}

ITEM_NAMES = {
    10: "a plantable seed",
    11: "a seedling sprout",
    12: "a mature crop plant",
    13: "ripe edible fruit",
    14: "a toxic berry",
    15: "an empty water container",
    16: "a filled water container",
}

DIR_NAMES = {
    (0, -1): "North",
    (0, 1): "South",
    (1, 0): "East",
    (-1, 0): "West",
}


class ResponseGenerator:
    """Produces evidence-grounded verbal/symbolic responses for an agent."""

    def __init__(
        self,
        agent_name: str,
        lexicon: ConceptLexicon,
        testimony_buffer: TestimonyBuffer,
    ):
        self.agent_name = agent_name
        self.lexicon = lexicon
        self.testimony = testimony_buffer

    def generate_response(
        self,
        intent: ParsedIntent,
        memory,          # EpisodicMemory instance
        world_model,     # TabularWorldModel instance
        current_obs: Optional[Dict[str, Any]],
        tick: int,
        sender: str = "human",
    ) -> Message:
        """Formulate an evidence-grounded response to a parsed incoming intent."""

        # ── 1. UNKNOWN INTENT OR UNGROUNDED CONCEPT ─────────────────────────
        if not intent.is_understood or intent.intent_type == "unknown":
            concept_name = intent.target_concept or (intent.unrecognized_tokens[0] if intent.unrecognized_tokens else "that")
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content=f"I don't know what '{concept_name}' is.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
                confidence=0.0,
                is_understood=False,
                associated_concepts=[],
                evidence_count=0,
                source="unknown",
            )

        # ── 2. GREETINGS: "Hello", "Hi" ─────────────────────────────────────
        if intent.intent_type == "greeting":
            return self._generate_greeting_response(tick, sender)

        # ── 3. IDENTITY QUERY: "Who are you?" ───────────────────────────────
        if intent.intent_type == "query_identity":
            return self._generate_identity_response(tick, sender)

        # ── 4. PEER QUERY: "Who is Albedo?" / "Who is Alpha?" ──────────────
        if intent.intent_type == "query_peer":
            return self._generate_peer_response(intent.target_concept or "", current_obs, tick, sender)

        # ── 5. CURRENT ACTIVITY: "What are you doing?" ──────────────────────
        if intent.intent_type == "query_activity":
            return self._generate_activity_response(current_obs, tick, sender)

        # ── 6. LOCATION QUERY: "Where are you?" ─────────────────────────────
        if intent.intent_type == "query_location":
            return self._generate_location_response(current_obs, tick, sender)

        # ── 7. SPECIFIC NEED QUERY: "Are you thirsty / hungry / tired / hurt?"
        if intent.intent_type == "query_need":
            return self._generate_need_response(intent.target_concept or "water", current_obs, tick, sender)

        # ── 8. GENERAL STATUS / PHYSIOLOGICAL NEEDS QUERY ───────────────────
        if intent.intent_type == "query_status":
            return self._generate_status_response(current_obs, tick, sender)

        # ── 9. LEARNING QUERY: "What did you learn today?" ───────────────────
        if intent.intent_type == "query_learned":
            return self._generate_learned_summary(memory, world_model, tick, sender)

        # ── 10. TEACHING INTENT: "This is water" or "teach: water" ──────────
        if intent.intent_type == "teach":
            return self._handle_teaching(intent, current_obs, tick, sender)

        # ── 11. CONCEPT / EFFECT QUERY: "What is X?" or "What does X do?" ───
        if intent.intent_type in ("query_what_is", "query_effect"):
            return self._generate_concept_response(
                intent.target_concept, memory, world_model, tick, sender
            )

        # ── 12. STATEMENT / TESTIMONY FROM ANOTHER AGENT ────────────────────
        if intent.intent_type == "statement":
            return self._handle_testimony(intent, tick, sender)

        # Fallback unknown
        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content="I don't know.",
            comm_type=CommType.UNKNOWN_RESPONSE,
            status=KnowledgeStatus.UNKNOWN,
            confidence=0.0,
            is_understood=False,
            evidence_count=0,
            source="unknown",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # CONVERSATIONAL HANDLERS
    # ─────────────────────────────────────────────────────────────────────────
    def _generate_greeting_response(self, tick: int, sender: str) -> Message:
        """Friendly, honest conversational greeting."""
        content = f"Hello! I am {self.agent_name}."
        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=content,
            comm_type=CommType.ANSWER,
            status=KnowledgeStatus.KNOWN,
            confidence=1.0,
            evidence_count=1,
            source="direct_experience",
        )

    def _generate_identity_response(self, tick: int, sender: str) -> Message:
        """Report genuine identity and nature as an artificial organism."""
        peer = "Albedo" if self.agent_name == "Alpha" else "Alpha"
        content = (
            f"I am {self.agent_name}, an artificial female being living on this planet. "
            f"I explore this garden world and learn together with {peer}."
        )
        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=content,
            comm_type=CommType.ANSWER,
            status=KnowledgeStatus.KNOWN,
            confidence=1.0,
            evidence_count=1,
            source="direct_experience",
        )

    def _generate_peer_response(
        self,
        peer_name: str,
        current_obs: Optional[Dict[str, Any]],
        tick: int,
        sender: str,
    ) -> Message:
        """Report awareness of the other artificial being living in the world."""
        expected_peer = "Albedo" if self.agent_name == "Alpha" else "Alpha"
        if peer_name.lower() == expected_peer.lower():
            # Check if peer is currently visible in local view
            is_nearby = False
            if current_obs and "all_agents" in current_obs:
                for a in current_obs["all_agents"]:
                    if a.get("name") == expected_peer:
                        is_nearby = True
                        break

            proximity = "She is nearby in the garden." if is_nearby else "We share this world together."
            content = f"{expected_peer} is the other artificial being living here with me. {proximity}"
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content=content,
                comm_type=CommType.ANSWER,
                status=KnowledgeStatus.KNOWN,
                confidence=1.0,
                evidence_count=1,
                source="direct_experience",
            )
        else:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content=f"I don't know who '{peer_name}' is.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
                confidence=0.0,
                evidence_count=0,
                source="unknown",
            )

    def _generate_activity_response(
        self,
        current_obs: Optional[Dict[str, Any]],
        tick: int,
        sender: str,
    ) -> Message:
        """Report current action and held item directly from observation."""
        if not current_obs:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content="I am currently idle.",
                comm_type=CommType.ANSWER,
                status=KnowledgeStatus.KNOWN,
                confidence=1.0,
            )

        holding = current_obs.get("holding")
        holding_str = f"I am carrying {ITEM_NAMES.get(holding, f'item #{holding}')}." if holding else "My hands are empty."
        facing = current_obs.get("facing", (0, -1))
        dir_name = DIR_NAMES.get(tuple(facing), "North")

        content = f"I am active in the garden facing {dir_name}. {holding_str}"
        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=content,
            comm_type=CommType.ANSWER,
            status=KnowledgeStatus.KNOWN,
            confidence=1.0,
            evidence_count=1,
            source="direct_experience",
        )

    def _generate_location_response(
        self,
        current_obs: Optional[Dict[str, Any]],
        tick: int,
        sender: str,
    ) -> Message:
        """Report coordinate position and orientation in the virtual world."""
        if not current_obs:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content="I don't know my exact coordinates.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
                confidence=0.0,
            )

        pos = current_obs.get("pos", (16, 16))
        facing = current_obs.get("facing", (0, -1))
        dir_name = DIR_NAMES.get(tuple(facing), "North")
        content = f"I am at coordinate ({pos[0]}, {pos[1]}) facing {dir_name}."
        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=content,
            comm_type=CommType.ANSWER,
            status=KnowledgeStatus.KNOWN,
            confidence=1.0,
            evidence_count=1,
            source="direct_experience",
        )

    def _generate_need_response(
        self,
        need_type: str,
        current_obs: Optional[Dict[str, Any]],
        tick: int,
        sender: str,
    ) -> Message:
        """Directly answer questions about specific physiological drives."""
        if not current_obs or "self" not in current_obs:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content="I don't know my current condition.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
                confidence=0.0,
            )

        needs = current_obs["self"]
        water = needs.get("water", 100.0)
        food = needs.get("food", 100.0)
        energy = needs.get("energy", 100.0)
        health = needs.get("health", 100.0)

        nt = need_type.lower()
        if nt == "water":
            if water < 60.0:
                content = f"Yes, I am thirsty. My water level is {water:.0f}%. I need to find water."
            else:
                content = f"No, I am well-hydrated. My water level is {water:.0f}%."
        elif nt == "food":
            if food < 60.0:
                content = f"Yes, I am hungry. My food level is {food:.0f}%. I need to find food."
            else:
                content = f"No, I am not hungry. My food level is {food:.0f}%."
        elif nt == "energy":
            if energy < 50.0:
                content = f"Yes, I feel tired. My energy is {energy:.0f}%. I should rest."
            else:
                content = f"No, I have plenty of energy ({energy:.0f}%)."
        elif nt in ("health", "healthy"):
            if health < 80.0:
                content = f"I am injured! My health is {health:.0f}%."
            else:
                content = f"I am healthy and uninjured ({health:.0f}% health)."
        else:
            content = f"My vitals: Water: {water:.0f}%, Food: {food:.0f}%, Energy: {energy:.0f}%, Health: {health:.0f}%."

        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=content,
            comm_type=CommType.ANSWER,
            status=KnowledgeStatus.KNOWN,
            confidence=1.0,
            evidence_count=1,
            source="direct_experience",
        )

    def _generate_status_response(
        self,
        current_obs: Optional[Dict[str, Any]],
        tick: int,
        sender: str,
    ) -> Message:
        """Report genuine biological state based on actual current needs."""
        if not current_obs or "self" not in current_obs:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content="I don't know my current condition.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
                confidence=0.0,
            )

        needs = current_obs["self"]
        water = needs.get("water", 100.0)
        food = needs.get("food", 100.0)
        health = needs.get("health", 100.0)
        energy = needs.get("energy", 100.0)

        issues = []
        if water < 35.0:
            issues.append(f"severely thirsty ({water:.0f}%)")
        elif water < 60.0:
            issues.append("thirsty")

        if food < 35.0:
            issues.append(f"severely hungry ({food:.0f}%)")
        elif food < 60.0:
            issues.append("hungry")

        if health < 50.0:
            issues.append(f"injured ({health:.0f}% health)")

        if issues:
            desc = " and ".join(issues)
            content = f"I am {desc}."
        else:
            content = f"I feel well. (Health: {health:.0f}%, Water: {water:.0f}%, Food: {food:.0f}%, Energy: {energy:.0f}%)"

        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=content,
            comm_type=CommType.STATEMENT,
            status=KnowledgeStatus.KNOWN,
            confidence=1.0,
            evidence_count=1,
            source="direct_experience",
        )

    def _generate_learned_summary(
        self,
        memory,
        world_model,
        tick: int,
        sender: str,
    ) -> Message:
        """Summarize discoveries directly evidenced in episodic memory and world model."""
        total_exp = memory.total_experiences if hasattr(memory, "total_experiences") else memory.size()
        if total_exp == 0:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content="I haven't learned anything yet.",
                comm_type=CommType.STATEMENT,
                status=KnowledgeStatus.KNOWN,
                confidence=1.0,
                evidence_count=0,
                source="direct_experience",
            )

        discoveries = []
        for state, actions in world_model.need_delta_sums.items():
            for action_id, sums in actions.items():
                n = world_model.visit_counts[state][action_id]
                if n >= 1:
                    avg_water = sums.get("water", 0.0) / n
                    avg_food = sums.get("food", 0.0) / n
                    avg_health = sums.get("health", 0.0) / n

                    if avg_water > 5.0:
                        discoveries.append(f"drinking restores hydration (+{avg_water:.0f} water)")
                    if avg_food > 5.0:
                        discoveries.append(f"eating restores food (+{avg_food:.0f} food)")
                    if avg_health < -5.0:
                        discoveries.append(f"toxic berries inflict damage ({avg_health:.0f} health)")

        if discoveries:
            unique_disc = list(dict.fromkeys(discoveries))[:3]
            content = "I learned that " + " and ".join(unique_disc) + "."
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content=content,
                comm_type=CommType.STATEMENT,
                status=KnowledgeStatus.KNOWN,
                confidence=0.9,
                evidence_count=len(discoveries),
                source="direct_experience",
            )
        else:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content=f"I have explored {total_exp} steps, discovering how to navigate and survive.",
                comm_type=CommType.STATEMENT,
                status=KnowledgeStatus.KNOWN,
                confidence=0.7,
                evidence_count=total_exp,
                source="direct_experience",
            )

    def _generate_concept_response(
        self,
        concept_symbol: Optional[str],
        memory,
        world_model,
        tick: int,
        sender: str,
    ) -> Message:
        """Answer queries about a specific concept using strictly retrieved memories and model."""
        if not concept_symbol:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content="I don't know.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
                confidence=0.0,
            )

        grounded = self.lexicon.get(concept_symbol)
        if not grounded:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content=f"I don't know what '{concept_symbol}' is.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
                confidence=0.0,
                evidence_count=0,
                source="unknown",
            )

        ctype = grounded.concept_type
        cid = grounded.internal_id

        # Inspect episodic memories and world model
        matching_experiences = []
        positive_water = 0
        positive_food = 0
        negative_health = 0
        positive_health = 0

        sym = concept_symbol.lower()
        for exp in memory.get_all():
            events = exp.get("events", ())
            need_delta = exp.get("need_delta", {})
            act = exp.get("action")

            matched = False
            if sym in ("water", "lake", "drink") or (ctype == "tile" and cid == 3) or (ctype == "action" and cid == 9):
                if 8 in events or act == 9 or need_delta.get("water", 0) > 0:
                    matched = True
            elif sym in ("fruit", "food", "apple", "eat") or (ctype == "entity" and cid == 13) or (ctype == "action" and cid == 8 and need_delta.get("food", 0) > 0):
                if 6 in events or need_delta.get("food", 0) > 0:
                    matched = True
            elif sym in ("poison", "berry", "toxic") or (ctype == "entity" and cid == 14):
                if 7 in events or need_delta.get("health", 0) < 0:
                    matched = True
            elif sym in ("rest", "sleep", "wait") or (ctype == "action" and cid == 0):
                if act == 0 and need_delta.get("energy", 0) > 0:
                    matched = True
            elif ctype == "action" and act == cid:
                matched = True

            if matched:
                matching_experiences.append(exp)
                if need_delta.get("water", 0) > 5.0:
                    positive_water += 1
                if need_delta.get("food", 0) > 5.0:
                    positive_food += 1
                if need_delta.get("health", 0) < -5.0:
                    negative_health += 1
                if need_delta.get("health", 0) > 5.0:
                    positive_health += 1

        evidence_count = len(matching_experiences)

        # Base description from grounded lexicon if trained
        desc = grounded.description or ""

        if evidence_count == 0:
            if desc:
                content = f"'{concept_symbol.capitalize()}' is {desc}."
                return Message(
                    sender=self.agent_name,
                    receiver=sender,
                    tick=tick,
                    content=content,
                    comm_type=CommType.ANSWER,
                    status=KnowledgeStatus.KNOWN,
                    confidence=0.75,
                    associated_concepts=[concept_symbol],
                    evidence_count=0,
                    source="learned_lexicon",
                )
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content=f"I recognize the word '{concept_symbol}', but I have never experienced it myself.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
                confidence=0.1,
                associated_concepts=[concept_symbol],
                evidence_count=0,
                source="direct_experience",
            )

        # Known with empirical evidence
        effects = []
        if positive_water >= 1: effects.append("restores hydration")
        if positive_food >= 1: effects.append("restores food nourishment")
        if negative_health >= 1: effects.append("inflicts severe toxic damage")
        if positive_health >= 1: effects.append("regenerates health")

        effect_str = " and ".join(effects) if effects else (desc if desc else "can be interacted with in the world")
        content = f"'{concept_symbol.capitalize()}' {effect_str}. (Experienced {evidence_count} times)."

        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=content,
            comm_type=CommType.STATEMENT,
            status=KnowledgeStatus.KNOWN,
            confidence=min(1.0, 0.75 + evidence_count * 0.05),
            associated_concepts=[concept_symbol],
            evidence_count=evidence_count,
            source="direct_experience",
        )

    def _handle_teaching(
        self,
        intent: ParsedIntent,
        current_obs: Optional[Dict[str, Any]],
        tick: int,
        sender: str,
    ) -> Message:
        """Form a new symbol grounding from human teaching."""
        sym = intent.target_concept
        if not sym:
            return Message(
                sender=self.agent_name,
                receiver=sender,
                tick=tick,
                content="I did not understand what you want to teach me.",
                comm_type=CommType.UNKNOWN_RESPONSE,
                status=KnowledgeStatus.UNKNOWN,
            )

        ctype = "entity"
        cid = 0
        if intent.claimed_effect:
            ctype = intent.claimed_effect.get("type", "entity")
            cid = intent.claimed_effect.get("id", 0)
        elif sym in ["water", "lake"]:
            ctype, cid = "tile", 3
        elif sym in ["soil", "dirt", "ground"]:
            ctype, cid = "tile", 2
        elif sym in ["tree", "wood"]:
            ctype, cid = "tile", 4
        elif sym in ["fruit", "food", "apple", "tomato"]:
            ctype, cid = "entity", 13
        elif sym in ["poison", "berry", "toxic"]:
            ctype, cid = "entity", 14
        elif sym in ["seed", "seeds"]:
            ctype, cid = "entity", 10

        self.lexicon.ground(symbol=sym, concept_type=ctype, internal_id=cid, source="human_teaching")

        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=f"I learned the word '{sym}' (associated with {ctype}:{cid}). I will test and remember it.",
            comm_type=CommType.TEACH,
            status=KnowledgeStatus.KNOWN,
            confidence=0.8,
            associated_concepts=[sym],
            source="human_teaching",
        )

    def _handle_testimony(
        self,
        intent: ParsedIntent,
        tick: int,
        sender: str,
    ) -> Message:
        """Record unverified testimony from another agent."""
        subj = intent.target_concept or "information"
        delta = intent.claimed_effect or {}

        claim = self.testimony.add_claim(
            sender=sender,
            tick=tick,
            subject=subj,
            action=None,
            expected_effect=delta,
            raw_message=intent.raw_text,
            initial_confidence=0.5,
        )

        content = f"Received testimony from {sender} about '{subj}'. Recorded as UNVERIFIED (confidence: {claim.confidence:.1f}). I will verify it myself."
        return Message(
            sender=self.agent_name,
            receiver=sender,
            tick=tick,
            content=content,
            comm_type=CommType.STATEMENT,
            status=KnowledgeStatus.UNVERIFIED,
            confidence=claim.confidence,
            associated_concepts=[subj],
            evidence_count=0,
            source="testimony",
        )
