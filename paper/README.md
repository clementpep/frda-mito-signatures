# Manuscript

`paper/manuscript.md` (created by T-017) never contains a hand-typed result:

- numbers: `{{C-004:/fxn/log2_fc:.2f}}` — value from the artifact of claim C-004,
- citations of our own results: `[C-004]` — must be a claim that passed verification,
- `frda render-paper` writes `paper/build/manuscript.md`; the `paper` gate fails on unresolved
  tokens, unverified claims, or statistics typed by hand (`p < 0.05` outside a token).

Authorship and submission are human decisions (task T-019).
