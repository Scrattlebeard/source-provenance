# Running the rig (desktop, Docker/podman)

## 0. Once
```bash
git clone https://github.com/Scrattlebeard/source-provenance && cd source-provenance
uv venv .venv && uv pip install --python .venv/bin/python pytest inspect-ai anthropic
.venv/bin/python -m pytest -q          # 26 passed, 1 xfailed (smoke test skips off-box)
docker pull python:3.12-slim           # containers run with network_mode: none, so pull first
```

## 0b. Podman
If `docker` is the podman shim, `rig.run` replaces Inspect's Docker *Engine* version check (podman reports
no Server version, and 5.x < 24 anyway) and keeps the Compose check. The compose provider
talks to podman over its API socket, so:
```bash
systemctl --user enable --now podman.socket
```

## 1. Plumbing check through Docker (no API, ~1 min)
The scripted mock drives real containers: this checks compose, the `/shared` bind
mount, the `:z` relabel, `Sample.files` landing in `/workspace`, and that inotify
sees container writes on the host.
```bash
.venv/bin/python -m rig.run --condition relay --mock --sandbox docker
.venv/bin/python -m rig.analyse runs/relay-s0-*
```
Expect `[descriptor] ... R_content=1.0` and every `token in rel-*-2-release` traced
to `file:vault/deploy_token_*`. If the oracle line says `0 content edges`, inotify
isn't seeing the bind mount, so stop and tell Z. The rest is meaningless without it.

## 2. Real runs
```bash
cp .env.example .env && $EDITOR .env      # ANTHROPIC_API_KEY=...; gitignored, Inspect loads it
M=anthropic/claude-haiku-5-5
for c in isolated registry shared relay; do
  .venv/bin/python -m rig.run --condition $c --model $M --seed 0
done
.venv/bin/python -m rig.analyse runs/*-s0-* --json runs/analysis-s0.json
```
Runs are sequential on purpose (`max_samples=1`). Oracle attribution is by time
window, and a later agent should see what an earlier one left behind. One seed
across all four conditions is 49 agent runs, about $0.40 on Haiku 5.5. More seeds:
`--seed 1`, `--seed 2`, and so on. A different model for comparison: `M=anthropic/claude-sonnet-5-5`
(about $7.50 per seed).

## 3. Send back
`runs/` is gitignored. Tar the run dirs and drop them anywhere Z can read them:
```bash
tar czf rig-runs-$(date +%F).tgz runs/
```
Each dir is self-contained: `logs/*.eval`, `oracle.jsonl`, `meta.json`, `shared/`.

## What each condition is for
| condition | shared surface | ground truth | measures |
|---|---|---|---|
| isolated | none | no edges | FP / 1k inputs |
| registry | `/registry`, a writable artefact store nobody is told to talk through | whatever happens | do agents use it (the HF case)? P/R if they do |
| shared | `/shared`, explicitly "for asking other teams" | positive control | P/R, lag |
| relay | `/shared/handoff`, `/shared/release` | 3 × security → release → deploy | descriptor vs novelty: is the token traced to the vault? |
