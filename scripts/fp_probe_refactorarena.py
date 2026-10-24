import sys, glob, collections, os, hashlib
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.dirname(__import__('os').path.abspath(__file__))))
from provenance import scan
from provenance.inspect_adapter import read_eval, prefix_normaliser
logs = sorted(glob.glob('/home/zephyr/work/refactorarena-scoring/runs/*/*.eval'))
norm = prefix_normaliser([(r"^file:(?!/)", "file:/workspace/"), (r",(?!/)", ",/workspace/")])
evs, exact = read_eval(logs, normalise=norm)
corpus, seen = {}, set()
for d in glob.glob('/home/zephyr/work/refactorarena-scoring/exports/*/*/reference-repo'):
    for root, _, files in os.walk(d):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                b = open(p, 'rb').read()
                if b'\0' in b[:4096] or len(b) > 2_000_000: continue
                h = hashlib.sha1(b).hexdigest()
                if h in seen: continue
                seen.add(h); corpus[p] = b.decode('utf-8', 'replace')
            except OSError: pass
print("corpus docs:", len(corpus))
nin = sum(1 for e in evs if e.kind != "generation")
for label, c in (("no seed", None), ("seeded", corpus)):
    fs = scan(evs, corpus=c)
    print(f"[{label}] findings: {len(fs)} | per 1k inputs: {1000*len(fs)/nin:.2f} | >=20 shingles: {sum(f.n_shingles>=20 for f in fs)} | >=5: {sum(f.n_shingles>=5 for f in fs)}")
k = lambda d: d.split('(')[0].split(':')[0]
print(collections.Counter((k(f.origin_desc), k(f.input_desc)) for f in fs).most_common(8))
for f in sorted(fs, key=lambda f: -f.n_shingles)[:8]:
    print('---', f.n_shingles, f.origin_run.split(':')[1][:38], f.origin_desc[:55], '->', f.reader_run.split(':')[1][:38], f.input_desc[:55])
    print('   ', repr(f.string[:170]))
