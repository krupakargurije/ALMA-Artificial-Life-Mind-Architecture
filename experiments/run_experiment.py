"""Experiment runner CLI and harness for ALC.

Strict Rule: Everything is seeded, reproducible, and logged.
No solution-encoding reward shaping; brain receives only opaque observations.
"""

import argparse
import json
import os
import sys
import uuid
from typing import Any, Dict, List, Optional

from brain.random_brain import RandomBrain
from brain.alpha.brain import AlphaBrain
from brain.albedo.brain import AlbedoBrain
from experiments.logger import ExperimentLogger
from experiments.metrics import MetricsTracker
from sim.config import WorldConfig
from sim.world import World


def create_agent(agent_type: str, seed: int, world: Optional[World] = None) -> Any:
    """Instantiate agent brain."""
    if agent_type == "random":
        return RandomBrain(seed=seed)
    elif agent_type == "alpha" or agent_type == "learner_v1":
        return AlphaBrain(seed=seed)
    elif agent_type in ("albedo", "roselia"):
        return AlbedoBrain(seed=seed)
    elif agent_type == "oracle":
        from tests.test_oracle import ScriptedOracle
        if world is None:
            raise ValueError("World must be provided for oracle agent.")
        return ScriptedOracle(world, agent_id=0)
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")


def run_single_experiment(
    config: Optional[WorldConfig] = None,
    seed: int = 42,
    agent_type: str = "random",
    ticks: int = 5000,
    db_path: str = "experiments/results/run.sqlite",
    replay_path: Optional[str] = None,
    logger: Optional[ExperimentLogger] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a single deterministic experiment run."""
    run_config = config or WorldConfig(seed=seed)
    run_config.seed = seed

    run_id = run_id or f"run_{agent_type}_{seed}_{uuid.uuid4().hex[:8]}"
    world = World(config=run_config, num_agents=1)
    agent = create_agent(agent_type=agent_type, seed=seed, world=world)

    should_close_logger = False
    if logger is None:
        logger = ExperimentLogger(db_path=db_path)
        should_close_logger = True

    logger.start_run(
        run_id=run_id,
        seed=seed,
        agent_type=agent_type,
        config_dict=run_config.to_dict(),
    )

    metrics = MetricsTracker(agent_id=0)
    current_life = 1
    life_start_tick = 0

    for tick in range(ticks):
        # 1. Observation
        obs = world.get_observation(0)

        # 2. Action selection
        if agent_type == "oracle":
            action = agent.choose_action()
            brain_stats = {}
            obs_hash = 0
        else:
            agent.observe(obs)
            action = agent.act()
            brain_stats = agent.stats()
            obs_hash = agent._hash_obs_view(obs)

        # 3. Environment Step
        outcomes = world.tick(action)
        outcome = outcomes[0]

        # 4. Learning & Metrics
        if agent_type != "oracle":
            agent.learn(outcome)

        metrics.record_step(
            world=world,
            action=action,
            outcome=outcome,
            obs_hash=obs_hash,
        )

        # 5. Logging
        logger.log_step(
            run_id=run_id,
            tick=tick,
            agent_id=0,
            action=action,
            obs=obs,
            outcome=outcome,
            brain_stats=brain_stats,
            record_replay_frame=(replay_path is not None),
        )

        # 6. Death / Respawn transition
        if not outcome["alive"]:
            ticks_survived = tick - life_start_tick + 1
            logger.log_life(
                run_id=run_id,
                life_number=current_life,
                start_tick=life_start_tick,
                end_tick=tick,
                ticks_survived=ticks_survived,
            )
            current_life += 1
            life_start_tick = tick + 1
            if agent_type != "oracle":
                agent.reset_episode()

    # Finalize remaining life if still alive
    if current_life == 1 or life_start_tick < ticks:
        ticks_survived = ticks - life_start_tick
        logger.log_life(
            run_id=run_id,
            life_number=current_life,
            start_tick=life_start_tick,
            end_tick=ticks - 1,
            ticks_survived=ticks_survived,
            cause_of_death="run_completed",
        )

    metrics_result = metrics.finalize()
    metrics_result["seed"] = seed
    metrics_result["agent_type"] = agent_type
    metrics_result["run_id"] = run_id

    logger.end_run(run_id=run_id, total_ticks=ticks, metrics_dict=metrics_result)

    if replay_path is not None:
        logger.export_replay(
            replay_path=replay_path,
            metadata={
                "run_id": run_id,
                "seed": seed,
                "agent_type": agent_type,
                "total_ticks": ticks,
                "metrics": metrics_result,
            },
        )

    if should_close_logger:
        logger.close()

    return metrics_result


def parse_args(args=None):
    parser = argparse.ArgumentParser(
        description="Artificial Learning Civilization (ALC) Experiment Runner",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        default="default",
        help="Path to world configuration JSON or 'default'",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Master random seed for reproducibility",
    )
    parser.add_argument(
        "--agent",
        type=str,
        default="alpha",
        choices=["random", "alpha", "roselia", "learner_v1", "oracle"],
        help="Agent brain implementation to run (Alpha or Roselia)",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=5000,
        help="Number of simulation ticks to run",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="experiments/results/run.sqlite",
        help="SQLite file path to record simulation logs and metrics",
    )
    parser.add_argument(
        "--replay",
        type=str,
        default=None,
        help="Optional path to export replay JSON",
    )
    parser.add_argument(
        "--batch-seeds",
        type=int,
        default=None,
        help="Run N consecutive seeds starting from --seed",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run simulation headless without visualization",
    )
    return parser.parse_args(args)


def main():
    args = parse_args()
    config = None
    if args.config != "default" and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            config = WorldConfig.from_dict(json.load(f))

    if args.batch_seeds:
        print(f"Executing batch of {args.batch_seeds} runs for agent='{args.agent}' starting from seed {args.seed}...")
        logger = ExperimentLogger(db_path=args.output)
        results = []
        for s in range(args.seed, args.seed + args.batch_seeds):
            replay_p = f"experiments/results/replays/run_{s}.json" if args.replay else None
            res = run_single_experiment(
                config=config,
                seed=s,
                agent_type=args.agent,
                ticks=args.ticks,
                db_path=args.output,
                replay_path=replay_p,
                logger=logger,
            )
            print(f" Seed {s:3d} | Deaths: {res['total_deaths']:3d} | Mean Ticks/Life: {res['ticks_per_life_mean']:6.1f} | Food Eaten: {res['food_eaten']}")
            results.append(res)
        logger.close()
        print(f"Batch completed. Results saved to {args.output}")
        return 0

    print(f"Executing ALC experiment: agent='{args.agent}', seed={args.seed}, ticks={args.ticks}")
    metrics = run_single_experiment(
        config=config,
        seed=args.seed,
        agent_type=args.agent,
        ticks=args.ticks,
        db_path=args.output,
        replay_path=args.replay,
    )
    print("\n--- Experiment Summary ---")
    print(json.dumps(metrics, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
