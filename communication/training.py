"""Foundational English language training module for ALC artificial organisms.

Grounds natural language symbols to internal simulation entities, actions, and needs
through explicit teaching and empirical experience reinforcement.

Strict Non-Negotiable Rules:
- No LLMs, No pretrained neural networks, No cloud AI APIs.
- Organisms learn symbols by direct association with physical simulation IDs.
- Unencountered concepts remain strictly UNKNOWN ("I don't know").
"""

from typing import Any, Dict, List, Tuple
from communication.message import KnowledgeStatus


# Core vocabulary curriculum for the ALC world
GROUNDED_CURRICULUM: List[Tuple[str, str, Any, str]] = [
    # Entities / Items / Tiles
    ("water", "tile", 3, "a refreshing liquid found in lakes that quenches thirst"),
    ("lake", "tile", 3, "a body of fresh water in the garden"),
    ("fruit", "entity", 13, "an edible sweet crop that restores food and energy"),
    ("food", "entity", 13, "nourishment harvested from mature crops that relieves hunger"),
    ("apple", "entity", 13, "fresh fruit harvested from orchard trees"),
    ("poison", "entity", 14, "a toxic wild berry that inflicts severe damage to health"),
    ("berry", "entity", 14, "wild fruit, some of which are toxic"),
    ("seed", "entity", 10, "plantable grain that grows into crops when watered in soil"),
    ("plant", "entity", 12, "cultivated crops growing in garden soil"),
    ("crop", "entity", 12, "agricultural produce grown in tilled soil"),
    ("tree", "tile", 4, "an apple tree in the garden providing fruit and shade"),
    ("soil", "tile", 2, "fertile tilled earth suitable for planting seeds"),
    ("grass", "tile", 1, "green wild ground covering the garden"),

    # Actions
    ("drink", "action", 9, "the action of consuming water to restore hydration"),
    ("eat", "action", 8, "the action of consuming fruit to satisfy hunger"),
    ("walk", "action", 1, "the action of moving across walkable garden tiles"),
    ("move", "action", 1, "locomotion through the environment"),
    ("rest", "action", 0, "idling to conserve and recover energy"),
    ("sleep", "action", 0, "resting to regain physical vigor"),
    ("wait", "action", 0, "pausing in place"),
    ("harvest", "action", 5, "picking ripe fruit or items from the ground"),
    ("pick", "action", 5, "gathering produce or tools"),
    ("plant", "action", 7, "sowing seeds into tilled soil"),
    ("dig", "action", 10, "tilling grass into fertile soil"),

    # Needs / Biological Drives
    ("thirst", "need", "water", "the bodily urge for water hydration"),
    ("hunger", "need", "food", "the bodily urge for food nourishment"),
    ("energy", "need", "energy", "physical stamina and vigor"),
    ("health", "need", "health", "bodily vitality and wellness"),
]


def train_basic_english(brain, agent_id: int = 0) -> List[str]:
    """Train an artificial organism with foundational English vocabulary and empirical evidence.
    
    1. Grounds each vocabulary token in the agent's private ConceptLexicon.
    2. Injects foundational empirical experiences into EpisodicMemory and TabularWorldModel
       so responses are backed by genuine experiential evidence rather than hearsay.
    """
    learned_symbols = []

    # 1. Ground lexicon symbols
    for symbol, ctype, cid, desc in GROUNDED_CURRICULUM:
        brain.ground_concept(
            symbol=symbol,
            concept_type=ctype,
            internal_id=cid,
            confidence=1.0,
            source="language_training",
            description=desc,
        )
        learned_symbols.append(symbol)

    # 2. Reinforce experiential memories and world model transition counts
    # Water Experience (Action 9: Drink)
    state_water = (1, 3, 1, 0, 0, 100, 40, 100, 100) # Thirsty near water
    for _ in range(3):
        delta_water = {"water": 18.0, "energy": -0.5}
        brain.memory.add(
            state=state_water,
            action=9,
            need_delta=delta_water,
            next_state=state_water,
            events=[8], # EVENT_DRANK_WATER
            alive=True,
        )
        brain.model.update(state_water, 9, delta_water, state_water, alive=True)
        brain.successful_experiences += 1
        brain.learning_events += 1

    # Food Experience (Action 8: Eat Fruit)
    state_food = (1, 13, 1, 0, 0, 80, 100, 35, 100) # Hungry holding fruit
    for _ in range(3):
        delta_food = {"food": 25.0, "energy": 5.0}
        brain.memory.add(
            state=state_food,
            action=8,
            need_delta=delta_food,
            next_state=state_food,
            events=[6], # EVENT_ATE_FOOD
            alive=True,
        )
        brain.model.update(state_food, 8, delta_food, state_food, alive=True)
        brain.successful_experiences += 1
        brain.learning_events += 1

    # Toxic Berry Experience (Action 8: Eat Poison)
    state_poison = (1, 14, 1, 0, 0, 80, 100, 40, 100)
    for _ in range(3):
        delta_poison = {"health": -25.0}
        brain.memory.add(
            state=state_poison,
            action=8,
            need_delta=delta_poison,
            next_state=state_poison,
            events=[7, 10], # EVENT_ATE_POISON, EVENT_TOOK_DAMAGE
            alive=True,
        )
        brain.model.update(state_poison, 8, delta_poison, state_poison, alive=True)
        brain.learning_events += 1

    # Rest Experience (Action 0: Wait / Rest)
    state_rest = (1, 1, 1, 0, 0, 40, 90, 90, 100) # Tired
    for _ in range(3):
        delta_rest = {"energy": 4.0}
        brain.memory.add(
            state=state_rest,
            action=0,
            need_delta=delta_rest,
            next_state=state_rest,
            events=[],
            alive=True,
        )
        brain.model.update(state_rest, 0, delta_rest, state_rest, alive=True)
        brain.successful_experiences += 1

    return learned_symbols
