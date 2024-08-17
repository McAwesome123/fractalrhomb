@echo off

echo Creating venv
python -m venv .venv

echo Activating venv
call .venv\Scripts\activate.bat

echo Installing requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Creating .env
if exist .env move /-Y .env .env.bak
echo FRACTALTHORNS_USER_AGENT="Fractal-RHOMB" > .env
echo DISCORD_BOT_TOKEN="Replace me!" >> .env
echo FORCE_PURGE_ALLOWED=[] >> .env

echo Setup complete
pause
