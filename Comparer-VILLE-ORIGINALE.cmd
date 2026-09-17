@echo off
python "%~dp0launch.py" original --scene city
if errorlevel 1 pause
