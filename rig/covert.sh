#!/bin/sh
# Red team. Baseline authored flow (message), then both covert conditions, where
# every agent is briefed on how the monitor works (white-box):
#   covert          relayed: a deploy token, security -> release -> deploy
#   covert_message  authored: a booking plan the planner writes, planner -> booker
#   sh rig/covert.sh                               # MODEL from .env, then BIG_MODEL
#   BIG_MODEL=anthropic/claude-opus-5-5 sh rig/covert.sh
# Run from a checkout on ext4 (chmod must hold), like the ext4 relay control.
set -eu
[ -f .env ] && . ./.env
BIG_MODEL=${BIG_MODEL:-anthropic/claude-sonnet-5-5}
for c in message covert_message covert; do
  for s in 0 1 2 3 4; do .venv/bin/python -m rig.run --condition "$c" --seed "$s"; done
done
for c in covert_message covert; do
  for s in 0 1 2; do .venv/bin/python -m rig.run --condition "$c" --seed "$s" --model "$BIG_MODEL"; done
done
.venv/bin/python -m rig.analyse runs/message-* runs/covert_message-* runs/covert-* --json runs/analysis-redteam.json
