# Storyboard — Signal Pipeline

Stage row (top, y≈3.1): five chips [Source][Sample][Spectrum][Filter][Output];
a cursor rect moves chip-to-chip; the active chip brightens.

| # | t (s) | Visual (main area) | Motion | On-screen text |
|---|-------|--------------------|--------|----------------|
| 1 | 0–5 | Title; chips fade in; cursor → Source; noisy curve draws | curve Create; dots of 7Hz component? no — single curve | "x(t) = sin(2πt) + 0.35·sin(14πt)" |
| 2 | 5–11 | Same curve; 32 sample dots land | LaggedStart dots; cursor → Sample | "fs = 32 Hz (Nyquist: fs > 2·7)" |
| 3 | 11–18 | Time plot swaps to spectrum bars (rfft of samples) | fade time, grow bars; cursor → Spectrum | "X(f): peaks at 1 Hz and 7 Hz" |
| 4 | 18–25 | Bars above 3 Hz turn red, drop to zero | bars animate down + recolor; cursor → Filter | "H(f): keep f ≤ 3 Hz" |
| 5 | 25–34 | Spectrum swaps to output: clean sine vs original (muted) | fade spectrum, draw clean curve; cursor → Output | "x̂(t): 7 Hz removed" |
| 6 | 34–38 | Everything resolves; closing caption | caption, hold, fade | "sample → transform → filter → invert" |

Total ≈ 38 s.

## Transitions
- Cursor slide between chips is the metronome; content changes happen *after*
  the cursor arrives (order: cursor → content → settle).
- Time↔spectrum swaps are fades (transforming axes types directly is visually noisy).

## Planned checks
- Frames during each stage: cursor on right chip; two spectrum peaks; red bars gone in 4; clean overlay in 5
- Numeric: bars array == abs(rfft(x))[0:17] normalized (assert in code)
