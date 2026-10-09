"""Automated unit tests for Phase 6: Interactive Artificial Organisms.

Verifies:
1. Human can send message to Alpha.
2. Human can send message to Albedo.
3. Alpha can send message to Albedo.
4. Albedo can send message to Alpha.
5. Alpha cannot directly access Albedo's memory.
6. Albedo cannot directly access Alpha's memory.
7. Unknown questions produce UNKNOWN rather than fabricated knowledge.
8. Known information can produce an answer.
9. Communicated information is initially marked as unverified.
10. Receiver can test communicated information.
11. Confirmed information updates receiver's world model.
12. Conversation events are persisted/logged.
13. Autonomous communication events are correctly transmitted.
"""

import os
import pytest

from brain.alpha import AlphaBrain
from brain.albedo import AlbedoBrain
from communication import (
    CommunicationChannel,
    CommType,
    KnowledgeStatus,
    Message,
)
from sim.config import WorldConfig
from sim.entities import EVENT_DRANK_WATER
from sim.world import World


@pytest.fixture
def clean_channel(tmp_path):
    log_file = str(tmp_path / "comm_test.jsonl")
    return CommunicationChannel(log_path=log_file)


def test_1_and_2_human_can_send_message_to_alpha_and_albedo(clean_channel):
    """Test human can send message to Alpha and Albedo independently."""
    alpha = AlphaBrain(seed=42)
    albedo = AlbedoBrain(seed=777)

    # Human asks Alpha a question
    human_msg_alpha = Message(
        sender="human",
        receiver="alpha",
        tick=10,
        content="How do you feel?",
        comm_type=CommType.QUERY,
    )
    clean_channel.send(human_msg_alpha)
    resp_alpha = alpha.receive_message(human_msg_alpha, tick=10)

    assert resp_alpha.sender == "Alpha"
    assert resp_alpha.receiver == "human"
    assert resp_alpha.status in [KnowledgeStatus.KNOWN, KnowledgeStatus.UNKNOWN]

    # Human asks Albedo independently
    human_msg_alb = Message(
        sender="human",
        receiver="albedo",
        tick=10,
        content="How do you feel?",
        comm_type=CommType.QUERY,
    )
    clean_channel.send(human_msg_alb)
    resp_alb = albedo.receive_message(human_msg_alb, tick=10)

    assert resp_alb.sender == "Albedo"
    assert resp_alb.receiver == "human"


def test_3_and_4_alpha_and_albedo_cross_communication(clean_channel):
    """Test Alpha and Albedo can communicate over the channel."""
    alpha = AlphaBrain(seed=42)
    albedo = AlbedoBrain(seed=777)

    # Alpha sends message to Albedo
    alpha_msg = Message(
        sender="Alpha",
        receiver="Albedo",
        tick=25,
        content="Water reduces thirst",
        comm_type=CommType.STATEMENT,
        confidence=0.9,
    )
    clean_channel.send(alpha_msg)

    # Albedo processes inbox
    inbox_alb = clean_channel.fetch_inbox("albedo")
    assert len(inbox_alb) == 1
    assert inbox_alb[0].content == "Water reduces thirst"

    resp_alb = albedo.receive_message(inbox_alb[0], tick=25)
    clean_channel.send(resp_alb)

    # Albedo sends message back to Alpha
    inbox_alpha = clean_channel.fetch_inbox("alpha")
    assert len(inbox_alpha) == 1
    assert inbox_alpha[0].sender == "Albedo"


