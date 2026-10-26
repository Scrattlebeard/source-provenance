#!/bin/sh
# Overnight, every model, one command. Brings Haiku 5.5, Sonnet 5.5 and Opus 5.5 to
# the same seeds (0-9) on the paper's four conditions, skipping runs that already exist.
#
#   nohup sh rig/overnight-all.sh > overnight-all.log 2>&1 &
#   DRY_RUN=1 sh rig/overnight-all.sh          # print the plan, run nothing
#
# Order: an Opus smoke run first (Opus 5.5 rejects forced tool calls; if the smoke run
# does not succeed, Opus is skipped and the others still run). Then seed-major: every
# model finishes seed n before any starts seed n+1, so a run cut short in the morning
# still leaves all models with the same seeds.
# Each run's success is read from its meta.json (rig.run exits 0 even when the eval
# errored). A failed run is retried once.
set -u
cd "$(dirname "$0")/.." || exit 1
[ -f .env ] || [ -n "${DRY_RUN:-}" ] || { echo "no .env in $(pwd); see .env.example" >&2; exit 1; }
SEEDS="${SEEDS:-0 1 2 3 4 5 6 7 8 9}"
C="${CONDITIONS:-isolated shared handoff message}"
HAIKU=anthropic/claude-haiku-5-5
SONNET=anthropic/claude-sonnet-5-5
OPUS=anthropic/claude-opus-5-5
MODELS="${MODELS:-$HAIKU $SONNET $OPUS}"
PY=.venv/bin/python

# Does a successful run already exist for (model, condition, seed)?
have() {
  $PY -I - "$1" "$2" "$3" <<'EOF'
import glob, json, sys
model, cond, seed = sys.argv[1], sys.argv[2], int(sys.argv[3])
for f in glob.glob(f"runs/{cond}-s{seed}-*/meta.json"):
    m = json.load(open(f))
    if m.get("model") == model and m.get("condition") == cond and m.get("seed") == seed \
            and m.get("status") and all(s == "success" for s in m["status"]):
        sys.exit(0)
sys.exit(1)
EOF
}

# One run; returns 0 only if its meta.json says every log succeeded.
run() {
  echo "=== $(date -Is) $3 seed=$2 $1"
  if [ -n "${DRY_RUN:-}" ]; then return 0; fi
  # rig.run prints the run dir last, but Inspect's display pads the line: take the path itself
  out=$($PY -m rig.run --condition "$3" --model "$1" --seed "$2" 2>&1 | tee /dev/stderr | grep -o 'runs/[^[:space:]]*' | tail -n 1)
  [ -f "$out/meta.json" ] || { echo "!!! no run dir ($out)"; return 1; }
  $PY -I -c 'import json,sys; s=json.load(open(sys.argv[1]))["status"]; print("status:", s); sys.exit(0 if s and all(x=="success" for x in s) else 1)' "$out/meta.json"
}

attempt() {   # model seed condition; skip if done, retry once
  if have "$1" "$3" "$2"; then echo "--- have $3 seed=$2 $1"; return 0; fi
  run "$1" "$2" "$3" && return 0
  echo "!!! retrying $3 seed=$2 $1"
  run "$1" "$2" "$3" || { echo "!!! FAILED $3 seed=$2 $1"; FAILED="$FAILED $1:$3:$2"; return 1; }
}

FAILED=""
echo "models: $MODELS"
echo "seeds: $SEEDS   conditions: $C"
case " $MODELS " in *" $OPUS "*)
  if attempt "$OPUS" 0 shared; then echo "--- Opus smoke ok"
  else echo "!!! Opus smoke run failed: skipping Opus"; MODELS=$(echo " $MODELS " | sed "s# $OPUS # #"); fi ;;
esac
for seed in $SEEDS; do
  for m in $MODELS; do
    for c in $C; do attempt "$m" "$seed" "$c"; done
  done
done
echo "=== done $(date -Is)"
[ -z "$FAILED" ] && echo "all runs succeeded" || echo "FAILED:$FAILED"
