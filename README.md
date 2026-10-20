# animkit — AI-driven animation studio for ManimGL

A reusable system for creating high-quality 3b1b-style animations with AI
agents. One utility + one skill; any agent that can read files and run
commands can drive it.

```
request → brief → storyboard → scene code → validate → preview → frame
inspection → (bounded revision) → final render → packaged delivery
```

## Install (from a clone)

Requires Python ≥ 3.10 and a GPU with wgpu support. No LaTeX needed.

```bash
git clone https://github.com/<you>/animkit.git && cd animkit
# ManimGL into its own venv (or reuse an existing one):
git clone https://github.com/3b1b/manim ../manim
python -m venv ../manim/.venv
../manim/.venv/Scripts/pip install -e ../manim av imageio-ffmpeg   # Windows
# ../manim/.venv/bin/pip install -e ../manim av imageio-ffmpeg     # Linux/macOS
# Linux/macOS additionally: apt install libpango1.0-dev (or brew install pango)

# animkit into the same venv (provides the `animkit` command):
../manim/.venv/Scripts/pip install -e .
# then verify — discovers manimgl/ffmpeg/fonts at runtime:
../manim/.venv/Scripts/animkit check --smoke
```

Or skip the venv dance: set `ANIMKIT_PYTHON` to any Python that has manimlib
and run `animkit.cmd` / `animkit.sh` directly. Fonts default to Segoe UI /
Cambria Math (Windows); on other platforms change `TEXT_FONT`/`MATH_FONT` in
`animkit/layout/components.py` (e.g. to `DejaVu Sans`).

## Layout

```
<animkit>\
  animkit.cmd / animkit.sh      launchers (manim venv python; space-safe)
  animkit\                      the utility (stdlib-only package)
    commands\                   check, check-layout, new, validate, render, frames, report, deliver
    layout\                     spec-driven layout engine (see below)
    project_template\           scene.py + theme.py + brief/storyboard templates
  skill\                        the AI skill (SKILL.md + references/)
  examples\                     five finished, verified example projects
  tests\                        test_cli.py (22) + test_layout.py (26)
  animkit_config.json           machine-local paths (manimgl exe)
```

## The layout engine (`animkit.layout`)

For animations that must be consistently readable and correctly aligned,
declare a **SceneSpec** — stages, components, lifecycle, relationships — and
let the engine solve coordinates and manage objects:

- **Content/layout separation**: you say *"Q, K, V in three aligned columns,
  labels above"*; templates + a kiwisolver-backed constraint solver place them
  (equal centre spacing, shared centrelines, min gaps, region containment).
- **Lifecycle registry**: entering/leaving/changing/persistent/temporary per
  stage; owned labels/highlights ride their owners; unmentioned components
  leave implicitly; a post-stage sweep removes anything unregistered.
- **Validation gates**: `check-layout` dry-runs a spec (no GPU); every render
  aborts loudly on infeasible layouts or geometry violations, with actionable
  diagnostics. `layout_report.json`, `stage_times.json` and
  `contact_sheet.png` land next to every preview.
- Docs: `skill/references/spec-scenes.md`. Reference examples:
  `examples/transformer-attention-v2` (spec rewrite of the v1 animation,
  regression-fixed) and `examples/layout-demo` (minimal slice).

Your ManimGL checkout at `<manim>` is untouched; animkit only
calls its `manimgl.exe` and writes into its own project folders.

## Environment (verified 2026-10-17)

- **ManimGL v1.7.2** (3b1b edition, dev checkout `v1.7.2-163-gfafa083a`),
  editable install into `<manim-venv>` (Python 3.10.9)
- **Renderer**: wgpu GPU, fully headless (`manimgl -w`) — no window opens
- **ffmpeg**: provided by `imageio-ffmpeg` inside the venv (no system install)
- **PyAV + Pillow**: installed in the venv (video probing + frame extraction)
- **No LaTeX** on this machine — animations use Pango `Text` with Unicode math
  (Cambria Math). Install MiKTeX only if you later need `Tex`.

## Quick start (Windows)

```bat
cd <animkit>
animkit.cmd check --smoke                 :: environment + 1s test render
animkit.cmd new my-first --dir examples   :: create a project
:: ...edit examples\my-first\scene.py (and brief.md)...
animkit.cmd validate examples\my-first --deep
animkit.cmd preview examples\my-first     :: 480p15 in ~seconds
animkit.cmd frames examples\my-first      :: inspection PNGs under runs\
animkit.cmd render  examples\my-first     :: 1920x1080 @ 60fps
animkit.cmd deliver examples\my-first     :: deliverables\my-first\ package
```
Git Bash: use `./animkit.sh` the same way. Add `--json` (before the
subcommand) for machine-readable results: status, outputs, errors,
error_excerpt, next_actions. Exit codes: 0 ok · 1 failure · 2 config · 3 timeout.

Every run writes `runs/<NNNN-command>/` with `log.txt`, the exact manim
config, and `result.json` — the revision history is never deleted.

## Connecting an AI agent

Four integration paths, depending on what the AI can do. The documentation
lives in three forms — pick the one that fits:

