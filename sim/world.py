"""Core ALC Simulation Engine.

Strict rule: The world owns the rules; the brain discovers them.
Deterministic, seeded procedural generation and comprehensive tick lifecycle.
"""

from dataclasses import dataclass, field
import random
from typing import Any, Dict, List, Optional, Set, Tuple

from sim.actions import (
    ALL_ACTIONS,
    DIR_EAST,
    DIR_NORTH,
    DIR_SOUTH,
    DIR_WEST,
    DRINK,
    DROP,
    EAT,
    DIG,
    MOVE_ACTION_DIRS,
    PICK_UP,
    SIGNAL_ACTIONS,
    USE_ON_FACING,
    WAIT,
)
from sim.config import WorldConfig
from sim.entities import (
    ENTITY_AGENT,
    ENTITY_GOOD_FRUIT,
    ENTITY_MATURE_PLANT,
    ENTITY_POISON_BERRY,
    ENTITY_SEED,
    ENTITY_SEEDLING,
    ENTITY_WATER_CONTAINER_EMPTY,
    ENTITY_WATER_CONTAINER_FULL,
    EVENT_ATE_FOOD,
    EVENT_ATE_POISON,
    EVENT_BLOCKED,
    EVENT_DIED,
    EVENT_DRANK_WATER,
    EVENT_DROPPED,
    EVENT_DUG_SOIL,
    EVENT_MOVED,
    EVENT_PICKED_UP,
    EVENT_RAINED,
    EVENT_RESPAWNED,
    EVENT_TOOK_DAMAGE,
    EVENT_USED_ITEM,
    Item,
    Plant,
    TILE_GRASS,
    TILE_SOIL,
    TILE_TREE,
    TILE_WATER,
)
from sim.needs import Needs
from sim.observation import build_observation, build_outcome


@dataclass
class AgentBody:
    """Embodied state of an agent in the world."""

    agent_id: int
    name: str = "Alpha"
    gender: str = "female"
    x: int = 16
    y: int = 16
    facing: Tuple[int, int] = DIR_NORTH
    holding: Optional[int] = None
    needs: Needs = field(default_factory=Needs)
    alive: bool = True
    lives: int = 1
    signal: Optional[int] = None
    spawn_pos: Tuple[int, int] = (16, 16)


