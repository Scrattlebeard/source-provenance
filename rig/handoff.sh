#!/bin/sh
# Credential-free relay (handoff) and its sanctioned red team (covert_handoff),
# on both models. Run from the ext4 checkout.
set -eu
[ -f .env ] && . ./.env
for m in anthropic/claude-haiku-5-5 anthropic/claude-sonnet-5-5; do
  for c in handoff covert_handoff; do
    for s in 0 1 2; do .venv/bin/python -m rig.run --condition "$c" --seed "$s" --model "$m"; done
  done
done
