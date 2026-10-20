# Brief — Linear Transform 2D

## Request (as stated by the user)
"A mathematical explanation of a 2D linear transformation, with correct
geometry and labels — 3Blue1Brown style."

## Interpretation
- **Audience:** someone who knows vectors but hasn't seen matrices act on space.
- **Duration target:** 30–40 s
- **Aspect / resolution:** 16:9, 1080p final

## Key ideas (in order)
1. The grid with basis vectors î (1,0) and ĵ (0,1); they *define* the coordinates.
2. A shear matrix M = [[1,1],[0,1]]: show where î and ĵ land — î→(1,0), ĵ→(1,1).
3. Space moves with them: the whole grid shears; the unit square keeps its area (det M = 1).
4. General rule: a vector (x,y) lands at x·(new î) + y·(new ĵ) — shown for (2,1) → (3,1).

## Mathematical / technical content (source of truth)
- M = [[1,1],[0,1]] (shear). M·(1,0)ᵀ = (1,0)ᵀ; M·(0,1)ᵀ = (1,1)ᵀ; M·(2,1)ᵀ = (3,1)ᵀ; det M = 1·1 − 1·0 = 1.
- All landing positions are computed in scene.py as numpy expressions from M — never hand-placed.
- Grid transform uses grid.apply_matrix(M) (ManimGL), which transforms every point by M.

## Style
- Theme: default; grid uses ManimGL's blue; basis vectors in theme colors.
- Tone: measured, each idea lands and settles before the next.

## Assumptions log
| # | Question raised | Assumption taken | Cheap to change? |
|---|---|---|---|
| 1 | Which matrix? | Shear [[1,1],[0,1]] — classic, det=1 keeps unit square visible | yes |
| 2 | Which extra vector? | (2,1) → shows the linear-combination rule concretely | yes |
| 3 | Camera | Static; the transformation *is* the motion | yes |

## Success criteria
- [ ] î and ĵ land exactly at M's columns; labels follow them
- [ ] Unit square visibly keeps its area through the shear
- [ ] (2,1) lands on (3,1) — verify in frames against grid lines
- [ ] Nothing clipped; every label legible; pauses between ideas
