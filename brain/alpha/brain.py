"""Alpha's Cognitive Brain Architecture.

Strict Rule: No LLMs, no hardcoded world rules, opaque IDs only.
Alpha discovers physics, biology, and agricultural cause-and-effect through experience.
Features Prioritized Experience Replay (PER), Dyna-style model planning, epistemic testimony verification,
and full state persistence.
"""

import json
import math
import os
import random
from typing import Any, Dict, List, Optional, Sequence, Tuple

from brain.common.episodic_memory import EpisodicMemory
from brain.common.state_abstraction import extract_compact_state, hash_state
from brain.common.world_model import TabularWorldModel
from brain.interface import Brain
from communication.autonomous import AutonomousCommDecisionEngine
from communication.interpreter import MessageInterpreter
from communication.message import CommType, KnowledgeStatus, Message
from communication.response_generator import ResponseGenerator
from communication.testimony import TestimonyBuffer
from communication.vocabulary import ConceptLexicon, GroundedConcept
from sim.actions import ALL_ACTIONS


class AlphaBrain(Brain):
    """Alpha's autonomous learning brain."""

    def __init__(
        self,
        action_set: Sequence[int] = ALL_ACTIONS,
        seed: int = 42,
        curiosity_weight: float = 1.8,
        gamma: float = 0.90,
    ):
        self.name: str = "Alpha"
        self.gender: str = "female"
        self.action_set = tuple(action_set)
        self.seed = seed
        self.rng = random.Random(seed)

        # Cognitive components
        self.memory = EpisodicMemory(capacity=3000, alpha=0.6)
        self.model = TabularWorldModel(gamma=gamma, curiosity_weight=curiosity_weight)

        # Communication & Symbol Grounding
        self.lexicon = ConceptLexicon(owner=self.name)
        self.testimony = TestimonyBuffer(owner=self.name)
        self.interpreter = MessageInterpreter(self.lexicon)
        self.response_gen = ResponseGenerator(
            agent_name=self.name,
            lexicon=self.lexicon,
            testimony_buffer=self.testimony,
        )
        self.auto_comm = AutonomousCommDecisionEngine(agent_name=self.name)

        # Transient perceptual state
        self.current_obs: Optional[Dict[str, Any]] = None
        self.current_state: Optional[Tuple] = None
        self.last_action: Optional[int] = None
        self.episode_steps: int = 0
        self.total_steps: int = 0
        self.lives_experienced: int = 1
        self.successful_experiences: int = 0
        self.learning_events: int = 0
        self.exploratory_actions: int = 0

    def reset_episode(self) -> None:
        """Transient state reset upon biological death (knowledge & memory persist)."""
        self.current_obs = None
        self.current_state = None
        self.last_action = None
        self.episode_steps = 0
        self.lives_experienced += 1

    def _hash_obs_view(self, obs: Optional[Dict[str, Any]]) -> int:
        """Deterministic hash of observation state."""
        if obs is None:
            return 0
        return hash_state(extract_compact_state(obs))

    def observe(self, obs: Dict[str, Any]) -> None:
        """Receive local sensory observation and form state abstraction."""
        self.current_obs = obs
        self.current_state = extract_compact_state(obs)

    def act(self) -> int:
        """Select action via holistic utility evaluation (needs drive + curiosity + epistemic testing - mistakes)."""
        if self.current_state is None:
            return self.rng.choice(self.action_set)

        self.episode_steps += 1
        self.total_steps += 1

        needs_dict = self.current_obs.get("self", {}) if self.current_obs else {}

        # Evaluate expected value for each opaque action
        action_values: List[Tuple[float, int]] = []
        unverified_claims = self.testimony.get_unverified_claims()

        for a in self.action_set:
            val = self.model.compute_action_value(
                state=self.current_state,
                action=a,
                current_needs=needs_dict,
            )

            # Epistemic motivation bonus: if action could verify an unverified claim
            if unverified_claims:
                for claim in unverified_claims:
                    if claim.action is not None and claim.action == a:
                        val += 2.0 * claim.confidence

            # Add minor stochastic perturbation for tie-breaking
            val += self.rng.uniform(-0.001, 0.001)
            action_values.append((val, a))

        # Greedy selection over UCB action value
        action_values.sort(key=lambda x: x[0], reverse=True)
        chosen_action = action_values[0][1]
        self.last_action = chosen_action

        # Check if action was exploratory (novel state-action pair)
        visit_cnt = self.model.visit_counts.get(self.current_state, {}).get(chosen_action, 0)
        if visit_cnt < 3:
            self.exploratory_actions += 1

        return chosen_action

    def learn(self, outcome: Dict[str, Any]) -> None:
        """Update cognitive model, prioritized episodic memory, and run background planning."""
        if self.current_state is None or self.last_action is None:
            return

        next_obs = outcome.get("obs_next", {})
        next_state = extract_compact_state(next_obs)
        need_delta = outcome.get("need_delta", {})
        events = next_obs.get("events", [])
        alive = outcome.get("alive", True)

        # 1. Update tabular world model and get TD-error
        td_error = self.model.update(
            state=self.current_state,
            action=self.last_action,
            need_delta=need_delta,
            next_state=next_state,
            alive=alive,
        )
        self.learning_events += 1

        # 2. Update prioritized episodic memory with measured TD-error
        self.memory.add(
            state=self.current_state,
            action=self.last_action,
            need_delta=need_delta,
            next_state=next_state,
            events=events,
            alive=alive,
            initial_td_error=td_error,
        )

        # Track positive physiological survival experiences
        if (
            need_delta.get("water", 0) > 0
            or need_delta.get("food", 0) > 0
            or need_delta.get("health", 0) > 0
            or need_delta.get("energy", 0) > 0
        ):
            self.successful_experiences += 1

        # 3. Prioritized Experience Replay & Dyna-Q Planning
        if self.total_steps % 5 == 0 and self.memory.size() >= 8:
            # Sample prioritized batch of high-surprise / critical experiences
            batch_exps, indices, weights = self.memory.sample_prioritized(batch_size=12, beta=0.4)
            new_td_errors = []
            for exp in batch_exps:
                td = self.model.update(
                    state=exp["state"],
                    action=exp["action"],
                    need_delta=exp["need_delta"],
                    next_state=exp["next_state"],
                    alive=exp["alive"],
                )
                new_td_errors.append(td)
                self.learning_events += 1

            self.memory.update_priorities(indices, new_td_errors)
            
            # Model-based simulated planning step
            self.model.planning_step(n_steps=5)

        # 4. Check if action verified any unverified testimony claims
        if self.last_action is not None and need_delta:
            for claim in self.testimony.get_unverified_claims():
                if claim.subject == "water" and need_delta.get("water", 0) > 0:
                    status = self.testimony.evaluate_test(claim.claim_id, need_delta, self.total_steps)
                    if status == KnowledgeStatus.CONFIRMED:
                        self.learning_events += 1
                elif claim.subject in ["food", "fruit"] and need_delta.get("food", 0) > 0:
                    status = self.testimony.evaluate_test(claim.claim_id, need_delta, self.total_steps)
                    if status == KnowledgeStatus.CONFIRMED:
                        self.learning_events += 1
                elif claim.subject in ["poison", "berry"] and need_delta.get("health", 0) < 0:
                    status = self.testimony.evaluate_test(claim.claim_id, need_delta, self.total_steps)
                    if status == KnowledgeStatus.CONFIRMED:
                        self.learning_events += 1

    def ground_concept(
        self,
        symbol: str,
        concept_type: str,
        internal_id: Any,
        confidence: float = 1.0,
        source: str = "human_teaching",
        description: str = "",
    ) -> GroundedConcept:
        """Ground a string symbol into Alpha's private lexicon."""
        return self.lexicon.ground(symbol, concept_type, internal_id, confidence, source, description)

    def receive_message(self, message: Message, tick: int) -> Message:
        """Process incoming communication and generate honest, evidence-grounded response."""
        intent = self.interpreter.parse(message.content)

        # Handle statement / testimony from another agent or human
        if intent.intent_type == "statement":
            claim = self.testimony.add_claim(
                sender=message.sender,
                tick=tick,
                subject=intent.target_concept or "general",
                action=None,
                expected_effect=intent.claimed_effect or {},
                raw_message=message.content,
                initial_confidence=message.confidence * 0.6,
            )
            return Message(
                sender=self.name,
                receiver=message.sender,
                tick=tick,
                content=f"Received testimony from {message.sender}: '{message.content}'. Recorded as UNVERIFIED (confidence: {claim.confidence:.1f}).",
                comm_type=CommType.STATEMENT,
                status=KnowledgeStatus.UNVERIFIED,
                confidence=claim.confidence,
                associated_concepts=[intent.target_concept] if intent.target_concept else [],
                evidence_count=0,
                source="testimony",
            )

        # Generate response using direct memory, world model, and needs
        return self.response_gen.generate_response(
            intent=intent,
            memory=self.memory,
            world_model=self.model,
            current_obs=self.current_obs,
            tick=tick,
            sender=message.sender,
        )

    def check_autonomous_communication(
        self,
        tick: int,
        outcome: Dict[str, Any],
        peer_name: str = "Albedo",
    ) -> Optional[Message]:
        """Evaluate if Alpha wants to autonomously communicate a discovery or warning."""
        return self.auto_comm.evaluate(
            tick=tick,
            outcome=outcome,
            current_obs=self.current_obs,
            peer_name=peer_name,
        )

    def stats(self) -> Dict[str, Any]:
        """Diagnostic metrics for logging and inspector visualization."""
        model_stats = self.model.stats()
        exp_rate = round((self.exploratory_actions / max(1, self.total_steps)) * 100, 1)
        return {
            "name": self.name,
            "gender": self.gender,
            "total_steps": self.total_steps,
            "episode_steps": self.episode_steps,
            "lives_experienced": self.lives_experienced,
            "memory_size": self.memory.size(),
            "known_states": model_stats["known_states"],
            "transitions_modeled": model_stats["total_transitions_modeled"],
            "recorded_mistakes": model_stats["recorded_mistakes"],
            "last_td_error": model_stats.get("last_td_error", 0.0),
            "successful_experiences": self.successful_experiences,
            "learning_events": self.learning_events,
            "exploration_rate": exp_rate,
            "grounded_symbols": len(self.lexicon.all_known_symbols()),
            "unverified_testimony": len(self.testimony.get_unverified_claims()),
        }

    def save(self, path: str) -> None:
        """Persist Alpha's complete brain state, parameters, models, and memory to disk."""
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        data = {
            "name": self.name,
            "gender": self.gender,
            "seed": self.seed,
            "total_steps": self.total_steps,
            "lives_experienced": self.lives_experienced,
            "successful_experiences": self.successful_experiences,
            "learning_events": self.learning_events,
            "exploratory_actions": self.exploratory_actions,
            "model": self.model.to_dict(),
            "memory": self.memory.to_dict(),
            "lexicon": self.lexicon.to_dict(),
            "testimony": self.testimony.to_dict(),
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> None:
        """Load and restore Alpha's complete brain state from disk."""
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.name = data.get("name", self.name)
        self.gender = data.get("gender", self.gender)
        self.total_steps = data.get("total_steps", 0)
        self.lives_experienced = data.get("lives_experienced", 1)
        self.successful_experiences = data.get("successful_experiences", 0)
        self.learning_events = data.get("learning_events", 0)
        self.exploratory_actions = data.get("exploratory_actions", 0)

        if "model" in data:
            self.model.from_dict(data["model"])
        if "memory" in data:
            self.memory.from_dict(data["memory"])
        if "lexicon" in data:
            self.lexicon.from_dict(data["lexicon"])
        if "testimony" in data:
            self.testimony.from_dict(data["testimony"])
