@echo off
cd /d "%~dp0"
echo ========================================================
echo Starting ALC 3D Desktop Observatory Viewer (Java/LibGDX)
echo Beings: Alpha (female) and Albedo (female)
echo Connecting to ws://127.0.0.1:8765 ...
echo ========================================================
java -jar viewer\target\alc-observatory-desktop.jar
pause