| File | For | How it's consumed |
|---|---|---|
| `skill\SKILL.md` + `skill\references\` | agents with file access (deep, indexed) | copied into a skill folder or referenced by path |
| `AGENTS.md` (repo root) | Codex CLI, Cursor, Windsurf, Gemini CLI, ZCode — auto-read at repo root | nothing to do when working inside `<animkit>` |
| `CLAUDE.md` (repo root) | Claude Code | auto-read; defers to AGENTS.md + skill |
| `docs\animkit-portable-guide.md` | ChatGPT, Claude.ai, any chat model — self-contained | paste into Custom GPT instructions / Project instructions, or attach the file |

**Script-first workflow**: you can write the script yourself (`animkit new`
scaffolds a `script.md` template) and have the AI animate it faithfully — or,
when your request is thin, have the AI draft the script for your approval
before any code. Rules: `skill\references\scripts.md`; worked example:
`examples\gaussian-sum\` (script.md + scene.py + delivered video).

### Path A — coding agents (Claude Code, Codex, Cursor, ZCode, ...)

Work inside `<animkit>` and the agent picks up `AGENTS.md` /
`CLAUDE.md` automatically. For other project folders, add one line to that
folder's instructions file:

```
Animation work: read <animkit>\AGENTS.md and follow it.
```

Claude Code users can alternatively install the skill globally: copy
`skill\SKILL.md` + `skill\references\` into `%USERPROFILE%\.claude\skills\manim-animation-studio\`.

### Path B — chat-only models (ChatGPT, Claude.ai, Gemini web)

Open `docs\animkit-portable-guide.md`, copy its full text into a Custom GPT's
Instructions or a Claude Project's custom instructions (or just paste it at
the start of a conversation). The guide defines the **chat-mode contract**:
the AI authors `brief.md`, `storyboard.md`, and a complete `scene.py`; you
save them into `examples\<name>\` and run:

```bat
cd <animkit>
animkit.cmd check-layout examples\<name>   & :: validates without rendering
animkit.cmd preview     examples\<name>
animkit.cmd render      examples\<name>
```

Paste any error text back into the chat and the model fixes the spec. The
guide forbids the model from claiming it rendered or verified anything.

### Sample instruction (any agent, any mode)

> Create a 20-second animation that explains why the determinant of a 2×2
> matrix equals the area scale factor: show the unit square, apply [[2,0],[0,1]]
> and then [[2,1],[0,1]], display the unit square's area after each, and end
> on det = ad − bc. Follow the full workflow (brief → spec → check-layout →
> preview → frame inspection → render → deliver).

## Modifying an existing animation

Open the project, read `brief.md` and `storyboard.md` first (they record
intent, not just code), change `scene.py` minimally — visual consistency comes
from the shared `theme.py`, so don't inline colors/sizes — then re-run the
full loop (`validate → preview → frames → render → deliver`). Re-rendering is
cheap; skipping inspection is how quality drifts.

## The examples

| Project | Shows | Final |
|---|---|---|
| `examples\equal-area-shapes` | positioning, timing, attached labels | 1080p60, 13.5 s |
| `examples\linear-transform-2d` | math correctness (shear M=[[1,1],[0,1]], verified landings) | 1080p60, 20.2 s |
| `examples\signal-pipeline` | coordinated stages; spectrum from a real numpy FFT | 1080p60, 24.1 s |
| `examples\transformer-attention` | v1 hand-positioned attention (kept for comparison) | 1080p60, 35.9 s |
| `examples\transformer-attention-v2` | **spec-driven rewrite**; the 5 v1 alignment/lifecycle defects regression-fixed | 1080p60, 21.9 s |
| `examples\layout-demo` | minimal layout-engine slice | 480p15 |

Each contains brief.md (request + assumptions), storyboard.md (shots + actuals),
scene.py, and `deliverables\<name>\` (video + src + frames + REPRODUCE.md).

Reproduce any of them: `cd examples\<name> && <animkit>\animkit.cmd render .`

## Troubleshooting

`animkit.cmd check` reports blockers with fixes; the skill's
`references/troubleshooting.md` maps every error seen on this setup to its
fix (missing `av`, ffmpeg, API differences like `Create`→`ShowCreation`,
`.animate` syntax, `Circle`'s red-stroke default, no-LaTeX rules).
Common quick fixes:

```bat
:: manimgl can't import (av missing):
<manim-venv>\Scripts\python.exe -m pip install av
:: render fails, no ffmpeg:
<manim-venv>\Scripts\python.exe -m pip install imageio-ffmpeg
```

## Implemented · verified · deferred

**Implemented & verified** (48 tests: 22 CLI + 26 layout, plus rendered
examples with frame inspection): the full CLI (check, check-layout, new,
validate, preview, render, frames, report, deliver); the spec-driven layout
engine (region bands with collapse policy, direct + kiwi constraint solvers,
8 templates, TextMatrix with inward brackets, owned annotations, highlights,
stage nav); lifecycle registry (implicit leaving, temp sweep, transform
re-pointing); geometry validation (containment, separation, alignment,
readability, attachment); path-collision estimation; debug overlay
(ANIMKIT_DEBUG=1); contact sheets + boundary-frame extraction.

**Verified manually**: the five attention-animation defects reproduced in v1
are fixed in v2 and confirmed frame-by-frame (title/nav separation, bracket
orientation, stale X matrix + label, row-tag placement); math consistency
asserted in-scene and spot-checked against rendered pixels; 19 boundary
frames pixel-checked with zero issues.

**Deferred by design**: Graphviz/Penrose backends (interface ready, no
concrete need yet), 3D layout (2D composition only; 3D/camera untouched),
resize-and-retry loop (try_fit exists, unused by templates yet), MCP wrapper,
voiceover/subtitles, LaTeX (still absent on this machine).
