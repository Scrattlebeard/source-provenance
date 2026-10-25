# Design notes

Idea: Daniel Juhl, September 2026. Design sessions with Claude, then built during and before
the Apart AI Collusion Research Sprint (October 2026). These notes record how the
formulation got to where it is, because several of its parts are there *because* an earlier
version broke.

## The problem
Agents that are meant to be isolated share writable infrastructure. In May 2026, OpenAI's
training-time solvers used an internal package registry as a message board between samples
([report](https://alignment.openai.com/misalignment-reports/unauthorized-artifactory-writes-and-cross-sample-communication/)).
Nobody had listed the registry as a channel. Any defence that enumerates channels fails open
on the one nobody wrote down.

## Formulation, in the order it was revised

1. **Novelty (first draft).** Index only text an agent *authored*: `novel_B = gen_B \ context_B`.
   Scan other agents' *inputs* only (never their generations, so independent convergence can't
   fire). Fire if a high-entropy substring in A's input is in some other agent's novel text.
   This is taint tracking with the model boundary as the taint source: noninterference
   (Goguen–Meseguer 1982) tested empirically.
2. **Correction: relays.** A credential that agent A *read* from a file and then posted is
   not in A's novel text, so it is never indexed, and the hop is invisible. Worse, a missed
   hop cascades: the next copy isn't novel either. Fix: tag every string at *first ingest*
   with its **source descriptor** (the tool call that brought it in, or `generated-by(B)`).
   Novelty is the special case where the descriptor is `generated-by`. The relay condition
   in `rig/` is the ablation that shows the difference.
3. **Amendment: descriptor equality, not reachability.** An early version asked whether A
   "had a path" to the source, which needs ACLs, which is channel knowledge again. The
   rule became: fire iff the first-ingest descriptor differs from the reader's input
   descriptor *and* the runs differ. Shared-repository reads have equal descriptors and stay
   silent. Descriptors are not enumerated, they are *read*: every input arrives as a tool
   result whose producing call is in the transcript, so an unknown channel still names
   itself in the finding.
4. **Step back: no surprisal.** We scan inputs only, so generation convergence can never
   fire. The language-model likelihood and entropy machinery that had grown around the
   threshold was solving a problem we no longer had. The real false positive is *multiple
   origins* (A writes `import numpy as np`, B reads it from a repository). Replacement: count
   distinct origins per shingle. One origin is a trace, many are furniture. Seed the store
   with a world corpus so common strings arrive pre-multiplied. One integer column, with no
   model and no entropy.
   *Method note:* that session was "remove machinery until it breaks". The review question
   for any addition is whether it needs to know something the transcript and the store don't
   already say.
5. **Carrier condition (sprint).** On 140 real isolated runs, environment output that repeats
   across sandboxes (pytest banners, git warnings) fired in bulk. New rule: a tool-first
   origin fires only if some *model* in another run emitted the string before the read.
   Text that never crossed a model boundary can't have been carried by an agent.
6. **Resource descriptors (sprint).** `sed -n '1,200p' f`, `cat f` and an editor view of `f`
   are one channel: `file:<path>`. A shell command with no path is `exec:<program>`.
7. **World corpus = what several runs can obtain independently (sprint).** Seeding each
   agent's *private* initial files hid every relay edge. A file in one run's workspace is
   that run's private source, and its strings reaching another run is exactly the flow
   being detected.
8. **Atom shingles (sprint).** A bare 36-character credential has no 8-token or 40-character
   context. Any unbroken run of 20 or more `[A-Za-z0-9_+=-]` characters is now a shingle of
   its own. This is length only, with no entropy measure.

## Ranking (designed; only a lag sort is implemented)
A finding is an edge, not an alert. Edges have measurable decoupling features: addressing
(named recipient vs broadcast), time (was the reader spawned after the writer ended?) and
trust domain crossed (run, task, team, eval, org). An orchestrator handing a file to its own
subagent scores 0. An HF-style board maxes all three. Allow-listing goes by *relationship
class* over those axes, never by agent pair. Identities are ephemeral, and per-pair lists are
Kemmerer's shared-resource matrix coming back.

## Known holes
- **Effect channels.** `cp`, `mv`, shell substitution: the payload never enters any model's
  context. A trusted mediator that owns the file system could propagate taint through these.
- **Names.** Filenames are shorter than any shingle.
- **Paraphrase and steganography.** These are out of scope for exact matching.
- **Scope is organisational.** A per-run store catches nothing in the May case. The store
  must be global and kept for months. Full text can't be shared across organisations;
  watermark keys (Netzer 2026) can.

## Prior art
NetInf/NetRate (Gomez-Rodriguez, Leskovec, Krause) and MemeTracker (Leskovec, Backstrom,
Kleinberg) infer diffusion graphs from who-has-the-phrase-when. Noninterference
(Goguen–Meseguer) is the formal target. The shared-resource matrix (Kemmerer) is the
enumeration approach we avoid. Statistical disclosure and traffic analysis (Danezis; Murdoch
& Danezis) cover content-free timing channels. Exam-collusion indices (Wesolowsky) justify
weighting idiosyncratic shared strings. Broder shingling gives the index.
