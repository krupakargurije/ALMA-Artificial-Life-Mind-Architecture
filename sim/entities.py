"""Tile taxonomy, opaque entity IDs, events, and simulation data structures."""

from dataclasses import dataclass
from typing import Optional, Tuple

# Tile IDs (opaque to brain)
TILE_OUT_OF_BOUNDS = 0
TILE_GRASS = 1
TILE_SOIL = 2
TILE_WATER = 3
TILE_TREE = 4

# Entity IDs (opaque to brain)
ENTITY_NONE = 0
ENTITY_SEED = 10
ENTITY_SEEDLING = 11
ENTITY_MATURE_PLANT = 12
ENTITY_GOOD_FRUIT = 13
ENTITY_POISON_BERRY = 14
ENTITY_WATER_CONTAINER_EMPTY = 15
ENTITY_WATER_CONTAINER_FULL = 16
ENTITY_AGENT = 20

# Event IDs (opaque to brain)
EVENT_NONE = 0
EVENT_MOVED = 1
EVENT_BLOCKED = 2
EVENT_PICKED_UP = 3
EVENT_DROPPED = 4
EVENT_USED_ITEM = 5
EVENT_ATE_FOOD = 6
EVENT_ATE_POISON = 7
EVENT_DRANK_WATER = 8
EVENT_DUG_SOIL = 9
EVENT_TOOK_DAMAGE = 10
EVENT_HEALED = 11
EVENT_DIED = 12
EVENT_RESPAWNED = 13
EVENT_RAINED = 14


@dataclass
class Item:
    """An item lying on the ground."""
    entity_id: int
    x: int
    y: int


@dataclass
class Plant:
    """A planted entity on a soil tile."""
    x: int
    y: int
    stage: int = ENTITY_SEEDLING
    wet_ticks: int = 0
    has_fruit: bool = False
    fruit_type: int = ENTITY_GOOD_FRUIT

    @property
    def entity_id(self) -> int:
        if self.stage == ENTITY_SEEDLING:
            return ENTITY_SEEDLING
        if self.has_fruit:
            return self.fruit_type
        return ENTITY_MATURE_PLANT
