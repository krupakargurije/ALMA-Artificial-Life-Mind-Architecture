# Artificial Learning Civilization (ALC)

A grounded simulation research platform where artificial beings start with minimal predefined knowledge in a garden world, perceive locally, act, and learn from consequences across lifetimes.

## Beings Living on the Planet
The simulation hosts exactly **two artificial beings**:
- **Alpha** (Agent 0, female) — autonomous learner with independent cognitive loop, memory, and world model in `brain/alpha/`.
- **Albedo** (Agent 1, female) — autonomous learner with independent cognitive loop, memory, and world model in `brain/albedo/`.

Neither agent shares internal memory or cognition with the other.

---

## Non-Negotiable Master Rules
1. **No LLMs or Pretrained Frameworks** in the brain loop.
2. **The World Owns the Rules; The Brain Discovers Them.**
3. **The Brain Sees Only Opaque Observations** and acts via integer IDs.
4. **The Viewer is an Observability Instrument** (pure event rendering and cognitive telemetry inspection).
5. **Deterministic & Seeded** across all runs.
6. **Fully Logged** steps and brain metrics in SQLite.
7. **No Solution-Encoding Reward Shaping.**
8. **Completely Independent Brains** in separate packages (`brain/alpha/` and `brain/albedo/`).

---

## 3D Desktop Observatory Viewer (Java / LibGDX)

The 3D Desktop Viewer communicates in real-time with the Python simulation engine over WebSockets (`ws://127.0.0.1:8765`).

```
Python Simulation Engine
├── World (32x32 Garden)
├── Alpha Brain (brain/alpha/)
├── Albedo Brain (brain/albedo/)
└── WebSocket Server (server/ws_server.py)
          │
          │  ws://127.0.0.1:8765
          ▼
Java / LibGDX 3D Desktop Viewer (viewer/)
├── 3D Voxel World (Grass, Soil, Water, Trees, Crops, Items)
├── Stylized 3D Avatars (Alpha & Albedo with facing arrows)
├── Alpha Observatory Panel (Energy, Water, Health, Known states, Memories, Learning events)
├── Albedo Observatory Panel (Independent meters & cognitive metrics)
├── Live Cognitive Event Stream (Observations, actions, rewards, memory updates)
└── Simulation Controls (Pause, Step, Speed 1x-50x)
```

### Running the Server & Viewer

#### 1. Start the Python WebSocket Server
```bash
# Using the launcher script
run_server.bat

# Or directly with Python
python -m server.ws_server --host 127.0.0.1 --port 8765 --seed 42 --tps 5.0
```

#### 2. Start the 3D Desktop Observatory Viewer
```bash
# Using the launcher script
run_viewer.bat

# Or directly with Java (standalone fat jar)
java -jar viewer/target/alc-observatory-desktop.jar

# Or via Maven
cd viewer
mvn exec:java
```

### Observatory Command Bar & Navigation HUD
The Observatory features a modern, clean top navigation bar that keeps the 3D garden view completely unobstructed:
- **`[ 💬 Console ]`**: Toggle the Human-Organism Interaction Console (or press **T**).
- **`[ 🔴 Alpha ]`**: Toggle Alpha's cognitive telemetry drawer (or press **1**).
- **`[ 🔵 Roselia ]`**: Toggle Roselia's cognitive telemetry drawer (or press **2**).
- **`[ 📜 Events ]`**: Toggle the live cognitive event stream (or press **3**).
- **`[ 👁 Clean ]`**: Instant Clean View mode to hide/show all panels for an unobstructed 3D view (or press **V**).
- Each panel features a **`[✕]`** close button in its top-right corner.

| Key / Input | Action |
|-------------|--------|
| **Left Click + Drag** | Orbit 3D camera around garden |
| **Right Click + Drag** | Pan camera view |
| **Mouse Scroll** | Zoom in / out |
| **T** or **/** | Toggle Interaction Console |
| **1** | Toggle Alpha Telemetry Panel |
| **2** | Toggle Roselia Telemetry Panel |
| **3** | Toggle Event Stream |
| **V** | Toggle Clean View Mode (hide all panels) |
| **Space** | Pause / Resume simulation |
| **N** | Advance single tick (step mode) |
| **A** | Focus camera on Alpha |
| **R** | Focus camera on Roselia |
| **C** | Reset camera to garden center |


---

## Phase 6: Interactive Artificial Organisms

Phase 6 introduces a fully grounded communication framework between humans and artificial beings, as well as between Alpha and Roselia themselves.

> **CRITICAL ARCHITECTURAL PRINCIPLE**:
> **This system does not use an external LLM, pretrained language model, chatbot API, or cloud AI service.**
> Alpha and Roselia formulate responses exclusively through:
> - Direct episodic memories of their own experiences
> - Tabular state-action transitions learned from the physical simulation
> - Biological needs drives (hydration, energy, health)
> - Private concept lexicons grounded via direct observation or teaching
>
> When asked about an unencountered or ungrounded concept, the beings produce an honest, explicit `UNKNOWN` ("I don't know") state with 0.0 confidence and 0 evidence.

### Basic English Conversation Training
Alpha and Roselia have undergone foundational experiential English training ([`communication/training.py`](file:///d:/antigravity_projects/Alpha/communication/training.py)) covering:
- **Greetings & Identity**: *"Hello!"*, *"Who are you?"*, *"Who is Roselia?"*
- **Bodily Needs & Drives**: *"Are you thirsty?"*, *"Are you hungry?"*, *"Are you tired?"*, *"How do you feel?"*
- **Activity & Location**: *"What are you doing?"*, *"Where are you?"*
- **World Concepts**: *"What is water?"*, *"What is fruit?"*, *"What does poison do?"*, *"What is a seed?"*
- **Strict Epistemic Unknowns**: Asking about unexperienced/untrained concepts (*"What is an airplane?"*, *"What is a computer?"*) produces an explicit, honest **`UNKNOWN`** response (*"I don't know what '<word>' is."*) with 0 confidence and 0 hallucination.

To run the interactive training and dialogue evaluation test harness:
```bash
python -m experiments.train_basic_english
```

---

## CLI & Experiment Tools

### Running Tests
```bash
python -m pytest
```

### Running Headless Experiments
```bash
python -m experiments.run_experiment --agent alpha --seed 42 --ticks 1000
python -m experiments.run_experiment --agent roselia --seed 777 --ticks 1000
```

### ASCII World Demo
```bash
python -m sim.render_ascii
```

### Reproduce Baseline (20 Seeds)
```bash
python -m experiments.run_baseline
```
