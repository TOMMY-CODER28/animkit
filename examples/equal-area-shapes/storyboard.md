# Storyboard — Equal Area Shapes

| # | t start (s) | Length (s) | Visual | Motion / animation | Camera | On-screen text |
|---|-------------|------------|--------|--------------------|--------|----------------|
| 1 | 0.0 | 1.5 | Title top; empty stage | Title fade-in | static | "Same area, different shapes" |
| 2 | 1.5 | 3.2 | Square (side 2) left-of-center | DrawBorderThenFill + labels | static | "a = 2", "A = a² = 4" |
| 3 | 4.7 | 3.2 | Circle (r≈1.128) right-of-center | DrawBorderThenFill + labels | static | "r = 2/√π ≈ 1.128", "A = πr² = 4" |
| 4 | 7.9 | 2.3 | Both area labels emphasized | brief color pulse on area texts | static | (same, highlighted) |
| 5 | 10.2 | 3.8 | Closing caption | caption fade-in, hold, fade all | static | "a² = πr² = 4" |

Total ≈ 14 s (within 13–16 s target).

## Transitions
- 1→2: square draws beneath the title (creation, nothing removed)
- 2→3: circle draws while square idles — attention shifts via motion
- 4: emphasis via color flash on area labels only (geometry unchanged)
- 5: everything fades together; formula caption closes

## Planned checks
- Frames at ~1.0 s (title), ~4.2 s (square+labels), ~7.5 s (circle+labels), ~11 s (caption)
- Math verified: R_EQUAL = 2/sqrt(pi) in scene.py; areas both display 4
