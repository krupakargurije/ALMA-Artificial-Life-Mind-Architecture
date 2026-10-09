@echo off
cd /d "%~dp0"
set PYTHONPATH=%~dp0
echo ========================================================
echo Starting Artificial Learning Civilization (ALC)
echo Launching Server and 3D Observatory Desktop Viewer...
echo ========================================================

start "ALC Simulation Server" /d "%~dp0" cmd /k "set PYTHONPATH=%~dp0&& python -m server.ws_server --host 127.0.0.1 --port 8765 --seed 42 --tps 5.0"

powershell -Command "Start-Sleep -Seconds 2"

start "ALC 3D Observatory Viewer" /d "%~dp0" cmd /k "java -jar viewer\target\alc-observatory-desktop.jar"

echo Both processes have been launched in interactive windows!
