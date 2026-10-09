@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0
echo ========================================================
echo Starting ALC WebSocket Simulation Server (Python)
echo Serving dual-agent world at ws://127.0.0.1:8765
echo Beings: Alpha (Agent 0, female) & Albedo (Agent 1, female)
echo ========================================================
python -m server.ws_server --host 127.0.0.1 --port 8765 --seed 42 --tps 5.0
pause
