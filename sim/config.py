"""Simulation configuration and difficulty knobs."""

from dataclasses import asdict, dataclass
import json
from typing import Any, Dict


@dataclass
class WorldConfig:
    """Configuration parameters for ALC world simulation."""

    # Grid dimensions
    width: int = 32
    height: int = 32

    # Master random seed
    seed: int = 42

    # Agent Needs (Initial & Maximum)
    max_energy: float = 100.0
    max_water: float = 100.0
    max_food: float = 100.0
    max_health: float = 100.0

    # Base decay rates per tick
    energy_decay: float = 0.05
    water_decay: float = 0.05
    food_decay: float = 0.04

    # Action-specific energy penalties
    move_energy_cost: float = 0.05
    dig_energy_cost: float = 0.10
    use_energy_cost: float = 0.05
    signal_energy_cost: float = 0.05

    # Consequences on zero needs
    starvation_damage: float = 0.50
    dehydration_damage: float = 0.50
    health_regen_rate: float = 0.10

    # Nutrition & Recovery
    drink_water_amount: float = 35.0
    good_fruit_food: float = 40.0
    good_fruit_energy: float = 20.0
    poison_berry_food: float = 15.0
    poison_berry_damage: float = 35.0

    # Plant growth dynamics
    seedling_growth_ticks: int = 25
    fruit_yield_ticks: int = 20
    soil_drying_ticks: int = 40
    adjacent_water_irrigates: bool = True

    # Weather & Renewable ecology
    rain_enabled: bool = True
    rain_interval: int = 150
    rain_duration: int = 30
    tree_seed_drop_prob: float = 0.008
    dig_unearth_seed_prob: float = 0.10

    # Initial procedural population
    initial_seeds: int = 12
    initial_water_tiles: int = 35
    initial_trees: int = 40
    initial_soil_tiles: int = 24
    initial_containers: int = 4
    initial_poison_bushes: int = 5

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorldConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "WorldConfig":
        return cls.from_dict(json.loads(json_str))