def test_5_and_6_strict_memory_isolation():
    """Verify Alpha and Albedo cannot directly access each other's memories or models."""
    alpha = AlphaBrain(seed=42)
    albedo = AlbedoBrain(seed=777)

    assert alpha.memory is not albedo.memory
    assert alpha.model is not albedo.model
    assert alpha.lexicon is not albedo.lexicon
    assert alpha.testimony is not albedo.testimony

    # Train Alpha with water experience
    obs = {
        "tick": 1,
        "self": {"energy": 80.0, "water": 30.0, "food": 90.0, "health": 100.0, "holding": None},
        "view": [[1] * 7 for _ in range(7)],
        "others": [],
        "events": [],
    }
    alpha.observe(obs)
    alpha.act()
    outcome = {
        "obs_next": {
            "tick": 2,
            "self": {"energy": 79.9, "water": 65.0, "food": 89.9, "health": 100.0, "holding": None},
            "view": [[1] * 7 for _ in range(7)],
            "others": [],
            "events": [EVENT_DRANK_WATER],
        },
        "need_delta": {"energy": -0.1, "water": 35.0, "food": -0.1, "health": 0.0},
        "alive": True,
    }
    alpha.learn(outcome)

    # Verify Alpha has memory of this, but Albedo has zero
    assert alpha.memory.size() == 1
    assert albedo.memory.size() == 0
    assert len(albedo.model.visit_counts) == 0


def test_7_unknown_questions_produce_unknown_state():
    """Verify unknown concepts produce explicit UNKNOWN rather than fabricated knowledge."""
    alpha = AlphaBrain(seed=42)

    # Ask about a concept never taught or experienced (e.g. "mountain", "car", "airplane")
    msg = Message(
        sender="human",
        receiver="alpha",
        tick=5,
        content="What is a mountain?",
        comm_type=CommType.QUERY,
    )
    resp = alpha.receive_message(msg, tick=5)

    assert resp.status == KnowledgeStatus.UNKNOWN
    assert resp.confidence == 0.0
    assert resp.evidence_count == 0
    assert "don't know" in resp.content.lower()


def test_8_known_information_produces_answer():
    """Verify directly experienced knowledge produces evidence-backed answers."""
    alpha = AlphaBrain(seed=42)

    # Teach symbol "water"
    alpha.ground_concept("water", "tile", 3)

    # Simulate experiencing drinking water 3 times
    for t in range(3):
        obs = {
            "tick": t,
            "self": {"energy": 80.0, "water": 30.0, "food": 90.0, "health": 100.0, "holding": None},
            "view": [[1] * 7 for _ in range(7)],
            "others": [],
            "events": [],
        }
        alpha.observe(obs)
        alpha.act()
        alpha.learn({
            "obs_next": {
                "tick": t + 1,
                "self": {"energy": 79.9, "water": 65.0, "food": 89.9, "health": 100.0, "holding": None},
                "view": [[1] * 7 for _ in range(7)],
                "others": [],
                "events": [EVENT_DRANK_WATER],
            },
            "need_delta": {"water": 35.0, "energy": -0.1},
            "alive": True,
        })

    # Now ask about water
    query = Message(
        sender="human",
        receiver="alpha",
        tick=10,
        content="What is water?",
        comm_type=CommType.QUERY,
    )
    resp = alpha.receive_message(query, tick=10)

    assert resp.status == KnowledgeStatus.KNOWN
    assert resp.confidence > 0.7
    assert resp.evidence_count >= 3
    assert "hydration" in resp.content.lower() or "water" in resp.content.lower()


def test_9_10_and_11_testimony_unverified_then_tested_and_confirmed():
    """Verify claims from another agent are initially UNVERIFIED, then testable, and confirmed."""
    albedo = AlbedoBrain(seed=777)

    # Albedo receives claim from Alpha that water reduces thirst
    claim_msg = Message(
        sender="Alpha",
        receiver="Albedo",
        tick=50,
        content="Water reduces thirst",
        comm_type=CommType.STATEMENT,
        confidence=0.9,
    )
    resp = albedo.receive_message(claim_msg, tick=50)

    # 9. Verify initial status is UNVERIFIED
    assert resp.status == KnowledgeStatus.UNVERIFIED
    assert len(albedo.testimony.get_unverified_claims()) == 1
    unverified = albedo.testimony.get_unverified_claims()[0]
    assert unverified.subject == "water"
    assert unverified.status == KnowledgeStatus.UNVERIFIED

    # 10. Albedo tests the hypothesis by drinking water in the environment
    obs = {
        "tick": 51,
        "self": {"energy": 75.0, "water": 40.0, "food": 80.0, "health": 100.0, "holding": None},
        "view": [[1] * 7 for _ in range(7)],
        "others": [],
        "events": [],
    }
    albedo.observe(obs)
    albedo.last_action = 9  # DRINK
    albedo.learn({
        "obs_next": {
            "tick": 52,
            "self": {"energy": 74.9, "water": 75.0, "food": 79.9, "health": 100.0, "holding": None},
            "view": [[1] * 7 for _ in range(7)],
            "others": [],
            "events": [EVENT_DRANK_WATER],
        },
        "need_delta": {"water": 35.0, "energy": -0.1},
        "alive": True,
    })

    # 11. Confirmed information updates receiver's world model
    assert unverified.status == KnowledgeStatus.CONFIRMED
    assert unverified.confidence == 1.0
    assert len(albedo.testimony.get_unverified_claims()) == 0


