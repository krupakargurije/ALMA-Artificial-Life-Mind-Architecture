"""Biological need dynamics: energy, water, food, and health."""

from dataclasses import dataclass
from typing import Dict
from sim.config import WorldConfig


@dataclass
class Needs:
    """Represents an agent's biological state."""

    energy: float = 100.0
    water: float = 100.0
    food: float = 100.0
    health: float = 100.0

    def tick_decay(self, config: WorldConfig, extra_energy_cost: float = 0.0) -> None:
        """Apply passive biological decay and thirst/hunger penalties for one tick."""
        self.energy = max(0.0, self.energy - (config.energy_decay + extra_energy_cost))
        self.water = max(0.0, self.water - config.water_decay)
        self.food = max(0.0, self.food - config.food_decay)

        # Starvation and dehydration damage
        damage = 0.0
        if self.water <= 0.0:
            damage += config.dehydration_damage
        if self.food <= 0.0:
            damage += config.starvation_damage

        if damage > 0.0:
            self.health = max(0.0, self.health - damage)
        elif (
            self.water > 70.0
            and self.food > 70.0
            and self.energy > 50.0
            and self.health < config.max_health
        ):
            # Slow natural healing when well nourished
            self.health = min(config.max_health, self.health + config.health_regen_rate)

    def drink(self, amount: float, max_water: float) -> None:
        """Replenish water reserves."""
        self.water = min(max_water, self.water + amount)

    def eat_good(
        self,
        food_gain: float,
        energy_gain: float,
        max_food: float,
        max_energy: float,
    ) -> None:
        """Replenish food and energy from wholesome sustenance."""
        self.food = min(max_food, self.food + food_gain)
        self.energy = min(max_energy, self.energy + energy_gain)

    def eat_poison(self, food_gain: float, damage: float, max_food: float) -> None:
        """Consume toxic flora, gaining slight calories but suffering severe damage."""
        self.food = min(max_food, self.food + food_gain)
        self.health = max(0.0, self.health - damage)

    def is_dead(self) -> bool:
        """Check if biological functions have ceased."""
        return self.health <= 0.0

    def delta(self, previous: "Needs") -> Dict[str, float]:
        """Compute delta vector: current - previous."""
        return {
            "energy": round(self.energy - previous.energy, 4),
            "water": round(self.water - previous.water, 4),
            "food": round(self.food - previous.food, 4),
            "health": round(self.health - previous.health, 4),
        }

    def to_dict(self) -> Dict[str, float]:
        return {
            "energy": round(self.energy, 2),
            "water": round(self.water, 2),
            "food": round(self.food, 2),
            "health": round(self.health, 2),
        }

    def copy(self) -> "Needs":
        return Needs(
            energy=self.energy,
            water=self.water,
            food=self.food,
            health=self.health,
        )

    def reset(self, config: WorldConfig) -> None:
        self.energy = config.max_energy
        self.water = config.max_water
        self.food = config.max_food
        self.health = config.max_health
