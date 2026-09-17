@echo off
python "%~dp0launch.py" remaster-v1 --scene arena
if errorlevel 1 pause
