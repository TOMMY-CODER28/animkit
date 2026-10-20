# Brief — Transformer Attention

## Request (as stated by the user)
"Can you create an algebraic animation of the Transformer architecture?"

## Interpretation
- **Algebraic** = the animation must show *the math operating on real numbers*,
  not just architecture boxes. The heart of a Transformer is scaled dot-product
  attention; feed-forward/residual/layernorm are context captions, not visuals.
- **Audience:** technical viewers who know vectors and matrix multiplication
  but haven't internalized what attention *does* to numbers.
- **Duration target:** 40–50 s (five stages + assembly)
- **Aspect / resolution:** 16:9, 1080p final

## Key ideas (in order)
1. Tokens become an embedding matrix X (3 tokens, d = 2 — small enough to read).
2. Three linear projections produce Q, K, V from the same X.
3. Scores S = QKᵀ: every cell is a dot product qᵢ·kⱼ (one shown explicitly).
4. Scale by 1/√dₖ and softmax each row → attention weights (rows sum to 1).
5. Output = A·V: each output token is a weighted mixture of all value vectors.
6. Assemble the full equation; note multi-head + residual in one closing line.

## Mathematical / technical content (source of truth)
Concrete example, computed with numpy in scene.py (never hand-typed results):

- X = [[1,0],[0,1],[1,1]]  (tokens a, b, c)
- W_Q = I, W_K = [[1,1],[0,1]], W_V = [[2,0],[0,1]]
- Q = XW_Q = X; K = XW_K = [[1,1],[0,1],[1,2]]; V = XW_V = [[2,0],[0,1],[2,1]]
- S = QKᵀ; exemplar cell S₃₃ = q₃·k₃ = 1·1 + 1·2 = 3
- dₖ = 2 → scores divided by √2; A = row-softmax(S/√2) (scipy-free: numpy exp)
- Out = A·V; asserts: A rows sum to 1; Out equals manual weighted-sum for row 1
- Teaching moments the numbers naturally show: row 1 scores (1,0,1) → weights
  (0.40,0.20,0.40) — equal similarity ⇒ equal attention; row 3 attends mostly
  to itself (0.58).

## Style
- Theme: default. Q = ACCENT, K = HILITE, V = ACCENT_WARM, weights = GOOD.
- Pipeline choreography (cursor + chips) as in signal-pipeline: Embed →
  Project → Score → Softmax → Mix.
- Unicode math in Cambria Math: ᵀ ₖ ᵢ ⱼ √ · Σ — glyph rendering verified at
  preview (fallback: plain letters if tofu boxes appear).

## Assumptions log
| # | Question raised | Assumption taken | Cheap to change? |
|---|---|---|---|
| 1 | "Architecture" could mean the full block diagram | Focus on attention math (the algebraic core); architecture as closing caption | moderate |
| 2 | Dimensions | 3 tokens × d=2 so every number is readable | yes |
| 3 | Which heads? | Single head shown; "×h heads in parallel" as text | yes |
| 4 | Unicode super/subscripts | Preferred; will verify glyphs render, plain fallback | yes |

## Success criteria
- [ ] Every displayed matrix equals the numpy-computed array (asserts at import)
- [ ] Softmax rows visibly sum to 1 (annotation) and match computed A
- [ ] Exemplar dot product q₃·k₃ shown cell-level equals S₃₃
- [ ] Final equation assembles on screen with all terms previously introduced
- [ ] No clipping/overlap at 480p; stage cursor correct in every stage
- [ ] No tofu/missing-glyph boxes in any text (checked in frames)
