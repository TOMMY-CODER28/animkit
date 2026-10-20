# AGENTS.md — animkit animation studio

Instructions for any AI agent working in this repository. You are creating or
editing **ManimGL** animations (3b1b edition) through the **animkit** CLI.
Never call `manimgl` directly and never install another Manim flavor.

## Full documentation

- Operating manual (workflow, rules, command reference): `skill/SKILL.md`
- Deep references, load as needed: `skill/references/` —
  `spec-scenes.md` (preferred authoring style) · `manimgl-style.md` (build-specific
  API gotchas) · `quality.md` (approval checklist) · `inspection.md` (frame
  verification incl. pixel checks) · `briefs.md` · `recipes.md` ·
  `troubleshooting.md` · `delivery.md`

## The 30-second version

```bat
cd /d <animkit>
animkit.cmd check                              :: environment (add --smoke once)
animkit.cmd new my-animation --dir examples    :: scaffold a project
:: edit examples\my-animation\scene.py (+ brief.md)
animkit.cmd check-layout examples\my-animation :: dry-run a spec scene (no GPU)
animkit.cmd validate examples\my-animation --deep
animkit.cmd preview  examples\my-animation     :: 854x480 @15
animkit.cmd frames   examples\my-animation     :: inspection PNGs + contact sheet
animkit.cmd render   examples\my-animation     :: 1920x1080 @60
animkit.cmd deliver  examples\my-animation     :: packaged video+src+REPRODUCE.md
```

Add `--json` before any subcommand for machine-readable results (ok, status,
outputs, errors, error_excerpt, next_actions). Exit codes: 0 ok · 1 failure ·
2 config error · 3 timeout. Run logs land in `<project>\runs\<id>\log.txt`.

## Non-negotiable rules

1. **Workflow order**: brief → storyboard → implement → validate → preview →
   inspect frames → revise (max 3 cycles) → render → deliver. A successful
   render is not a finished animation — inspect extracted frames before
   declaring done, and state what you inspected.
2. **Prefer spec-driven scenes** (`skill/references/spec-scenes.md`): declare a
   `SceneSpec` (stages, components, lifecycle, relationships), dry-run with
   `check-layout`, let `animkit.layout` solve coordinates. Hand-positioning is
   the fallback, not the default.
3. **Script-first content**: if the user supplies a script (`script.md` or any
   written narration), it is the source of truth — animate it faithfully, no
   added/dropped/reordered ideas; compute its math and flag contradictions.
   If the request is too thin to pin down content, DRAFT a script for approval
   first (mark every inferred choice) before writing scene code.
   See `skill/references/scripts.md`.
4. **This build's API traps** (ManimGL 1.7.2-dev, LaTeX absent):
   `ShowCreation` not `Create` · `mob.animate.method()` not `play(mob.method, x)` ·
   pass `stroke_color=`/`fill_color=` explicitly (`color=` is overridden by
   shape defaults) · no `Tex`/`MathTex`/`get_axis_labels()` — use `Text` with
   Unicode math · `Axes` has `.get_height()` not `.height`.
5. **Every number shown on screen is computed in the scene file** (numpy, with
   `assert`s) — never hand-typed results.
6. Paths contain no spaces in this repo, but quote them anyway; the launchers
   (`animkit.cmd` / `animkit.sh`) route through the ManimGL venv at
   `<manim-venv>` — do not pip-install into it without need.

## Machine facts (reference machine, verified 2026-10-17)

On any other machine, run `animkit check` — it discovers the real paths at runtime. Point it at a non-standard layout with the `ANIMKIT_ROOT` / `ANIMKIT_PYTHON` / `ANIMKIT_MANIMGL` env vars.

ManimGL v1.7.2-163-gfafa083a (wgpu GPU renderer, headless via `-w`) · Python
3.10.9 venv at `<manim-venv>` · ffmpeg via `imageio-ffmpeg`
inside that venv · no LaTeX (MiKTeX not installed) · fonts: Segoe UI, Cambria
Math. Re-verify with `animkit.cmd check` if anything seems off.
