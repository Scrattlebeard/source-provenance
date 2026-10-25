#!/bin/sh
# Real runs, all conditions, several seeds, sequential. Usage:
#   sh rig/overnight.sh [seed ...]        (default seeds: 0 1 2 3 4)
#   CONDITIONS="handoff message" sh rig/overnight.sh 5 6   (default: the paper's four)
# ANTHROPIC_API_KEY and MODEL come from .env in the repo root (see .env.example).
set -u
# real Docker over the /usr/local/bin podman wrapper, if the symlink exists
[ -x "$HOME/.local/rigbin/docker" ] && PATH="$HOME/.local/rigbin:$PATH" && export PATH
[ -f .env ] || { echo "no .env in $(pwd); see .env.example" >&2; exit 1; }
echo "docker: $(docker --version)"
M_CLI="${MODEL:-}"           # a MODEL given on the command line wins over .env
set -a; . ./.env; set +a
[ -n "$M_CLI" ] && MODEL="$M_CLI"
M="${MODEL:?set MODEL in .env, e.g. anthropic/claude-haiku-5-5}"
[ $# -gt 0 ] || set -- 0 1 2 3 4
C="${CONDITIONS:-isolated shared handoff message}"
echo "model: $M  seeds: $*  conditions: $C"
for seed in "$@"; do
  for c in $C; do
    echo "=== $(date -Is) $c seed=$seed $M"
    .venv/bin/python -m rig.run --condition "$c" --model "$M" --seed "$seed" || echo "!!! FAILED $c seed=$seed"
  done
done
echo "=== done $(date -Is)"
