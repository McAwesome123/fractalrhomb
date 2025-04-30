#!/bin/bash

cd ${0%/*}

if [ -f .venv/Scripts/activate ]; then
	source .venv/Scripts/activate
else
	source .venv/bin/activate
fi

echo "Starting bot"

python fractalrhomb.py $*
