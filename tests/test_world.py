"""Unit tests for ALC simulation engine rules, needs, and determinism."""

import pytest
from sim.actions import (
    DIR_EAST,
    DIR_NORTH,
    DIR_SOUTH,
    DIR_WEST,
    DRINK,
    DROP,
    EAT,
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
    ENTITY_MATURE_PLANT,
    ENTITY_POISON_BERRY,
    ENTITY_SEED,
    ENTITY_SEEDLING,
    EVENT_ATE_FOOD,
    EVENT_ATE_POISON,
    EVENT_BLOCKED,
    EVENT_DIED,
    EVENT_DRANK_WATER,
    EVENT_RESPAWNED,
    EVENT_TOOK_DAMAGE,
    EVENT_USED_ITEM,
    Plant,
    TILE_GRASS,
    TILE_SOIL,
    TILE_WATER,
)
from sim.world import World


def test_planting_needs_seed_on_soil():
    """Verify planting strictly requires holding a seed and facing a soil tile."""
    config = WorldConfig(seed=123, rain_enabled=False)
    world = World(config=config, num_agents=1)
    agent = world.agents[0]

    # Setup facing tile as GRASS
    fx, fy = agent.x + agent.facing[0], agent.y + agent.facing[1]
    world.grid[fy][fx] = TILE_GRASS
    agent.holding = ENTITY_SEED

    # 1. Attempt planting on GRASS -> Should fail / be blocked
    outcomes = world.tick(USE_ON_FACING)
    assert EVENT_BLOCKED in outcomes[0]["obs_next"]["events"]
    assert (fx, fy) not in world.plants
    assert agent.holding == ENTITY_SEED

    # 2. Convert facing tile to SOIL, empty hand -> Should fail / blocked
    world.grid[fy][fx] = TILE_SOIL
    agent.holding = None
    outcomes = world.tick(USE_ON_FACING)
    assert EVENT_BLOCKED in outcomes[0]["obs_next"]["events"]
    assert (fx, fy) not in world.plants

    # 3. Holding SEED and facing SOIL -> Planting succeeds!
    agent.holding = ENTITY_SEED
    outcomes = world.tick(USE_ON_FACING)
    assert EVENT_USED_ITEM in outcomes[0]["obs_next"]["events"]
    assert (fx, fy) in world.plants
    assert world.plants[(fx, fy)].stage == ENTITY_SEEDLING
    assert agent.holding is None


def test_growth_needs_water():
    """Verify that seedlings only mature and produce fruit when exposed to water/moisture."""
    config = WorldConfig(
        seed=123,
        rain_enabled=False,
        seedling_growth_ticks=5,
        fruit_yield_ticks=5,
        adjacent_water_irrigates=False,
    )
    world = World(config=config, num_agents=1)

    # Place a seedling on an isolated dry soil tile
    dry_x, dry_y = 5, 5
    world.grid[dry_y][dry_x] = TILE_SOIL
    plant_dry = Plant(x=dry_x, y=dry_y, stage=ENTITY_SEEDLING, wet_ticks=0)
    world.plants[(dry_x, dry_y)] = plant_dry

    # Tick 10 times without water
    for _ in range(10):
        world.tick(WAIT)

    assert plant_dry.stage == ENTITY_SEEDLING
    assert plant_dry.wet_ticks == 0

    # Now add moisture to the tile
    world.moisture[(dry_x, dry_y)] = 20

    # Tick 5 times -> should mature
    for _ in range(5):
        world.tick(WAIT)

    assert plant_dry.stage == ENTITY_MATURE_PLANT
    assert not plant_dry.has_fruit

    # Tick another 5 times with moisture remaining -> should yield fruit
    for _ in range(5):
        world.tick(WAIT)

    assert plant_dry.has_fruit is True
    assert plant_dry.fruit_type == ENTITY_GOOD_FRUIT


