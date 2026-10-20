# Quality checklist — apply to every preview

A successful render is not a finished animation. Before approving frames:

## Typography & color
- [ ] Text crisp at 480p preview (if unreadable at 480p, it's too small —
      raise font size; 1080p won't save it)
- [ ] ≤ 2 font families (theme default: Segoe UI + Cambria Math for math)
- [ ] ≤ 4 distinct colors on screen at once (theme palette counts as one scheme)
- [ ] Contrast: nothing darker than INK_MUTED (#AAB2BA) on the dark background

## Layout & labels
- [ ] Nothing within 0.3 manim units of the frame edge (safe area check)
- [ ] Labels clearly attached to their object — a label floating equidistant
      between two objects is a bug
- [ ] No label-on-label or label-on-curve overlap; check the busy frames
      (all-elements-present moments), not the calm ones
- [ ] Visual hierarchy: title > labels > captions in size; one focal point
      per shot

## Mathematical / technical correctness
- [ ] Every position claimed to be "at (x, y)" actually is — verify against
      grid lines or axis ticks in the frame (see inspection.md for the pixel method)
- [ ] Values in labels match values in code constants (no drift after edits)
- [ ] Geometry claims (area preserved, symmetry, alignment) visible and true

## Motion & pacing
- [ ] One idea per shot; a pause after each idea (IDEA_PAUSE or longer)
- [ ] No two unrelated motions at once (transform + unrelated fade = confusion)
- [ ] Transitions either transform (continuity) or fully clear (new context),
      never half-fade leftovers
- [ ] Camera static unless the move *is* the explanation (zoom into detail,
      pan along a pipeline)
- [ ] Total duration within the brief's target; drift > 30% means re-time or
      revise the brief with stated rationale

## Anti-patterns (automatic reject)
- Text that re-wraps or jumps during a transform
- A moving object whose static label doesn't follow (or vice versa: updater
  left running after the object is gone)
- Decorative motion: wiggles, spins, pulses that carry no meaning
- An equation appearing that is never referred to again
- Empty holds > 2 s (dead air) — cut them, don't pad duration

## Bounded revision loop

Cycle: fix scene.py → `preview` → `frames` → check this list.
**Hard stop at 3 cycles.** Passing = every success criterion in brief.md
checks out. Failing after 3: deliver best state + honest list of what's wrong.
Between cycles change *one thing at a time*; two fixes per cycle makes the
third cycle un-diagnosable.
