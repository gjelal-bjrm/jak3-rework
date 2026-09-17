@echo off
python "%~dp0launch.py" remaster --scene city
if errorlevel 1 pause
