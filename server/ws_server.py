"""WebSocket streaming server for ALC simulation and viewer observatory.

Broadcasts real-time 3D world state, physiological needs, and cognitive event streams
to connected 3D desktop/browser viewers.
"""

import asyncio
import json
import os
import sys
from typing import Any, Dict, List, Optional, Set

import websockets
from websockets.server import WebSocketServerProtocol

from brain.alpha.brain import AlphaBrain
from brain.albedo.brain import AlbedoBrain
from communication import CommunicationChannel, CommType, KnowledgeStatus, Message
from communication.training import train_basic_english
from sim.actions import (
    DIG, DRINK, DROP, EAT, MOVE_E, MOVE_N, MOVE_S, MOVE_W, PICK_UP,
    USE_ON_FACING, WAIT,
)
from sim.config import WorldConfig
from sim.entities import (
    EVENT_ATE_FOOD, EVENT_ATE_POISON, EVENT_BLOCKED, EVENT_DIED,
    EVENT_DRANK_WATER, EVENT_DROPPED, EVENT_DUG_SOIL, EVENT_HEALED,
    EVENT_MOVED, EVENT_PICKED_UP, EVENT_RAINED, EVENT_RESPAWNED,
    EVENT_TOOK_DAMAGE, EVENT_USED_ITEM,
)
from sim.world import World

ACTION_NAMES = {
    WAIT: "WAIT",
    MOVE_N: "MOVE_NORTH",
    MOVE_S: "MOVE_SOUTH",
    MOVE_E: "MOVE_EAST",
    MOVE_W: "MOVE_WEST",
    PICK_UP: "PICK_UP",
    DROP: "DROP",
    USE_ON_FACING: "USE_ON_FACING",
    EAT: "EAT",
    DRINK: "DRINK",
    DIG: "DIG",
}

EVENT_DESCRIPTIONS = {
    EVENT_MOVED: "moved to adjacent tile",
    EVENT_BLOCKED: "movement blocked by obstacle",
    EVENT_PICKED_UP: "harvested / picked up item",
    EVENT_DROPPED: "dropped held item on ground",
    EVENT_USED_ITEM: "used held item on tile (planted/watered)",
    EVENT_ATE_FOOD: "consumed fruit (food/energy restored)",
    EVENT_ATE_POISON: "consumed toxic berry (damage suffered!)",
    EVENT_DRANK_WATER: "drank water (hydration restored)",
    EVENT_DUG_SOIL: "tilled grass into cultivable soil",
    EVENT_TOOK_DAMAGE: "took health damage",
    EVENT_HEALED: "health regenerated naturally",
    EVENT_DIED: "succumbed to physiological exhaustion",
    EVENT_RESPAWNED: "respawned with memory intact",
    EVENT_RAINED: "rain shower fell across garden",
}


