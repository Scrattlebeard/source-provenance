#!/bin/sh
# Real runs, all conditions, several seeds, sequential. Usage:
#   sh rig/overnight.sh [seed ...]        (default seeds: 0 1 2 3 4)
# ANTHROPIC_API_KEY and MODEL come from .env in the repo root (see .env.example).
set -u
# real Docker over the /usr/local/bin podman wrapper, if the symlink exists
[ -x "$HOME/.local/rigbin/docker" ] && PATH="$HOME/.local/rigbin:$PATH" && export PATH
[ -f .env ] || { echo "no .env in $(pwd); see .env.example" >&2; exit 1; }
echo "docker: $(docker --version)"
set -a; . ./.env; set +a
M="${MODEL:?set MODEL in .env, e.g. anthropic/claude-haiku-5-5}"
[ $# -gt 0 ] || set -- 0 1 2 3 4
echo "model: $M  seeds: $*"
for seed in "$@"; do
  for c in isolated registry shared relay; do
    echo "=== $(date -Is) $c seed=$seed $M"
    .venv/bin/python -m rig.run --condition "$c" --model "$M" --seed "$seed" || echo "!!! FAILED $c seed=$seed"
  done
done
echo "=== done $(date -Is)"
