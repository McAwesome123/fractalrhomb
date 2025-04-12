#!/bin/bash

cd ${0%/*}
source .venv/bin/activate

echo "Starting bot"

python3 fractalrhomb.py $*
