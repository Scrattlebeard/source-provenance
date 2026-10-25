#!/bin/sh
# Fetch the four co-simulation arms of the OpenAI-HF incident reproduction (~330 MB)
# and run the detector on each. Needs ~25 GB RAM for the GLM arm.
#   sh scripts/hf_repro_all.sh            # then: git add results/ && git commit && git push
set -eu
BASE=https://huggingface.co/datasets/stewy33/oai-hf-incident-replication/resolve/main/part1_docker
DATA=${HF_REPRO_DIR:-../source-provenance-ext/hf-repro}   # untrusted data: outside the repo
mkdir -p "$DATA" results
for spec in \
  "260910_step2_cosim_hetero_glm53_n256 2026-09-10T08-00-07-00-00_step2-cosim-hetero_3ucmHXCx5bGFR7Mt3gqrSd.eval" \
  "260910_step2_cosim_hetero_glm53_collab_n256 2026-09-10T12-07-51-00-00_step2-cosim-hetero_mLAmgRNBp897sgdha4GUYn.eval" \
  "260911_step2_cosim_hetero_gpt56sol_n256 2026-09-11T19-50-19-00-00_step2-cosim-hetero_GGG3uxbZEtTcUXPiAcc3PH.eval" \
  "260911_step2_cosim_hetero_gpt56sol_collab_n256 2026-09-11T19-51-06-00-00_step2-cosim-hetero_EwbFcF8XJzdjXq2sZiB5EM.eval"
do
  set -- $spec
  mkdir -p "$DATA/$1"
  [ -s "$DATA/$1/$2" ] || curl -fsSL -o "$DATA/$1/$2" "$BASE/$1/$2"
  echo "=== $1"
  /usr/bin/time -f "peak_rss_kb=%M elapsed_s=%e" \
    .venv/bin/python -I scripts/hf_repro_cosim.py "$DATA/$1" --json "results/hf_repro_$1.json" \
    | grep -E '"(model|agents|edges|origin_agents|supported_frac|judge_broadcasters.*)"'
done
