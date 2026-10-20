# Storyboard — Transformer Attention

Stage chips (top): [Embed] [Project] [Score] [Softmax] [Mix], cursor marks active.

| # | t (s) | Visual | Motion | On-screen text |
|---|-------|--------|--------|----------------|
| 1 | 0–7 | Title; chips row; X matrix (3×2) with token labels a b c | title fade, chips lagged, X writes in | "X: 3 tokens, each a 2-vector" |
| 2 | 7–15 | Q, K, V (3×2 each) in a row, color-coded, labels above | cursor→Project; three matrices fade in scaled; X shrinks to top-left | "Q = XW_Q, K = XW_K, V = XW_V" |
| 3 | 15–26 | Q left, Kᵀ right; highlight q₃ row + k₃ col; S (3×3) appears bottom-center; exemplar cell S₃₃ flashes | cursor→Score; highlight rects, arrow to cell; S cells write | "scores: Sᵢⱼ = qᵢ·kⱼ — e.g. q₃·k₃ = 1·1+1·2 = 3" |
| 4 | 26–34 | S (small, left) → A (right); row 1 scores annotated above A row 1: weights; "Σ = 1" tag on A rows | cursor→Softmax; transform S cells → A values; row-sum brace | "A = softmax(S/√dₖ) — each row sums to 1" |
| 5 | 34–44 | A left, V right → Out (3×2) center-bottom; final equation assembles beneath chips | cursor→Mix; A·V cell emphasis; equation terms fade in sequentially | "Attention(Q,K,V) = softmax(QKᵀ/√dₖ)·V" |
| 6 | 44–49 | Closing: multi-head + residual caption; fade out | caption, hold, fade all | "× h heads in parallel · residual: x + Attn(x)" |

Total ≈ 49 s.

**Actual:** 35.9 s final (default run_times for un-flagged plays made stages faster
than estimated; all five stages + assembly + closing complete — recorded rather
than padded). Two fix cycles: Kᵀ is 2×3 (IndexError on 3-row column access);
stage-2 inspection frame initially extracted at the wrong fraction — timeline
re-derived from actual run_times. Verified: cursor on the correct chip in 6/6
sampled moments (pixel match to chip geometry), matrix values straight from
numpy with import-time asserts (S₃₃=3, softmax rows Σ=1, Out=A·V), no
missing-glyph boxes in the Unicode equation band (5 box-like columns vs
dozens for tofu). Vision pass on frames unavailable this session (tool
rejected the CDN URLs); glyph shapes inferred from no-tofu check + prior
verified renders of the same font stack — noted as not directly vision-verified.

## Transitions
- Stage contents replace each other in the working area (fade old → new),
  chips + cursor persist throughout (continuity of the pipeline metaphor).
- The equation in stage 5 assembles term-by-term from the *introduced* pieces
  (softmax arrow, QKᵀ, √dₖ, V) — nothing appears that wasn't shown before.

## Planned checks
- Frames at each stage: cursor position; matrix values vs numpy arrays
  (spot-check S₃₃ = 3, A₃₃ = 0.58, Out₁₁ = 1.60)
- Glyph check: no empty-box glyphs in ᵀ ₖ ᵢ ⱼ √ Σ text
- Edge margins ≥ 8 px at 480p; no label overlap in the busy stage-5 frame
