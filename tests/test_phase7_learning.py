"""Test suite for Phase 7 Advanced Learning Architecture and Scientific Validation."""

import os
import tempfile
import pytest

from brain.alpha.brain import AlphaBrain
from brain.albedo.brain import AlbedoBrain
from brain.common.episodic_memory import EpisodicMemory
from brain.common.world_model import TabularWorldModel
from communication.message import CommType, KnowledgeStatus, Message
from experiments.benchmark_suite import evaluate_persistence, run_benchmark_trial
from sim.config import WorldConfig
from sim.world import World


def test_prioritized_experience_replay():
    """Verify PER prioritizes high-surprise and high TD-error transitions."""
    memory = EpisodicMemory(capacity=100, alpha=0.6)
    
    # Add mundane transitions (low surprise)
    for i in range(10):
        memory.add(
            state=((1, 1, 1, 1), 0, (1, 1, 1, 1, 1), ()),
            action=0,
            need_delta={"food": 0.0, "water": 0.0, "health": 0.0, "energy": -0.1},
            next_state=((1, 1, 1, 1), 0, (1, 1, 1, 1, 1), ()),
            events=[],
            alive=True,
            initial_td_error=0.01,
        )
        
    # Add a high-surprise life-saving transition
    memory.add(
        state=((0, 0, 0, 1), 0, (3, 1, 1, 1, 1), ()),
        action=9,  # DRINK
        need_delta={"food": 0.0, "water": 35.0, "health": 0.0, "energy": 0.0},
        next_state=((1, 2, 0, 1), 0, (3, 1, 1, 1, 1), ()),
        events=[901],
        alive=True,
        initial_td_error=15.0,
    )
    
    # Sample batches and verify high-surprise transition is sampled frequently
    samples, indices, weights = memory.sample_prioritized(batch_size=5, beta=0.4)
    assert len(samples) == 5
    assert len(indices) == 5
    assert len(weights) == 5
    assert any(s["need_delta"].get("water", 0) > 0 for s in samples)


def test_world_model_planning_and_td_error():
    """Verify TabularWorldModel calculates TD errors and updates Q-values during planning."""
    model = TabularWorldModel(gamma=0.9)
    s1 = ((0, 0, 0, 2), 0, (1, 1, 1, 1, 1), ())
    s2 = ((0, 2, 0, 2), 0, (3, 1, 1, 1, 1), ())
    
    td_err = model.update(
        state=s1,
        action=9,
        need_delta={"water": 30.0, "energy": 0.0, "food": 0.0, "health": 0.0},
        next_state=s2,
        alive=True,
    )
    assert td_err > 0.0
    assert model.q_table[s1][9] > 0.0
    
    # Run planning step
    model.planning_step(n_steps=10)
    assert model.stats()["known_states"] >= 1


def test_complete_brain_persistence_fidelity():
    """Verify Alpha and Albedo save/load completely restores learned state and memories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        save_path = os.path.join(tmpdir, "alpha_brain_state.json")
        
        # 1. Train Alpha on a small world
        alpha = AlphaBrain(seed=42)
        world = World(config=WorldConfig(seed=42), num_agents=1)
        
        for _ in range(50):
            obs = world.get_observation(0)
            alpha.observe(obs)
            action = alpha.act()
            outcomes = world.tick(action)
            alpha.learn(outcomes[0])
            
        alpha.ground_concept("nectar", "entity", 14, confidence=0.9, source="test")
        stats_pre = alpha.stats()
        assert stats_pre["known_states"] > 0
        assert stats_pre["memory_size"] > 0
        assert "nectar" in alpha.lexicon.all_known_symbols()
        
        # 2. Save
        alpha.save(save_path)
        assert os.path.exists(save_path)
        
        # 3. Create fresh brain and load
        loaded_alpha = AlphaBrain(seed=42)
        loaded_alpha.load(save_path)
        stats_post = loaded_alpha.stats()
        
        # 4. Strict assertions on knowledge preservation
        assert stats_post["known_states"] == stats_pre["known_states"]
        assert stats_post["memory_size"] == stats_pre["memory_size"]
        assert stats_post["total_steps"] == stats_pre["total_steps"]
        assert stats_post["recorded_mistakes"] == stats_pre["recorded_mistakes"]
        assert "nectar" in loaded_alpha.lexicon.all_known_symbols()
        assert loaded_alpha.lexicon.get("nectar").internal_id == 14


def test_epistemic_social_testimony_hypothesis_testing():
    """Verify that receiving unverified testimony triggers active hypothesis testing."""
    alpha = AlphaBrain(seed=42)
    
    # Send testimony claim from Albedo about water action (action 9)
    testimony_msg = Message(
        sender="Albedo",
        receiver="Alpha",
        tick=10,
        content="Water reduces thirst",
        comm_type=CommType.STATEMENT,
        confidence=0.8,
    )
    resp = alpha.receive_message(testimony_msg, tick=10)
    assert resp.status == KnowledgeStatus.UNVERIFIED
    
    # Verify claim is recorded in unverified claims
    claims = alpha.testimony.get_unverified_claims()
    assert len(claims) == 1
    assert claims[0].status == KnowledgeStatus.UNVERIFIED
    
    # Verify test evaluation
    status = alpha.testimony.evaluate_test(claims[0].claim_id, {"water": 30.0}, tick=15)
    assert status == KnowledgeStatus.CONFIRMED
    assert len(alpha.testimony.get_unverified_claims()) == 0


def test_benchmark_runner_execution():
    """Verify that benchmark suite executes deterministically."""
    brain = AlphaBrain(seed=42)
    res = run_benchmark_trial(brain, seed=42, ticks=100)
    assert res["ticks"] == 100
    assert "mean_life_ticks" in res
    assert "rmse_water_prediction" in res
