# Storyboard — Multiply a Matrix by a Vector

Source: script.md (verbatim Show/Say mapping). Nav chips = stage names.

| # | Stage | Template | Free comps | Entering | Leaving | Narration ≈ |
|---|-------|----------|-----------|----------|---------|-------------|
| 1 | inputs | two_columns | A, v | A, v | — | ~8 s |
| 2 | row-1 | two_columns | A, v + calc1 | hA(row0), hv(col) | — | ~9 s |
| 3 | row-2 | two_columns | A, v + calc2 | hA(row1), hv(col) | calc1, stage-2 highlights | ~9 s |
| 4 | result | operands_result | A, v, result | result | calc2, stage-3 highlights | ~10 s |

Transitions: fades only; A and v persist through every stage and hold their
positions (stay-preferred). Holds per script (1s/2s/2s/2s), extended by
narration sync. No on-screen captions (narration is separate).

Planned checks
- Frames: stage 1 (two matrices side by side), stage 2 (row-0 highlight +
  calc "= 3"), stage 3 (row-1 highlight + calc "= 2"), stage 4 (operands +
  result [3, 2], label A·v)
- Numbers vs numpy asserts; narration sync (stage ≥ narration)
