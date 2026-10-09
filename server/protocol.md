# ALC WebSocket Communication Protocol Specification

This document defines the schema for bidirectional communication between the ALC simulation server (`server/ws_server.py`) and the 3D Desktop Viewer (`viewer/`).

## Connection
- **URL**: `ws://127.0.0.1:8765`
- **Format**: JSON (UTF-8)

---

## 1. Server-to-Client Messages

### A. `world_init`
Sent immediately upon client connection or after world reset.

```json
{
  "type": "world_init",
  "width": 32,
  "height": 32,
  "seed": 42,
  "tiles": [
    [1, 1, 1, 3, 3, ...],
    ...
  ],
  "agents": [
    {"id": 0, "name": "Alpha", "gender": "female", "x": 14, "y": 16},
    {"id": 1, "name": "Albedo", "gender": "female", "x": 13, "y": 16}
  ]
}
```

### B. `tick_frame`
Streamed on every simulation tick.

```json
{
  "type": "tick_frame",
  "tick": 1832,
  "weather": "CLEAR",
  "is_raining": false,
  "agents": [
    {
      "id": 0,
      "name": "Alpha",
      "gender": "female",
      "x": 14,
      "y": 16,
      "facing": [0, -1],
      "holding": 10,
      "needs": {
        "energy": 72.4,
        "water": 61.2,
        "food": 85.0,
        "health": 94.0
      },
      "alive": true,
      "lives": 1,
      "cognition": {
        "current_action": 1,
        "action_name": "MOVE_N",
        "known_states": 1284,
        "memory_size": 4921,
        "successful_experiences": 2817,
        "exploration_rate": 38.0,
        "learning_events": 421,
        "recorded_mistakes": 0.0
      }
    },
    {
      "id": 1,
      "name": "Roselia",
      "gender": "female",
      "x": 13,
      "y": 16,
      "facing": [1, 0],
      "holding": null,
      "needs": {
        "energy": 88.0,
        "water": 75.5,
        "food": 62.0,
        "health": 100.0
      },
      "alive": true,
      "lives": 1,
      "cognition": {
        "current_action": 5,
        "action_name": "PICK_UP",
        "known_states": 1140,
        "memory_size": 4310,
        "successful_experiences": 2450,
        "exploration_rate": 41.5,
        "learning_events": 380,
        "recorded_mistakes": 0.0
      }
    }
  ],
  "plants": [
    {"x": 15, "y": 16, "stage": 12, "has_fruit": true, "fruit_type": 13}
  ],
  "ground_items": [
    {"x": 12, "y": 14, "entity_id": 10}
  ],
  "events": [
    {"tick": 1832, "agent_name": "Alpha", "event_id": 8, "text": "Alpha drank water from lake"}
  ]
}
```

### C. `chat_message`
Broadcast immediately when a message is exchanged (Human → Agent, Agent → Human, Agent ↔ Agent, or Autonomous).

```json
{
  "type": "chat_message",
  "message": {
    "sender": "Alpha",
    "receiver": "human",
    "tick": 1832,
    "content": "Water increases water by +18.0.",
    "comm_type": "answer",
    "confidence": 0.85,
    "understood": true,
    "concepts": ["water"],
    "status": "KNOWN",
    "evidence_count": 12,
    "supporting_memories": [1402, 1680]
  }
}
```

When an organism has no experience or evidence for a query, it produces an explicit `UNKNOWN` response:

```json
{
  "type": "chat_message",
  "message": {
    "sender": "Alpha",
    "receiver": "human",
    "tick": 1833,
    "content": "I don't know what 'mountain' is.",
    "comm_type": "unknown",
    "confidence": 0.0,
    "understood": false,
    "concepts": ["mountain"],
    "status": "UNKNOWN",
    "evidence_count": 0,
    "supporting_memories": []
  }
}
```

---

## 2. Client-to-Server Commands

Clients can send JSON commands to control simulation flow and interact with agents:

### `pause`
Halts automatic tick advancement.
```json
{"command": "pause"}
```

### `resume`
Resumes automatic tick advancement.
```json
{"command": "resume"}
```

### `step`
Advances simulation by exactly one tick when paused.
```json
{"command": "step"}
```

### `set_speed`
Sets the simulation tick rate (ticks per second, 1 to 100).
```json
{"command": "set_speed", "tps": 10}
```

### `reset`
Resets the simulation with an optional seed.
```json
{"command": "reset", "seed": 42}
```

### `human_message` (Phase 6)
Sends a natural language query or statement to an agent (`"alpha"`, `"roselia"`, or `"both"`).
The recipient agent parses the query, searches its private episodic memory and learned world model, and formulates an honest answer (or `UNKNOWN`):

```json
{
  "command": "human_message",
  "target": "alpha",
  "text": "What does water do?"
}
```

### `teach_symbol` (Phase 6)
Associates a human word/symbol with an observed entity or action in the recipient agent's private lexicon:

```json
{
  "command": "teach_symbol",
  "target": "both",
  "symbol": "water",
  "concept_type": "entity",
  "concept_id": 3
}
```

---

## 3. Communication Epistemology & Knowledge States

All inter-agent and human-agent messages track explicit knowledge states:
- `KNOWN`: Grounded in direct episodic experience and verified world model dynamics.
- `UNKNOWN`: The organism has never encountered or grounded the concept; produces an honest "I don't know" with 0 confidence.
- `UNCERTAIN`: Some empirical observations exist, but evidence count or consistency is low.
- `CONTRADICTORY`: Experiences yield conflicting outcomes under similar conditions.
- `UNVERIFIED`: Communicated testimony from another agent (or human) that has not yet been experimentally verified by this organism.
- `CONFIRMED`: Formerly unverified testimony that the receiving organism has successfully tested in the environment and validated.
- `REFUTED`: Formerly unverified testimony that failed empirical testing in the environment.

*Note: This system does not use an external LLM, pretrained language model, or cloud API. All communication is grounded in the organisms' own empirical memory and cognitive state.*
