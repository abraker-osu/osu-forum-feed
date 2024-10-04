#!/usr/bin/env bash
set -e

# Activate venv
if [ ! -d "venv" ]; then
    echo "No venv was found. Creating..."
    python3 -m venv venv
fi

if [ ! -d "venv" ]; then
    echo "Failed to create venv!"
    exit 1
fi

source venv/bin/activate

if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo "Venv activation failed"
    exit 1
fi

# Don't let CDPATH interfere with the cd command
unset CDPATH
cd "$(dirname "$0")"

exec python3 $(pwd)/src/run.py
