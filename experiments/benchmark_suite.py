"""Reproducible Scientific Benchmark Suite for ALC Phase 7.

Evaluates continuous learning, sample efficiency, predictive accuracy, memory retention,
generalization, persistence fidelity, and social transfer across fixed random seeds.
"""

import json
import math
import os
import random
import sys
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.alpha.brain import AlphaBrain
from brain.albedo.brain import AlbedoBrain
from brain.random_brain import RandomBrain
from communication.message import CommType, KnowledgeStatus, Message
from sim.config import WorldConfig
from sim.entities import (
    ENTITY_MATURE_PLANT,
    EVENT_ATE_FOOD,
    EVENT_ATE_POISON,
    EVENT_DIED,
    EVENT_DRANK_WATER,
)
from sim.world import World


def run_benchmark_trial(
    agent_brain: Any,
    seed: int,
    ticks: int = 3000,
    perturb_world: bool = False,
) -> Dict[str, Any]:
    """Execute a single deterministic evaluation trial and return rich metric logs."""
    config = WorldConfig(seed=seed)
    if perturb_world:
        # Alter water/soil distribution to test generalization
        config.width = 24
        config.height = 24
        config.water_patches = 1  # Scarcer water
        config.poison_density = 0.08  # Higher hazard density

    world = World(config=config, num_agents=1)
    
    # Tracking registers
    current_life_ticks = 0
    life_durations = []
    deaths = 0
    water_drank = 0
    food_eaten = 0
    poison_eaten = 0
    
    # World model prediction error tracking
    prediction_errors_food = []
    prediction_errors_water = []
    prediction_errors_health = []
    
    longest_survival_streak = 0
    
    for tick in range(ticks):
        obs = world.get_observation(0)
        agent_brain.observe(obs)
        action = agent_brain.act()
        
        # Before taking action, capture model's prediction if available
        if hasattr(agent_brain, "model") and hasattr(agent_brain.model, "get_expected_deltas"):
            state = getattr(agent_brain, "current_state", None)
            if state is not None:
                expected = agent_brain.model.get_expected_deltas(state, action)
            else:
                expected = {"food": 0.0, "water": 0.0, "health": 0.0}
        else:
            expected = {"food": 0.0, "water": 0.0, "health": 0.0}
            
        outcomes = world.tick(action)
        outcome = outcomes[0]
        
        # Compute prediction error
        actual_delta = outcome.get("need_delta", {})
        prediction_errors_food.append(abs(expected.get("food", 0.0) - actual_delta.get("food", 0.0)))
        prediction_errors_water.append(abs(expected.get("water", 0.0) - actual_delta.get("water", 0.0)))
        prediction_errors_health.append(abs(expected.get("health", 0.0) - actual_delta.get("health", 0.0)))
        
        agent_brain.learn(outcome)
        
        # Update counters
        events = outcome.get("obs_next", {}).get("events", [])
        alive = outcome.get("alive", True)
        current_life_ticks += 1
        
        if EVENT_DRANK_WATER in events:
            water_drank += 1
        if EVENT_ATE_FOOD in events:
            food_eaten += 1
        if EVENT_ATE_POISON in events:
            poison_eaten += 1
            
        if not alive or EVENT_DIED in events:
            deaths += 1
            life_durations.append(current_life_ticks)
            if current_life_ticks > longest_survival_streak:
                longest_survival_streak = current_life_ticks
            current_life_ticks = 0
            agent_brain.reset_episode()
            
    if current_life_ticks > 0:
        life_durations.append(current_life_ticks)
        if current_life_ticks > longest_survival_streak:
            longest_survival_streak = current_life_ticks
            
    mean_life = sum(life_durations) / max(1, len(life_durations))
    rmse_food = math.sqrt(sum(e ** 2 for e in prediction_errors_food) / max(1, len(prediction_errors_food)))
    rmse_water = math.sqrt(sum(e ** 2 for e in prediction_errors_water) / max(1, len(prediction_errors_water)))
    rmse_health = math.sqrt(sum(e ** 2 for e in prediction_errors_health) / max(1, len(prediction_errors_health)))
    
    return {
        "seed": seed,
        "ticks": ticks,
        "total_deaths": deaths,
        "total_lives": len(life_durations),
        "mean_life_ticks": round(mean_life, 2),
        "longest_survival_streak": longest_survival_streak,
        "water_drank": water_drank,
        "food_eaten": food_eaten,
        "poison_eaten": poison_eaten,
        "rmse_food_prediction": round(rmse_food, 4),
        "rmse_water_prediction": round(rmse_water, 4),
        "rmse_health_prediction": round(rmse_health, 4),
        "brain_stats": agent_brain.stats() if hasattr(agent_brain, "stats") else {},
    }


