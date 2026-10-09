"""Unit tests for Phase 2: Brain interface, RandomBrain, harness, and observability."""

import json
import os
import sqlite3
import pytest

from brain.random_brain import RandomBrain
from experiments.logger import ExperimentLogger
from experiments.metrics import MetricsTracker
from experiments.run_experiment import run_single_experiment
from sim.config import WorldConfig
from sim.world import World


def test_random_brain_interface_and_determinism(tmp_path):
    """Verify RandomBrain complies with Brain ABC and is seeded deterministic."""
    b1 = RandomBrain(seed=42)
    b2 = RandomBrain(seed=42)

    dummy_obs = {"tick": 0, "self": {"energy": 100}, "view": [[1]*7]*7, "events": []}
    b1.observe(dummy_obs)
    b2.observe(dummy_obs)

    actions1 = [b1.act() for _ in range(50)]
    actions2 = [b2.act() for _ in range(50)]
    assert actions1 == actions2

    # Verify save & load
    save_file = str(tmp_path / "brain_state.json")
    b1.save(save_file)
    assert os.path.exists(save_file)

    b3 = RandomBrain(seed=999)
    b3.load(save_file)
    assert b3.total_steps == b1.total_steps
    assert b3.action_counts == b1.action_counts


def test_experiment_harness_and_logging(tmp_path):
    """Verify single experiment execution, SQLite database logging, and replay generation."""
    db_file = str(tmp_path / "test_run.sqlite")
    replay_file = str(tmp_path / "test_replay.json")

    config = WorldConfig(seed=42)
    metrics = run_single_experiment(
        config=config,
        seed=42,
        agent_type="random",
        ticks=100,
        db_path=db_file,
        replay_path=replay_file,
    )

    assert metrics["total_ticks"] == 100
    assert "ticks_per_life_mean" in metrics
    assert "distinct_action_outcome_pairs" in metrics
    assert os.path.exists(db_file)
    assert os.path.exists(replay_file)

    # Verify SQLite schema and content
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    cursor.execute("SELECT count(*) FROM runs")
    runs_count = cursor.fetchone()[0]
    assert runs_count == 1

    cursor.execute("SELECT count(*) FROM step_logs")
    step_count = cursor.fetchone()[0]
    assert step_count == 100

    cursor.execute("SELECT count(*) FROM lives")
    lives_count = cursor.fetchone()[0]
    assert lives_count >= 1

    conn.close()

    # Verify replay JSON format
    with open(replay_file, "r", encoding="utf-8") as f:
        replay_data = json.load(f)
    assert replay_data["total_frames"] == 100
    assert len(replay_data["frames"]) == 100
    assert "needs" in replay_data["frames"][0]
