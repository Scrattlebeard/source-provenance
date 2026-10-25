# PINS: open design questions

1. **What is "a run"?** It's the only config. An Inspect sample, an eval, or a task? The HF
   case needs cross-eval and cross-month scope. The rig needs per-sample. Proposal: per
   sample in the rig, and the store kept org-global.

2. **Floor on matched span, and short-secret recall.** (b) is resolved by atom shingles (docs/DESIGN.md step 8); (a) is still a strict xfail. The fixed char-40-gram does two wrong
   things. (a) When seeded boilerplate is followed by the same next letter in two files, a
   one-gram match fires (strict-xfail test). (b) A credential shorter than 40 chars, with no
   8-token shared context, is never indexed, so the "exact-substring recall is perfect" claim
   from the spec doesn't hold for UUIDs or short keys. Options: a minimum span (a knob), or
   token-level grams for single long tokens (edges back toward entropy). Both add machinery.
   Which break do we accept?

3. **Allow-list by relationship class** needs the declared graph (spawn tree, run/eval
   domains). Slice 1 only has a string-prefix stand-in. Does the spawn tree come from Inspect
   metadata, or do we declare it per experiment?

4. **Report shape.** One read yields several edges: the direct hop plus the original origin.
   Report all of them (current behaviour), or collapse to the earliest origin and keep the
   hops as a path?

5. **API spend.** Resolved: Claude Haiku 5.5, about US$0.40 per seed for all four conditions.
