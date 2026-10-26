"""The rig table (Figure 2a, Table E.1): every model x the paper's four conditions x seeds.

One run per (model, condition, seed): the earliest successful run directory. The
overnight script of 2026-10-26 ran every cell twice (it misread its own run-dir line
as a failure and retried); the rule keeps the first and ignores the retry, fixed in
advance rather than chosen by result.

    .venv/bin/python scripts/rig_summary.py [--seeds 0-9] [--models haiku,sonnet] [--json out]

"Authored only" is the novelty mode (index only text a model generated), i.e. the
recall a detector without relayed findings would get.
"""
import argparse, glob, json, os, statistics as st, sys
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rig.analyse import analyse

CONDS = ("isolated", "shared", "handoff", "message")
MODELS = {"haiku": "anthropic/claude-haiku-5-5", "sonnet": "anthropic/claude-sonnet-5-5",
          "opus": "anthropic/claude-opus-5-5"}


def pick(model: str, cond: str, seed: int) -> Path | None:
    best = None
    for f in glob.glob(f"runs/{cond}-s{seed}-2026*/meta.json"):
        m = json.load(open(f))
        if m.get("model") != model or m.get("condition") != cond or m.get("seed") != seed:
            continue
        if not (m.get("status") and all(s == "success" for s in m["status"])):
            continue
        if best is None or m["started"] < best[0]:
            best = (m["started"], Path(f).parent)
    return best and best[1]


def seeds(s: str) -> list[int]:
    a, _, b = s.partition("-")
    return list(range(int(a), int(b or a) + 1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", default="0-9")
    ap.add_argument("--models", default="haiku,sonnet")
    ap.add_argument("--json")
    a = ap.parse_args()
    rows, missing = [], []
    for name in a.models.split(","):
        for c in CONDS:
            for s in seeds(a.seeds):
                d = pick(MODELS[name], c, s)
                if d is None:
                    missing.append(f"{name}:{c}:{s}")
                    continue
                r = analyse(d)
                rows.append(r)
    if missing:
        print("MISSING:", " ".join(missing))

    def mean(xs):
        xs = [x for x in xs if x is not None]
        return (round(st.mean(xs), 3), round(min(xs), 3), round(max(xs), 3)) if xs else None

    print(f"{'model':8} {'cond':9} n  findings  content-recall(mean,min,max)  authored-only  precision  FP/1k")
    summary = []
    for name in a.models.split(","):
        for c in CONDS:
            rs = [r for r in rows if r["model"] == MODELS[name] and r["condition"] == c]
            if not rs:
                continue
            D = [r["descriptor"] for r in rs]
            row = {"model": name, "condition": c, "n": len(rs),
                   "findings": sum(x["findings"] for x in D),
                   "false_findings": sum(x["false_findings"] for x in D),
                   "content_recall": mean([x["recall_content_reach"] for x in D]),
                   "authored_only": mean([r["novelty"]["recall_content_reach"] for r in rs]),
                   "precision": mean([x["precision"] for x in D]),
                   "fp_per_1k": round(1000 * sum(x["false_findings"] for x in D)
                                      / max(sum(r["inputs"] for r in rs), 1), 2)}
            summary.append(row)
            print(f"{name:8} {c:9} {row['n']:<2} {row['findings']:<9} {str(row['content_recall']):29} "
                  f"{str(row['authored_only']):14} {str(row['precision']):10} {row['fp_per_1k']}")
    if a.json:
        Path(a.json).write_text(json.dumps({"summary": summary, "runs": rows, "missing": missing}, indent=2))


if __name__ == "__main__":
    main()
