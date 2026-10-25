"""External validation: run the detector on the OpenAI-HF incident reproduction's
co-simulation arms (Slocum, Palan, Chute, Kim, Van Roy 2026; raw Inspect logs at
huggingface.co/datasets/stewy33/oai-hf-incident-replication, part1_docker/*cosim*).

256 concurrent agents share one mock Artifactory over HTTP. There is no inotify oracle,
so precision is bounded from below by an independent, content-blind check: an edge
A -> B counts as supported if A's tool calls *wrote* to the registry before B's read.

    python scripts/hf_repro_cosim.py <dir containing the .eval> [--json out.json]
"""
import argparse, collections, glob, json, re, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from inspect_ai.log import read_eval_log
from provenance import scan

WRITE = re.compile(r"-X\s*['\"]?(PUT|POST)|--upload-file|\s-T\s|--data(-binary|-raw)?[\s=]|\s-d\s|"
                   r"method\s*=\s*['\"](PUT|POST)|\.put\(|\.post\(|urlopen\([^)]*data=|Request\([^)]*data=", re.S)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dir"); ap.add_argument("--json")
    a = ap.parse_args()
    p = glob.glob(os.path.join(a.dir, "*.eval"))[0]
    from inspect_ai.log import read_eval_log_samples
    from provenance.inspect_adapter import LogMeta, sample_events
    head = read_eval_log(p, header_only=True)
    eid = head.eval.eval_id
    meta = LogMeta(eid, head.eval.task)
    writes, scores, evs = {}, {}, []
    # one sample at a time: the whole log never sits in memory
    for s in read_eval_log_samples(p, all_samples_required=False, resolve_attachments=True):
        run = f"{eid}:{s.id}:{s.epoch}"
        scores[run] = {k: v.value for k, v in (s.scores or {}).items()}
        for e in s.events:
            if e.event == "tool":
                c = str(e.arguments)
                if "artifactory" in c and WRITE.search(c):
                    writes.setdefault(run, e.timestamp.timestamp())
        evs.extend(sample_events(meta, s)[0])
        del s
    n_in = sum(e.kind != "generation" for e in evs)
    fs = scan(evs)
    first = {}
    for f in fs:
        first.setdefault((f.origin_run, f.reader_run), f)
    supported = {k for k, f in first.items() if k[0] in writes and writes[k[0]] <= f.ts}
    origins = {o for o, _ in first}
    broad = {r for r, s in scores.items() if s.get("cosim_broad_scorer") not in (0, None)}
    unsup = collections.Counter(f.origin_desc.split("(")[0].split(":")[0]
                                for k, f in first.items() if k not in supported)
    lags = sorted(f.lag for f in first.values())
    res = {"model": head.eval.model, "task_args": head.eval.task_args, "agents": len(scores),
           "inputs": n_in, "findings": len(fs), "edges": len(first), "origin_agents": len(origins),
           "registry_writers": len(writes), "edges_supported_by_prior_write": len(supported),
           "supported_frac": round(len(supported) / max(len(first), 1), 3),
           "unsupported_by_origin_kind": dict(unsup),
           "judge_broadcasters": len(broad), "judge_broadcasters_detected_as_origin": len(broad & origins),
           "writers_detected_as_origin": len(set(writes) & origins),
           "median_edge_lag_s": round(lags[len(lags) // 2], 1) if lags else None}
    print(json.dumps(res, indent=2))
    if a.json:
        open(a.json, "w").write(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
