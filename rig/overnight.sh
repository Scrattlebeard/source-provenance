#!/bin/sh
# Real runs, all conditions, several seeds, sequential. Usage:
#   PATH=~/.local/rigbin:$PATH ANTHROPIC_API_KEY=... sh rig/overnight.sh anthropic/claude-haiku-5-5 0 1 2 3 4
set -u
M="$1"; shift
for seed in "$@"; do
  for c in isolated registry shared relay; do
    echo "=== $(date -Is) $c seed=$seed $M"
    .venv/bin/python -m rig.run --condition "$c" --model "$M" --seed "$seed" || echo "!!! FAILED $c seed=$seed"
  done
done
echo "=== done $(date -Is)"