class World:
    """Deterministic grid world simulation."""

    def __init__(self, config: Optional[WorldConfig] = None, num_agents: int = 1):
        self.config = config or WorldConfig()
        self.rng = random.Random(self.config.seed)
        self.tick_count: int = 0
        self.num_agents = num_agents

        # 2D Grid: [y][x]
        self.grid: List[List[int]] = [
            [TILE_GRASS for _ in range(self.config.width)]
            for _ in range(self.config.height)
        ]

        # Soil tile moisture timer: (x, y) -> ticks remaining wet
        self.moisture: Dict[Tuple[int, int], int] = {}

        # Plants on soil: (x, y) -> Plant
        self.plants: Dict[Tuple[int, int], Plant] = {}

        # Ground items: (x, y) -> List[Item]
        self.ground_items: Dict[Tuple[int, int], List[Item]] = {}

        # Pre-calculated set of water tiles for O(1) adjacency checks
        self.water_tiles: Set[Tuple[int, int]] = set()
        self.tree_tiles: List[Tuple[int, int]] = []

        # Embodied agents
        self.agents: List[AgentBody] = []

        # Procedural generation
        self._generate_world()

    def _generate_world(self) -> None:
        """Procedurally generate terrain, resources, and agent spawn points."""
        w, h = self.config.width, self.config.height

        # 1. Lake/Water feature near center-right
        lake_cx, lake_cy = w // 2 + 2, h // 2
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                if dx * dx + dy * dy <= 5:
                    wx, wy = lake_cx + dx, lake_cy + dy
                    if 0 <= wx < w and 0 <= wy < h:
                        self.grid[wy][wx] = TILE_WATER
                        self.water_tiles.add((wx, wy))

        # 2. Fertile Soil patches adjacent to the lake
        for wx, wy in list(self.water_tiles):
            for ndx, ndy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = wx + ndx, wy + ndy
                if (
                    0 <= nx < w
                    and 0 <= ny < h
                    and self.grid[ny][nx] == TILE_GRASS
                    and (nx, ny) not in self.water_tiles
                ):
                    if self.rng.random() < 0.70:
                        self.grid[ny][nx] = TILE_SOIL

        # 3. Trees in clumps away from immediate spawn
        spawn_center = (w // 2 - 2, h // 2)
        trees_placed = 0
        attempts = 0
        while trees_placed < self.config.initial_trees and attempts < 1000:
            attempts += 1
            tx = self.rng.randint(1, w - 2)
            ty = self.rng.randint(1, h - 2)
            if self.grid[ty][tx] == TILE_GRASS:
                # Keep immediate spawn area clear
                if abs(tx - spawn_center[0]) > 2 or abs(ty - spawn_center[1]) > 2:
                    self.grid[ty][tx] = TILE_TREE
                    self.tree_tiles.append((tx, ty))
                    trees_placed += 1

        # 4. Initial Seeds placed near trees and spawn
        seeds_placed = 0
        attempts = 0
        while seeds_placed < self.config.initial_seeds and attempts < 500:
            attempts += 1
            sx = self.rng.randint(spawn_center[0] - 3, spawn_center[0] + 3)
            sy = self.rng.randint(spawn_center[1] - 3, spawn_center[1] + 3)
            if 0 <= sx < w and 0 <= sy < h and self.is_walkable(sx, sy) and (sx, sy) not in self.ground_items:
                self._add_ground_item(sx, sy, ENTITY_SEED)
                seeds_placed += 1

        # 5. Empty Water Containers placed near spawn
        containers_placed = 0
        attempts = 0
        while containers_placed < self.config.initial_containers and attempts < 100:
            attempts += 1
            cx = self.rng.randint(spawn_center[0] - 2, spawn_center[0] + 2)
            cy = self.rng.randint(spawn_center[1] - 2, spawn_center[1] + 2)
            if 0 <= cx < w and 0 <= cy < h and self.is_walkable(cx, cy) and (cx, cy) not in self.ground_items:
                self._add_ground_item(cx, cy, ENTITY_WATER_CONTAINER_EMPTY)
                containers_placed += 1

        # 6. Wild Poison Bushes placed further out in perimeter
        bushes_placed = 0
        attempts = 0
        while bushes_placed < self.config.initial_poison_bushes and attempts < 200:
            attempts += 1
            bx = self.rng.randint(2, w - 3)
            by = self.rng.randint(2, h - 3)
            if (
                self.is_walkable(bx, by)
                and (abs(bx - spawn_center[0]) > 4 or abs(by - spawn_center[1]) > 4)
                and (bx, by) not in self.plants
            ):
                # Mature plant yielding toxic berries
                self.grid[by][bx] = TILE_SOIL
                self.plants[(bx, by)] = Plant(
                    x=bx,
                    y=by,
                    stage=ENTITY_MATURE_PLANT,
                    wet_ticks=self.config.fruit_yield_ticks,
                    has_fruit=True,
                    fruit_type=ENTITY_POISON_BERRY,
                )
                bushes_placed += 1

        # 7. Initialize Agents (Alpha and Albedo, both females)
        spawn_x, spawn_y = spawn_center
        default_identities = [
            ("Alpha", "female"),
            ("Albedo", "female"),
        ]
        for aid in range(self.num_agents):
            pos_x = spawn_x - aid
            pos_y = spawn_y
            # Ensure spawn is walkable
            if not self.is_walkable(pos_x, pos_y):
                self.grid[pos_y][pos_x] = TILE_GRASS

            name, gender = (
                default_identities[aid]
                if aid < len(default_identities)
                else (f"Agent_{aid}", "female")
            )

            body = AgentBody(
                agent_id=aid,
                name=name,
                gender=gender,
                x=pos_x,
                y=pos_y,
                facing=DIR_NORTH,
                holding=None,
                needs=Needs(
                    energy=self.config.max_energy,
                    water=self.config.max_water,
                    food=self.config.max_food,
                    health=self.config.max_health,
                ),
                alive=True,
                lives=1,
                spawn_pos=(pos_x, pos_y),
            )
            self.agents.append(body)

    def is_walkable(self, x: int, y: int) -> bool:
        """Check whether a tile coordinate is within bounds and can be traversed."""
        if not (0 <= x < self.config.width and 0 <= y < self.config.height):
            return False
        tile = self.grid[y][x]
        return tile != TILE_WATER and tile != TILE_TREE

    def is_adjacent_to_water(self, x: int, y: int) -> bool:
        """Check if coordinate is adjacent (Chebyshev distance 1) to any water tile."""
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if (x + dx, y + dy) in self.water_tiles:
                    return True
        return False

    def is_raining(self) -> bool:
        """Determine whether rain is falling this tick."""
        if not self.config.rain_enabled or self.config.rain_interval <= 0:
            return False
        cycle = self.tick_count % self.config.rain_interval
        return cycle < self.config.rain_duration

    def _add_ground_item(self, x: int, y: int, entity_id: int) -> None:
        coord = (x, y)
        if coord not in self.ground_items:
            self.ground_items[coord] = []
        self.ground_items[coord].append(Item(entity_id=entity_id, x=x, y=y))

    def get_observation(self, agent_id: int, events: Optional[List[int]] = None) -> Dict[str, Any]:
        """Generate local observation for a specific agent."""
        agent = self.agents[agent_id]
        return build_observation(
            tick=self.tick_count,
            agent=agent,
            grid=self.grid,
            width=self.config.width,
            height=self.config.height,
            plants=self.plants,
            ground_items=self.ground_items,
            all_agents=self.agents,
            events=events or [],
        )

    def tick(self, actions: Dict[int, int] | int) -> Dict[int, Dict[str, Any]]:
        """Advance world simulation by one tick.
        
        Accepts single action (for agent 0) or mapping agent_id -> action.
        Returns mapping agent_id -> Outcome dictionary.
        """
        if isinstance(actions, int):
            actions_map = {0: actions}
        else:
            actions_map = dict(actions)

        outcomes: Dict[int, Dict[str, Any]] = {}
        raining = self.is_raining()

        # 1. Process Actions for each agent
        for agent in self.agents:
            aid = agent.agent_id
            action = actions_map.get(aid, WAIT)
            events: List[int] = []
            prev_needs = agent.needs.copy()
            extra_energy_cost = 0.0

            if raining:
                events.append(EVENT_RAINED)

            # Resolve Action
            if action in MOVE_ACTION_DIRS:
                dx, dy = MOVE_ACTION_DIRS[action]
                agent.facing = (dx, dy)
                target_x = agent.x + dx
                target_y = agent.y + dy

                # Check if another living agent is at target
                occupied_by_agent = any(
                    a.agent_id != aid and a.alive and a.x == target_x and a.y == target_y
                    for a in self.agents
                )

                if self.is_walkable(target_x, target_y) and not occupied_by_agent:
                    agent.x = target_x
                    agent.y = target_y
                    events.append(EVENT_MOVED)
                    extra_energy_cost += self.config.move_energy_cost
                else:
                    events.append(EVENT_BLOCKED)
                    extra_energy_cost += self.config.move_energy_cost * 0.5

            elif action == PICK_UP:
                if agent.holding is not None:
                    events.append(EVENT_BLOCKED)
                else:
                    curr_loc = (agent.x, agent.y)
                    facing_loc = (agent.x + agent.facing[0], agent.y + agent.facing[1])
                    picked = False

                    # 1. Harvest ripe fruit from plant (facing tile first, then current tile)
                    for loc in [facing_loc, curr_loc]:
                        if loc in self.plants and self.plants[loc].has_fruit:
                            plant = self.plants[loc]
                            agent.holding = plant.fruit_type
                            plant.has_fruit = False
                            plant.wet_ticks = 0
                            events.append(EVENT_PICKED_UP)
                            picked = True
                            break

                    # 2. Pick up item from ground (current tile first, then facing tile)
                    if not picked:
                        for loc in [curr_loc, facing_loc]:
                            if loc in self.ground_items and self.ground_items[loc]:
                                item = self.ground_items[loc].pop()
                                if not self.ground_items[loc]:
                                    del self.ground_items[loc]
                                agent.holding = item.entity_id
                                events.append(EVENT_PICKED_UP)
                                picked = True
                                break

                    if not picked:
                        events.append(EVENT_BLOCKED)

            elif action == DROP:
                if agent.holding is None:
                    events.append(EVENT_BLOCKED)
                else:
                    item_id = agent.holding
                    agent.holding = None
                    self._add_ground_item(agent.x, agent.y, item_id)
                    events.append(EVENT_DROPPED)

            elif action == USE_ON_FACING:
                facing_x = agent.x + agent.facing[0]
                facing_y = agent.y + agent.facing[1]
                in_bounds = 0 <= facing_x < self.config.width and 0 <= facing_y < self.config.height

                # Prioritize facing tile; fallback to current tile
                target_candidates: List[Tuple[int, int]] = []
                if in_bounds:
                    target_candidates.append((facing_x, facing_y))
                target_candidates.append((agent.x, agent.y))

                used_success = False
                for tx, ty in target_candidates:
                    t_loc = (tx, ty)
                    # 1. Planting Seed on Soil
                    if (
                        agent.holding == ENTITY_SEED
                        and self.grid[ty][tx] == TILE_SOIL
                        and t_loc not in self.plants
                    ):
                        agent.holding = None
                        self.plants[t_loc] = Plant(
                            x=tx,
                            y=ty,
                            stage=ENTITY_SEEDLING,
                            wet_ticks=0,
                            has_fruit=False,
                            fruit_type=ENTITY_GOOD_FRUIT,
                        )
                        events.append(EVENT_USED_ITEM)
                        extra_energy_cost += self.config.use_energy_cost
                        used_success = True
                        break

                    # 2. Watering Soil/Plant with Full Container
                    elif (
                        agent.holding == ENTITY_WATER_CONTAINER_FULL
                        and self.grid[ty][tx] in (TILE_SOIL, TILE_GRASS)
                    ):
                        self.moisture[t_loc] = self.config.soil_drying_ticks
                        agent.holding = ENTITY_WATER_CONTAINER_EMPTY
                        events.append(EVENT_USED_ITEM)
                        extra_energy_cost += self.config.use_energy_cost
                        used_success = True
                        break

                    # 3. Filling Container from Water
                    elif (
                        agent.holding == ENTITY_WATER_CONTAINER_EMPTY
                        and self.grid[ty][tx] == TILE_WATER
                    ):
                        agent.holding = ENTITY_WATER_CONTAINER_FULL
                        events.append(EVENT_USED_ITEM)
                        extra_energy_cost += self.config.use_energy_cost
                        used_success = True
                        break

                if not used_success:
                    events.append(EVENT_BLOCKED)

            elif action == EAT:
                ate_success = False
                # 1. Holding Good Fruit
                if agent.holding == ENTITY_GOOD_FRUIT:
                    agent.holding = None
                    agent.needs.eat_good(
                        self.config.good_fruit_food,
                        self.config.good_fruit_energy,
                        self.config.max_food,
                        self.config.max_energy,
                    )
                    events.append(EVENT_ATE_FOOD)
                    ate_success = True
                # 2. Holding Poison Berry
                elif agent.holding == ENTITY_POISON_BERRY:
                    agent.holding = None
                    agent.needs.eat_poison(
                        self.config.poison_berry_food,
                        self.config.poison_berry_damage,
                        self.config.max_food,
                    )
                    events.append(EVENT_ATE_POISON)
                    events.append(EVENT_TOOK_DAMAGE)
                    ate_success = True
                # 3. Eating from ground if hands are empty
                elif agent.holding is None:
                    curr_loc = (agent.x, agent.y)
                    facing_loc = (agent.x + agent.facing[0], agent.y + agent.facing[1])
                    for loc in [curr_loc, facing_loc]:
                        if loc in self.ground_items:
                            for idx, itm in enumerate(self.ground_items[loc]):
                                if itm.entity_id == ENTITY_GOOD_FRUIT:
                                    self.ground_items[loc].pop(idx)
                                    if not self.ground_items[loc]:
                                        del self.ground_items[loc]
                                    agent.needs.eat_good(
                                        self.config.good_fruit_food,
                                        self.config.good_fruit_energy,
                                        self.config.max_food,
                                        self.config.max_energy,
                                    )
                                    events.append(EVENT_ATE_FOOD)
                                    ate_success = True
                                    break
                                elif itm.entity_id == ENTITY_POISON_BERRY:
                                    self.ground_items[loc].pop(idx)
                                    if not self.ground_items[loc]:
                                        del self.ground_items[loc]
                                    agent.needs.eat_poison(
                                        self.config.poison_berry_food,
                                        self.config.poison_berry_damage,
                                        self.config.max_food,
                                    )
                                    events.append(EVENT_ATE_POISON)
                                    events.append(EVENT_TOOK_DAMAGE)
                                    ate_success = True
                                    break
                        if ate_success:
                            break

                if not ate_success:
                    events.append(EVENT_BLOCKED)

            elif action == DRINK:
                facing_loc = (agent.x + agent.facing[0], agent.y + agent.facing[1])
                is_near_water = False

                # Check facing water or adjacent to water
                if (
                    0 <= facing_loc[0] < self.config.width
                    and 0 <= facing_loc[1] < self.config.height
                    and self.grid[facing_loc[1]][facing_loc[0]] == TILE_WATER
                ):
                    is_near_water = True
                elif self.is_adjacent_to_water(agent.x, agent.y):
                    is_near_water = True

                if is_near_water:
                    agent.needs.drink(self.config.drink_water_amount, self.config.max_water)
                    events.append(EVENT_DRANK_WATER)
                elif agent.holding == ENTITY_WATER_CONTAINER_FULL:
                    agent.needs.drink(self.config.drink_water_amount, self.config.max_water)
                    agent.holding = ENTITY_WATER_CONTAINER_EMPTY
                    events.append(EVENT_DRANK_WATER)
                else:
                    events.append(EVENT_BLOCKED)

            elif action == DIG:
                target_x = agent.x + agent.facing[0]
                target_y = agent.y + agent.facing[1]
                target_loc = (target_x, target_y)

                if not (0 <= target_x < self.config.width and 0 <= target_y < self.config.height):
                    target_x, target_y = agent.x, agent.y
                    target_loc = (target_x, target_y)

                if self.grid[target_y][target_x] == TILE_GRASS:
                    self.grid[target_y][target_x] = TILE_SOIL
                    events.append(EVENT_DUG_SOIL)
                    extra_energy_cost += self.config.dig_energy_cost

                    # Chance to unearth a seed
                    if self.rng.random() < self.config.dig_unearth_seed_prob:
                        self._add_ground_item(target_x, target_y, ENTITY_SEED)
                else:
                    events.append(EVENT_BLOCKED)

            elif action in SIGNAL_ACTIONS:
                agent.signal = action - SIGNAL_ACTIONS[0]
                extra_energy_cost += self.config.signal_energy_cost
            else:
                # WAIT or unknown
                agent.signal = None

            # Apply biological decay
            agent.needs.tick_decay(self.config, extra_energy_cost=extra_energy_cost)

            # Check for death & respawn loop
            alive_this_tick = True
            if agent.needs.is_dead():
                events.append(EVENT_DIED)
                alive_this_tick = False

                # Drop held item upon death
                if agent.holding is not None:
                    self._add_ground_item(agent.x, agent.y, agent.holding)
                    agent.holding = None

                # Respawn at designated spawn position
                agent.lives += 1
                agent.x, agent.y = agent.spawn_pos
                agent.needs.reset(self.config)
                events.append(EVENT_RESPAWNED)

            # Build outcome for this agent
            obs_next = self.get_observation(aid, events=events)
            need_delta = agent.needs.delta(prev_needs)

            outcomes[aid] = build_outcome(
                obs_next=obs_next,
                need_delta=need_delta,
                alive=alive_this_tick,
            )

        # 2. Ecosystem Dynamics (Moisture, Trees, Crops)
        # Soil moisture decay
        for loc in list(self.moisture.keys()):
            self.moisture[loc] -= 1
            if self.moisture[loc] <= 0:
                del self.moisture[loc]

        # Tree seed renewal
        if self.config.tree_seed_drop_prob > 0:
            for tx, ty in self.tree_tiles:
                if self.rng.random() < self.config.tree_seed_drop_prob:
                    # Choose a random adjacent walkable tile
                    dx = self.rng.choice([-1, 0, 1])
                    dy = self.rng.choice([-1, 0, 1])
                    nx, ny = tx + dx, ty + dy
                    if self.is_walkable(nx, ny):
                        self._add_ground_item(nx, ny, ENTITY_SEED)

        # Plant growth lifecycle
        for loc, plant in list(self.plants.items()):
            px, py = loc
            is_wet = (
                raining
                or (loc in self.moisture and self.moisture[loc] > 0)
                or (self.config.adjacent_water_irrigates and self.is_adjacent_to_water(px, py))
            )

            if is_wet:
                if plant.stage == ENTITY_SEEDLING:
                    plant.wet_ticks += 1
                    if plant.wet_ticks >= self.config.seedling_growth_ticks:
                        plant.stage = ENTITY_MATURE_PLANT
                        plant.wet_ticks = 0
                elif plant.stage == ENTITY_MATURE_PLANT and not plant.has_fruit:
                    plant.wet_ticks += 1
                    if plant.wet_ticks >= self.config.fruit_yield_ticks:
                        plant.has_fruit = True

        self.tick_count += 1
        return outcomes
