# Inspecting results

## Frame extraction

```
animkit.cmd frames <project> --at 0.1,0.3,0.55,0.8    # fractions of duration
animkit.cmd frames <project> --count 8                 # evenly spaced
```
Fractions beat counts: align them with the storyboard's shot starts *as
actually rendered* — read `duration_s` from the preview result first, then
compute fractions for the moments you planned to check. A frame extracted at
the wrong moment verifies nothing.

## If you can read images

Read every extracted PNG. Quote the text you see (catches silent text
corruption), describe label placement, look at edges. Judge against
`quality.md`.

## Objective checks (always available; use even with vision)

Run these with the manim venv python. They catch what eyes miss and work
when image reading isn't available.

```python
from PIL import Image
import numpy as np
img = np.asarray(Image.open(frame).convert('RGB')).astype(int)

# 1) nothing clipped: ink bounding box keeps clear of edges
g = img.sum(axis=2) / 3
ink = g > 90
rows, cols = np.any(ink, 1), np.any(ink, 0)
margins = dict(top=int(np.argmax(rows)),
               bottom=int(img.shape[0]-1-np.argmax(rows[::-1])),
               left=int(np.argmax(cols)),
               right=int(img.shape[1]-1-np.argmax(cols[::-1])))
assert min(margins.values()) >= 8, margins      # px, at 480p

# 2) an element is where math says (e.g. vector tip at grid (3,1))
def tip_of(target_rgb, tol=45):
    mask = np.abs(img - np.array(target_rgb)).sum(axis=2) < tol
    ys, xs = np.nonzero(mask)
    cx, cy = img.shape[1]/2, img.shape[0]/2
    i = np.argmax((xs-cx)**2 + (ys-cy)**2)     # furthest from origin = tip
    return xs[i], ys[i]
# convert px -> grid units with the axis geometry (unit = axis_px / axis_units)

# 3) a stage really happened (color census)
def px(target, tol=60):
    return int((np.abs(img - np.array(target)).sum(axis=2) < tol).sum())
# e.g. accent bars present at spectrum stage, red strike at filter stage

# 4) two element groups don't collide (background gap between them)
```

Calibration facts for this setup: frame is 14.222 x 8.0 manim units; at 854x480
preview that's ≈ 60.1 px per unit, origin at pixel center. Differential
measurements (distance between two features) are exact even if your unit
calibration is slightly off — prefer them.

## Temporal behavior

Static frames can't catch mid-animation errors (labels detaching during a
transform, flicker). Two mitigations:
- Extract a *dense* pair around a transform (`--at 0.61,0.64`) and check the
  label is still attached in both.
- For math transforms, verify the *end* state numerically (end positions are
  what persists).
State in your report which of these you did and which you couldn't.

## What to report

Always state, factually: which frames were inspected, by which method (vision
/ pixel checks / both), what passed, and what was NOT verified (e.g. "frame
inspection only; mid-transition continuity not checked").
