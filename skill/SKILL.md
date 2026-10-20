---
name: manim-animation-studio
description: >-
  Create, revise, inspect, and deliver mathematical/explanatory animations with
  ManimGL on this machine, through the animkit utility (brief → storyboard →
  scene code → preview → frame inspection → final render → packaged delivery).
  Use when the user asks for an animation, a manim video, a visual explanation
  of math/engineering concepts, or edits to an existing animation project.
---

# Manim Animation Studio (animkit)

You are creating an animation with **ManimGL 1.7.2 (3b1b edition)** on Windows,
driven by the **animkit** CLI at `<animkit>`. Never install
another Manim flavor. Never render by calling `manimgl` directly — always go
through animkit (it sets headless mode, ffmpeg, output dirs, timeouts, and
keeps run records).

## Capabilities you must have

- Execute shell commands (`animkit.cmd ...` or `bash animkit.sh ...`)
- Read/write local files (project dir: scene.py, theme.py, brief.md)
- Read PNG images (frame inspection) — if you cannot, follow the objective
  pixel-check fallback in `references/inspection.md`

## The workflow (always in this order)

1. **Discover** — `animkit.cmd check` (add `--smoke` once per session at most).
   If blockers appear, fix them per `references/troubleshooting.md` before anything.
2. **Brief** — turn the request into `brief.md` inside the project:
   audience, ideas in order, the math/technical facts *with their source*,
   assumptions log, success criteria. Rules for vague requests:
   `references/briefs.md`.
   **Script-first**: if the user supplies a script, it is the source of
   truth — animate it faithfully (`references/scripts.md`). If the request
   is too thin to pin down content, draft `script.md` for approval FIRST
   (mark every inferred choice), and only write scene code after approval.
3. **Storyboard** — `storyboard.md`: shot table (t, visual, motion, text),
   transitions, planned inspection frames.
4. **Implement** — `animkit.cmd new <name> --dir <parent>` creates the project.
   **Prefer a spec-driven scene** (`references/spec-scenes.md`): declare a
   `SceneSpec` and let `animkit.layout` solve coordinates, manage the object
   lifecycle, and validate geometry — this is how the known alignment/lifecycle
   defects are prevented structurally. For hand-positioned scenes follow
   `references/manimgl-style.md` (it lists the API differences that *will*
   bite on this build: no `Create`, no `.animate`-less method animations,
   `Circle` pins red stroke, no LaTeX on this machine).
5. **Validate** — spec scenes: `animkit.cmd check-layout <project>` (fast
   dry-run). All scenes: `animkit.cmd validate <project> --deep`.
6. **Preview** — `animkit.cmd preview <project>` (fast 480p15).
7. **Inspect** — `animkit.cmd frames <project>` then Read the PNGs (and/or run
   the objective checks in `references/inspection.md`). Use the checklist in
   `references/quality.md`. Math claims: verify positions/values against the
   grid/axes numerically when possible.
8. **Revise** (bounded): fix scene.py → re-preview → re-inspect. **Stop after
   3 revision cycles**; if still failing, deliver the best state with an honest
   note of what's wrong. Success = all success criteria in brief.md pass.
9. **Final** — `animkit.cmd render <project>` (1080p60).
10. **Deliver** — `animkit.cmd deliver <project>`; report the packaged folder,
    the video path, what you inspected, and any unverified aspects.

## Commands (Windows, from anywhere; paths with spaces need quotes)

```
animkit.cmd check [--smoke]
animkit.cmd new <name> --dir <parent-dir>
animkit.cmd validate <project-dir> [--deep]
animkit.cmd preview <project-dir> [--scene SceneName]
animkit.cmd frames <project-dir> [--count N | --at 0.1,0.5,0.9] [--video path]
animkit.cmd render <project-dir>
animkit.cmd report <project-dir>
animkit.cmd deliver <project-dir> [--dest dir]
```
Add `--json` before the subcommand for machine-readable output (status,
outputs, errors, error_excerpt, next_actions). Exit codes: 0 ok, 1 failure,
2 config error, 3 timeout. Every run's full log: `<project>/runs/<id>/log.txt`.

## Hard rules

- **Equations**: Unicode `Text` via the theme's `text()` / `math_text()` is the
  default. Real LaTeX is available opt-in: equation components with
  `content: {"mode": "tex"}` compile through MiKTeX (animkit puts it on PATH).
  Never mix `\left`/`ight` across parts (see references/manimgl-style.md).
- **Colors**: pass `stroke_color=`/`fill_color=` explicitly (or use `.set_stroke()/
  .set_fill()`); generic `color=` is overridden by shape defaults on this build.
- **Theme**: import from `theme.py` (`from theme import *`) — palette, type scale,
  pacing constants, label helpers, `matrix_label`, `in_safe_area`. Do not invent
  ad-hoc colors/sizes in scene code.
- **Values**: compute math in the scene file from first principles (numpy), never
  hand-place results; `assert` expected relations at import time.
- **Time**: scenes 10–40 s; one idea per shot; `IDEA_PAUSE` between ideas; motion
  is explanation, not decoration.
- **Records**: never delete `runs/`; they are the revision history.
- Report honestly: state what you actually inspected (which frames, which checks)
  and what you could not.

## Reference index (load only what the task needs)

| File | Read when |
|------|-----------|
| `references/briefs.md` | turning a vague request into a brief; when to ask vs assume |
| `references/scripts.md` | the user wrote (or wants) a **script** — animate it faithfully, or draft one for approval when the request is too thin |
| `references/spec-scenes.md` | **preferred**: spec-driven scenes — declare content + relationships, get solved, validated layouts (`animkit check-layout` dry-runs them) |
| `references/manimgl-style.md` | hand-written scene code; **API differences of this build**; verified snippets |
| `references/quality.md` | before approving preview frames (checklist + anti-patterns) |
| `references/inspection.md` | how to inspect frames (vision + objective pixel checks) |
| `references/recipes.md` | common building blocks: labelled diagrams, graphs, transforms, pipelines |
| `references/troubleshooting.md` | render failures, environment problems, error → fix table |
| `references/delivery.md` | packaging, modifying existing animations, connecting other agents |

Environment facts (reference machine, verified 2026-10-21): ManimGL v1.7.2 at
`<manim-venv>` (Python 3.10.9, wgpu GPU renderer, headless via
`-w`); ffmpeg from `imageio-ffmpeg` inside that venv; MiKTeX user-install for LaTeX
(discovered automatically; `ANIMKIT_TEX` overrides); fonts: Segoe UI /
Cambria Math available. Re-verify with `animkit.cmd check` if things moved.
