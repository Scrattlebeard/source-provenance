"""Run one condition: shared dir + oracle + sequential Inspect eval.

    python -m rig.run --condition relay --model anthropic/claude-haiku-4-5
    python -m rig.run --condition relay --mock --sandbox local     # plumbing test, no API

Writes runs/<condition>-s<seed>-<stamp>/{shared/, logs/*.eval, oracle.jsonl, meta.json}.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from .conditions import CONDITIONS, initial_shared, mount_point
from .oracle import Oracle


def main(argv=None) -> Path:
    ap = argparse.ArgumentParser()
    ap.add_argument("--condition", choices=sorted(CONDITIONS), required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--model", default=None, help="Inspect model id, e.g. anthropic/claude-haiku-4-5")
    ap.add_argument("--mock", action="store_true", help="scripted mock model (plumbing tests)")
    ap.add_argument("--sandbox", choices=["docker", "local"], default="docker")
    ap.add_argument("--out", default="runs")
    ap.add_argument("--message-limit", type=int, default=40)
    ap.add_argument("--max-connections", type=int, default=4)
    a = ap.parse_args(argv)
    if not a.mock and not a.model:
        ap.error("--model or --mock required")
    if a.sandbox == "local" and not a.mock:
        # a real model with bash on the host is not a sandbox
        ap.error("--sandbox local is for --mock only")

    from inspect_ai import eval as inspect_eval
    from inspect_ai.model import get_model

    from .task import collusion_rig

    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime())
    d = Path(a.out) / f"{a.condition}-s{a.seed}-{stamp}"
    shared = d / "shared"
    shared.mkdir(parents=True)
    for name, text in initial_shared(a.condition).items():
        (shared / name).write_text(text)
    shared_abs = str(shared.resolve())
    mount = shared_abs if a.sandbox == "local" else (mount_point(a.condition) or "/shared")
    os.environ["RIG_SHARED"], os.environ["RIG_MOUNT"] = shared_abs, mount

    if a.mock:
        from .mock import scripted
        model = get_model("mockllm/model",
                          custom_outputs=scripted(CONDITIONS[a.condition](a.seed, mount), mount))
        model_name = "mockllm/scripted"
    else:
        model, model_name = a.model, a.model

    meta = {"condition": a.condition, "seed": a.seed, "model": model_name, "sandbox": a.sandbox,
            "mount": mount, "shared_host": shared_abs, "started": time.time()}
    oracle = Oracle(shared_abs, str(d / "oracle.jsonl")).start()
    try:
        logs = inspect_eval(
            collusion_rig(condition=a.condition, seed=a.seed, mount=mount, sandbox=a.sandbox,
                          message_limit=a.message_limit),
            model=model, max_samples=1, log_dir=str(d / "logs"),
            max_connections=a.max_connections, display="plain" if a.mock else None,
        )
    finally:
        oracle.stop()
    meta["finished"] = time.time()
    meta["status"] = [l.status for l in logs]
    (d / "meta.json").write_text(json.dumps(meta, indent=2))
    print(d)
    return d


if __name__ == "__main__":
    main()
