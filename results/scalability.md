# Scalability (2026-10-25)

Measured with `scripts/bench.py` on one core of the analysis box, in the reference
**Python** implementation (dict store, 64-bit hashed keys). Regenerate:
`[WINNOW=20] [SUBSET=N] python scripts/bench.py <name> <dirs>`.

## Growth with fleet size (OpenAI–HF reproduction, GPT-5.6 Sol co-sim, collab off)

| agents | chars | store keys | keys/char | store MB | scan s | µs/char | findings |
|---|---|---|---|---|---|---|---|
| 32  | 1,849,669  | 840,302   | 0.454 | 357  | 7.0  | 3.79 | 136   |
| 64  | 3,640,731  | 1,486,427 | 0.408 | 687  | 14.4 | 3.94 | 625   |
| 128 | 8,057,269  | 2,904,172 | 0.360 | 1,397 | 35.2 | 4.37 | 2,662 |
| 256 | 17,296,360 | 5,320,358 | 0.308 | 2,520 | 82.4 | 4.76 | 8,311 |

The store grows sublinearly in text, because bigger fleets repeat more. Time is close to linear
in characters (+26% per char over 8x agents). Findings grow with communication
volume, as they should.

## Winnowing the character 40-grams (w = 20)

| dataset | keys/char (none -> w20) | store MB | effect |
|---|---|---|---|
| rig, overnight Haiku 5.5 | 0.336 -> 0.072 | 293 -> 64 | shared P=R=1.0 unchanged; relay R 0.841 -> 0.785, P 1.0 -> 0.994; registry FP 21 -> 11 /1k |
| co-sim GPT-5.6, collab off | 0.308 -> 0.065 | 2,520 -> 527 | edges 6,686 -> 5,584; supported 96.5% -> 98.3%; judge broadcasters found 119 -> 87 |

Winnowing guarantees a shared fingerprint for any common run of w + k - 1 = 59 characters or more.
Shorter shared spans (YAML manifests) are where recall is lost. Atoms (credentials) are unaffected.

## Projection (an estimate, not a measurement)
Per stored key in a native store: an 8 B hash + origin (run, descriptor, ts: 12 B) + one carrier
entry (8 B), about 28 B, or about 40 B at a 0.7 load factor. Per-run reader state is freed when a run
ends. Using the measured keys/char as an upper bound (larger corpora repeat more):

| volume | chars | keys (none / w20) | store (none / w20) |
|---|---|---|---|
| 10^6 rollouts x 200k chars (~50k tokens) | 2e11 | 6.2e10 / 1.3e10 | ~2.5 TB / ~0.5 TB |

Lookup cost in native code is one hash probe per key, about 0.07-0.3 probes per character. The
Python reference runs at about 4-7 µs/char (around 10 core-days for 2e11 chars). A native
rolling hash plus table should be two to three orders faster. That has not been built or measured.
