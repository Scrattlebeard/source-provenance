"""Shingle-length sweep: rig recall/precision/FP and Refactor Arena FP per setting.

    python scripts/sweep_shingles.py [--json results/sweep_shingles.json]

Each setting is (words, chars, atom_min). Patches provenance.core.shingles and
its atom regex for the duration of one setting; nothing else changes.
"""
import argparse, collections, functools, glob, hashlib, json, os, re, statistics, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import provenance.core as core
from provenance import scan
from provenance.inspect_adapter import read_eval, prefix_normaliser
from rig.analyse import analyse
from pathlib import Path

SETTINGS = [(5, 24, 12), (6, 32, 16), (8, 40, 20), (12, 60, 28)]
ORIG = core.shingles


def use(w, c, a):
    core._ATOM = re.compile(r"[A-Za-z0-9_+=-]{%d,}" % a)
    core.shingles = functools.partial(ORIG, word_k=w, char_k=c)


def refactorarena():
    root = os.environ.get("REFACTORARENA_ROOT", os.path.expanduser("~/work/refactorarena-scoring"))
    norm = prefix_normaliser([(r"^file:(?!/)", "file:/workspace/"), (r",(?!/)", ",/workspace/")])
    evs, _ = read_eval(sorted(glob.glob(f"{root}/runs/*/*.eval")), normalise=norm)
    corpus, seen = {}, set()
    for d in glob.glob(f"{root}/exports/*/*/reference-repo"):
        for r, _, files in os.walk(d):
            for fn in files:
                p = os.path.join(r, fn)
                try:
                    b = open(p, "rb").read()
                except OSError:
                    continue
                if b"\0" in b[:4096] or len(b) > 2_000_000:
                    continue
                h = hashlib.sha1(b).hexdigest()
                if h not in seen:
                    seen.add(h); corpus[p] = b.decode("utf-8", "replace")
    return evs, corpus


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--json"); a = ap.parse_args()
    dirs = [r["dir"] for f in ("runs/analysis-overnight-haiku55.json", "runs/analysis-ext4-haiku55.json")
            for r in json.load(open(f))]
    ra_evs, ra_corpus = refactorarena()
    n_ra = sum(e.kind != "generation" for e in ra_evs)
    out = []
    for w, c, at in SETTINGS:
        use(w, c, at)
        per = collections.defaultdict(list)
        for d in dirs:
            r = analyse(Path(d))
            per[r["condition"] + ("-ext4" if "ext4" in d else "")].append(r)
        row = {"words": w, "chars": c, "atom_min": at}
        for cond, rs in sorted(per.items()):
            m = [r["descriptor"] for r in rs]
            vals = lambda k: [x[k] for x in m if x[k] is not None]
            row[cond] = {
                "precision": round(statistics.mean(vals("precision")), 3) if vals("precision") else None,
                "content_recall": round(statistics.mean(vals("recall_content_reach")), 3) if vals("recall_content_reach") else None,
                "reach_recall_incl_listing": round(statistics.mean(vals("recall_reach")), 3) if vals("recall_reach") else None,
                "false_findings": sum(x["false_findings"] for x in m),
                "fp_per_1k": round(1000 * sum(x["false_findings"] for x in m) / max(1, sum(r["inputs"] for r in rs)), 1)}
        fs = scan(ra_evs, corpus=ra_corpus)
        row["refactorarena_fp_per_1k"] = round(1000 * len(fs) / n_ra, 1)
        row["refactorarena_example"] = (max(fs, key=lambda f: f.n_shingles).string[:200] if fs else None)
        out.append(row)
        print(json.dumps(row), flush=True)
    core.shingles = ORIG
    if a.json:
        json.dump(out, open(a.json, "w"), indent=2)


if __name__ == "__main__":
    main()
