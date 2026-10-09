"""Sensory state abstraction and local perception hashing for ALC brains.

Strict Rule: Domain-agnostic abstraction. No hardcoded world rules or entity names.
Discretizes local 7x7 view, immediate surroundings, holding state, and physiological need levels.
"""

from typing import Any, Dict, Tuple


def discretize_need(value: float, max_value: float = 100.0) -> int:
    """Discretize continuous physiological need into 3 qualitative drive states:
    
    0: Low / Urgent need (< 40%)
    1: Medium / Moderate need (40% - 75%)
    2: High / Satisfied (> 75%)
    """
    fraction = value / max(max_value, 1.0)
    if fraction < 0.40:
        return 0
    elif fraction < 0.75:
        return 1
    return 2


def extract_compact_state(obs: Dict[str, Any]) -> Tuple:
    """Extract a compact, generic discrete state tuple from raw observation.
    
    State representation:
    - need_drives: (energy_level, water_level, food_level, health_level)
    - holding: opaque entity ID or 0
    - immediate_terrain: (tile_center, tile_north, tile_south, tile_east, tile_west)
    - visible_entities: sorted tuple of unique opaque entity IDs present in 7x7 view
    """
    self_data = obs.get("self", {})
    energy_lvl = discretize_need(self_data.get("energy", 100.0))
    water_lvl = discretize_need(self_data.get("water", 100.0))
    food_lvl = discretize_need(self_data.get("food", 100.0))
    health_lvl = discretize_need(self_data.get("health", 100.0))
    holding_id = self_data.get("holding") if self_data.get("holding") is not None else 0

    view = obs.get("view", [])
    # 7x7 center is [3][3]
    if len(view) == 7 and len(view[3]) == 7:
        center = view[3][3]
        north = view[2][3]
        south = view[4][3]
        east = view[3][4]
        west = view[3][2]
        immediate = (center, north, south, east, west)
        # Unique non-zero items visible in 7x7
        visible = tuple(sorted({cell for row in view for cell in row if cell > 0}))
    else:
        immediate = (0, 0, 0, 0, 0)
        visible = ()

    needs_tuple = (energy_lvl, water_lvl, food_lvl, health_lvl)
    return (needs_tuple, holding_id, immediate, visible)


def hash_state(compact_state: Tuple) -> int:
    """Deterministic hash of compact state tuple."""
    return hash(compact_state)
