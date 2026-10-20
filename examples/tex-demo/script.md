# Script — Tex Demo

> You write this (or ask the AI to draft it, then edit). The script is the
> source of truth: content, order, and emphasis come from here — the AI adds
> no ideas of its own. Any format works; the conventions below just make
> translation exact.

## Stage 1 — <short name>

Show: <what is on screen — equations, matrices, labels, verbatim>
Say: <spoken/narration line — becomes the caption if ≤ 10 words>
Math: <any values to compute, e.g. "n = 100", "verify both sides equal">

## Stage 2 — <short name>

Show:
Say:
Math:

## Stage 3 — <short name>

Show:
Say:
Math:

---

Conventions (optional but helpful):
- One `## Stage N — name` per scene stage; they become nav chips in order.
- `Show:` = on-screen content. Quote equations exactly as they should appear.
- `Say:` = narration. Short lines become the stage caption; longer ones are
  held for a future voiceover unless you mark them "on screen".
- `Math:` = values to compute with numpy + relations to assert.
- Pacing: add "(pause)" or "(hold 2s)" anywhere; otherwise each stage holds
  ~1.2 s after its motion.
