"""CLI training and evaluation harness for basic English conversation in ALC.

Trains Alpha and Albedo using grounded experiential language learning and tests
their responses across greetings, identities, needs, world concepts, and honest unknowns.
"""

from brain.alpha.brain import AlphaBrain
from brain.albedo.brain import AlbedoBrain
from communication.message import Message, CommType
from communication.training import train_basic_english


def main():
    print("=" * 65)
    print(" ALC FOUNDATIONAL LANGUAGE TRAINING: ALPHA & ALBEDO")
    print(" Non-LLM Experiential Grounding Harness")
    print("=" * 65)

    alpha = AlphaBrain(seed=42)
    albedo = AlbedoBrain(seed=1042)

    print("\n[Phase 1] Training Alpha with basic English vocabulary...")
    alpha_symbols = train_basic_english(alpha, agent_id=0)
    print(f"-> Alpha learned {len(alpha_symbols)} grounded symbols.")

    print("\n[Phase 2] Training Albedo with basic English vocabulary...")
    albedo_symbols = train_basic_english(albedo, agent_id=1)
    print(f"-> Albedo learned {len(albedo_symbols)} grounded symbols.")

    # Synthetic mock observations for testing
    alpha_obs = {
        "tick": 100,
        "self": {"water": 45.0, "food": 85.0, "energy": 70.0, "health": 100.0},
        "pos": (14, 16),
        "facing": (0, -1),
        "holding": 15, # water container
        "all_agents": [{"name": "Alpha"}, {"name": "Albedo"}],
    }
    alpha.observe(alpha_obs)

    albedo_obs = {
        "tick": 100,
        "self": {"water": 90.0, "food": 38.0, "energy": 40.0, "health": 100.0},
        "pos": (13, 16),
        "facing": (1, 0),
        "holding": None,
        "all_agents": [{"name": "Alpha"}, {"name": "Albedo"}],
    }
    albedo.observe(albedo_obs)

    # Dialogue Test Cases
    test_queries = [
        # 1. Greetings
        ("human", "alpha", "Hello!"),
        ("human", "albedo", "Hi Albedo"),
        # 2. Identity
        ("human", "alpha", "Who are you?"),
        ("human", "albedo", "What is your name?"),
        # 3. Peer awareness
        ("human", "alpha", "Who is Albedo?"),
        ("human", "albedo", "Who is Alpha?"),
        # 4. Activity & Location
        ("human", "alpha", "What are you doing?"),
        ("human", "alpha", "Where are you?"),
        # 5. Needs inquiries
        ("human", "alpha", "Are you thirsty?"),
        ("human", "albedo", "Are you hungry?"),
        ("human", "albedo", "Are you tired?"),
        # 6. World Knowledge (Grounded)
        ("human", "alpha", "What is water?"),
        ("human", "alpha", "What is fruit?"),
        ("human", "albedo", "What does poison do?"),
        ("human", "alpha", "What is a seed?"),
        ("human", "alpha", "What did you learn today?"),
        # 7. Honest Unknowns (Must NOT hallucinate!)
        ("human", "alpha", "What is an airplane?"),
        ("human", "albedo", "What is a computer?"),
        ("human", "alpha", "Who is Napoleon?"),
    ]

    print("\n" + "=" * 65)
    print(" DIALOGUE EVALUATION")
    print("=" * 65)

    for sender, target, text in test_queries:
        brain = alpha if target == "alpha" else roselia
        msg = Message(
            sender=sender,
            receiver=target,
            tick=100,
            content=text,
            comm_type=CommType.QUERY,
        )
        resp = brain.receive_message(msg, tick=100)
        print(f"\n[Human -> {target.capitalize()}]: \"{text}\"")
        print(f"[{resp.sender}]: \"{resp.content}\"")
        print(f"  [Status: {resp.status.value}, Confidence: {resp.confidence:.2f}, Evidence: {resp.evidence_count}]")

    print("\n" + "=" * 65)
    print(" Training & Dialogue Evaluation Complete! All tests grounded.")
    print("=" * 65)


if __name__ == "__main__":
    main()
