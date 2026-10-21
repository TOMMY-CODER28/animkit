# Brief — Multiply a Matrix by a Vector

## Request (as stated by the user)
The user supplied a complete script (script.md). Per the script-first
contract, the script is the source of truth: same stages, same order, same
numbers, narration kept separate from on-screen text.

## Interpretation
- **Audience:** beginners (stated).
- **Duration target:** 45–60 s (stated). Narration (~36 s) + holds/pads
  should land ~48–55 s; verified after generation.
- **Voice:** one consistent Kokoro voice (af_heart), English.

## Key ideas (from the script, in order — do not reorder)
1. Inputs: A = [[1,1],[0,1]] beside v = [1,2].
2. First output value: row 0 of A · v, shown as 1 × 1 + 1 × 2 = 3.
3. Second output value: row 1 of A · v, shown as 0 × 1 + 1 × 2 = 2.
4. Result Av = [3, 2] in operands-and-result layout, "A·v" labelled.

## Mathematical content (computed, asserted in scene.py)
- A = [[1,1],[0,1]], v = [1,2]; first = 3; second = 2; A @ v == [3, 2].

## Style
- Theme default. Narration: TTS, no captions (script: keep narration
  separate from on-screen text). On-screen text only from Show: lines.
- Pacing: holds 1s / 2s / 2s / 2s as scripted; narration sync extends holds.

## Assumptions log (visual choices only — content comes from the script)
| # | Question | Assumption | Cheap? |
|---|---|---|---|
| 1 | Highlight colours | rows ACCENT, v-entries HILITE, calc result GOOD | yes |
| 2 | Stage 4 "A v = result" | result vector labelled "A·v" (the shown vector IS the result) | yes |
| 3 | Nav chips | Inputs / Row 1 / Row 2 / Result (stage names) | yes |
| 4 | Script holds+narration total ~37 s, below the stated 45–60 s target | speed 0.9 and pad 0.8 s (beginner-appropriate pacing) to land ~47 s | yes |

## Success criteria
- [ ] All four stages present in order; nav chips match
- [ ] Every displayed number equals the numpy-computed array (asserts pass)
- [ ] Highlights exactly as scripted (row + both v entries, per stage)
- [ ] Calculation lines verbatim: 1 × 1 + 1 × 2 = 3 and 0 × 1 + 1 × 2 = 2
- [ ] Narration: one voice, per-stage, video ≥ narration per stage
- [ ] No clipping/overlap; result visible until narration ends
