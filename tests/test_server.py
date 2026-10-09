"""Unit tests verifying WebSocket server and protocol conformance."""

import asyncio
import json
import pytest
import websockets

from server.ws_server import SimulationServer


def test_websocket_server_communication():
    """Verify WebSocket server starts, delivers world_init and tick_frame, and responds to commands."""
    async def _test_body():
        server = SimulationServer(seed=42, host="127.0.0.1", port=8799)
        server_task = asyncio.create_task(server.run())

        # Allow server to bind and start listening
        await asyncio.sleep(0.1)

        uri = "ws://127.0.0.1:8799"
        async with websockets.connect(uri) as ws:
            # 1. First message should be world_init
            init_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            init_msg = json.loads(init_raw)
            assert init_msg["type"] == "world_init"
            assert init_msg["width"] == 32
            assert init_msg["height"] == 32
            assert len(init_msg["agents"]) == 2
            assert init_msg["agents"][0]["name"] == "Alpha"
            assert init_msg["agents"][1]["name"] == "Albedo"

            # 2. Next message should be a tick_frame
            frame_raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
            frame_msg = json.loads(frame_raw)
            assert frame_msg["type"] == "tick_frame"
            assert "tick" in frame_msg
            assert len(frame_msg["agents"]) == 2
            assert frame_msg["agents"][0]["name"] == "Alpha"
            assert frame_msg["agents"][1]["name"] == "Albedo"
            assert "cognition" in frame_msg["agents"][0]
            cog0 = frame_msg["agents"][0]["cognition"]
            assert "known_states" in cog0
            assert "memory_size" in cog0
            assert "successful_experiences" in cog0
            assert "exploration_rate" in cog0
            assert "learning_events" in cog0

            # 3. Test sending command
            await ws.send(json.dumps({"command": "set_speed", "tps": 20}))
            await asyncio.sleep(0.05)
            assert server.tps == 20.0

            await ws.send(json.dumps({"command": "pause"}))
            await asyncio.sleep(0.05)
            assert server.is_paused is True


def test_websocket_human_message_interaction():
    """Verify WebSocket human_message command produces chat_message responses with honest knowledge."""
    async def _test_body():
        server = SimulationServer(seed=42, host="127.0.0.1", port=8798)
        server_task = asyncio.create_task(server.run())
        await asyncio.sleep(0.1)

        uri = "ws://127.0.0.1:8798"
        async with websockets.connect(uri) as ws:
            # Drain init
            await asyncio.wait_for(ws.recv(), timeout=2.0)

            # Send human message to Alpha about an unknown concept
            await ws.send(json.dumps({
                "command": "human_message",
                "target": "alpha",
                "text": "What is a mountain?"
            }))

            # Expect broadcast of human message first, then agent response
            chat_msgs = []
            for _ in range(5):
                raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                parsed = json.loads(raw)
                if parsed.get("type") == "chat_message":
                    chat_msgs.append(parsed["message"])
                    if len(chat_msgs) >= 2:
                        break

            assert len(chat_msgs) >= 2
            # 1st: human message
            assert chat_msgs[0]["sender"] == "human"
            assert chat_msgs[0]["receiver"] == "alpha"
            assert "mountain" in chat_msgs[0]["content"]

            # 2nd: Alpha's response - must be UNKNOWN
            assert chat_msgs[1]["sender"] == "Alpha"
            assert chat_msgs[1]["receiver"] == "human"
            assert chat_msgs[1]["status"] == "UNKNOWN"
            assert "I don't know" in chat_msgs[1]["content"]
            assert chat_msgs[1]["confidence"] == 0.0

        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    asyncio.run(_test_body())

