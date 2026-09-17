@echo off
python "%~dp0launch.py" original --scene palace
if errorlevel 1 pause