def test_12_conversation_events_persisted(tmp_path):
    """Verify all messages on the channel are recorded in the research log."""
    log_file = str(tmp_path / "research_log.jsonl")
    channel = CommunicationChannel(log_path=log_file)

    msg = Message(
        sender="human",
        receiver="alpha",
        tick=1,
        content="Hello Alpha",
        comm_type=CommType.GREETING,
    )
    channel.send(msg)

    assert os.path.exists(log_file)
    with open(log_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    assert len(lines) == 1
    assert "Hello Alpha" in lines[0]


def test_13_autonomous_communication_transmitted():
    """Verify autonomous communication triggers when significant event occurs."""
    alpha = AlphaBrain(seed=42)

    # Simulate discovery of water with huge delta
    outcome = {
        "obs_next": {
            "tick": 100,
            "self": {"water": 75.0, "health": 100.0},
            "events": [EVENT_DRANK_WATER],
        },
        "need_delta": {"water": 35.0},
        "alive": True,
    }

    auto_msg = alpha.check_autonomous_communication(tick=100, outcome=outcome, peer_name="Albedo")
    assert auto_msg is not None
    assert auto_msg.is_autonomous is True
    assert auto_msg.receiver == "Albedo"
    assert "water" in auto_msg.content.lower()


def test_14_basic_english_conversation_trained():
    """Verify basic English conversation training, identity, needs, and unknown integrity."""
    from communication.training import train_basic_english

    alpha = AlphaBrain(seed=42)
    symbols = train_basic_english(alpha, agent_id=0)
    assert len(symbols) >= 20

    alpha.observe({
        "tick": 50,
        "self": {"water": 45.0, "food": 85.0, "energy": 70.0, "health": 100.0},
        "pos": (14, 16),
        "facing": (0, -1),
        "holding": 15,
        "all_agents": [{"name": "Alpha"}, {"name": "Albedo"}],
    })

    # 1. Greeting
    resp_greet = alpha.receive_message(Message(sender="human", receiver="alpha", tick=50, content="Hello!"), tick=50)
    assert resp_greet.status == KnowledgeStatus.KNOWN
    assert "Alpha" in resp_greet.content

    # 2. Identity
    resp_who = alpha.receive_message(Message(sender="human", receiver="alpha", tick=50, content="Who are you?"), tick=50)
    assert resp_who.status == KnowledgeStatus.KNOWN
    assert "Alpha" in resp_who.content

    # 3. Specific Need (thirsty)
    resp_thirst = alpha.receive_message(Message(sender="human", receiver="alpha", tick=50, content="Are you thirsty?"), tick=50)
    assert resp_thirst.status == KnowledgeStatus.KNOWN
    assert "thirsty" in resp_thirst.content.lower()

    # 4. Grounded World Knowledge (water)
    resp_water = alpha.receive_message(Message(sender="human", receiver="alpha", tick=50, content="What is water?"), tick=50)
    assert resp_water.status == KnowledgeStatus.KNOWN
    assert resp_water.evidence_count >= 1

    # 5. Untrained Concept -> Strictly UNKNOWN
    resp_unknown = alpha.receive_message(Message(sender="human", receiver="alpha", tick=50, content="What is a helicopter?"), tick=50)
    assert resp_unknown.status == KnowledgeStatus.UNKNOWN
    assert resp_unknown.confidence == 0.0
    assert "I don't know" in resp_unknown.content

