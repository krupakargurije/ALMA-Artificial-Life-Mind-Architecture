"""Local observation and outcome generation pipeline.

Strict rule: Opaque integer IDs only. The brain never receives semantic names.
"""

from typing import Any, Dict, List, Optional, Tuple
from sim.config import WorldConfig
from sim.entities import (
    ENTITY_AGENT,
    TILE_OUT_OF_BOUNDS,
)


def extract_local_view(
    grid: List[List[int]],
    agent_x: int,
    agent_y: int,
    width: int,
    height: int,
    plants: Dict[Tuple[int, int], Any],
    ground_items: Dict[Tuple[int, int], List[Any]],
    other_agents: List[Any],
    view_radius: int = 3,
) -> List[List[int]]:
    """Extract a (2*view_radius + 1) x (2*view_radius + 1) integer grid around (agent_x, agent_y).
    
    Center [3][3] represents the tile/item beneath the observing agent.
    Other agents within view appear as ENTITY_AGENT (20).
    Entities/items take visual precedence over raw terrain tiles.
    """
    view_size = 2 * view_radius + 1
    view: List[List[int]] = [[TILE_OUT_OF_BOUNDS for _ in range(view_size)] for _ in range(view_size)]

    # Pre-index other agent locations
    other_locs = {(a.x, a.y) for a in other_agents if a.alive}

    for r_idx, dy in enumerate(range(-view_radius, view_radius + 1)):
        wy = agent_y + dy
        for c_idx, dx in enumerate(range(-view_radius, view_radius + 1)):
            wx = agent_x + dx

            # Map boundary check
            if not (0 <= wx < width and 0 <= wy < height):
                view[r_idx][c_idx] = TILE_OUT_OF_BOUNDS
                continue

            coord = (wx, wy)

            # 1. Other agent presence (takes top rendering precedence, except for self)
            if coord in other_locs and (dx != 0 or dy != 0):
                view[r_idx][c_idx] = ENTITY_AGENT
                continue

            # 2. Plant on tile
            if coord in plants:
                view[r_idx][c_idx] = plants[coord].entity_id
                continue

            # 3. Ground item on tile
            if coord in ground_items and ground_items[coord]:
                # Top item on ground
                view[r_idx][c_idx] = ground_items[coord][-1].entity_id
                continue

            # 4. Underlying base terrain tile
            view[r_idx][c_idx] = grid[wy][wx]

    return view


def build_observation(
    tick: int,
    agent: Any,
    grid: List[List[int]],
    width: int,
    height: int,
    plants: Dict[Tuple[int, int], Any],
    ground_items: Dict[Tuple[int, int], List[Any]],
    all_agents: List[Any],
    events: List[int],
) -> Dict[str, Any]:
    """Construct standard Observation dictionary conforming to Section 4 schema."""
    other_agents = [a for a in all_agents if a.agent_id != agent.agent_id]

    view = extract_local_view(
        grid=grid,
        agent_x=agent.x,
        agent_y=agent.y,
        width=width,
        height=height,
        plants=plants,
        ground_items=ground_items,
        other_agents=other_agents,
        view_radius=3,
    )

    # Relative coordinates and signals for others within 7x7 local view
    others_list: List[Dict[str, Any]] = []
    for other in other_agents:
        if not other.alive:
            continue
        rel_x = other.x - agent.x
        rel_y = other.y - agent.y
        if abs(rel_x) <= 3 and abs(rel_y) <= 3:
            others_list.append({
                "rel_x": rel_x,
                "rel_y": rel_y,
                "signal": other.signal,
            })

    return {
        "tick": tick,
        "self": {
            "energy": round(agent.needs.energy, 2),
            "water": round(agent.needs.water, 2),
            "food": round(agent.needs.food, 2),
            "health": round(agent.needs.health, 2),
            "holding": agent.holding,
        },
        "view": view,
        "others": others_list,
        "events": list(events),
    }


def build_outcome(
    obs_next: Dict[str, Any],
    need_delta: Dict[str, float],
    alive: bool,
) -> Dict[str, Any]:
    """Construct standard Outcome dictionary conforming to Section 4 schema."""
    return {
        "obs_next": obs_next,
        "need_delta": need_delta,
        "alive": alive,
    }
