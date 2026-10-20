# ManimGL 1.7.2 (this build) — style and API guide

Verified against the installed dev checkout (`v1.7.2-163-gfafa083a`,
Python 3.10.9). Differences from ManimCE and from older ManimGL docs are marked
**GOTCHA**. When unsure about any API, grep the source:
`<manim-venv>\Lib\site-packages\manimlib\`
(e.g. `grep -n "def get_graph" mobject/coordinate_systems.py`) — the source is
the only fully version-correct reference.

## Scene skeleton (use for every scene)

```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))   # make theme importable

from manimlib import *
from theme import *                               # palette, pacing, helpers

class MyScene(Scene):                             # name must match project.json
    def construct(self):
        ...
```

## GOTCHAS (each of these produced a real failure or wrong output here)

1. **No `Create`** — that's ManimCE. Use `ShowCreation(line_or_curve)`.
   For shapes prefer `DrawBorderThenFill(shape)`; for text `Write`/`FadeIn`.
2. **Method-as-animation syntax is dead**: `self.play(mob.set_color, RED)`
   raises `TypeError: Object cannot be converted to an animation`.
   Use `self.play(mob.animate.set_color(RED))` or
   `self.play(mob.animate.shift(UP))`.
3. **`Circle` pins `stroke_color=RED`** (and other shapes pin their own
   defaults), silently overriding a generic `color=` kwarg. Always pass
   `stroke_color=` / `fill_color=`, or call `.set_stroke()/.set_fill()`.
4. **No LaTeX on this machine**: `Tex`/`MathTex` will crash at render.
   `Axes.get_axis_labels()` also uses `Tex` internally — use the theme's
   `axis_label()` instead. Math via Unicode in `math_text()`: π √ ² ³ ≤ ≥ · ×
   î ĵ ẕ ∑ ∫ ≈ → ± ∞ and subscript/superscript chars.
5. **`Axes` has no `.height`/`.width` attributes** — use `.get_height()` /
   `.get_width()`.
6. **`get_graph_by_values` doesn't exist** — build plots with
   `axes.get_graph(func, x_range=[a, b])`, wrapping sampled data with
   `lambda t: float(np.interp(t, ts, xs))`.
7. **Scene name matching is case-insensitive in ManimGL**, but animkit
   validates exact case against project.json — keep them identical anyway.
8. `pydub` prints a harmless `Couldn't find ffmpeg` RuntimeWarning on every
   run; ignore it.

## Verified building blocks

```python
# axes sized and placed explicitly
ax = Axes(x_range=[0, 2, 0.5], y_range=[-1.6, 1.6, 1],
          width=9.5, height=3.4,
          axis_config=dict(stroke_color=INK_MUTED, stroke_width=2,
                           include_tip=False, tick_size=0.06))
ax.move_to(ORIGIN + 0.25 * DOWN)
curve = ax.get_graph(lambda t: float(np.sin(TAU * t)), x_range=[0, 2])
curve.set_stroke(ACCENT, width=4)
pt = Dot(ax.c2p(1.0, 0.0), radius=0.055).set_fill(GOOD, 1.0).set_stroke(width=0)

# grid + linear map (the 3b1b classic)
plane = NumberPlane(x_range=(-7, 7, 1), y_range=(-4, 4, 1))
self.play(plane.animate.apply_matrix(np.array([[1., 1.], [0., 1.]])), run_time=3)

# vectors (arrow from origin)
v = Vector(np.array([2.0, 1.0]))          # then .set_stroke(color, width=6)

# bar chart (no BarChart class; build from rects aligned to an axis)
bar = RoundedRectangle(width=0.62, height=mag * (ax.get_height()/y_max),
                       corner_radius=0.03)
bar.set_fill(ACCENT, opacity=0.85)
bar.move_to(ax.c2p(f, 0), aligned_edge=DOWN)

# grouped simultaneous animation
self.play(FadeOut(a), FadeOut(b), ShowCreation(c), run_time=1.2)
# staggered
self.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.03))

# labels that follow objects (clear before removing!)
lab.add_updater(lambda m: m.next_to(mob, DOWN, buff=0.25))
lab.clear_updaters()
```

## Code style

- One `construct` per scene; break into `# ---- shot N: ... ----` comment
  sections matching storyboard rows.
- All constants (colors, sizes, timing) come from `theme.py`; if a new constant
  is needed twice, add it to the theme, not the scene.
- Numeric data: compute with numpy at module level, `assert` the relations the
  animation claims (see examples/signal-pipeline/scene.py).
- Positioning: `next_to`, `to_edge`, `to_corner` with explicit `buff`; avoid
  raw coordinates except deliberate `move_to(3.2 * LEFT)` class placements.
- Keep every mobject within `in_safe_area(mob)` — check during development if
  unsure, especially wide labels.
