# Artificial Learning Civilization — Agent Build Plan

**Audience:** an AI coding agent (Claude Code or similar) building this repo from scratch.
**Owner:** Krupakar. Ask him before changing anything under "Open decisions" (section 9).

## 1. Goal (one paragraph)

Two artificial beings start with no task-specific knowledge in a small 3D-looking garden world. They have needs (energy, water, food, health), perceive locally, act, and learn from consequences. Learning persists across sessions. Later they communicate and teach each other. The brain is written from scratch. A separate viewer lets a human watch and inspect them.

First research question to answer:
> Can a system with minimal predefined knowledge acquire persistent, transferable knowledge by interacting with an environment and another agent?

## 2. Non-negotiable rules

1. **No LLMs, pretrained models, or agent frameworks** (no OpenAI/Anthropic/Gemini/Llama calls, LangChain, etc.) anywhere in the brain. Plain NumPy, SQLite, and standard libraries are fine. PyTorch is allowed only for small networks trained from scratch, and only from Phase 3 onward; start without it.
2. **The world owns the rules; the brain discovers them.** Never write code that says "if near seed then plant" or "water makes plants grow" inside a brain, a reward function, or the viewer.
3. **The brain sees only observations and chooses from opaque action IDs.** It must not read world internals (plant growth timers, tile types by name, other agent's memory).
4. **The viewer is dumb.** It renders events it receives. It never decides anything.
5. **Everything is seeded and reproducible.** One master seed per run; same seed gives same run.
6. **Everything is logged.** Every step writes observation, action, outcome, and key brain stats to the run log.
7. **No reward shaping that encodes the solution.** Allowed drives: survival needs (hunger/thirst/health deltas) and generic curiosity/novelty. Not allowed: reward for "planted seed" or "watered plant."

## 3. Architecture

```
┌────────────┐   observations     ┌────────────┐
│   World    │ ─────────────────► │  Brain A   │
│ simulation │ ◄───────────────── │  Brain B   │   (Python, independent
│ (rules,    │   action IDs       └────────────┘    objects, own memory)
│  physics)  │
└─────┬──────┘
      │ events (JSON over WebSocket)
      ▼
┌────────────┐
│  Viewer    │   3D voxel-style rendering + inspector panel
└────────────┘
```

- **Simulation + brains:** Python 3.11+. Single process, headless-capable, runs far faster than real time.
- **Server:** Python WebSocket server (`websockets` or FastAPI) that streams events and accepts viewer commands (pause, speed, select agent).
- **Viewer:** see Open decision D1. Default recommendation: React + three.js voxel renderer in the browser.
- **Storage:** SQLite for run logs and brain snapshots at first.

### Repo layout

```
alc/
  README.md
  BUILD_PLAN.md          (this file)
  PROGRESS.md            (agent updates after every phase)
  DECISIONS.md           (agent records every design choice + why)
  pyproject.toml
  sim/
    world.py             tiles, entities, rules, tick()
    entities.py          Seed, Plant, Fruit, WaterSource, Agent body
    needs.py             energy, water, food, health dynamics
    actions.py           fixed action set with opaque integer IDs
    observation.py       builds the local observation for one agent
    config.py            world parameters, seeds, difficulty knobs
  brain/
    interface.py         Brain base class (observe, act, learn, save, load)
    random_brain.py      baseline
    learner_v1.py        first real learning brain (Phase 3)
    memory.py            episodic memory store
    persistence.py       save/load brain state
  comms/                 (Phase 6) signal channel
  server/
    ws_server.py         event stream + control commands
    protocol.md          message schemas
  viewer/                web (or Java) frontend
  experiments/
    run_experiment.py    CLI: config + seed -> logs + metrics
    metrics.py
    analysis.ipynb
  tests/
```

## 4. Core interfaces (implement exactly these first)

```python
# brain/interface.py
class Brain:
    def reset_episode(self) -> None: ...            # NOT knowledge reset; only transient state
    def observe(self, obs: "Observation") -> None: ...
    def act(self) -> int: ...                       # returns an action ID
    def learn(self, outcome: "Outcome") -> None: ...# called after the world responds
    def save(self, path: str) -> None: ...
    def load(self, path: str) -> None: ...
    def stats(self) -> dict: ...                    # for the inspector panel
```

```python
# sim/observation.py
Observation = {
  "tick": int,
  "self": {"energy": float, "water": float, "food": float, "health": float,
           "holding": int | None},      # opaque item-type ID, not a name
  "view": int[7][7],                    # local grid around the agent, opaque tile/entity IDs
  "others": [ {"rel_x": int, "rel_y": int, "signal": int | None} ],
  "events": [int],                      # opaque IDs of things that just happened to me
}
Outcome = {"obs_next": Observation, "need_delta": {...}, "alive": bool}
```

Opaque IDs matter: the brain gets `3`, not `"seed"`. The viewer maps IDs to visuals; the brain never sees names.

### Action set (v1, fixed, small)

`MOVE_N, MOVE_S, MOVE_E, MOVE_W, PICK_UP, DROP, USE_ON_FACING (generic), EAT, DRINK, WAIT, DIG, EMIT_SIGNAL_k` (signals disabled until Phase 6).

`USE_ON_FACING` is deliberately generic: planting and watering emerge from using the held item on the faced tile. The world decides what that does.

## 5. World rules (v1, in `sim/world.py` only)

- Grid world, 32×32, tiles: grass, soil, water, tree. 3D look is a viewer concern; the sim stays 2D grid + height ignored.
- Seeds: pick up, then use on soil → planted seedling.
- Seedling grows into plant only if adjacent/wet for N ticks (water via a water-carrying item or rain). Plant yields fruit after M ticks.
- Fruit: EAT restores food/energy. Some berries (a second fruit type) reduce health, so there is something to learn to avoid.
- Needs decay each tick; water and food replenish only via DRINK/EAT. Zero health = death → respawn with brain memory intact (this is the "learning from mistakes" loop), counted as one life.
- Curriculum knobs in `config.py` (start easy): seeds and water placed close to the spawn, slow need decay, rain boosting growth. Make harder later by config only.

## 6. Phases (do them in order; do not start the next until acceptance passes)

Each phase ends with: tests green, a short demo command in README, and a `PROGRESS.md` entry (what was built, what was learned, open problems).

### Phase 0 — Scaffold (small)
- Create repo layout, `pyproject.toml`, lint/test setup (pytest, ruff), CI config.
- **Accept:** `pytest` runs (even if trivial), `python -m experiments.run_experiment --help` works.

### Phase 1 — Headless world
- Implement `sim/` per section 5, deterministic with a seed.
- ASCII renderer for debugging (`python -m sim.render_ascii`).
- Unit tests: planting needs a seed on soil; growth needs water; eating raises food; poison berry lowers health; needs decay; death triggers respawn; same seed → identical world after 1000 ticks.
- **Accept:** a scripted "oracle" test (lives only in `tests/`, never imported by brains) can survive 5,000 ticks, proving the world is solvable.

### Phase 2 — Brain interface, random baseline, harness
- Implement `Brain` interface, `RandomBrain`, and `run_experiment.py` (config + seed -> run log in SQLite + metrics JSON).
- Metrics: ticks survived per life, food eaten, plants successfully grown, distinct action-outcome pairs tried, deaths.
- Run 20 seeds of RandomBrain to get the baseline distribution.
- **Accept:** reproducible baseline report committed in `experiments/results/baseline.md`.

### Phase 3 — First learning brain (`learner_v1`)
Build in this order, testing each addition against the baseline:
1. **Episodic memory:** store (obs, action, outcome) tuples; efficient local-view hashing.
2. **Learned world model:** predict next observation features and need deltas from (obs, action). Start with a count-based / tabular model over a compact state abstraction; only move to a small NumPy/PyTorch net if tabular saturates.
3. **Intrinsic drive:** novelty/curiosity (prediction error or visit counts) plus need-based drives (hunger, thirst, health deltas). No task-specific reward.
4. **Action selection:** epsilon-greedy or UCB over model-predicted value, with exploration decaying on experience, not on wall-clock.
5. **Mistake memory:** actions that led to negative need deltas in a context get reduced value, but remain re-testable.
- **Accept (measurable):** over the same seeds, `learner_v1` beats RandomBrain on mean ticks survived with a statistically meaningful margin (report mean ± CI); logs show it eventually performs the pick-up → plant → water → wait → eat chain without any code naming that chain. If it does not discover it, record that honestly in `PROGRESS.md` and iterate on the brain or curriculum knobs, not the rules.

### Phase 4 — Server + viewer
- `ws_server.py` streams per-tick events; schema in `server/protocol.md`:
  `world_init`, `tick`, `entity_update`, `agent_action`, `agent_stats`, `death`, `respawn`.
- Control messages from viewer: `pause`, `resume`, `set_speed`, `select_agent`, `reset_run`.
- Viewer renders voxel-style terrain, two characters, simple walk/pick/plant/eat animations, driven only by events.
- Inspector panel per brain: current action, needs, memory size, success rate, exploration rate, recent decisions.
- **Accept:** run the sim, open the viewer, watch two brains live; pausing and speed control work; viewer contains no game logic (review for this).

### Phase 5 — Persistence and continuous learning
- Save/load full brain state (memory + model) per agent; autosave every N ticks.
- A run can be stopped and resumed; "Day 1 knowledge still present on Day 10" test: train, save, reload, show retained performance.
- **Accept:** resumed brain's survival on a fresh seed ≥ a brain that never learned; no catastrophic forgetting on the earlier skill in a regression test.

### Phase 6 — Two brains interacting
- Agents see each other in `others`. Brains remain fully separate objects.
- Add a **signal channel**: `EMIT_SIGNAL_k` for k in a small set (e.g. 4), no predefined meaning, small energy cost; visible to nearby agents as an opaque ID.
- Experiments (run with ≥20 seeds each): no signals vs signals; agents learning alone vs together.
- Metrics: does a signal correlate with a resource/event (mutual information between signal ID and context)? Does a naive agent's behavior change after seeing a signal?
- **Accept:** a written result, positive or negative, with the numbers. Copying one brain's parameters into another is forbidden as "teaching."

### Phase 7 — Experiment framework
- Config-driven experiments, ablations (memory off, curiosity off, model off), plots, and a results README.
- **Accept:** one command reproduces every figure in the results README.

### Later (not part of the first build)
Generations and evolution, storage and tools, harder worlds, a Java/LibGDX or Unity viewer, more than two agents. Only after Phases 0–7.

## 7. Observability requirements (apply from Phase 2 on)

Every run produces: per-life summary, per-tick action log, brain stats snapshots, and a replay file the viewer can play back. "Why did it do that?" must always be answerable from the logs.

## 8. Working rules for the agent

1. Plan before coding each phase: write a half-page plan into `PROGRESS.md`, then implement.
2. Small commits, one concern each. Tests alongside code.
3. After each phase, stop and report: what works, evidence (metrics/commands), what you are unsure about. Wait for approval before the next phase.
4. Record every non-obvious design choice in `DECISIONS.md` (choice, alternatives, reason).
5. If a rule in section 2 would be violated by the easiest solution, do the harder solution or ask. Never quietly hard-code knowledge.
6. If a result is negative (the brain does not learn), report it plainly. Do not tune the world until the result looks good without saying so.
7. Keep Phase 3 simple first. A tabular model that demonstrably learns beats a neural net that doesn't.

## 9. Open decisions (ask the owner)

- **D1 — Viewer technology.** Default: React + three.js (browser), since the protocol is language-agnostic and iteration is fastest. Alternative: Java + LibGDX as the original doc suggested. Switching later only means reimplementing the viewer against `protocol.md`.
- **D2 — Torch or no Torch for Phase 3.** Default: NumPy-only until tabular approach saturates.
- **D3 — Respawn policy.** Default: respawn after death with memory intact. Alternative: permanent death plus generations (moves toward evolution, later).

## 10. First prompt to give the agent

> Read `BUILD_PLAN.md` fully. Do Phase 0 and Phase 1 only. Before writing code, put a short implementation plan in `PROGRESS.md`. Follow the rules in section 2 strictly: no LLMs, no hard-coded knowledge in brains, opaque IDs, seeded determinism. When Phase 1's acceptance tests pass, stop and give me a report with the commands to run the ASCII demo. Do not begin Phase 2 until I say so. Use the defaults for D1–D3 unless I tell you otherwise.
