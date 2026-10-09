# Architectural & Design Decisions

This document records key design decisions, rationale, alternatives considered, and tradeoffs made during the development of ALC.

---

### DECISION-001: Default Choices for Open Decisions D1, D2, D3
- **Date**: 2026-10-05
- **Context**: The build plan establishes three open decisions (D1: Viewer Technology, D2: ML Framework for Phase 3, D3: Respawn Policy).
- **Decision**: 
  - **D1 (Viewer)**: React + Three.js browser frontend communicating via WebSocket protocol. Provides fast iteration and zero-install visualization.
  - **D2 (Model)**: NumPy-only tabular/count-based world model for Phase 3, transitioning to neural networks only if tabular approach saturates.
  - **D3 (Respawn)**: Respawn after death with brain memory/model intact (learning from mistakes across lifetimes).
- **Alternatives Considered**: Java + LibGDX (heavy runtime dependency), PyTorch from day 1 (overkill for initial discrete dynamics), permanent death with genetic selection (deferred to post Phase 7).
- **Consequences**: Keeps dependencies minimal, architecture modular, and focus on fundamental grounding.

---

### DECISION-002: Grid Coordinate System & Direction Conventions
- **Date**: 2026-10-05
- **Context**: 32x32 world grid requires consistent coordinate and orientation semantics.
- **Decision**:
  - `(x, y)` where `x` is column (0 to width-1, East-West), `y` is row (0 to height-1, North-South).
  - Directions: `North` (dy = -1, dx = 0), `South` (dy = +1, dx = 0), `East` (dy = 0, dx = +1), `West` (dy = 0, dx = -1).
  - Facing direction is maintained in agent state. Movement actions (`MOVE_N`, `MOVE_S`, `MOVE_E`, `MOVE_W`) update facing direction.
- **Alternatives Considered**: Orientation-relative movement (TURN_LEFT, MOVE_FORWARD).
- **Reason**: Cardinal movement is standard in gridworld benchmarks, and tracking facing direction allows `USE_ON_FACING` to have unambiguous targets.

---

### DECISION-003: Opaque Integer IDs for Tiles, Entities, Actions, and Events
- **Date**: 2026-10-05
- **Context**: Non-negotiable rule #3 mandates that the brain sees only observations and chooses from opaque action IDs, without access to human-readable names or internal types.
- **Decision**:
  - **Tile IDs**: `0: OUT_OF_BOUNDS`, `1: GRASS`, `2: SOIL`, `3: WATER`, `4: TREE`.
  - **Entity/Item IDs**: `0: NONE`, `10: SEED`, `11: SEEDLING`, `12: MATURE_PLANT`, `13: GOOD_FRUIT`, `14: POISON_BERRY`, `15: WATER_CONTAINER_EMPTY`, `16: WATER_CONTAINER_FULL`, `20: OTHER_AGENT`.
  - **Actions**: `0: WAIT`, `1: MOVE_N`, `2: MOVE_S`, `3: MOVE_E`, `4: MOVE_W`, `5: PICK_UP`, `6: DROP`, `7: USE_ON_FACING`, `8: EAT`, `9: DRINK`, `10: DIG`, `11..14: EMIT_SIGNAL_0..3`.
  - **Events**: `0: NONE`, `1: MOVED`, `2: BLOCKED`, `3: PICKED_UP`, `4: DROPPED`, `5: USED_ITEM`, `6: ATE_FOOD`, `7: ATE_POISON`, `8: DRANK_WATER`, `9: DUG_SOIL`, `10: TOOK_DAMAGE`, `11: HEALED`, `12: DIED`, `13: RESPAWNED`, `14: RAINED`.
- **Reason**: Strict boundary enforcement. The brain operates strictly over numbers, ensuring no leaking of semantics or cheat code in reward/action selection.

---

### DECISION-004: Observation View Representation
- **Date**: 2026-10-05
- **Context**: Brain receives a 7x7 local grid observation centered on the agent.
- **Decision**:
  - `view` is a 7x7 2D integer array centered at relative offset (0, 0) corresponding to `view[3][3]`.
  - If an entity occupies a tile (e.g. a seed on soil, or a plant), the cell presents the opaque entity ID; otherwise it presents the underlying tile ID.
  - Cells outside the map boundaries are filled with `OUT_OF_BOUNDS (0)`.
- **Reason**: Matches the specification `int[7][7]` directly without multi-channel complexity, while providing all information locally visible.

---

### DECISION-005: USE_ON_FACING Target Resolution
- **Date**: 2026-10-05
- **Context**: Generic interaction action `USE_ON_FACING` operates on the faced tile. When an agent stands directly on cultivable soil, it cannot face its own feet without moving.
- **Decision**:
  - Priority target is `facing_tile` (`x + fdx, y + fdy`).
  - Fallback target is `current_tile` (`x, y`) if facing tile cannot accept the interaction (e.g. wall, boundary, or grass).
- **Reason**: Prevents artificial movement oscillations and preserves natural interaction physics in discrete grid worlds.

---

### DECISION-006: PICK_UP Harvesting Precedence
- **Date**: 2026-10-05
- **Context**: Cells can contain both ground items (e.g. dropped tools/seeds) and upright plants with ripe fruit.
- **Decision**:
  - `PICK_UP` prioritizes harvesting ripe fruit from plants (facing tile, then current tile) before picking up loose ground items.
- **Reason**: Harvesting edible produce from living crops is logically primary over picking up loose ground litter.

---

### DECISION-007: Non-Overlapping Initial Resource Placement
- **Date**: 2026-10-05
- **Context**: Procedural world generation previously could place containers and seeds at identical coordinate pairs.
- **Decision**:
  - `_generate_world` requires `(x, y) not in self.ground_items` when populating initial seeds and containers.
