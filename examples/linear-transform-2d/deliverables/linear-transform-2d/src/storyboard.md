# Storyboard — Linear Transform 2D

| # | t start (s) | Length (s) | Visual | Motion / animation | Camera | On-screen text |
|---|-------------|------------|--------|--------------------|--------|----------------|
| 1 | 0.0 | 4.5 | Grid; î, ĵ with labels; unit square | grid fades in, vectors grow, square draws | static | "Basis vectors: î = (1, 0), ĵ = (0, 1)" |
| 2 | 4.5 | 4.5 | Matrix M appears top-right; caption names the shear | matrix writes in | static | "M = [1 1; 0 1]  (shear)" |
| 3 | 9.0 | 6.0 | Whole plane shears; î, ĵ, square, vector move with it | grid.animate.apply_matrix(M), 3s; labels follow | static | î label → "(1, 0)", ĵ label → "(1, 1)" |
| 4 | 15.0 | 6.0 | Vector v=(2,1) highlighted before+after | v draws pre-shear (shot 3 start), lands on (3,1); dashed landing mark | static | "v = (2, 1) → Mv = (3, 1)" |
| 5 | 21.0 | 8.0 | Rule caption; area note; fade out | caption in, hold, all out | static | "Mv = x·(new î) + y·(new ĵ);  det M = 1: area preserved" |

Total ≈ 29–34 s.

## Transitions
- Single continuous shear animation carries shot 3 — the centerpiece.
- All labels ride their objects via updaters, cleared before removal.

## Planned checks
- Frames: ~3.5s (basis), ~8s (matrix shown), ~14s (mid/post-shear: verify ĵ at (1,1) against grid), ~19s (v landed at (3,1)), ~25s (rule)
- Numeric checks in code: landing positions computed from M via numpy, not typed
