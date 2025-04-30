#!/bin/bash

cd ${0%/*}

echo Creating venv
python -m venv .venv

echo Activating venv

if [ -f .venv/Scripts/activate ]; then
	source .venv/Scripts/activate
else
	source .venv/bin/activate
fi

echo Installing requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Creating .env
if [ -f ./.env ]; then
	mv -ib .env .env.bak
fi
echo 'FRACTALTHORNS_USER_AGENT="Fractal-RHOMB/{VERSION_SHORT}"' > .env
echo 'DISCORD_BOT_TOKEN="Replace me!"' >> .env
echo 'BOT_ADMIN_USERS=[]' >> .env

deactivate

echo Setup complete
echo Add a bot token to .env and use start_bot.sh to run
read -n1 -r -s -p "Press any key to continue..."
echo
