"""Tabular count-based world model, intrinsic curiosity, and utility valuation for ALC.

Strict Rule: No pretrained weights, no task-specific reward shaping.
Drives permitted: biological needs (hunger/thirst/health deltas) and generic curiosity/novelty.
Mistakes leading to damage get reduced value, but remain re-testable.
"""

from collections import defaultdict
import json
import math
import random
from typing import Any, Dict, List, Optional, Tuple


def state_to_key(state: Tuple) -> str:
    """Serialize arbitrary nested state tuple into a deterministic JSON string."""
    return json.dumps(state)


def key_to_state(key: str) -> Tuple:
    """Deserialize JSON string back into nested state tuple."""
    def _to_tuples(item):
        if isinstance(item, list):
            return tuple(_to_tuples(x) for x in item)
        return item
    return _to_tuples(json.loads(key))


class TabularWorldModel:
    """Discovers world dynamics and predicts consequences of actions from experience."""

    def __init__(
        self,
        gamma: float = 0.90,
        curiosity_weight: float = 1.5,
        mistake_penalty_weight: float = 3.0,
    ):
        self.gamma = gamma
        self.curiosity_weight = curiosity_weight
        self.mistake_penalty_weight = mistake_penalty_weight

        # N(s, a): Visit counts
        self.visit_counts: Dict[Tuple, Dict[int, int]] = defaultdict(lambda: defaultdict(int))

        # Expected need delta per (s, a): (s, a) -> {need: running_mean}
        self.need_delta_sums: Dict[Tuple, Dict[int, Dict[str, float]]] = defaultdict(
            lambda: defaultdict(lambda: {"energy": 0.0, "water": 0.0, "food": 0.0, "health": 0.0})
        )

        # Transition counts: (s, a, s') -> count
        self.transition_counts: Dict[Tuple, Dict[int, Dict[Tuple, int]]] = defaultdict(
            lambda: defaultdict(lambda: defaultdict(int))
        )

        # Mistake memory: (s, a) -> total damage experienced
        self.mistake_memory: Dict[Tuple, Dict[int, float]] = defaultdict(lambda: defaultdict(float))

        # Value / Q table: (s, a) -> float
        self.q_table: Dict[Tuple, Dict[int, float]] = defaultdict(lambda: defaultdict(float))

        # Rolling tracking for TD-error and prediction loss
        self.last_td_error: float = 0.0
        self.total_updates: int = 0

    def update(
        self,
        state: Tuple,
        action: int,
        need_delta: Dict[str, float],
        next_state: Tuple,
        alive: bool,
    ) -> float:
        """Update model statistics from a realized transition. Returns the absolute TD-error."""
        self.visit_counts[state][action] += 1
        n = self.visit_counts[state][action]
        self.total_updates += 1

        # Update running sum of need deltas
        sums = self.need_delta_sums[state][action]
        for k in ["energy", "water", "food", "health"]:
            sums[k] += need_delta.get(k, 0.0)

        # Record transition
        self.transition_counts[state][action][next_state] += 1

        # Mistake memory: record damage
        health_delta = need_delta.get("health", 0.0)
        if health_delta < -1.0:
            # Significant damage occurred (e.g. poison or fatal injury)
            self.mistake_memory[state][action] += abs(health_delta)

        # Compute immediate biological utility
        # Positive food/water gains are rewarding; damage is heavily penalized
        immediate_reward = (
            need_delta.get("food", 0.0) * 1.5
            + need_delta.get("water", 0.0) * 1.5
            + need_delta.get("health", 0.0) * 2.5
            + need_delta.get("energy", 0.0) * 0.2
        )

        # Terminal state penalty
        if not alive:
            immediate_reward -= 50.0

        # Bellman update
        best_next_q = 0.0
        if alive and next_state in self.q_table and self.q_table[next_state]:
            best_next_q = max(self.q_table[next_state].values())

        alpha = 1.0 / (1.0 + 0.05 * n)  # Learning rate decays with visit count
        target = immediate_reward + self.gamma * best_next_q
        current_q = self.q_table[state][action]
        td_error = target - current_q
        self.last_td_error = abs(td_error)
        self.q_table[state][action] = current_q + alpha * td_error
        return abs(td_error)

    def planning_step(self, n_steps: int = 5) -> None:
        """Dyna-style model-based simulated planning over known transition graphs."""
        if not self.visit_counts or n_steps <= 0:
            return
        
        all_states = list(self.visit_counts.keys())
        for _ in range(n_steps):
            s = random.choice(all_states)
            actions_in_s = list(self.visit_counts[s].keys())
            if not actions_in_s:
                continue
            a = random.choice(actions_in_s)
            
            # Predict next state from empirical transition counts
            next_state_counts = self.transition_counts[s].get(a, {})
            if not next_state_counts:
                continue
            
            best_s_prime = max(next_state_counts.items(), key=lambda item: item[1])[0]
            expected_deltas = self.get_expected_deltas(s, a)
            
            # Simulated Bellman update
            immediate_reward = (
                expected_deltas.get("food", 0.0) * 1.5
                + expected_deltas.get("water", 0.0) * 1.5
                + expected_deltas.get("health", 0.0) * 2.5
                + expected_deltas.get("energy", 0.0) * 0.2
            )
            best_next_q = 0.0
            if best_s_prime in self.q_table and self.q_table[best_s_prime]:
                best_next_q = max(self.q_table[best_s_prime].values())
                
            n = self.visit_counts[s][a]
            alpha = 1.0 / (1.0 + 0.05 * n)
            target = immediate_reward + self.gamma * best_next_q
            current_q = self.q_table[s][a]
            self.q_table[s][a] = current_q + alpha * (target - current_q)

    def get_expected_deltas(self, state: Tuple, action: int) -> Dict[str, float]:
        """Compute expected need deltas for (state, action)."""
        n = self.visit_counts[state][action]
        if n == 0:
            return {"energy": 0.0, "water": 0.0, "food": 0.0, "health": 0.0}
        sums = self.need_delta_sums[state][action]
        return {k: sums[k] / n for k in sums}

    def compute_action_value(
        self,
        state: Tuple,
        action: int,
        current_needs: Dict[str, float],
    ) -> float:
        """Compute holistic action utility combining Q-value, biological drives, curiosity, and mistake avoidance."""
        base_q = self.q_table[state].get(action, 0.0)
        n = self.visit_counts[state].get(action, 0)

        # 1. Biological Need Context Weighting:
        # If thirsty (water low), water gain is valued higher
        # If hungry (food low), food gain is valued higher
        expected = self.get_expected_deltas(state, action)
        water_deficiency = max(0.0, 100.0 - current_needs.get("water", 100.0)) / 100.0
        food_deficiency = max(0.0, 100.0 - current_needs.get("food", 100.0)) / 100.0

        need_drive_bonus = (
            expected["water"] * (1.0 + 2.0 * water_deficiency)
            + expected["food"] * (1.0 + 2.0 * food_deficiency)
            + expected["health"] * 2.0
            + expected["energy"] * 0.1
        )

        # 2. Intrinsic Curiosity Bonus (UCB exploration bonus):
        # Decays proportionally to experience / visit counts, not wall-clock time
        curiosity_bonus = self.curiosity_weight / math.sqrt(n + 1)

        # 3. Mistake Aversion:
        # Actions that produced severe damage in this context are suppressed
        damage_penalty = self.mistake_penalty_weight * (self.mistake_memory[state].get(action, 0.0) / (n + 1))

        return base_q + need_drive_bonus + curiosity_bonus - damage_penalty

    def stats(self) -> Dict[str, Any]:
        """Return diagnostic metrics for logger and inspector."""
        total_transitions = sum(
            sum(len(targets) for targets in acts.values())
            for acts in self.transition_counts.values()
        )
        total_mistakes = sum(
            sum(self.mistake_memory[s].values()) for s in self.mistake_memory
        )
        return {
            "known_states": len(self.visit_counts),
            "total_transitions_modeled": total_transitions,
            "recorded_mistakes": round(total_mistakes, 2),
            "last_td_error": round(self.last_td_error, 4),
            "total_updates": self.total_updates,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete model parameters to JSON-compatible dictionary."""
        # Convert tuple keys to string keys
        visit_counts_ser = {
            state_to_key(s): dict(acts) for s, acts in self.visit_counts.items()
        }
        q_table_ser = {
            state_to_key(s): dict(acts) for s, acts in self.q_table.items()
        }
        need_deltas_ser = {
            state_to_key(s): {str(a): dict(needs) for a, needs in acts.items()}
            for s, acts in self.need_delta_sums.items()
        }
        mistakes_ser = {
            state_to_key(s): dict(acts) for s, acts in self.mistake_memory.items()
        }
        transitions_ser = {
            state_to_key(s): {
                str(a): {state_to_key(s_next): cnt for s_next, cnt in targets.items()}
                for a, targets in acts.items()
            }
            for s, acts in self.transition_counts.items()
        }
        return {
            "gamma": self.gamma,
            "curiosity_weight": self.curiosity_weight,
            "mistake_penalty_weight": self.mistake_penalty_weight,
            "total_updates": self.total_updates,
            "last_td_error": self.last_td_error,
            "visit_counts": visit_counts_ser,
            "q_table": q_table_ser,
            "need_delta_sums": need_deltas_ser,
            "mistake_memory": mistakes_ser,
            "transition_counts": transitions_ser,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """Deserialize and restore model parameters from dictionary."""
        self.gamma = data.get("gamma", self.gamma)
        self.curiosity_weight = data.get("curiosity_weight", self.curiosity_weight)
        self.mistake_penalty_weight = data.get("mistake_penalty_weight", self.mistake_penalty_weight)
        self.total_updates = data.get("total_updates", 0)
        self.last_td_error = data.get("last_td_error", 0.0)

        self.visit_counts.clear()
        for k, acts in data.get("visit_counts", {}).items():
            s = key_to_state(k)
            for a_str, cnt in acts.items():
                self.visit_counts[s][int(a_str)] = cnt

        self.q_table.clear()
        for k, acts in data.get("q_table", {}).items():
            s = key_to_state(k)
            for a_str, q_val in acts.items():
                self.q_table[s][int(a_str)] = q_val

        self.need_delta_sums.clear()
        for k, acts in data.get("need_delta_sums", {}).items():
            s = key_to_state(k)
            for a_str, needs in acts.items():
                for need_k, sum_val in needs.items():
                    self.need_delta_sums[s][int(a_str)][need_k] = sum_val

        self.mistake_memory.clear()
        for k, acts in data.get("mistake_memory", {}).items():
            s = key_to_state(k)
            for a_str, dmg in acts.items():
                self.mistake_memory[s][int(a_str)] = dmg

        self.transition_counts.clear()
        for k, acts in data.get("transition_counts", {}).items():
            s = key_to_state(k)
            for a_str, targets in acts.items():
                for s_next_k, cnt in targets.items():
                    s_next = key_to_state(s_next_k)
                    self.transition_counts[s][int(a_str)][s_next] = cnt
