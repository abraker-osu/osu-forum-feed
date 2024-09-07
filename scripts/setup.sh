#!/bin/bash
set -e

# Activate venv
if [ ! -d "venv" ]; then
    echo "No venv was found. Creating..."
    python3 -m venv venv
fi

source venv/bin/activate

if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Venv activation failed"
    exit 1
fi

# Install libs
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
python3 -m pip list

echo "[ DONE ]"