def test_eating_raises_food_and_energy():
    """Verify eating good fruit replenishes food and energy."""
    config = WorldConfig(seed=42, good_fruit_food=40.0, good_fruit_energy=20.0)
    world = World(config=config, num_agents=1)
    agent = world.agents[0]

    agent.needs.food = 30.0
    agent.needs.energy = 40.0
    agent.holding = ENTITY_GOOD_FRUIT

    outcomes = world.tick(EAT)
    assert EVENT_ATE_FOOD in outcomes[0]["obs_next"]["events"]
    assert agent.holding is None
    # Food and energy should have increased significantly (accounting for 1-tick decay)
    assert agent.needs.food > 65.0
    assert agent.needs.energy > 55.0


def test_poison_berry_lowers_health():
    """Verify consuming toxic berries depletes health and triggers poison event."""
    config = WorldConfig(seed=42, poison_berry_damage=35.0)
    world = World(config=config, num_agents=1)
    agent = world.agents[0]

    initial_health = agent.needs.health
    agent.holding = ENTITY_POISON_BERRY

    outcomes = world.tick(EAT)
    assert EVENT_ATE_POISON in outcomes[0]["obs_next"]["events"]
    assert EVENT_TOOK_DAMAGE in outcomes[0]["obs_next"]["events"]
    assert agent.holding is None
    assert agent.needs.health <= initial_health - 34.0


def test_needs_decay():
    """Verify natural decay of energy, water, and food over ticks."""
    config = WorldConfig(
        seed=42,
        energy_decay=0.1,
        water_decay=0.2,
        food_decay=0.15,
        rain_enabled=False,
    )
    world = World(config=config, num_agents=1)
    agent = world.agents[0]

    initial_energy = agent.needs.energy
    initial_water = agent.needs.water
    initial_food = agent.needs.food

    ticks = 10
    for _ in range(ticks):
        world.tick(WAIT)

    assert agent.needs.energy < initial_energy
    assert agent.needs.water < initial_water
    assert agent.needs.food < initial_food
    assert round(agent.needs.water, 1) == round(initial_water - (config.water_decay * ticks), 1)


def test_death_triggers_respawn():
    """Verify health exhaustion triggers death event, increments life counter, and respawns."""
    config = WorldConfig(seed=42, dehydration_damage=50.0, rain_enabled=False)
    world = World(config=config, num_agents=1)
    agent = world.agents[0]

    # Move agent away from spawn
    agent.x, agent.y = 2, 2
    agent.needs.health = 20.0
    agent.needs.water = 0.0  # Dehydration causes 50 damage -> fatal

    outcomes = world.tick(WAIT)
    # Outcome for this tick reports alive=False and death/respawn events
    assert outcomes[0]["alive"] is False
    assert EVENT_DIED in outcomes[0]["obs_next"]["events"]
    assert EVENT_RESPAWNED in outcomes[0]["obs_next"]["events"]

    # Agent is respawned at spawn position with refreshed needs
    assert agent.lives == 2
    assert (agent.x, agent.y) == agent.spawn_pos
    assert agent.needs.health == config.max_health
    assert agent.needs.water == config.max_water


def test_determinism_same_seed_1000_ticks():
    """Verify identical master seeds produce byte-for-byte identical simulations over 1,000 ticks."""
    seed = 88888
    ticks = 1000
    config1 = WorldConfig(seed=seed)
    config2 = WorldConfig(seed=seed)

    world1 = World(config=config1, num_agents=1)
    world2 = World(config=config2, num_agents=1)

    # Use a fixed pseudo-random action script
    action_seq = [
        MOVE_N, MOVE_E, MOVE_S, MOVE_W,
        WAIT, PICK_UP, USE_ON_FACING, EAT,
        DRINK, WAIT, MOVE_E, MOVE_E,
    ]

    for t in range(ticks):
        act = action_seq[t % len(action_seq)]
        out1 = world1.tick(act)
        out2 = world2.tick(act)
        assert out1 == out2

    # Verify deep world state equality
    assert world1.grid == world2.grid
    assert world1.plants == world2.plants
    assert world1.ground_items == world2.ground_items
    assert world1.moisture == world2.moisture

    a1 = world1.agents[0]
    a2 = world2.agents[0]
    assert (a1.x, a1.y) == (a2.x, a2.y)
    assert a1.facing == a2.facing
    assert a1.holding == a2.holding
    assert a1.lives == a2.lives
    assert a1.needs.to_dict() == a2.needs.to_dict()
