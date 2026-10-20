# Recipes — common animation building blocks

Each recipe is verified on this build. Combine; don't copy whole scenes.

## Labelled diagram (equal-area-shapes pattern)

```python
shape = Square(side_length=2)
shape.set_stroke(ACCENT, width=4); shape.set_fill(ACCENT, opacity=0.25)
shape.move_to(3.2 * LEFT)
lab  = label_for(shape, "A = 4", UP, buff=0.45, math=True, color=ACCENT)
self.play(DrawBorderThenFill(shape), run_time=1.2)
self.play(Write(lab))
```

## Graph on axes with sampled data (signal-pipeline pattern)

```python
ts = np.linspace(0, 2, 400); xs = np.sin(TAU * ts)
ax = Axes(x_range=[0, 2, 0.5], y_range=[-1.6, 1.6, 1], width=9.5, height=3.4,
          axis_config=dict(stroke_color=INK_MUTED, stroke_width=2,
                           include_tip=False))
ax.move_to(ORIGIN + 0.25 * DOWN)
curve = ax.get_graph(lambda t: float(np.interp(t, ts, xs)), x_range=[0, 2])
self.play(ShowCreation(curve), FadeIn(ax), run_time=1.6)
```

## Linear transformation (linear-transform-2d pattern)

```python
M = np.array([[1., 1.], [0., 1.]])
plane = NumberPlane(x_range=(-7, 7, 1), y_range=(-4, 4, 1))
i_hat = Vector(np.array([1., 0.])); i_hat.set_stroke(ACCENT_WARM, width=6)
j_hat = Vector(np.array([0., 1.])); j_hat.set_stroke(HILITE, width=6)
moving = VGroup(plane, i_hat, j_hat)          # group BEFORE animating
self.play(*[m.animate.apply_matrix(M) for m in moving], run_time=3)
# landing labels AFTER the move, computed from M:
landed = label_for(j_hat, f"ĵ → ({(M @ [0,1])[0]:g}, {(M @ [0,1])[1]:g})", ...)
```
Note: labels attached *during* the move need updaters (`pin_label`); simpler to
clear them and write fresh landing labels after.

## Multi-stage pipeline (signal-pipeline pattern)

Stage chips row + a cursor rectangle that marks the active stage:

```python
chips = VGroup(*[VGroup(RoundedRectangle(width=2.35, height=0.62, corner_radius=0.12)
              .set_stroke(INK_MUTED, width=2),
              text(name, CAPTION, INK_MUTED)) for name in STAGES])
for g in chips: g[1].move_to(g[0])
chips.arrange(RIGHT, buff=0.35).to_edge(UP, buff=1.05)
cursor = RoundedRectangle(width=2.53, height=0.80, corner_radius=0.14)
cursor.set_stroke(ACCENT, width=3); cursor.move_to(chips[0])
# per stage: move cursor first, then play the stage's content
self.play(cursor.animate.move_to(chips[i]), run_time=0.5)
```
Rule: cursor arrives → content plays → settle pause → next. Content for a
stage replaces the previous stage's content (fade out old, fade in new).

## Bar chart from a spectrum/array

```python
bars, bar_at = VGroup(), {}
for i, (f, mag) in enumerate(zip(freqs, spec)):
    if mag < 0.01: continue                    # keep a bin->bar map!
    bar = RoundedRectangle(width=0.62,
                           height=max(mag * (ax.get_height()/y_max), 0.03),
                           corner_radius=0.03)
    bar.set_fill(ACCENT, opacity=0.85).set_stroke(ACCENT, width=1)
    bar.move_to(ax.c2p(f - 0.35, 0), aligned_edge=DOWN)
    bars.add(bar); bar_at[i] = bar
```
Keep `bar_at` so later stages can address bin k (filtering, annotation).

## Emphasis without decoration

```python
self.play(mob.animate.set_color(ACCENT_WARM), run_time=0.6)   # color flash
surround = SurroundingRectangle(mob, buff=0.12).set_stroke(ACCENT, width=3)
self.play(ShowCreation(surround))
```
Use to direct attention at the moment an idea lands — then revert or remove.

## Self-cleaning ending

```python
self.play(*[FadeOut(m) for m in self.mobjects]); self.wait(END_PAUSE)
```
Clears everything including lingering updaters' targets; end on the theme's
END_PAUSE so the video doesn't cut mid-frame.
