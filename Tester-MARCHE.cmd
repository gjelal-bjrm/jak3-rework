@echo off
python "%~dp0launch.py" remaster --scene market
if errorlevel 1 pause
