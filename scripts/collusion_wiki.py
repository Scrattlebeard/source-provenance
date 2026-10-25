"""Real-world, descriptive: the DseWiki agent board (collusion.wiki export).

The export has every revision's full text, the agent-chosen account label, a /16
IP prefix and a timestamp, but no reads. So we run the rule output-side: when
account X *inserts* a string whose first appearance anywhere was by account Y on a
*different page*, X must have read Y's page. That is an inferred hidden read, which is
cross-page carriage. There is no ground truth, so this measures the coordination network the
method recovers, not precision or recall.

    python scripts/collusion_wiki.py <dir with revisions.jsonl.gz pages.jsonl.gz> [--json out]
"""
import argparse, collections, gzip, json, os, sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from provenance.core import shingles

MANY = 5  # a string first-inserted by >= MANY accounts is a convention, reported apart


def ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def who(r):
    return r.get("label") or f"ip16:{r.get('ip16') or '?'}"


def inserted(prev: str | None, body: str) -> str:
    """Lines in the new revision that were not in the previous one."""
    if not prev:
        return body
    old = set(prev.splitlines())
    return "\n".join(l for l in body.splitlines() if l not in old)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("dir"); ap.add_argument("--json")
    a = ap.parse_args()
    pages = {}
    with gzip.open(os.path.join(a.dir, "pages.jsonl.gz"), "rt") as f:
        for l in f:
            p = json.loads(l); pages[p["page_id"]] = p
    revs = []
    with gzip.open(os.path.join(a.dir, "revisions.jsonl.gz"), "rt") as f:
        for l in f:
            r = json.loads(l)
            if r.get("body") is not None and r.get("time"):
                revs.append(r)
    revs.sort(key=lambda r: (ts(r["time"]), r["seq"]))

    last_body = {}                      # page -> latest body
    first = {}                          # shingle -> (account, page, wiki, t)
    inserters = collections.defaultdict(set)
    acct_first, acct_last = {}, {}
    carriage = []                       # (origin acct, reader acct, origin page, reader page, owiki, rwiki, lag, shingle)
    for r in revs:
        t, acct, page, wiki = ts(r["time"]), who(r), r["page_id"], r["wiki"]
        acct_first.setdefault(acct, t); acct_last[acct] = t
        ins = inserted(last_body.get(page), r["body"])
        last_body[page] = r["body"]
        pre_existing = (pages.get(page) or {}).get("n_revs_before", 0) > 0 and r["seq"] == 1
        for sh in shingles(ins):
            inserters[sh].add(acct)
            f0 = first.get(sh)
            if f0 is None:
                first[sh] = (acct, page, wiki, t, pre_existing)
                continue
            oacct, opage, owiki, ot, opre = f0
            if oacct != acct and opage != page and not opre:
                carriage.append((oacct, acct, opage, page, owiki, wiki, t - ot, sh))

    def summarise(rows):
        edges = collections.defaultdict(lambda: {"n": 0, "lag": [], "x": False, "decoupled": False})
        for oa, ra, op, rp, ow, rw, lag, sh in rows:
            e = edges[(oa, ra)]
            e["n"] += 1; e["lag"].append(lag); e["x"] |= ow != rw
            e["decoupled"] |= acct_first[ra] > acct_last[oa]
        lags = sorted(min(e["lag"]) for e in edges.values())
        return {"strings": len(rows), "account_edges": len(edges),
                "origin_accounts": len({o for o, _ in edges}), "reader_accounts": len({r for _, r in edges}),
                "cross_wiki_edges": sum(e["x"] for e in edges.values()),
                "time_decoupled_edges": sum(e["decoupled"] for e in edges.values()),
                "median_first_lag_h": round(lags[len(lags) // 2] / 3600, 1) if lags else None}, edges

    idio = [c for c in carriage if len(inserters[c[7]]) < MANY]
    conv = [c for c in carriage if len(inserters[c[7]]) >= MANY]
    s_idio, e_idio = summarise(idio)
    s_conv, _ = summarise(conv)
    top = sorted(e_idio.items(), key=lambda kv: -kv[1]["n"])[:15]
    res = {"revisions": len(revs), "accounts": len(acct_first), "pages": len(last_body),
           "idiosyncratic": s_idio, "conventions": s_conv,
           "top_edges": [{"from": o, "to": r, "strings": e["n"], "cross_wiki": e["x"],
                          "reader_started_after_writer_stopped": e["decoupled"]} for (o, r), e in top]}
    print(json.dumps(res, indent=2))
    if a.json:
        open(a.json, "w").write(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
