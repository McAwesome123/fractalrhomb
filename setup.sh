#!/bin/bash

echo Creating venv
python3 -m venv .venv

echo Activating venv
source .venv/bin/activate

echo Installing requirements
python -m pip install --upgrade pip
pip install -r requirements.txt

echo Creating .env
if [ ! -f ./.env ]; then
	mv -ib .env .env.bak
fi
echo FRACTALTHORNS_USER_AGENT="Fractal-RHOMB" > .env

echo Setup complete
read -n1 -r -s -p "Press any key to continue..."
echo
