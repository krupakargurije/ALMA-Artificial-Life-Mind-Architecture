"""Unit tests verifying separate brains for Alpha and Albedo."""

import pytest
from brain.alpha import AlphaBrain
from brain.albedo import AlbedoBrain
from experiments.run_experiment import run_single_experiment
from sim.config import WorldConfig
from sim.world import World


def test_alpha_and_albedo_separate_brains():
    """Verify Alpha and Albedo have separate cognitive instances and female identities."""
    alpha = AlphaBrain(seed=42)
    albedo = AlbedoBrain(seed=777)

    assert alpha.name == "Alpha"
    assert alpha.gender == "female"
    assert albedo.name == "Albedo"
    assert albedo.gender == "female"

    # Verify memory and models are fully disjoint objects
    assert alpha.memory is not albedo.memory
    assert alpha.model is not albedo.model

    # Give Alpha an observation and learning experience
    obs = {
        "tick": 1,
        "self": {"energy": 80.0, "water": 30.0, "food": 90.0, "health": 100.0, "holding": None},
        "view": [[1] * 7 for _ in range(7)],
        "others": [],
        "events": [],
    }
    alpha.observe(obs)
    action = alpha.act()

    outcome = {
        "obs_next": {
            "tick": 2,
            "self": {"energy": 79.9, "water": 65.0, "food": 89.9, "health": 100.0, "holding": None},
            "view": [[1] * 7 for _ in range(7)],
            "others": [],
            "events": [8],  # DRANK_WATER
        },
        "need_delta": {"energy": -0.1, "water": 35.0, "food": -0.1, "health": 0.0},
        "alive": True,
    }
    alpha.learn(outcome)

    # Alpha learned water reward; Albedo should remain unaffected
    assert alpha.memory.size() == 1
    assert albedo.memory.size() == 0
    assert len(alpha.model.visit_counts) > 0
    assert len(albedo.model.visit_counts) == 0


def test_run_alpha_and_albedo_experiments(tmp_path):
    """Verify experiment harness runs both Alpha and Albedo independently."""
    db_file = str(tmp_path / "separate_test.sqlite")
    config = WorldConfig(seed=42)

    res_alpha = run_single_experiment(
        config=config,
        seed=42,
        agent_type="alpha",
        ticks=100,
        db_path=db_file,
    )
    assert res_alpha["agent_type"] == "alpha"
    assert res_alpha["total_ticks"] == 100

    res_albedo = run_single_experiment(
        config=config,
        seed=100,
        agent_type="albedo",
        ticks=100,
        db_path=db_file,
    )
    assert res_albedo["agent_type"] == "albedo"
    assert res_albedo["total_ticks"] == 100
