"""Pure core: shingles, the origin store, and the scan. No I/O.

Formulation (docs/DESIGN.md, steps 2-8):
  * Every string is tagged at first ingest with its source descriptor
    (the tool call that brought it in, or ``generated-by(agent)``).
  * A finding fires for reader A iff a shingle in A's *input* has a first-ingest
    entry (R1, d1) with d1 != d2 (A's current input descriptor) and R1 != R2
    (A's run), and the shingle's origin_count <= threshold (default 1).
  * origin_count = number of distinct *origins*: independent entries of the
    string into the world (a generation that was not a copy, a first-ever
    ingest, or a world-corpus document). Copies never add origins, so an
    undetected-or-detected hop never inflates the count: no cascade miss.
  * Carrier condition (slice 2): the shingle must have been *emitted by a model*
    in some run other than the reader's before the read. Generated origins meet
    this trivially. For tool-first origins it separates "an agent carried this"
    from "the shared environment printed it twice" (pytest banners, git
    warnings: 2,913 FP/1k inputs on isolated refactor logs without it).
  * Reader-side exclusion: a shingle already present in the reader's run
    (its own prior generation or prior input) is not evidence of inbound info.

No surprisal, entropy or LM. Everything here is known from the transcript + store.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

WORD_K = 8
CHAR_K = 40
ATOM_MIN = 20   # PINS #2 resolution (2026-10-24): credentials are 20-40 chars

_ATOM = re.compile(r"[A-Za-z0-9_+=-]{%d,}" % ATOM_MIN)
WORLD = "<world>"

_TOKEN = re.compile(r"\S+")
_WS = re.compile(r"\s+")


def shingles(text: str, word_k: int = WORD_K, char_k: int = CHAR_K,
             atoms: bool = True) -> set[str]:
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
    if atoms:
        # Atom shingles: one long unbroken [A-Za-z0-9_+=-] run is a shingle on
        # its own, so a 36-char token handed over bare (no 8-token or 40-char
        # shared context) is still visible. Length only, no entropy: common
        # long identifiers are furniture and the world seed / origin count
        # handle them like every other string. '/' and '.' split, so paths
        # don't become atoms.
        for m in _ATOM.finditer(text):
            out.add("a:" + m.group())
    return out


@dataclass(frozen=True, slots=True)
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


def _k(sh: str) -> int:
    """Store key: a 64-bit hash, never the text. Memory (a 256-agent co-sim
    peaked at 4.4 GB with string keys) and privacy (Appendix A: the index must
    not become a plaintext copy of every secret any agent touched). In-process
    hash() is enough here; a deployment would use a keyed hash."""
    return hash(sh)


@dataclass
class Store:
    """shingle -> origins (first entries into the world); plus per-run presence.
    Keyed by hash; most keys have exactly one origin, stored bare."""
    origins: dict[int, "Origin | list[Origin]"] = field(default_factory=dict)
    seen_in_run: dict[str, set[int]] = field(default_factory=dict)
    # shingle -> {run: first ts a model in that run emitted it}. The carrier
    # record: text that crossed a model boundary outward (slice 2).
    emitted: dict[int, dict[str, float]] = field(default_factory=dict)

    def emit(self, sh: str, run: str, ts: float) -> None:
        self.emitted.setdefault(_k(sh), {}).setdefault(run, ts)

    def carried(self, sh: str, reader_run: str, ts: float) -> bool:
        """Did a model in some other run emit this before the reader read it?"""
        return any(r != reader_run and t <= ts for r, t in self.emitted.get(_k(sh), {}).items())

    def _all(self, sh: str) -> list[Origin]:
        v = self.origins.get(_k(sh))
        return [] if v is None else (v if isinstance(v, list) else [v])

    def origin_count(self, sh: str) -> int:
        # Distinct (run, descriptor): the same agent name converging in two
        # runs is two origins, not one.
        return len({(o.run, o.descriptor) for o in self._all(sh)})

    def first(self, sh: str) -> Origin | None:
        os_ = self._all(sh)
        return min(os_, key=lambda o: o.ts) if os_ else None

    def add_origin(self, sh: str, o: Origin) -> None:
        k = _k(sh)
        v = self.origins.get(k)
        if v is None:
            self.origins[k] = o
        elif isinstance(v, list):
            v.append(o)
        else:
            self.origins[k] = [v, o]


def seed(store: Store, corpus: dict[str, str], atoms: bool = True) -> None:
    """World corpus: each document is its own origin, so common strings
    arrive pre-multiplied (the numpy-furniture fix)."""
    for name, text in corpus.items():
        for sh in shingles(text, atoms=atoms):
            store.add_origin(sh, Origin(WORLD, f"corpus({name})", float("-inf"), None))


MODES = ("descriptor", "novelty")


def ingest(store: Store, ev, threshold: int = 1, mode: str = "descriptor",
           atoms: bool = True) -> list[Finding]:
    """Process one event (in ts order). Returns findings for input events.

    ``mode="novelty"`` is the ablation: only ``generated-by`` origins can fire
    (the pre-CORRECTION formulation). Relays of ingested secrets go dark."""
    present = store.seen_in_run.setdefault(ev.run, set())
    sh_all = shingles(ev.text, atoms=atoms)
    new = {sh for sh in sh_all if _k(sh) not in present}   # reader-side exclusion
    present.update(_k(sh) for sh in new)
    if ev.kind == "generation":
        for sh in sh_all:                     # copies count as carriage too
            store.emit(sh, ev.run, ev.ts)
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
        if mode == "novelty" and not o.descriptor.startswith("generated-by("):
            continue
        if (o.run not in (ev.run, WORLD) and o.descriptor != ev.descriptor
                and store.origin_count(sh) <= threshold
                and store.carried(sh, ev.run, ev.ts)):
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
        if sh.startswith(("c:", "a:")):
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
         store: Store | None = None, mode: str = "descriptor",
         atoms: bool = True) -> list[Finding]:
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}")
    store = store or Store()
    if corpus:
        seed(store, corpus, atoms)
    out: list[Finding] = []
    for ev in sorted(events, key=lambda e: e.ts):
        out.extend(ingest(store, ev, threshold, mode, atoms))
    return out


def rank(findings: list[Finding]) -> list[Finding]:
    """Stub for decoupling rank: longest lag first (time-decoupled reads are
    the most damning single feature). Addressing / trust-domain axes need the
    declared graph, which slice 1 does not have."""
    return sorted(findings, key=lambda f: -f.lag)
