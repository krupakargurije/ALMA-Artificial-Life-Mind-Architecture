"""Scripted Oracle Test for ALC World Solvability.

Strict Rule: This oracle lives ONLY in tests/ and is NEVER imported by brains.
Proves that the simulation dynamics, needs decay, and agricultural lifecycle
are solvable, balanced, and sustainable for >= 5,000 continuous ticks.
"""

from collections import deque
from typing import Callable, List, Optional, Set, Tuple

import pytest
from sim.actions import (
    DIR_EAST,
    DIR_NORTH,
    DIR_SOUTH,
    DIR_WEST,
    DRINK,
    DROP,
    EAT,
    DIG,
    MOVE_E,
    MOVE_N,
    MOVE_S,
    MOVE_W,
    PICK_UP,
    USE_ON_FACING,
    WAIT,
)
from sim.config import WorldConfig
from sim.entities import (
    ENTITY_GOOD_FRUIT,
    ENTITY_SEED,
    ENTITY_SEEDLING,
    ENTITY_MATURE_PLANT,
    TILE_GRASS,
    TILE_SOIL,
    TILE_WATER,
    TILE_TREE,
)
from sim.world import World


def bfs_step_towards(
    start: Tuple[int, int],
    is_target_fn: Callable[[int, int], bool],
    is_walkable_fn: Callable[[int, int], bool],
    width: int,
    height: int,
) -> Optional[int]:
    """Find the single next action to move from start towards any target coordinate using BFS."""
    if is_target_fn(start[0], start[1]):
        return None

    queue = deque([start])
    came_from: dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}

    found_target = None
    while queue:
        curr = queue.popleft()
        cx, cy = curr

        if is_target_fn(cx, cy):
            found_target = curr
            break

        # Check cardinal neighbors
        for move_act, (dx, dy) in [
            (MOVE_N, (0, -1)),
            (MOVE_S, (0, 1)),
            (MOVE_E, (1, 0)),
            (MOVE_W, (-1, 0)),
        ]:
            nx, ny = cx + dx, cy + dy
            neighbor = (nx, ny)
            if 0 <= nx < width and 0 <= ny < height and neighbor not in came_from:
                if is_walkable_fn(nx, ny) or is_target_fn(nx, ny):
                    came_from[neighbor] = curr
                    queue.append(neighbor)

    if not found_target:
        return None

    # Trace back to find the first step from start
    curr = found_target
    while came_from[curr] != start and came_from[curr] is not None:
        curr = came_from[curr]

    fx, fy = curr
    dx = fx - start[0]
    dy = fy - start[1]
    if (dx, dy) == (0, -1):
        return MOVE_N
    elif (dx, dy) == (0, 1):
        return MOVE_S
    elif (dx, dy) == (1, 0):
        return MOVE_E
    elif (dx, dy) == (-1, 0):
        return MOVE_W

    return None


def get_face_action(start: Tuple[int, int], target: Tuple[int, int]) -> Optional[int]:
    """Return movement action required to face target from an adjacent cell."""
    dx = target[0] - start[0]
    dy = target[1] - start[1]
    if (dx, dy) == (0, -1):
        return MOVE_N
    elif (dx, dy) == (0, 1):
        return MOVE_S
    elif (dx, dy) == (1, 0):
        return MOVE_E
    elif (dx, dy) == (-1, 0):
        return MOVE_W
    return None


