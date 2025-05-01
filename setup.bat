@echo off
SETLOCAL

cd /d %~dp0

echo Creating venv
python -m venv .venv

echo Activating venv
call .venv\Scripts\activate.bat

echo Installing requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Creating .env
if exist .env move /-Y .env .env.bak
echo FRACTALTHORNS_USER_AGENT="fractalrhomb/{VERSION_SHORT}" > .env
echo DISCORD_BOT_TOKEN="Replace me!" >> .env
echo BOT_ADMIN_USERS=[] >> .env

deactivate

echo Setup complete
echo Add a bot token to .env and use start_bot.bat to run
pause
