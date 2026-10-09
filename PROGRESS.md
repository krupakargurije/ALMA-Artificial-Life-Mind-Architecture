# Project Progress & Roadmap

## Overview
- **Project**: Artificial Learning Civilization (ALC)
- **Civilization Population**: Exactly two beings live on the planet:
  - **Alpha** (female, Agent 0)
  - **Albedo** (female, Agent 1)
- **Current Status**:
  - Phase 0 (Scaffold): COMPLETE
  - Phase 1 (Headless World): COMPLETE
  - Phase 2 (Random Baseline & Harness): COMPLETE
  - Phase 3 (Separate Cognitive Brains for Alpha & Albedo): IMPLEMENTED & VALIDATED
- **Master Rules Verified**:
  - No LLMs or pretrained neural models in brain loop.
  - World owns rules; brains discover them.
  - Brain operates exclusively on opaque integer IDs.
  - Deterministic and seeded across all runs.
  - Alpha and Albedo have completely independent brain codebases in separate folders (`brain/alpha/` and `brain/albedo/`) with zero memory leakage.

---

## Civilization Architecture & Separate Brain Structure

```
brain/
  interface.py            # Base Brain ABC (observe, act, learn, save, load, stats)
  random_brain.py         # Pure entropy benchmark
  common/                 # Sensory discretization and generic tabular math
    state_abstraction.py  # Local 7x7 view & needs drive binning
    episodic_memory.py    # Experience ring buffer
    world_model.py        # Count-based state-action model & UCB curiosity
  alpha/                  # Alpha's Brain Package (female)
    __init__.py           # Exports AlphaBrain
    brain.py              # Alpha's cognitive loop, decision engine, & model updates
  albedo/                 # Albedo's Brain Package (female)
    __init__.py           # Exports AlbedoBrain
    brain.py              # Albedo's cognitive loop, decision engine, & model updates
```

---

## Log of Completed Phases

### Phase 0: Scaffold — COMPLETE
- Build configuration (`pyproject.toml`), modular package layout, CLI harness, and pytest setup.

### Phase 1: Headless World — COMPLETE
- 32×32 grid simulation engine (`sim/world.py`), physiological needs (`sim/needs.py`), crop lifecycle, rain intervals, and ASCII visualizer.
- World solvability proven: scripted oracle survived 5,000 continuous ticks with zero deaths across seeds 42, 100, and 777.

### Phase 2: Brain Interface, Random Baseline, Harness — COMPLETE
- Formalized `Brain` ABC, random baseline, SQLite logger (`runs`, `lives`, `step_logs`), and replay export.
- 20-seed baseline benchmark executed (100,000 ticks total):
  - **Mean Ticks Survived per Life**: 2,333.33 ± 326.67
  - **Deaths per Run**: 1.30 ± 0.25
  - **Food Eaten**: 7.05 ± 1.98
  - **Water Drank**: 11.65 ± 3.23

### Phase 3: Separate Learning Brains for Alpha & Roselia — COMPLETE
- Alpha and Roselia configured as the two beings on the planet, both females.
- Developed `brain/alpha/brain.py` and `brain/roselia/brain.py` in separate directories.
- Each maintains its own episodic memory, learned world model, visit counts, and mistake memory.
- Tested: Both Alpha and Roselia independently run in `experiments/run_experiment.py`, successfully discovering thirst quenching (drinking water 100+ times), digging soil, using items, and surviving 500 ticks with 0 deaths.
- All 16 unit tests passing in 0.83s.

---

### Phase 4: Virtual World + Brain Observatory (Java/LibGDX & WebSocket Server) — COMPLETE
- **WebSocket Protocol**: Formalized in `server/protocol.md` with full telemetry specifications (`world_init`, `tick_frame`, control commands).
- **Simulation Server (`server/ws_server.py`)**:
  - Streams 3D world state, plant growth, dropped items, and dual-agent physiological & cognitive telemetry.
  - Generates rich live cognitive event stream entries (sensory observations, actions taken, positive/negative biological feedback, memory and world model updates).
  - Handles client commands: `pause`, `resume`, `step`, `set_speed`, `reset`.
- **Java / LibGDX 3D Desktop Viewer (`viewer/`)**:
  - Built with Apache Maven (`pom.xml`) targeting Java 21, LibGDX LWJGL3, Java-WebSocket, and Gson.
  - Bundled as a standalone 14.4MB fat jar: `viewer/target/alc-observatory-desktop.jar`.
  - **3D Voxel World**: Procedural 3D voxel terrain (grass, soil, translucent water, rocks, trees), dynamic crops (sprouts, mature food, poison berries), and dropped items.
  - **Dual Agent Avatars**: Stylized 3D models for **Alpha** (coral/gold) and **Roselia** (turquoise/violet) with real-time 3D facing arrows.
  - **Interactive 3D Camera**: Left-drag orbit, right-drag pan, mouse scroll zoom, and keyboard focus keys (`A` for Alpha, `R` for Roselia, `C` for Center).
  - **Observatory HUD**:
    - **Alpha Panel**: Color-coded biological meters (Energy, Water, Food, Health), current action, known states, memory count, successful experiences, exploration rate, learning events, recorded mistakes.
    - **Roselia Panel**: Independent real-time meters and cognitive telemetry for Roselia.
    - **Live Cognitive Event Stream**: Scrolling feed showing observations, causal actions, internal rewards (+hydration, +food, -damage), and model updates.
    - **Interactive Controls**: `[Space]` Pause/Play, `[N]` Step, `[1..5]` Speed (1-50 TPS).