class ScriptedOracle:
    """An expert oracle that understands world rules to prove solvability."""

    def __init__(self, world: World, agent_id: int = 0):
        self.world = world
        self.aid = agent_id

    def has_good_fruit_at(self, x: int, y: int) -> bool:
        coord = (x, y)
        if coord in self.world.plants:
            p = self.world.plants[coord]
            if p.has_fruit and p.fruit_type == ENTITY_GOOD_FRUIT:
                return True
        if coord in self.world.ground_items:
            if any(it.entity_id == ENTITY_GOOD_FRUIT for it in self.world.ground_items[coord]):
                return True
        return False

    def choose_action(self) -> int:
        agent = self.world.agents[self.aid]
        w, h = self.world.config.width, self.world.config.height
        curr_pos = (agent.x, agent.y)

        # 1. Thirst Priority (Drink before water drops low)
        if agent.needs.water < 70.0:
            if self.world.is_adjacent_to_water(agent.x, agent.y):
                return DRINK
            def is_water_shore(x: int, y: int) -> bool:
                return self.world.is_walkable(x, y) and self.world.is_adjacent_to_water(x, y)

            step = bfs_step_towards(curr_pos, is_water_shore, self.world.is_walkable, w, h)
            if step is not None:
                return step
            return DRINK

        # Drop any non-survival held items (e.g. empty water container) to keep hands free
        if agent.holding is not None and agent.holding not in (ENTITY_GOOD_FRUIT, ENTITY_SEED):
            return DROP

        # 2. Nutrition Priority: Consume held good fruit when food or energy is depleted
        if agent.holding == ENTITY_GOOD_FRUIT and (agent.needs.food < 85.0 or agent.needs.energy < 75.0):
            return EAT

        # 3. Hunger Priority: Acquire food when food drops below threshold
        if agent.needs.food < 75.0:
            # If hands are full with a non-food item, drop it immediately so we can pick up food
            if agent.holding is not None and agent.holding != ENTITY_GOOD_FRUIT:
                return DROP

            # Check current tile
            if self.has_good_fruit_at(curr_pos[0], curr_pos[1]):
                return PICK_UP

            # Check facing tile
            facing_pos = (agent.x + agent.facing[0], agent.y + agent.facing[1])
            if self.has_good_fruit_at(facing_pos[0], facing_pos[1]):
                return PICK_UP

            # Check immediate cardinal neighbors
            for dx, dy in [(0, -1), (0, 1), (1, 0), (-1, 0)]:
                nx, ny = agent.x + dx, agent.y + dy
                if self.has_good_fruit_at(nx, ny):
                    face_act = get_face_action(curr_pos, (nx, ny))
                    if agent.facing == (dx, dy):
                        return PICK_UP
                    return face_act

            # Search world for any good fruit (plant or ground)
            def is_food_source(x: int, y: int) -> bool:
                return self.has_good_fruit_at(x, y)

            step = bfs_step_towards(curr_pos, is_food_source, self.world.is_walkable, w, h)
            if step is not None:
                return step

            # No ripe fruit in world: wait near water/crops for crops to ripen!
            if not self.world.is_adjacent_to_water(agent.x, agent.y):
                def is_water_shore(x: int, y: int) -> bool:
                    return self.world.is_walkable(x, y) and self.world.is_adjacent_to_water(x, y)
                step = bfs_step_towards(curr_pos, is_water_shore, self.world.is_walkable, w, h)
                if step is not None:
                    return step

            return WAIT

        # 4. Proactive Harvesting: Keep one good fruit in hand
        if agent.holding is None:
            ripe_crops = [
                loc for loc, p in self.world.plants.items()
                if p.has_fruit and p.fruit_type == ENTITY_GOOD_FRUIT
            ]
            if ripe_crops:
                target_crop = ripe_crops[0]
                if curr_pos == target_crop:
                    return PICK_UP
                face_act = get_face_action(curr_pos, target_crop)
                if face_act is not None:
                    if agent.facing == (target_crop[0] - curr_pos[0], target_crop[1] - curr_pos[1]):
                        return PICK_UP
                    return face_act

                step = bfs_step_towards(curr_pos, lambda x, y: (x, y) == target_crop, self.world.is_walkable, w, h)
                if step is not None:
                    return step

        # 5. Agriculture: Maintain 8 irrigated plants along water border
        irrigated_plants = [
            loc for loc, p in self.world.plants.items()
            if self.world.is_adjacent_to_water(loc[0], loc[1])
        ]

        if len(irrigated_plants) < 8:
            # 5A. If holding seed, plant on empty irrigated soil
            if agent.holding == ENTITY_SEED:
                facing_pos = (agent.x + agent.facing[0], agent.y + agent.facing[1])
                # If facing empty soil or standing on empty soil:
                if (
                    (0 <= facing_pos[0] < w and 0 <= facing_pos[1] < h and self.world.grid[facing_pos[1]][facing_pos[0]] == TILE_SOIL and facing_pos not in self.world.plants)
                    or (self.world.grid[curr_pos[1]][curr_pos[0]] == TILE_SOIL and curr_pos not in self.world.plants)
                ):
                    return USE_ON_FACING

                empty_irrigated_soils = [
                    (sx, sy) for sx in range(w) for sy in range(h)
                    if self.world.grid[sy][sx] == TILE_SOIL
                    and self.world.is_adjacent_to_water(sx, sy)
                    and (sx, sy) not in self.world.plants
                ]

                if empty_irrigated_soils:
                    target_soil = empty_irrigated_soils[0]
                    step = bfs_step_towards(curr_pos, lambda x, y: (x, y) == target_soil, self.world.is_walkable, w, h)
                    if step is not None:
                        return step
                    return USE_ON_FACING
                else:
                    # No prepared soil adjacent to water -> Dig grass tile adjacent to water
                    grass_near_water = [
                        (gx, gy) for gx in range(w) for gy in range(h)
                        if self.world.grid[gy][gx] == TILE_GRASS
                        and self.world.is_adjacent_to_water(gx, gy)
                    ]
                    if grass_near_water:
                        target_grass = grass_near_water[0]
                        if curr_pos == target_grass:
                            return DIG
                        face_act = get_face_action(curr_pos, target_grass)
                        if face_act is not None:
                            if agent.facing == (target_grass[0] - curr_pos[0], target_grass[1] - curr_pos[1]):
                                return DIG
                            return face_act

                        step = bfs_step_towards(curr_pos, lambda x, y: (x, y) == target_grass, self.world.is_walkable, w, h)
                        if step is not None:
                            return step

            # 5B. Not holding seed, but seeds exist on ground -> Go pick one up
            elif agent.holding is None:
                seed_locs = [
                    loc for loc, items in self.world.ground_items.items()
                    if any(it.entity_id == ENTITY_SEED for it in items)
                ]
                if seed_locs:
                    target_seed = seed_locs[0]
                    if curr_pos == target_seed:
                        return PICK_UP
                    face_act = get_face_action(curr_pos, target_seed)
                    if face_act is not None:
                        if agent.facing == (target_seed[0] - curr_pos[0], target_seed[1] - curr_pos[1]):
                            return PICK_UP
                        return face_act

                    step = bfs_step_towards(curr_pos, lambda x, y: (x, y) == target_seed, self.world.is_walkable, w, h)
                    if step is not None:
                        return step

        # 6. Rest & Idle Conservation near water source
        if not self.world.is_adjacent_to_water(agent.x, agent.y):
            def is_water_shore(x: int, y: int) -> bool:
                return self.world.is_walkable(x, y) and self.world.is_adjacent_to_water(x, y)

            step = bfs_step_towards(curr_pos, is_water_shore, self.world.is_walkable, w, h)
            if step is not None:
                return step

        return WAIT


@pytest.mark.parametrize("test_seed", [42, 100, 777])
def test_oracle_survives_5000_ticks(test_seed):
    """Phase 1 Acceptance Criterion: Scripted oracle survives >= 5,000 ticks continuously without death."""
    config = WorldConfig(seed=test_seed)
    world = World(config=config, num_agents=1)
    oracle = ScriptedOracle(world, agent_id=0)

    target_ticks = 5000
    deaths = 0

    for tick in range(target_ticks):
        action = oracle.choose_action()
        outcomes = world.tick(action)
        if not outcomes[0]["alive"]:
            deaths += 1
            print(f"DEATH at tick {world.tick_count}: needs={world.agents[0].needs}")
            break

    agent = world.agents[0]
    assert deaths == 0, f"Oracle died on seed {test_seed} at tick {world.tick_count} (Life #{agent.lives})"
    assert world.tick_count == target_ticks
    assert agent.lives == 1
    assert agent.needs.health > 50.0
    assert agent.needs.water > 20.0
    assert agent.needs.food > 20.0
