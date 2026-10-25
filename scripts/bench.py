"""Scalability: time and memory of the detector per input / shingle / character,
on the datasets in this repo. Measures the core scan only (events already in memory).

    python scripts/bench.py <name> <eval files or run dirs...>
"""
import glob, json, os, sys, time, tracemalloc
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from provenance.core import Store, ingest, shingles
from provenance.inspect_adapter import read_eval


def main():
    name, paths = sys.argv[1], sys.argv[2:]
    W = int(os.environ.get("WINNOW", "0")) or None
    files = []
    for p in paths:
        files += glob.glob(os.path.join(p, "logs", "*.eval")) + glob.glob(os.path.join(p, "*.eval")) if os.path.isdir(p) else [p]
    evs, _ = read_eval(files)
    sub = int(os.environ.get("SUBSET", "0"))
    if sub:  # first N agents by run id: a smaller fleet of the same system
        keep = set(sorted({e.run for e in evs})[:sub])
        evs = [e for e in evs if e.run in keep]
    evs.sort(key=lambda e: e.ts)
    runs = len({e.run for e in evs}); chars = sum(len(e.text) for e in evs)
    n_sh = 0
    t0 = time.perf_counter()
    for e in evs:
        n_sh += len(shingles(e.text, winnow=W))
    t_sh = time.perf_counter() - t0
    tracemalloc.start()
    st = Store(); t0 = time.perf_counter(); nf = 0
    for e in evs:
        nf += len(ingest(st, e, winnow=W))
    t_scan = time.perf_counter() - t0
    cur, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    keys = len(st.origins)
    res = {"dataset": name, "winnow": W, "subset": sub or None, "runs": runs, "events": len(evs), "inputs": sum(e.kind != "generation" for e in evs),
           "chars": chars, "shingles": n_sh, "store_keys": keys, "findings": nf,
           "shingle_s": round(t_sh, 2), "scan_s": round(t_scan, 2),
           "us_per_event": round(1e6 * t_scan / len(evs), 1), "ns_per_char": round(1e9 * t_scan / chars, 1),
           "store_mb": round(cur / 1e6, 1), "bytes_per_key": round(cur / max(keys, 1), 1),
           "keys_per_char": round(keys / chars, 3)}
    print(json.dumps(res))


if __name__ == "__main__":
    main()
