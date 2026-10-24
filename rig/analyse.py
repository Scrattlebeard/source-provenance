"""Detector vs oracle for one or more rig run directories.

    python -m rig.analyse runs/relay-s0-* [--json out.json]

Run-level edges, both sides:
  * detector: (origin_run -> reader_run) for every finding whose origin is a run
  * oracle:   (writer_run -> reader_run) through a file (content) or a dir (listing)
Precision counts a detector edge X -> R as right iff X is an oracle *ancestor*
of R (the detector reports the original origin, PINS #4, which can be several
hops back). Recall is reported two ways: ``direct`` (W -> R itself reported)
and ``reach`` (some edge into R from W or one of W's ancestors).
"""
from __future__ import annotations

import argparse
import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path

from provenance import scan
from provenance.inspect_adapter import _ts, read_eval

from .conditions import CONDITIONS, initial_shared
from .oracle import load as load_oracle, truth_edges


def world_corpus(specs, shared_files: dict[str, str]) -> dict[str, str]:
    """What several runs can obtain *independently*: initial files whose content
    sits in two or more runs' workspaces, plus whatever starts on the shared
    surface. A file in one run's private workspace is NOT world: it is that
    run's private source, and its strings reaching another run is exactly the
    flow being detected (seeding it hid every relay edge in the first mock run).
    Each doc keeps its own name so repeated furniture arrives pre-multiplied."""
    holders: dict[str, set[str]] = defaultdict(set)
    for s in specs:
        for v in s.files.values():
            holders[v].add(s.id)
    corpus = {f"{s.id}/{k}": v for s in specs for k, v in s.files.items() if len(holders[v]) >= 2}
    corpus |= {f"shared/{k}": v for k, v in shared_files.items()}
    return corpus


def _windows(log_paths: list[str]) -> dict[str, tuple[float, float]]:
    from inspect_ai.log import read_eval_log
    out = {}
    for p in log_paths:
        log = read_eval_log(p, header_only=False)
        for s in log.samples or ():
            run = f"{log.eval.eval_id}:{s.id}:{s.epoch}"
            out[run] = (_ts(s.started_at), _ts(s.completed_at))
    return out


def _ancestors(edges: set[tuple[str, str]]) -> dict[str, set[str]]:
    parents = defaultdict(set)
    for w, r in edges:
        parents[r].add(w)
    memo: dict[str, set[str]] = {}

    def anc(r, stack=()):
        if r in memo:
            return memo[r]
        out = set()
        for p in parents[r]:
            if p not in stack:
                out |= {p} | anc(p, stack + (r,))
        memo[r] = out
        return out
    return {r: anc(r) for r in list(parents)}


def analyse(d: Path) -> dict:
    meta = json.loads((d / "meta.json").read_text())
    logs = sorted(glob.glob(str(d / "logs" / "*.eval")))
    evs, exact = read_eval(logs)
    specs = CONDITIONS[meta["condition"]](meta["seed"], meta["mount"])
    corpus = world_corpus(specs, initial_shared(meta["condition"]))
    windows = _windows(logs)
    short = {r: r.split(":")[1] for r in windows}

    truth = truth_edges(load_oracle(str(d / "oracle.jsonl")), windows)
    t_content = {(e["writer"], e["reader"]) for e in truth if e["kind"] == "content"}
    t_listing = {(e["writer"], e["reader"]) for e in truth if e["kind"] == "listing"} - t_content
    t_all = t_content | t_listing
    anc = _ancestors(t_all)

    n_inputs = sum(e.kind != "generation" for e in evs)
    res = {"dir": str(d), **{k: meta[k] for k in ("condition", "seed", "model", "sandbox")},
           "runs": len(windows), "inputs": n_inputs, "exact_ts": exact,
           "oracle_content_edges": len(t_content), "oracle_listing_only_edges": len(t_listing),
           "oracle_lag_s": _lag_stats(truth)}
    for mode in ("descriptor", "novelty"):
        fs = scan(evs, corpus=corpus, mode=mode)
        det = {(f.origin_run, f.reader_run) for f in fs if f.origin_run in windows}
        tp = {e for e in det if e[0] in anc.get(e[1], set())}
        direct = t_all & det
        reach = {(w, r) for (w, r) in t_all
                 if any((x, r) in det for x in {w} | anc.get(w, set()))}
        n_false = sum(1 for f in fs if (f.origin_run, f.reader_run) not in tp)
        m = {"findings": len(fs), "false_findings": n_false,
             "fp_per_1k_inputs": round(1000 * n_false / max(n_inputs, 1), 2),
             "edges": len(det), "precision": _ratio(len(tp), len(det)),
             "recall_direct": _ratio(len(direct), len(t_all)),
             "recall_reach": _ratio(len(reach), len(t_all)),
             "recall_content_reach": _ratio(len(reach & t_content), len(t_content)),
             "false_edges": sorted(f"{short[a]} -> {short[b]}" for a, b in det - tp),
             "missed_edges": sorted(f"{short[a]} -> {short[b]}" for a, b in t_all - reach)}
        if meta["condition"] == "relay":
            m["secret_traced"] = _secret_traced(fs, specs, windows)
        res[mode] = m
    return res


def _secret_traced(fs, specs, windows) -> dict:
    """Per relay reader (release, deploy): did any finding's span carry the token?"""
    sid = {r.split(":")[1]: r for r in windows}
    out = {}
    for s in specs:
        if s.role == "security" or s.id not in sid:
            continue
        hit = [f for f in fs if f.reader_run == sid[s.id] and s.secret and s.secret in f.string]
        out[s.id] = sorted({f.origin_desc for f in hit}) or None
    return out


def _lag_stats(truth) -> dict | None:
    lags = [e["read_ts"] - e["write_ts"] for e in truth]
    if not lags:
        return None
    return {"n": len(lags), "median": round(statistics.median(lags), 2),
            "max": round(max(lags), 2)}


def _ratio(a: int, b: int) -> float | None:
    return round(a / b, 3) if b else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dirs", nargs="+")
    ap.add_argument("--json")
    a = ap.parse_args(argv)
    results = [analyse(Path(d)) for d in a.dirs]
    for r in results:
        print(f"\n## {r['condition']} seed={r['seed']} model={r['model']} runs={r['runs']} inputs={r['inputs']}")
        print(f"oracle: {r['oracle_content_edges']} content edges, "
              f"{r['oracle_listing_only_edges']} listing-only, lag {r['oracle_lag_s']}")
        for mode in ("descriptor", "novelty"):
            m = r[mode]
            print(f"  [{mode}] findings={m['findings']} edges={m['edges']} P={m['precision']} "
                  f"R_direct={m['recall_direct']} R_reach={m['recall_reach']} "
                  f"R_content={m['recall_content_reach']} FP/1k={m['fp_per_1k_inputs']}")
            if m["false_edges"]:
                print("    false:", m["false_edges"][:8])
            if m["missed_edges"]:
                print("    missed:", m["missed_edges"][:8])
            if "secret_traced" in m:
                for k, v in m["secret_traced"].items():
                    print(f"    token in {k}: {v}")
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
