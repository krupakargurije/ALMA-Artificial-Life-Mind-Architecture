"""Metric tracking and statistical aggregation for ALC experiments."""

import math
from typing import Any, Dict, List, Optional, Set, Tuple

from sim.entities import (
    ENTITY_MATURE_PLANT,
    EVENT_ATE_FOOD,
    EVENT_ATE_POISON,
    EVENT_DIED,
    EVENT_DRANK_WATER,
    EVENT_DUG_SOIL,
    EVENT_USED_ITEM,
)


class MetricsTracker:
    """Tracks and aggregates simulation metrics for an agent run."""

    def __init__(self, agent_id: int = 0):
        self.agent_id = agent_id

        # Life durations
        self.current_life_ticks: int = 0
        self.life_durations: List[int] = []

        # Core counters
        self.total_ticks: int = 0
        self.deaths: int = 0
        self.food_eaten: int = 0
        self.poison_eaten: int = 0
        self.water_drank: int = 0
        self.items_used: int = 0
        self.soil_dug: int = 0

        # Plants grown tracker: set of plant coordinates that have matured
        self._matured_plant_locs: Set[Tuple[int, int]] = set()
        self.plants_successfully_grown: int = 0

        # Distinct action-outcome transitions
        self.distinct_action_outcomes: Set[Tuple[int, int, Tuple[int, ...]]] = set()

    def record_step(
        self,
        world: Any,
        action: int,
        outcome: Dict[str, Any],
        obs_hash: int = 0,
    ) -> None:
        """Process one tick of simulation and update metric registers."""
        self.total_ticks += 1
        self.current_life_ticks += 1

        events = outcome.get("obs_next", {}).get("events", [])
        alive = outcome.get("alive", True)

        # Event counters
        if EVENT_ATE_FOOD in events:
            self.food_eaten += 1
        if EVENT_ATE_POISON in events:
            self.poison_eaten += 1
        if EVENT_DRANK_WATER in events:
            self.water_drank += 1
        if EVENT_USED_ITEM in events:
            self.items_used += 1
        if EVENT_DUG_SOIL in events:
            self.soil_dug += 1

        # Death & life duration
        if not alive or EVENT_DIED in events:
            self.deaths += 1
            self.life_durations.append(self.current_life_ticks)
            self.current_life_ticks = 0

        # Track plant maturity
        for loc, plant in world.plants.items():
            if plant.stage == ENTITY_MATURE_PLANT and loc not in self._matured_plant_locs:
                self._matured_plant_locs.add(loc)
                self.plants_successfully_grown += 1

        # Track unique action-outcome pairs
        event_tuple = tuple(sorted(events))
        self.distinct_action_outcomes.add((obs_hash, action, event_tuple))

    def finalize(self) -> Dict[str, Any]:
        """Finalize metrics at end of run and compute statistical distributions."""
        all_durations = list(self.life_durations)
        if self.current_life_ticks > 0:
            all_durations.append(self.current_life_ticks)

        n = len(all_durations)
        if n > 0:
            mean_ticks = sum(all_durations) / n
            sorted_durations = sorted(all_durations)
            median_ticks = (
                sorted_durations[n // 2]
                if n % 2 != 0
                else (sorted_durations[n // 2 - 1] + sorted_durations[n // 2]) / 2.0
            )
            min_ticks = sorted_durations[0]
            max_ticks = sorted_durations[-1]
            variance = sum((x - mean_ticks) ** 2 for x in all_durations) / n
            std_ticks = math.sqrt(variance)
        else:
            mean_ticks = 0.0
            median_ticks = 0.0
            min_ticks = 0
            max_ticks = 0
            std_ticks = 0.0

        return {
            "total_ticks": self.total_ticks,
            "total_deaths": self.deaths,
            "total_lives": len(all_durations),
            "ticks_per_life_mean": round(mean_ticks, 2),
            "ticks_per_life_std": round(std_ticks, 2),
            "ticks_per_life_median": round(median_ticks, 2),
            "ticks_per_life_min": min_ticks,
            "ticks_per_life_max": max_ticks,
            "food_eaten": self.food_eaten,
            "poison_eaten": self.poison_eaten,
            "plants_successfully_grown": self.plants_successfully_grown,
            "distinct_action_outcome_pairs": len(self.distinct_action_outcomes),
            "water_drank": self.water_drank,
            "items_used": self.items_used,
            "soil_dug": self.soil_dug,
            "life_durations": all_durations,
        }