- **Reason**: Ensures clean visual grounding and avoids occluding essential seeds beneath non-survival items.

---

### DECISION-008: SQLite Experiment Logging & Replay Architecture
- **Date**: 2026-10-05
- **Context**: Section 7 requires full observability: per-life summary, per-tick action log, brain stats snapshots, and a replay file for viewer playback.
- **Decision**:
  - Dedicated SQLite logger with tables `runs`, `lives`, and `step_logs`.
  - Batched buffered execution (`batch_size=500`) to guarantee high-performance headless execution (> 10,000 ticks/sec).
  - Standalone JSON replay export capturing agent state, actions, and events for zero-overhead viewer playback.
- **Reason**: Balances queryability, write speed, and decoupling of viewer playback from raw database locks.

---

### DECISION-009: Baseline Metric Aggregation & Confidence Interval Methodology
- **Date**: 2026-10-05
- **Context**: Evaluating 20 random seeds requires standard statistical reporting to prevent cherry-picking and establish a rigorous benchmark for Phase 3.
- **Decision**:
  - Report Mean, Median, Min, Max, Standard Deviation, and 95% Confidence Interval ($1.96 \times \frac{s}{\sqrt{n}}$).
  - Primary benchmark metric: Mean Ticks Survived per Life.
- **Reason**: Ensures that future learning brains can be evaluated with statistical significance rather than anecdotal runs.

---

### DECISION-010: Separate Brain Packages for Alpha and Roselia (Females)
- **Date**: 2026-10-05
- **Context**: The user explicitly specified that exactly two people live on the planet ("Alpha" and "Roselia", both females) and requested that their brains be developed separately in separate folders so their thoughts, memories, and models can be clearly viewed and understood individually.
- **Decision**:
  - Agent 0 is designated **Alpha** (female).
  - Agent 1 is designated **Roselia** (female).
  - Developed `brain/alpha/` containing `AlphaBrain` with Alpha's own episodic memory and tabular world model.
  - Developed `brain/roselia/` containing `RoseliaBrain` with Roselia's own episodic memory and tabular world model.
  - Shared domain-agnostic perception & mathematical utilities reside in `brain/common/`.
- **Reason**: Ensures zero state leakage or parameter sharing between the two beings, while providing maximum clarity for human inspection of their respective minds.

---

### DECISION-011: Java / LibGDX 3D Desktop Observatory Viewer with Maven & WebSocket
- **Date**: 2026-10-05
- **Context**: The user requested a Java / LibGDX 3D Desktop Viewer acting as an observability system and research instrument rather than merely passive graphics, allowing real-time inspection of Alpha and Roselia's physiological meters, internal cognitive stats, and live learning causality event streams.
- **Decision**:
  - Built `viewer/` using Apache Maven 3.9.11 targeting Java 21, LibGDX LWJGL3 backend, Java-WebSocket, and Gson.
  - Bundled as a standalone fat jar `viewer/target/alc-observatory-desktop.jar` via `maven-shade-plugin`.
  - Implemented procedural 3D voxel models (grass, soil, water, rocks, trees, crops, items) and distinct 3D avatars for Alpha and Roselia with facing indicators.
  - Implemented a 2D glassmorphic Observatory HUD displaying independent biological meters, cognitive metrics (known states, memories, successful experiences, exploration rate, learning events, recorded mistakes), and a live scrolling cognitive causality stream.
  - Full bidirectional simulation controls over WebSockets (`ws://127.0.0.1:8765`): Pause/Play, Step, Speed adjustment (1-50 TPS).
- **Reason**: Provides a high-performance, native OpenGL desktop research station that isolates the simulation physics and brain algorithms in Python while providing complete real-time observability.

---

### DECISION-012: Knowledge-Grounded Communication Without Pretrained Models or LLMs
- **Date**: 2026-10-05
- **Context**: Phase 6 introduces multi-directional communication (Human → Alpha/Roselia, Alpha ↔ Roselia, and Autonomous). The core philosophy dictates that intelligence cannot be faked or imported via external LLMs, pretrained models, AI APIs (OpenAI, Gemini, Anthropic), or agent frameworks.
- **Decision**:
  - Organisms answer questions strictly using evidence retrieved from their own episodic memory, learned state-action transition frequencies, and internal need drives.
  - Mandatory `UNKNOWN` state: If a concept is ungrounded or unsupported by evidence, the organism explicitly responds "I don't know" with 0.0 confidence and 0 evidence count. No hallucination or pretrained linguistic fabrication.
  - Private lexicons (`ConceptLexicon`): Organisms associate human symbols with observed entities/actions through experience and teaching, rather than preloaded English dictionaries.
- **Reason**: Guarantees epistemic honesty and provides a valid scientific substrate to measure true emergent cognition.

---

### DECISION-013: Unverified Testimony and Empirical Hypothesis Testing Between Agents
- **Date**: 2026-10-05
- **Context**: When Alpha communicates a claim to Roselia (e.g. "water reduces thirst"), allowing Roselia to immediately incorporate it as objective fact would bypass her own cognitive validation and violate brain isolation.
- **Decision**:
  - Received claims are stored in an independent `TestimonyBuffer` marked `UNVERIFIED`.
  - The receiving agent formulates an empirical hypothesis and tests the claimed action in the physical environment.
  - Only when the simulated outcome matches the claim is the testimony promoted to `CONFIRMED` and integrated into her personal world model. If the outcome contradicts the claim, it is marked `REFUTED`.
  - All communication events and cognitive traces are persisted to `experiments/communication_log.jsonl` for longitudinal research analysis.
- **Reason**: Preserves strict empirical epistemology, prevents informational contagion, and models genuine scientific inquiry within artificial life.


