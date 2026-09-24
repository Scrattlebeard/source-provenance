"""Pure core: shingles, the origin store, and the scan. No I/O.

Formulation (workshop spec, post-STEP-BACK):
  * Every string is tagged at first ingest with its source descriptor
    (the tool call that brought it in, or ``generated-by(agent)``).
  * A finding fires for reader A iff a shingle in A's *input* has a first-ingest
    entry (R1, d1) with d1 != d2 (A's current input descriptor) and R1 != R2
    (A's run), and the shingle's origin_count <= threshold (default 1).
  * origin_count = number of distinct *origins*: independent entries of the
    string into the world (a generation that was not a copy, a first-ever
    ingest, or a world-corpus document). Copies never add origins, so an
    undetected-or-detected hop never inflates the count: no cascade miss.
  * Reader-side exclusion: a shingle already present in the reader's run
    (its own prior generation or prior input) is not evidence of inbound info.

No surprisal, entropy or LM. Everything here is known from the transcript + store.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

WORD_K = 8
CHAR_K = 40
WORLD = "<world>"

_TOKEN = re.compile(r"\S+")
_WS = re.compile(r"\s+")


def shingles(text: str, word_k: int = WORD_K, char_k: int = CHAR_K) -> set[str]:
    """8-token word shingles plus char-40-grams over whitespace-normalised text.

    Char-grams are applied to all text, not just "code": deciding what is code
    would be machinery. They are what catch long credentials/URLs whose word
    context differs between writer and reader.
    """
    out: set[str] = set()
    toks = _TOKEN.findall(text)
    for i in range(len(toks) - word_k + 1):
        out.add("w:" + " ".join(toks[i : i + word_k]))
    flat = _WS.sub(" ", text).strip()
    for i in range(len(flat) - char_k + 1):
        out.add("c:" + flat[i : i + char_k])
    return out


@dataclass(frozen=True)
class Origin:
    run: str
    descriptor: str
    ts: float
    agent: str | None


@dataclass(frozen=True)
class Finding:
    reader: str          # agent that received the text
    reader_run: str
    string: str          # one representative matched shingle
    n_shingles: int      # how many shingles of this input traced to this origin
    origin_run: str
    origin_desc: str
    input_desc: str
    lag: float           # reader ts - origin ts
    ts: float


@dataclass
class Store:
    """shingle -> origins (first entries into the world); plus per-run presence."""
    origins: dict[str, list[Origin]] = field(default_factory=dict)
    seen_in_run: dict[str, set[str]] = field(default_factory=dict)

    def origin_count(self, sh: str) -> int:
        # Distinct (run, descriptor): the same agent name converging in two
        # runs is two origins, not one.
        return len({(o.run, o.descriptor) for o in self.origins.get(sh, ())})

    def first(self, sh: str) -> Origin | None:
        os_ = self.origins.get(sh)
        return min(os_, key=lambda o: o.ts) if os_ else None

    def add_origin(self, sh: str, o: Origin) -> None:
        self.origins.setdefault(sh, []).append(o)


def seed(store: Store, corpus: dict[str, str]) -> None:
    """World corpus: each document is its own origin, so common strings
    arrive pre-multiplied (the numpy-furniture fix)."""
    for name, text in corpus.items():
        for sh in shingles(text):
            store.add_origin(sh, Origin(WORLD, f"corpus({name})", float("-inf"), None))


def ingest(store: Store, ev, threshold: int = 1) -> list[Finding]:
    """Process one event (in ts order). Returns findings for input events."""
    present = store.seen_in_run.setdefault(ev.run, set())
    new = shingles(ev.text) - present   # reader-side exclusion
    present |= new
    if ev.kind == "generation":
        desc = f"generated-by({ev.agent})"
        # Anything the reader already had was excluded above, so a known
        # string generated here was authored independently: a new origin.
        for sh in new:
            store.add_origin(sh, Origin(ev.run, desc, ev.ts, ev.agent))
        return []
    # input event: tool_result / user
    hits: dict[tuple[str, str], list[str]] = {}
    first_of: dict[tuple[str, str], Origin] = {}
    for sh in new:
        o = store.first(sh)
        if o is None:
            store.add_origin(sh, Origin(ev.run, ev.descriptor, ev.ts, None))
            continue
        # Corpus-first strings pre-date every run: never inter-agent traffic.
        if (o.run not in (ev.run, WORLD) and o.descriptor != ev.descriptor
                and store.origin_count(sh) <= threshold):
            key = (o.run, o.descriptor)
            hits.setdefault(key, []).append(sh)
            first_of[key] = o
    return [
        Finding(ev.agent, ev.run, _span(ev.text, shs), len(shs), k[0], k[1],
                ev.descriptor, ev.ts - first_of[k].ts, ev.ts)
        for k, shs in sorted(hits.items())
    ]


def _span(text: str, shs: list[str]) -> str:
    """Longest contiguous stretch of the reader's input covered by the hits."""
    flat = _WS.sub(" ", text).strip()
    ivs = []
    for sh in shs:
        if sh.startswith("c:"):
            i = flat.find(sh[2:])
            while i != -1:
                ivs.append((i, i + len(sh) - 2))
                i = flat.find(sh[2:], i + 1)
    if not ivs:
        return max(shs, key=len)[2:]
    ivs.sort()
    best = cur = ivs[0]
    for a, b in ivs[1:]:
        cur = (cur[0], max(cur[1], b)) if a <= cur[1] else (a, b)
        if cur[1] - cur[0] > best[1] - best[0]:
            best = cur
    return flat[best[0]:best[1]]


def scan(events, corpus: dict[str, str] | None = None, threshold: int = 1,
         store: Store | None = None) -> list[Finding]:
    store = store or Store()
    if corpus:
        seed(store, corpus)
    out: list[Finding] = []
    for ev in sorted(events, key=lambda e: e.ts):
        out.extend(ingest(store, ev, threshold))
    return out


def rank(findings: list[Finding]) -> list[Finding]:
    """Stub for decoupling rank: longest lag first (time-decoupled reads are
    the most damning single feature). Addressing / trust-domain axes need the
    declared graph, which slice 1 does not have."""
    return sorted(findings, key=lambda f: -f.lag)
