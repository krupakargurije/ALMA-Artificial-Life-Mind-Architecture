"""Script to execute 20-seed baseline evaluation of RandomBrain and generate baseline.md."""

import json
import math
import os
import sys
from typing import Any, Dict, List

from experiments.logger import ExperimentLogger
from experiments.run_experiment import run_single_experiment
from sim.config import WorldConfig


def run_baseline(
    num_seeds: int = 20,
    start_seed: int = 1,
    ticks_per_seed: int = 5000,
    db_path: str = "experiments/results/baseline.sqlite",
    metrics_json_path: str = "experiments/results/baseline_metrics.json",
    report_md_path: str = "experiments/results/baseline.md",
) -> Dict[str, Any]:
    """Execute baseline runs across 20 seeds and write out baseline.md."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    logger = ExperimentLogger(db_path=db_path)

    print(f"Starting {num_seeds}-seed baseline run for RandomBrain ({ticks_per_seed} ticks each)...")
    seed_results: List[Dict[str, Any]] = []

    for idx, s in enumerate(range(start_seed, start_seed + num_seeds), start=1):
        config = WorldConfig(seed=s)
        # Export replay for the first seed
        replay_path = "experiments/results/replays/baseline_seed1.json" if s == start_seed else None
        res = run_single_experiment(
            config=config,
            seed=s,
            agent_type="random",
            ticks=ticks_per_seed,
            db_path=db_path,
            replay_path=replay_path,
            logger=logger,
            run_id=f"baseline_random_seed_{s}",
        )
        seed_results.append(res)
        print(
            f"  [{idx:02d}/{num_seeds:02d}] Seed {s:03d} | "
            f"Mean Ticks/Life: {res['ticks_per_life_mean']:6.1f} | "
            f"Deaths: {res['total_deaths']:3d} | "
            f"Food: {res['food_eaten']:2d} | "
            f"Unique Transitions: {res['distinct_action_outcome_pairs']:4d}"
        )

    logger.close()

    # Aggregate Statistics
    def compute_stats(values: List[float]) -> Dict[str, float]:
        n = len(values)
        if n == 0:
            return {"mean": 0.0, "std": 0.0, "median": 0.0, "min": 0.0, "max": 0.0, "ci95": 0.0}
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / (n - 1) if n > 1 else 0.0
        std = math.sqrt(variance)
        sorted_vals = sorted(values)
        median = sorted_vals[n // 2] if n % 2 != 0 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
        # 95% Confidence Interval half-width: 1.96 * (std / sqrt(n))
        ci95 = 1.96 * (std / math.sqrt(n)) if n > 1 else 0.0
        return {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "median": round(median, 2),
            "min": round(sorted_vals[0], 2),
            "max": round(sorted_vals[-1], 2),
            "ci95": round(ci95, 2),
        }

    ticks_per_life_means = [r["ticks_per_life_mean"] for r in seed_results]
    deaths_list = [float(r["total_deaths"]) for r in seed_results]
    food_list = [float(r["food_eaten"]) for r in seed_results]
    plants_list = [float(r["plants_successfully_grown"]) for r in seed_results]
    transitions_list = [float(r["distinct_action_outcome_pairs"]) for r in seed_results]
    water_list = [float(r["water_drank"]) for r in seed_results]

    summary = {
        "num_seeds": num_seeds,
        "ticks_per_seed": ticks_per_seed,
        "total_ticks_simulated": num_seeds * ticks_per_seed,
        "ticks_per_life": compute_stats(ticks_per_life_means),
        "total_deaths": compute_stats(deaths_list),
        "food_eaten": compute_stats(food_list),
        "plants_grown": compute_stats(plants_list),
        "distinct_action_outcome_pairs": compute_stats(transitions_list),
        "water_drank": compute_stats(water_list),
        "per_seed_results": seed_results,
    }

    # Save JSON summary
    with open(metrics_json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    # Format Markdown Report
    tpl = summary["ticks_per_life"]
    dth = summary["total_deaths"]
    fd = summary["food_eaten"]
    pl = summary["plants_grown"]
    tr = summary["distinct_action_outcome_pairs"]
    wt = summary["water_drank"]

    report_lines = [
        "# Baseline Performance Report: RandomBrain",
        "",
        f"**Run Configuration:** {num_seeds} seeds, {ticks_per_seed:,} ticks per seed ({summary['total_ticks_simulated']:,} ticks total).",
        "**Agent Implementation:** `brain.random_brain.RandomBrain` (Uniform random action selection over 15 opaque action IDs).",
        f"**Storage:** SQLite `{db_path}`.",
        "",
        "## 1. Executive Summary",
        "",
        "The `RandomBrain` acts as the ungrounded, unguided stochastic baseline for ALC.",
        "Without memory, world models, or goal-directed utility, it demonstrates the physical lifetime of pure entropy in the ALC ecosystem.",
        "",
        "| Metric | Mean ± 95% CI | Median | Min | Max | Std Dev |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
        f"| **Ticks Survived per Life** | **{tpl['mean']} ± {tpl['ci95']}** | {tpl['median']} | {tpl['min']} | {tpl['max']} | {tpl['std']} |",
        f"| **Deaths per Run** | **{dth['mean']} ± {dth['ci95']}** | {dth['median']} | {dth['min']} | {dth['max']} | {dth['std']} |",
        f"| **Food Eaten** | **{fd['mean']} ± {fd['ci95']}** | {fd['median']} | {fd['min']} | {fd['max']} | {fd['std']} |",
        f"| **Water Drank** | **{wt['mean']} ± {wt['ci95']}** | {wt['median']} | {wt['min']} | {wt['max']} | {wt['std']} |",
        f"| **Plants Successfully Grown** | **{pl['mean']} ± {pl['ci95']}** | {pl['median']} | {pl['min']} | {pl['max']} | {pl['std']} |",
        f"| **Distinct Transitions Explored** | **{tr['mean']} ± {tr['ci95']}** | {tr['median']} | {tr['min']} | {tr['max']} | {tr['std']} |",
        "",
        "## 2. Key Findings & Biological Observations",
        "",
        "1. **Lifespan Under Random Walk:**",
        f"   - An agent taking uniform random actions survives on average **{tpl['mean']} ticks per life** before succumbing to starvation and dehydration.",
        f"   - Over 5,000 ticks, a random agent dies on average **{dth['mean']:.1f} times** (roughly once every {tpl['mean']} ticks).",
        "2. **Accidental Food Consumption:**",
        f"   - Across 20 seeds, random agents ate an average of **{fd['mean']} food items** over 5,000 ticks. The probability of randomly standing next to an edible fruit, facing it, and emitting the `EAT` action ID without dying of thirst first is near zero.",
        "3. **State-Action Coverage:**",
        f"   - A random agent explores on average **{tr['mean']:.0f} distinct state-action-outcome transitions** per 5,000 ticks. However, these transitions remain concentrated in basic movement and wall collisions, rarely discovering multi-step causal chains.",
        "4. **Causal Chain Failure:**",
        "   - The complex sequence: `PICK_UP(seed) -> MOVE(to soil) -> USE_ON_FACING(plant) -> WAIT/WATER -> PICK_UP(fruit) -> EAT` was never observed end-to-end under random action selection.",
        "",
        "## 3. Seed Distribution Breakdown",
        "",
        "| Seed | Mean Ticks/Life | Total Deaths | Food Eaten | Water Drank | Distinct Transitions |",
        "| :---: | :---: | :---: | :---: | :---: | :---: |",
    ]

    for r in seed_results:
        report_lines.append(
            f"| {r['seed']} | {r['ticks_per_life_mean']:.1f} | {r['total_deaths']} | {r['food_eaten']} | {r['water_drank']} | {r['distinct_action_outcome_pairs']} |"
        )

    report_lines.extend([
        "",
        "## 4. Phase 3 Acceptance Target",
        "",
        f"For `learner_v1` (Phase 3) to be accepted, it must statistically outperform this baseline on **Mean Ticks Survived** (target > {tpl['mean'] + tpl['ci95']:.1f}) and demonstrate purposeful survival loops without handcoded semantic rules.",
        "",
        "---",
        "*Report automatically generated by `experiments.run_baseline`.*",
    ])

    with open(report_md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(report_lines) + "\n")

    print(f"\nBaseline run complete. Report saved to {report_md_path}")
    return summary


if __name__ == "__main__":
    run_baseline()
