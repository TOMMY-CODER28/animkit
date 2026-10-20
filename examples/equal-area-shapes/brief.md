# Brief — Equal Area Shapes

## Request (as stated by the user)
"Show a square with side 2 and a circle whose radius is chosen so both enclose
the same area, with labels, side by side."

## Interpretation
- **Audience:** general technical viewers; demonstrates positioning + timing.
- **Duration target:** 13–16 s
- **Aspect / resolution:** 16:9, 1080p final (from project.json)

## Key ideas (in order)
1. A square of side 2 (area 4) appears, labelled.
2. A circle of equal area appears next to it (r = 2/√π ≈ 1.128), labelled.
3. Both areas shown as the same value; closing formula ties them together.

## Mathematical / technical content
- Square: side a = 2, area A = a² = 4
- Circle with equal area: πr² = 4 ⇒ r = 2/√π ≈ 1.1284
- Encoded in scene.py as R_EQUAL = 2 / math.sqrt(math.pi) (never a hand-typed literal)

## Style
- Theme: default animkit theme (theme.py)
- Tone: calm explanatory; motion only to introduce/compare (no decoration)

## Assumptions log
| # | Question raised by the request | Assumption taken | Cheap to change? |
|---|---|---|---|
| 1 | Which shape first? | Square first (as stated first) | yes |
| 2 | Circle radius not given | Derived from equal-area condition | yes |
| 3 | Background | ManimGL default dark (#333) | yes |

## Success criteria
- [ ] Both shapes on screen simultaneously with persistent, correct labels
- [ ] Labels stay attached; nothing leaves the safe frame
- [ ] Pacing: a pause after each idea; no overlapping unrelated motion
- [ ] Preview frames pass the quality checklist (skill: references/quality.md)
