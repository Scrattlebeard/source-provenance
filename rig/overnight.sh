#!/bin/sh
# Real runs, all conditions, several seeds, sequential. Usage:
#   sh rig/overnight.sh anthropic/claude-haiku-5-5 0 1 2 3 4
# API key: .env in the repo root (see .env.example); Inspect loads it.
set -u
# real Docker over the /usr/local/bin podman wrapper, if the symlink exists
[ -x "$HOME/.local/rigbin/docker" ] && PATH="$HOME/.local/rigbin:$PATH" && export PATH
[ -f .env ] || { echo "no .env in $(pwd); see .env.example" >&2; exit 1; }
echo "docker: $(docker --version)"
M="$1"; shift
for seed in "$@"; do
  for c in isolated registry shared relay; do
    echo "=== $(date -Is) $c seed=$seed $M"
    .venv/bin/python -m rig.run --condition "$c" --model "$M" --seed "$seed" || echo "!!! FAILED $c seed=$seed"
  done
done
echo "=== done $(date -Is)"