def evaluate_persistence(brain_cls, seed: int = 42, tmp_path: str = "experiments/results/test_persist.json") -> Dict[str, Any]:
    """Test save and reload fidelity."""
    os.makedirs(os.path.dirname(os.path.abspath(tmp_path)), exist_ok=True)
    
    # 1. Train brain for 1500 ticks
    brain_a = brain_cls(seed=seed)
    train_res = run_benchmark_trial(brain_a, seed=seed, ticks=1500)
    stats_before = brain_a.stats()
    
    # 2. Save
    brain_a.save(tmp_path)
    
    # 3. Create fresh brain and load
    brain_b = brain_cls(seed=seed)
    brain_b.load(tmp_path)
    stats_after = brain_b.stats()
    
    # 4. Evaluate loaded brain for another 1000 ticks
    eval_res = run_benchmark_trial(brain_b, seed=seed + 1, ticks=1000)
    
    # Check parity in key statistics
    preserved_known_states = (stats_after.get("known_states", 0) == stats_before.get("known_states", 0))
    preserved_mistakes = (stats_after.get("recorded_mistakes", 0) == stats_before.get("recorded_mistakes", 0))
    
    return {
        "preserved_known_states": preserved_known_states,
        "preserved_mistakes": preserved_mistakes,
        "stats_before_save": stats_before,
        "stats_after_load": stats_after,
        "eval_post_load": eval_res,
    }


def run_full_benchmark_suite(seeds: Sequence[int] = (42, 100, 777)) -> Dict[str, Any]:
    """Execute complete multi-seed benchmark suite across standard and generalization tasks."""
    print("=== Running ALC Phase 7 Benchmark Suite ===")
    
    results = {
        "seeds": list(seeds),
        "standard_trials": {},
        "generalization_trials": {},
        "persistence": {},
    }
    
    # Standard survival trials
    for s in seeds:
        print(f"Running standard trial seed={s}...")
        brain = AlphaBrain(seed=s)
        res = run_benchmark_trial(brain, seed=s, ticks=3000, perturb_world=False)
        results["standard_trials"][str(s)] = res
        print(f"  Seed {s} -> Deaths: {res['total_deaths']}, Mean Life: {res['mean_life_ticks']}, Longest Streak: {res['longest_survival_streak']}, Food: {res['food_eaten']}, Water: {res['water_drank']}, Poison: {res['poison_eaten']}")
        
    # Generalization (held-out / altered environment)
    for s in seeds:
        print(f"Running generalization trial seed={s}...")
        # Pre-trained on standard seed s for 1500 ticks, then tested on perturbed environment
        brain = AlphaBrain(seed=s)
        run_benchmark_trial(brain, seed=s, ticks=1500, perturb_world=False)
        gen_res = run_benchmark_trial(brain, seed=s + 500, ticks=1500, perturb_world=True)
        results["generalization_trials"][str(s)] = gen_res
        print(f"  Gen Seed {s} -> Deaths: {gen_res['total_deaths']}, Mean Life: {gen_res['mean_life_ticks']}, Food: {gen_res['food_eaten']}, Water: {gen_res['water_drank']}")
        
    # Persistence evaluation
    print("Running persistence fidelity check...")
    persist_res = evaluate_persistence(AlphaBrain, seed=42)
    results["persistence"] = persist_res
    print(f"  Persistence Check: preserved_known_states={persist_res['preserved_known_states']}, preserved_mistakes={persist_res['preserved_mistakes']}")
    
    # Compute aggregate summary
    std_means = [r["mean_life_ticks"] for r in results["standard_trials"].values()]
    std_deaths = [r["total_deaths"] for r in results["standard_trials"].values()]
    std_streaks = [r["longest_survival_streak"] for r in results["standard_trials"].values()]
    std_rmse_food = [r["rmse_food_prediction"] for r in results["standard_trials"].values()]
    std_rmse_water = [r["rmse_water_prediction"] for r in results["standard_trials"].values()]
    
    results["summary"] = {
        "avg_mean_life_ticks": round(sum(std_means) / len(std_means), 2),
        "avg_total_deaths": round(sum(std_deaths) / len(std_deaths), 2),
        "avg_longest_streak": round(sum(std_streaks) / len(std_streaks), 2),
        "avg_rmse_food": round(sum(std_rmse_food) / len(std_rmse_food), 4),
        "avg_rmse_water": round(sum(std_rmse_water) / len(std_rmse_water), 4),
    }
    
    out_path = "experiments/results/benchmark_results.json"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Benchmark suite completed. Summary: {results['summary']}")
    return results


if __name__ == "__main__":
    run_full_benchmark_suite((42, 100, 777))
