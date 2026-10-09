"""ASCII Debug Visualizer for ALC.

Strict rule: Viewer is dumb. It displays simulation events/state.
Can be executed directly via: python -m sim.render_ascii
"""

import argparse
import sys
import time
from typing import Optional

from sim.actions import (
    DIR_EAST,
    DIR_NORTH,
    DIR_SOUTH,
    DIR_WEST,
    DRINK,
    MOVE_N,
    MOVE_S,
    MOVE_E,
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
    ENTITY_WATER_CONTAINER_EMPTY,
    ENTITY_WATER_CONTAINER_FULL,
    TILE_GRASS,
    TILE_SOIL,
    TILE_TREE,
    TILE_WATER,
)
from sim.world import World

TILE_GLYPHS = {
    TILE_GRASS: ".",
    TILE_SOIL: ",",
    TILE_WATER: "~",
    TILE_TREE: "#",
}

ENTITY_GLYPHS = {
    ENTITY_SEED: "*",
    ENTITY_SEEDLING: "i",
    ENTITY_MATURE_PLANT: "Y",
    ENTITY_GOOD_FRUIT: "o",
    ENTITY_POISON_BERRY: "x",
    ENTITY_WATER_CONTAINER_EMPTY: "u",
    ENTITY_WATER_CONTAINER_FULL: "w",
}

FACING_GLYPHS = {
    DIR_NORTH: "^",
    DIR_SOUTH: "v",
    DIR_EAST: ">",
    DIR_WEST: "<",
}


def render_world_ascii(world: World, agent_id: int = 0) -> str:
    """Render the full 32x32 world and agent status to an ASCII string."""
    agent = world.agents[agent_id]
    lines = []

    # Header / Status HUD
    rain_str = "[RAINING]" if world.is_raining() else "[CLEAR]"
    lines.append("=" * 66)
    lines.append(
        f" ALC WORLD | Tick: {world.tick_count:04d} | Weather: {rain_str} | {agent.name} ({agent.gender}) | Life #{agent.lives}"
    )
    lines.append(
        f" Energy: {agent.needs.energy:5.1f}/100 | Water: {agent.needs.water:5.1f}/100 | "
        f" Food: {agent.needs.food:5.1f}/100 | Health: {agent.needs.health:5.1f}/100"
    )
    holding_name = (
        ENTITY_GLYPHS.get(agent.holding, f"ID:{agent.holding}")
        if agent.holding is not None
        else "NONE"
    )
    facing_glyph = FACING_GLYPHS.get(agent.facing, "?")
    lines.append(
        f" Agent Pos: ({agent.x:02d}, {agent.y:02d}) | Facing: {facing_glyph} | Holding: {holding_name}"
    )
    lines.append("-" * 66)

    # 32x32 Grid Rendering
    other_agents = {a.agent_id: (a.x, a.y, a.name) for a in world.agents if a.alive}
    my_initial = agent.name[0].upper()

    for y in range(world.config.height):
        row_chars = []
        for x in range(world.config.width):
            coord = (x, y)

            # 1. Main agent
            if (x, y) == (agent.x, agent.y):
                row_chars.append(f"{my_initial}{facing_glyph}")
                continue

            # 2. Other agents (e.g. Albedo 'B' or 'A')
            agent_here = False
            for o_aid, (ox, oy, oname) in other_agents.items():
                if o_aid != agent_id and (ox, oy) == (x, y):
                    initial = oname[0].upper()
                    row_chars.append(f"{initial} ")
                    agent_here = True
                    break
            if agent_here:
                continue

            # 3. Plants
            if coord in world.plants:
                plant = world.plants[coord]
                if plant.stage == ENTITY_SEEDLING:
                    row_chars.append("i ")
                elif plant.has_fruit:
                    if plant.fruit_type == ENTITY_GOOD_FRUIT:
                        row_chars.append("F ")
                    else:
                        row_chars.append("X ")
                else:
                    row_chars.append("Y ")
                continue

            # 4. Ground Items
            if coord in world.ground_items and world.ground_items[coord]:
                top_item = world.ground_items[coord][-1]
                glyph = ENTITY_GLYPHS.get(top_item.entity_id, "?")
                row_chars.append(f"{glyph} ")
                continue

            # 5. Terrain
            tile_type = world.grid[y][x]
            glyph = TILE_GLYPHS.get(tile_type, "?")
            row_chars.append(f"{glyph} ")

        lines.append("".join(row_chars))

    lines.append("-" * 66)
    lines.append(
        " Legend: A=Alpha, B=Albedo, #=Tree, ~=Water, .=Grass, ,=Soil, *=Seed, i=Seedling, Y=Plant, F=Fruit"
    )
    lines.append("=" * 66)
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="ALC ASCII Terminal Viewer")
    parser.add_argument("--ticks", type=int, default=30, help="Number of ticks to run")
    parser.add_argument("--seed", type=int, default=42, help="World seed")
    parser.add_argument("--delay", type=float, default=0.1, help="Delay between ticks (sec)")
    args = parser.parse_args()

    config = WorldConfig(seed=args.seed)
    world = World(config=config, num_agents=1)

    print(render_world_ascii(world))

    # Demo run with simple wandering and actions
    actions_cycle = [
        MOVE_E,
        MOVE_E,
        DRINK,
        PICK_UP,
        MOVE_S,
        USE_ON_FACING,
        WAIT,
        MOVE_W,
        WAIT,
    ]

    for t in range(args.ticks):
        time.sleep(args.delay)
        action = actions_cycle[t % len(actions_cycle)]
        world.tick(action)
        # Clear screen / carriage return or reprint
        print(f"\n--- TICK {world.tick_count} ---")
        print(render_world_ascii(world))


if __name__ == "__main__":
    main()
