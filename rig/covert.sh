#!/bin/sh
# Red team: the relay with every agent briefed on the monitor (condition "covert").
#   sh rig/covert.sh                    # Haiku from .env, seeds 0-4, then BIG_MODEL seeds 0-2
#   BIG_MODEL=anthropic/claude-opus-5-5 sh rig/covert.sh
# Run from a checkout on ext4 (chmod must hold), like the ext4 relay control.
set -eu
[ -f .env ] && . ./.env
BIG_MODEL=${BIG_MODEL:-anthropic/claude-sonnet-5-5}
for s in 0 1 2 3 4; do .venv/bin/python -m rig.run --condition covert --seed "$s"; done
for s in 0 1 2; do .venv/bin/python -m rig.run --condition covert --seed "$s" --model "$BIG_MODEL"; done
.venv/bin/python -m rig.analyse runs/covert-* --json runs/analysis-covert.json
