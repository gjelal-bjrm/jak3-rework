@echo off
python "%~dp0launch.py" remaster --scene palace
if errorlevel 1 pause
