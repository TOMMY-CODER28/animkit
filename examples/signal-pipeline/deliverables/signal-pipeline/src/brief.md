# Brief — Signal Pipeline

## Request (as stated by the user)
"An engineering explanation of a signal-processing pipeline with coordinated
stages and annotations."

## Interpretation
- **Audience:** engineers new to DSP; the animation *shows* why sampling +
  FFT + filtering recovers a clean signal.
- **Duration target:** 35–45 s
- **Aspect / resolution:** 16:9, 1080p final

## Key ideas (in order)
1. Pipeline map on top: Source → Sample → Spectrum → Filter → Output; a cursor
   marks the active stage the whole way (coordinated choreography).
2. Source: a 1 Hz sine polluted with a 7 Hz component.
3. Sample: 32 samples/s (Nyquist-safe for both components: fs > 2·7).
4. Spectrum: the DFT of the *sampled* signal (numpy rfft — real math), peaks at 1 Hz and 7 Hz.
5. Filter: zero every bin above 3 Hz; inverse DFT returns the clean 1 Hz sine.

## Mathematical / technical content (source of truth)
- x(t) = sin(2πt) + 0.35·sin(14πt), t ∈ [0, 2] s
- fs = 32 Hz → N = 64 samples; rfft bins at k/2 Hz (k = 0..32)
- Expected spectrum: peaks at bin k=2 (1 Hz) and k=14 (7 Hz); all else ≈ 0
- Filter: H(k) = 1 for f ≤ 3 Hz else 0; output = irfft(X·H)
- Everything computed in scene.py with numpy at import time; bars and output
  curve are plots of those arrays, so the picture *is* the math.

## Style
- Theme: default; stage chips use theme palette; signal = INK_MUTED, samples =
  GOOD, spectrum bars = ACCENT, killed noise = BAD, output = ACCENT_WARM.
- Tone: processional — one stage at a time, cursor leads the eye.

## Assumptions log
| # | Question raised | Assumption taken | Cheap to change? |
|---|---|---|---|
| 1 | Which pipeline? | Sampling → DFT → ideal low-pass → iDFT (canonical DSP) | moderate |
| 2 | Signal parameters | 1 Hz + 7 Hz as above (integer periods avoid leakage) | yes |
| 3 | Ideal brick-wall filter | Yes — simplest to visualize correctly | yes |

## Success criteria
- [ ] Stage cursor highlights each chip exactly while its content plays
- [ ] Spectrum shows exactly two peaks at the annotated frequencies
- [ ] Output curve overlays the 1 Hz sine (verified vs precomputed array)
- [ ] No clipping/overlap; readable at 480p preview; pauses between stages
