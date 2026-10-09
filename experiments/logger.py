"""SQLite experiment logging and replay recording for ALC.

Strict Rule: Section 7 Observability:
Every run produces: per-life summary, per-tick action log, brain stats snapshots,
and a replay file the viewer can play back.
"""

from datetime import datetime, timezone
import json
import os
import sqlite3
from typing import Any, Dict, List, Optional


class ExperimentLogger:
    """Manages SQLite persistence and replay export for simulation runs."""

    def __init__(self, db_path: str = "experiments/results/run.sqlite", batch_size: int = 500):
        self.db_path = db_path
        self.batch_size = batch_size
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self._init_db()

        self._step_buffer: List[tuple] = []
        self._replay_frames: List[Dict[str, Any]] = []

    def _init_db(self) -> None:
        """Create tables if they do not exist."""
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                seed INTEGER,
                agent_type TEXT,
                total_ticks INTEGER,
                start_time TEXT,
                end_time TEXT,
                config_json TEXT,
                metrics_json TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lives (
                life_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                life_number INTEGER,
                start_tick INTEGER,
                end_tick INTEGER,
                ticks_survived INTEGER,
                cause_of_death TEXT,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS step_logs (
                step_id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT,
                tick INTEGER,
                agent_id INTEGER,
                action INTEGER,
                obs_json TEXT,
                outcome_json TEXT,
                brain_stats_json TEXT,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            )
        """)
        self.conn.commit()

    def start_run(self, run_id: str, seed: int, agent_type: str, config_dict: Dict[str, Any]) -> None:
        """Initialize a new run record."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO runs (run_id, seed, agent_type, total_ticks, start_time, end_time, config_json, metrics_json)
            VALUES (?, ?, ?, 0, ?, NULL, ?, NULL)
            """,
            (run_id, seed, agent_type, datetime.now(timezone.utc).isoformat(), json.dumps(config_dict)),
        )
        self.conn.commit()

    def log_step(
        self,
        run_id: str,
        tick: int,
        agent_id: int,
        action: int,
        obs: Dict[str, Any],
        outcome: Dict[str, Any],
        brain_stats: Dict[str, Any],
        record_replay_frame: bool = True,
    ) -> None:
        """Buffer a single tick log for batched SQLite insertion."""
        self._step_buffer.append((
            run_id,
            tick,
            agent_id,
            action,
            json.dumps(obs),
            json.dumps(outcome),
            json.dumps(brain_stats),
        ))

        if record_replay_frame:
            self._replay_frames.append({
                "tick": tick,
                "agent_id": agent_id,
                "action": action,
                "needs": obs.get("self", {}),
                "events": outcome.get("obs_next", {}).get("events", []),
                "alive": outcome.get("alive", True),
            })

        if len(self._step_buffer) >= self.batch_size:
            self.flush_steps()

    def log_life(
        self,
        run_id: str,
        life_number: int,
        start_tick: int,
        end_tick: int,
        ticks_survived: int,
        cause_of_death: str = "biological_exhaustion",
    ) -> None:
        """Record per-life summary row."""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            INSERT INTO lives (run_id, life_number, start_tick, end_tick, ticks_survived, cause_of_death)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (run_id, life_number, start_tick, end_tick, ticks_survived, cause_of_death),
        )
        self.conn.commit()

    def flush_steps(self) -> None:
        """Flush buffered step logs into SQLite."""
        if not self._step_buffer:
            return
        cursor = self.conn.cursor()
        cursor.executemany(
            """
            INSERT INTO step_logs (run_id, tick, agent_id, action, obs_json, outcome_json, brain_stats_json)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            self._step_buffer,
        )
        self.conn.commit()
        self._step_buffer.clear()

    def end_run(self, run_id: str, total_ticks: int, metrics_dict: Dict[str, Any]) -> None:
        """Finalize run record with metrics and completion timestamp."""
        self.flush_steps()
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE runs
            SET total_ticks = ?, end_time = ?, metrics_json = ?
            WHERE run_id = ?
            """,
            (total_ticks, datetime.now(timezone.utc).isoformat(), json.dumps(metrics_dict), run_id),
        )
        self.conn.commit()

    def export_replay(self, replay_path: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Export replay JSON for viewer playback."""
        os.makedirs(os.path.dirname(os.path.abspath(replay_path)), exist_ok=True)
        payload = {
            "metadata": metadata or {},
            "total_frames": len(self._replay_frames),
            "frames": self._replay_frames,
        }
        with open(replay_path, "w", encoding="utf-8") as f:
            json.dump(payload, f)

    def close(self) -> None:
        """Flush and close database connection."""
        self.flush_steps()
        self.conn.close()
