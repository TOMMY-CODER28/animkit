# Animating a user-written script

When the user provides a script (any format — `script.md`, prose, bullet
points, even a narrated outline), the division of labor changes:

> **The user owns the content. You own the animation.**

Your job is *fidelity*: translate their script into a SceneSpec exactly —
same ideas, same order, same emphasis, same numbers. This is the opposite of
the from-request workflow, where you invent content and log assumptions.

## When the request is too thin: draft the script first

If the user hasn't supplied a script AND the request doesn't pin down the
content (no equations, no structure, just a topic), **draft `script.md` and
get it approved before writing any scene code.** One cheap content review
beats three expensive video-revision cycles.

Drafting rules:
- One `## Stage N — name` per idea; 3–6 stages for a 20–40 s video.
- Use canonical math and canonical examples (integer periods, det=1 matrices,
  n=100 for Gaussian sums) and **mark every inferred choice**: `[assumed:
  n=100]`, `[assumed: shear matrix]`. The user should see at a glance what
  they can veto.
- `Show:` lines must be renderable with the component library (matrices,
  equations, text, highlights). If the idea needs geometry or graphs the
  library doesn't cover, say so in the draft.
- Ask at most 3 questions alongside the draft (audience level, duration,
  any must-include). Everything else is in the draft as marked assumptions.
- **Do not write scene.py until the user approves the script** (or has said
  "just proceed" — then the approved-by-default draft becomes the source of
  truth and the fidelity contract below applies to it).

## The fidelity contract

1. **No added, dropped, or reordered ideas.** If the script has four stages,
   the spec has four stages, in that order. Nav chips match the stages.
2. **Equations and numbers are quoted verbatim** on screen, then *computed*
   with numpy. If the script asserts an equality or a value, add an `assert`.
3. **Math errors stop the work.** If computation contradicts the script
   (e.g. the script claims 2+3·4 = 20), do not render the wrong math — show
   the user the computed value and ask. Everything else ambiguous: pick the
   reasonable reading and log it in the assumptions log (brief.md).
4. **Emphasis follows the script.** Words like "big", "then", "highlight",
   "only after" map to template choice, transition intent, and highlights.
   "Only" and "nothing else" → exactly those components, no title flourish.
5. **Pacing hints are honored**: "(pause)", "(hold 2s)", "let it sink in" →
   `timing.hold`. Default hold 1.0–1.5 s per stage.

## Mapping rules (script → spec)

| Script element | Spec translation |
|---|---|
| `## Stage N — name` (or "Scene", "Beat", numbered section) | `StageSpec(id=slug(name), …)`, in script order; name → nav chip label |
| `Show: <equation>` | `equation` component, parts quoted verbatim; color key terms with theme colors |
| `Show: <numbers / grid>` | `matrix` component (values from the computed numpy array, never literals) |
| `Show: highlight X` / "circle the …" | `highlight` component targeting the matrix part |
| `Show: <diagram description>` | if it maps to matrices/equations/text, build it; if it needs geometry (triangles, graphs, rectangles), say so and propose the nearest spec representation or a hand-positioned scene — **do not silently fake it** |
| `Say: <short line>` (≤ ~10 words) | stage `caption` |
| `Say: <long narration>` | keep out of the video; record under brief "narration (future voiceover)" unless marked "on screen" |
| `Math: n = 100` etc. | module-level numpy constants + asserts |
| "(pause)" / "(hold 2s)" | `timing.hold` |

## Procedure

1. Read the script fully. List the stages and every Show/Say/Math item.
2. Compute all the math first (module level, with asserts). If anything
   contradicts the script → stop, report, ask (rule 3).
3. Fill brief.md: request = "animate the attached script (source of truth)",
   content sections quote the script, assumptions log covers only
   *visual* choices (templates, colors, layout) — never content changes.
4. storyboard.md: one row per script stage, quoting its Show line.
5. Build the SceneSpec (see `spec-scenes.md`), `check-layout`, preview,
   inspect frames, render, deliver — the standard loop.
6. In the delivery report, add a **fidelity checklist**: each script stage →
   spec stage → verified frame. The user should be able to diff script vs
   video stage by stage.