class SimulationServer:
    """Orchestrates simulation execution and WebSocket broadcast."""

    def __init__(self, seed: int = 42, host: str = "127.0.0.1", port: int = 8765):
        self.host = host
        self.port = port
        self.seed = seed
        self.tps: float = 5.0  # Ticks per second
        self.is_paused: bool = False
        self.step_once: bool = False

        self.connected_clients: Set[WebSocketServerProtocol] = set()

        # World and Brain initialization
        self.init_simulation(seed)

    def init_simulation(self, seed: int) -> None:
        """Initialize or reset world and both learning brains."""
        self.seed = seed
        self.config = WorldConfig(seed=seed)
        self.world = World(config=self.config, num_agents=2)

        # Alpha (Agent 0, female) and Albedo (Agent 1, female)
        self.alpha_brain = AlphaBrain(seed=seed)
        self.albedo_brain = AlbedoBrain(seed=seed + 999)
        self.roselia_brain = self.albedo_brain  # alias
        self.brains = {0: self.alpha_brain, 1: self.albedo_brain}

        # Central Communication Channel & Research Logger
        self.channel = CommunicationChannel()

        # Foundational English language training
        train_basic_english(self.alpha_brain, agent_id=0)
        train_basic_english(self.albedo_brain, agent_id=1)

    def build_world_init_message(self) -> Dict[str, Any]:
        """Construct full world initialization payload."""
        return {
            "type": "world_init",
            "width": self.config.width,
            "height": self.config.height,
            "seed": self.seed,
            "tiles": self.world.grid,
            "agents": [
                {
                    "id": a.agent_id,
                    "name": a.name,
                    "gender": a.gender,
                    "x": a.x,
                    "y": a.y,
                }
                for a in self.world.agents
            ],
        }

    def step_tick(self) -> Dict[str, Any]:
        """Advance one tick of dual-agent simulation and return frame."""
        actions: Dict[int, int] = {}
        agents_data: List[Dict[str, Any]] = []

        # 1. Perception & Action Selection
        for agent in self.world.agents:
            aid = agent.agent_id
            brain = self.brains[aid]
            obs = self.world.get_observation(aid)
            brain.observe(obs)
            action = brain.act()
            actions[aid] = action

        # 2. Simulation Physics Step
        outcomes = self.world.tick(actions)

        # 3. Learning & Observability Frame Assembly
        all_events: List[Dict[str, Any]] = []
        for agent in self.world.agents:
            aid = agent.agent_id
            brain = self.brains[aid]
            outcome = outcomes[aid]
            brain.learn(outcome)

            action_id = actions[aid]
            action_name = ACTION_NAMES.get(action_id, f"ACTION_{action_id}")
            brain_stats = brain.stats()

            agents_data.append({
                "id": aid,
                "name": agent.name,
                "gender": agent.gender,
                "x": agent.x,
                "y": agent.y,
                "facing": list(agent.facing),
                "holding": agent.holding,
                "needs": agent.needs.to_dict(),
                "alive": outcome["alive"],
                "lives": agent.lives,
                "cognition": {
                    "current_action": action_id,
                    "action_name": action_name,
                    "known_states": brain_stats.get("known_states", 0),
                    "memory_size": brain_stats.get("memory_size", 0),
                    "successful_experiences": brain_stats.get("successful_experiences", 0),
                    "exploration_rate": brain_stats.get("exploration_rate", 0.0),
                    "learning_events": brain_stats.get("learning_events", 0),
                    "recorded_mistakes": brain_stats.get("recorded_mistakes", 0.0),
                    "total_steps": brain_stats.get("total_steps", 0),
                },
            })

            # Process event stream logs with cognitive causality
            for evt_id in outcome.get("obs_next", {}).get("events", []):
                evt_desc = EVENT_DESCRIPTIONS.get(evt_id, f"event_{evt_id}")
                all_events.append({
                    "tick": self.world.tick_count,
                    "agent_name": agent.name,
                    "event_id": evt_id,
                    "text": f"{agent.name} {evt_desc}",
                    "category": "action",
                })

            # Biological feedback events
            need_delta = outcome.get("need_delta", {})
            for need_key, delta_val in need_delta.items():
                if delta_val > 5.0:
                    all_events.append({
                        "tick": self.world.tick_count,
                        "agent_name": agent.name,
                        "event_id": 901,
                        "text": f"{agent.name}: Positive internal reward (+{delta_val:.0f} {need_key})",
                        "category": "reward",
                    })
                elif delta_val < -10.0 and need_key == "health":
                    all_events.append({
                        "tick": self.world.tick_count,
                        "agent_name": agent.name,
                        "event_id": 902,
                        "text": f"{agent.name}: Negative reward ({delta_val:.0f} health damage)",
                        "category": "damage",
                    })

            # Cognitive learning state notification
            has_major_event = any(
                e in outcome.get("obs_next", {}).get("events", [])
                for e in (EVENT_DRANK_WATER, EVENT_ATE_FOOD, EVENT_ATE_POISON, EVENT_DIED)
            )
            if has_major_event or (self.world.tick_count % 20 == 0 and aid == 0):
                all_events.append({
                    "tick": self.world.tick_count,
                    "agent_name": agent.name,
                    "event_id": 903,
                    "text": f"{agent.name}: World model & memory updated (known_states={brain_stats.get('known_states', 0)})",
                    "category": "learning",
                })

        # 4. Check Autonomous Communication
        # Alpha -> Albedo / Human
        auto_alpha = self.alpha_brain.check_autonomous_communication(
            self.world.tick_count, outcomes[0], "Albedo"
        )
        if auto_alpha:
            self.channel.send(auto_alpha)
            all_events.append({
                "tick": self.world.tick_count,
                "agent_name": "Alpha",
                "event_id": 910,
                "text": f"Alpha communicated: '{auto_alpha.content}'",
                "category": "learning",
            })
            # If destined for Albedo, deliver as testimony
            if auto_alpha.receiver.lower() in ["albedo", "roselia", "all", "both"]:
                rec_resp = self.albedo_brain.receive_message(auto_alpha, self.world.tick_count)
                self.channel.send(rec_resp)
                all_events.append({
                    "tick": self.world.tick_count,
                    "agent_name": "Albedo",
                    "event_id": 912,
                    "text": f"Albedo received message from Alpha -> marked UNVERIFIED",
                    "category": "learning",
                })

        # Albedo -> Alpha / Human
        auto_albedo = self.albedo_brain.check_autonomous_communication(
            self.world.tick_count, outcomes[1], "Alpha"
        )
        if auto_albedo:
            self.channel.send(auto_albedo)
            all_events.append({
                "tick": self.world.tick_count,
                "agent_name": "Albedo",
                "event_id": 911,
                "text": f"Albedo communicated: '{auto_albedo.content}'",
                "category": "learning",
            })
            # If destined for Alpha, deliver as testimony
            if auto_albedo.receiver.lower() in ["alpha", "all", "both"]:
                rec_resp = self.alpha_brain.receive_message(auto_albedo, self.world.tick_count)
                self.channel.send(rec_resp)
                all_events.append({
                    "tick": self.world.tick_count,
                    "agent_name": "Alpha",
                    "event_id": 913,
                    "text": f"Alpha received message from Albedo -> marked UNVERIFIED",
                    "category": "learning",
                })

        # Plants list
        plants_data = [
            {
                "x": p.x,
                "y": p.y,
                "stage": p.stage,
                "has_fruit": p.has_fruit,
                "fruit_type": p.fruit_type,
            }
            for p in self.world.plants.values()
        ]

        # Ground items list
        ground_items_data: List[Dict[str, Any]] = []
        for (gx, gy), items in self.world.ground_items.items():
            for itm in items:
                ground_items_data.append({"x": gx, "y": gy, "entity_id": itm.entity_id})

        # Recent communication history for UI
        comm_history = [m.to_dict() for m in self.channel.get_history(30)]

        return {
            "type": "tick_frame",
            "tick": self.world.tick_count,
            "weather": "RAINING" if self.world.is_raining() else "CLEAR",
            "is_raining": self.world.is_raining(),
            "is_paused": self.is_paused,
            "agents": agents_data,
            "plants": plants_data,
            "ground_items": ground_items_data,
            "events": all_events,
            "communication": comm_history,
        }

    async def process_human_message(self, target: str, text: str) -> None:
        """Process incoming human interaction message and elicit knowledge-grounded response."""
        tgt = target.lower()
        tick = self.world.tick_count
        human_msg = Message(
            sender="human",
            receiver=tgt,
            tick=tick,
            content=text,
            comm_type=CommType.QUERY,
            status=KnowledgeStatus.KNOWN,
        )
        self.channel.send(human_msg)

        # Broadcast human message to viewer
        await self.broadcast(json.dumps({
            "type": "chat_message",
            "message": human_msg.to_dict(),
        }))

        # Route query to targeted brain(s)
        targets = ["alpha", "albedo"] if tgt in ["both", "all"] else [tgt]
        for t in targets:
            brain = self.alpha_brain if t == "alpha" else self.albedo_brain
            resp_msg = brain.receive_message(human_msg, tick)
            self.channel.send(resp_msg)

            # Broadcast response immediately to connected viewers
            await self.broadcast(json.dumps({
                "type": "chat_message",
                "message": resp_msg.to_dict(),
            }))

    async def handle_client_message(self, message_str: str) -> None:
        """Handle incoming command from viewer."""
        try:
            msg = json.loads(message_str)
            cmd = msg.get("command")
            if cmd == "pause":
                self.is_paused = True
                print(f"[Simulation] Paused at tick {self.world.tick_count}")
            elif cmd == "resume":
                self.is_paused = False
                print(f"[Simulation] Resumed at tick {self.world.tick_count}")
            elif cmd == "step":
                self.step_once = True
                print(f"[Simulation] Stepping tick {self.world.tick_count}")
            elif cmd == "set_speed":
                tps = float(msg.get("tps", 5.0))
                self.tps = max(1.0, min(100.0, tps))
            elif cmd == "reset":
                new_seed = int(msg.get("seed", self.seed))
                self.init_simulation(new_seed)
                # Broadcast new world_init to all clients
                init_msg = json.dumps(self.build_world_init_message())
                await self.broadcast(init_msg)
            elif cmd == "human_message":
                target = msg.get("target", "alpha")
                text = msg.get("text", "")
                if text:
                    await self.process_human_message(target, text)
            elif cmd == "teach_symbol":
                target = msg.get("target", "alpha").lower()
                sym = msg.get("symbol", "")
                ctype = msg.get("concept_type", "entity")
                cid = int(msg.get("concept_id", 0))
                targets = ["alpha", "albedo"] if target in ["both", "all"] else [target]
                for t in targets:
                    brain = self.alpha_brain if t == "alpha" else self.albedo_brain
                    brain.ground_concept(sym, ctype, cid, source="human_teaching")
                    confirm = Message(
                        sender=brain.name,
                        receiver="human",
                        tick=self.world.tick_count,
                        content=f"I learned the symbol '{sym}' grounded to {ctype}:{cid}.",
                        comm_type=CommType.TEACH,
                        status=KnowledgeStatus.KNOWN,
                    )
                    self.channel.send(confirm)
                    await self.broadcast(json.dumps({
                        "type": "chat_message",
                        "message": confirm.to_dict(),
                    }))
        except Exception as e:
            print(f"Error handling client message: {e}")

    async def broadcast(self, message: str) -> None:
        """Broadcast JSON message to all connected viewers."""
        if not self.connected_clients:
            return
        # Snapshot the set first to avoid "Set changed size during iteration"
        disconnected = set()
        for client in list(self.connected_clients):
            try:
                await client.send(message)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        self.connected_clients -= disconnected

    async def client_handler(self, websocket: WebSocketServerProtocol) -> None:
        """Handle new client lifecycle and message stream."""
        self.connected_clients.add(websocket)
        print(f"[WebSocket] Client connected: {websocket.remote_address}. Active: {len(self.connected_clients)}")

        # Send world_init immediately upon connection
        init_payload = json.dumps(self.build_world_init_message())
        await websocket.send(init_payload)

        try:
            async for message in websocket:
                await self.handle_client_message(message)
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.connected_clients.discard(websocket)
            print(f"[WebSocket] Client disconnected. Active: {len(self.connected_clients)}")

    async def simulation_loop(self) -> None:
        """Continuous simulation ticking and broadcast loop."""
        while True:
            if not self.is_paused or self.step_once:
                self.step_once = False
                frame_data = self.step_tick()
                if self.connected_clients:
                    payload = json.dumps(frame_data)
                    await self.broadcast(payload)

            sleep_duration = 1.0 / self.tps
            await asyncio.sleep(sleep_duration)

    async def run(self) -> None:
        """Start WebSocket server and concurrent simulation loop."""
        print(f"=== ALC Simulation Observatory Server ===")
        print(f"Serving WebSocket at ws://{self.host}:{self.port}")
        print(f"Entities: Alpha (female, Agent 0) & Albedo (female, Agent 1)")
        print(f"Ready for Desktop / Browser 3D Viewer connection.\n")

        async with websockets.serve(self.client_handler, self.host, self.port):
            await self.simulation_loop()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="ALC WebSocket Simulation Server")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--seed", type=int, default=42, help="World seed")
    parser.add_argument("--tps", type=float, default=5.0, help="Initial ticks per second")
    args = parser.parse_args()

    server = SimulationServer(seed=args.seed, host=args.host, port=args.port)
    server.tps = args.tps

    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        print("\nServer terminated by user.")


if __name__ == "__main__":
    main()