- Launch scripts added: `run_server.bat` and `run_viewer.bat`.
- **Phase 4 Graphics & Garden Overhaul**:
  - **Procedural Texture Generator (`TexturePalette.java`)**: 100% self-contained HD procedural textures generated via `Pixmap` (lush grass with clover, furrowed tilled garden loam, caustic water, cobblestones, cedar timber planks, oak tree bark, leafy canopies, leather boots, and expressive face portraits for Alpha & Roselia).
  - **Lush 3D Garden World (`GardenMeshes.java` & `World3DRenderer.java`)**:
    - Sunken pond with cobblestone perimeter and floating translucent water lilies.
    - Raised wooden planter beds with dark loam soil for farming crops.
    - Branching sculpted apple trees with multi-tier leaf canopies and hanging apples.
    - Split-rail rustic wooden fence enclosing the 32x32 garden sanctuary.
    - 3D nature props: blooming poppies, daisies, lavenders, grass tufts, stone well, garden bench, and glowing amber lantern posts.
    - Dynamic atmospheric weather: rain streak particles and overcast mood during rain, warm sunny lighting with sky fill and rim light when clear.
  - **Articulated Humanoid Avatars (`AgentAvatar.java`)**:
    - Full anatomical articulation: shoulders, sleeved upper arms, elbows, forearms, hands with fingers, hips, thighs, knee joints, shins, and boots with soles.
    - Feminine aesthetic: Alpha (coral outfit, amber eyes, ponytail) and Roselia (turquoise outfit, jewel eyes, swept hair).
    - Smooth position & yaw interpolation (`lerp`) across simulation ticks.
    - Natural forward-kinematics bipedal walking gait: alternating hip swings, knee bends during back-swing, pelvis bobbing, and opposite arm swinging.
    - Idle breathing animation when stationary.
    - Item handling: both hands raise and cradle the actual 3D item (bucket, fruit, seed) when carried.
- All unit tests passing.

---

### Phase 6: Interactive Artificial Organisms — COMPLETE
- **Communication Architecture (`communication/`)**:
  - `message.py`: Protocol dataclass `Message`, `CommType` (`QUERY`, `ANSWER`, `STATEMENT`, `TEACH`, `AUTONOMOUS`, `UNKNOWN`), and explicit epistemic statuses (`KNOWN`, `UNKNOWN`, `UNCERTAIN`, `CONTRADICTORY`, `UNVERIFIED`, `CONFIRMED`, `REFUTED`).
  - `vocabulary.py`: `ConceptLexicon` and `GroundedConcept`. Enables agents to associate symbols with observed entities/actions through experience rather than preloaded English dictionaries.
  - `testimony.py`: `TestimonyBuffer` and `TestimonyClaim`. Communicated knowledge from other agents begins as `UNVERIFIED`. Receivers formulate empirical testing hypotheses, evaluate the outcome against the physical world, and only promote confirmed claims to their own world model.
  - `interpreter.py`: `MessageInterpreter` classifies queries into semantic intents (`query_what_is`, `query_effect`, `query_learned`, `query_status`, `teach`, `statement`) without an LLM.
  - `response_generator.py`: Generates truthful answers grounded strictly in retrieved episodic memories, need deltas, and state transition counts. Ungrounded or unexperienced concepts produce explicit `UNKNOWN` ("I don't know") responses with 0 confidence and 0 evidence.
  - `autonomous.py`: `AutonomousCommDecisionEngine` triggers spontaneous messages for high-utility discoveries, danger warnings (poison berries, health drops), and critical physiological distress.
  - `channel.py`: `CommunicationChannel` manages routing, history retention, and complete JSONL telemetry logging (`experiments/communication_log.jsonl`).
- **Independent Brains & Zero Memory Leakage**:
  - `brain/alpha/brain.py` and `brain/roselia/brain.py` maintain separate lexicons, testimony buffers, and cognitive evaluators.
  - Inter-agent communication occurs strictly over the explicit channel. Alpha cannot inspect Roselia's memory or internal state, and vice versa.
- **WebSocket Protocol Extensions**:
  - Added `chat_message` broadcast packet.
  - Added `human_message` and `teach_symbol` client commands.
  - Embedded real-time `communication` history in `tick_frame`.
- **Java / LibGDX 3D Observatory Interaction Console**:
  - Glassmorphic center interaction console with target selector (`[Alpha]`, `[Roselia]`, `[Both]`).
  - Direct keyboard input box with caret animation and `[ Send ]` button.
  - Quick question prompt pills ("What is water?", "What does water do?", "What did you learn?", "How do you feel?").
  - Live conversation history with color-coded sender tags and knowledge badges (`KNOWN`, `UNKNOWN`, `UNVERIFIED`, `CONFIRMED`).
  - Prominent autonomous communication notification banner.
- **Verification & Test Suite**:
  - 26/26 automated tests passing in ~1.0s (`tests/test_communication.py`, `tests/test_server.py`, etc.).
  - Zero external LLMs, AI APIs, or pretrained models used.

---

## Roadmap & Next Phases
1. **Phase 7: Symbolic Cultural Evolution**: Multi-generational symbol diffusion and spontaneous dialect development between Alpha and Roselia.
2. **Phase 8: Cooperative Tool Use & Construction**: Joint task coordination negotiated solely via learned communication tokens.

