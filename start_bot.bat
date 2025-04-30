@echo off
SETLOCAL

cd /d %~dp0
call .venv\Scripts\activate.bat

echo Starting bot

python fractalrhomb.py %*

deactivate
