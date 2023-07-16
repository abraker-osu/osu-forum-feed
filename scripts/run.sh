#!/usr/bin/env bash

# Don't let CDPATH interfere with the cd command
unset CDPATH
cd "$(dirname "$0")"

exec py run.py db