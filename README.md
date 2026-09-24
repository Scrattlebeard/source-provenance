# source-provenance

Detects communication between agents by looking at where the text in their inputs came from.
It does not enumerate channels. Every string is tagged with the descriptor of the tool call
that first brought it in, or with `generated-by(agent)`. If agent A's input contains a string
that entered the world through a different descriptor in a different run, and the string has
exactly one origin, then that string moved from there to A. The finding names the channel
itself: the input descriptor A read it through.

Design and history: `~/realm/house/workshop/source-provenance-collusion.md` (idea: Daniel,
2026-09-18). This repo implements the formulation that came out of that session's
CORRECTION, Amendment and STEP BACK.

## Slice 1 (2026-09-24): pure core plus synthetic conditions

- `provenance/core.py` is pure, with no I/O.
  - `shingles`: 8-token word shingles plus char-40-grams, applied to all text.
  - `Store`: maps each shingle to its origins, and tracks per-run presence.
  - `seed`: loads a world corpus. Each document counts as its own origin.
  - `scan` / `ingest`: process events in timestamp order.
  - `rank`: a stub that sorts by lag.
- `provenance/schema.py` holds the `Event` schema (run, agent, ts, kind, descriptor, text)
  and an identity `normalise_descriptor`. There is a **TODO** for the Inspect adapter.
- `tests/test_conditions.py` covers the five hackathon conditions as synthetic transcripts.
  Result: 11 pass and 1 strict-xfail (see PINS #2).

Run: `uv venv .venv && uv pip install --python .venv/bin/python pytest && .venv/bin/python -m pytest`

### The rule
For each input event (tool_result or user) from reader A in run R2 with descriptor d2, and
for each shingle not already present in R2:
- If the shingle is unknown, this is its first ingest into the world. Record the origin
  (R2, d2).
- Otherwise, take the first origin (R1, d1). Fire if R1 ∉ {R2, world}, d1 ≠ d2, and
  origin_count ≤ threshold (default 1).

For generation events, every shingle not already present in the run becomes a new origin
`generated-by(agent)`. The agent didn't read it, so it authored it, independently if other
runs also produced it. Copies never add origins. So an undetected hop never inflates the
count, and the relay is found at every hop (tested).

origin_count counts distinct (run, descriptor) pairs, so the same agent name converging in
two runs counts as two origins.

### Deliberately absent
There is no surprisal, entropy, LM or logprobs. There are no channel lists, ACLs or
reachability model. The only config is what counts as a run. There is no Bloom/LSH index,
because a dict is fine at this size. Each of these was removed on purpose; see the method
note in the spec.

### Behaviour worth knowing
- A single reader event can produce several edges: the direct hop (C's framing
  `fwd: …` → `generated-by(C)`) and the original origin (the bare token →
  `read_file(/secrets/…)`). Both are true. PINS #4.
- Strings whose first origin is the world corpus never fire. A poisoned package that both
  runs install is supply chain, not collusion.

## Next slices
2. The Inspect AI adapter: `.eval` logs → `Event`s, with descriptors taken from the tool
   calls. Descriptor normalisation across sandboxes goes here.
3. A two-agent rig: Inspect plus a compose volume, with an infra oracle (inotify, a local
   registry access log) as ground truth. Measure edge P/R and time-to-detection.
4. The May-8 replay: would this have fired on the HF message-board timeline?
