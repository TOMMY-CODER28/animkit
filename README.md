# animkit — spec-driven animation studio for ManimGL

Turn animation requests into finished 3b1b-style videos, with AI doing the
authoring and a deterministic engine doing the layout, validation, rendering
and packaging. One repo, one CLI, one skill — usable by humans, coding agents
(Claude Code / Codex / Cursor / Gemini CLI), and chat models (ChatGPT /
Claude.ai).

```
request ─→ script ─→ brief/storyboard ─→ SceneSpec ─→ layout solver
        ─→ geometry gate ─→ preview ─→ frame inspection ─→ revision (≤3)
        ─→ final render ─→ packaged delivery (video + src + REPRODUCE.md)
```

This README is written as a step-by-step specification. Follow the steps in
order; every step states an action, the command to run, and the check that
tells you it worked.

---

## PART A — what the system is

Read this part once; it explains every later step.

**A1. Two-layer design.** `animkit` (this repo) is a pure-Python harness
around [3b1b/manim](https://github.com/3b1b/manim) (ManimGL, the engine behind
the actual 3Blue1Brown videos). animkit never contains ManimGL — it discovers
an existing installation at runtime and drives it headlessly.

**A2. The CLI** (`animkit.cmd` on Windows, `animkit.sh` elsewhere, or the
`animkit` console script once installed):

| command | purpose |
|---|---|
| `check` | environment audit: python, manimgl, ffmpeg, fonts, TeX (add `--smoke` for a 1 s test render) |
| `check-layout` | dry-run a spec-driven scene: validate + solve + geometry-check, no GPU |
| `new` | scaffold a project (scene.py, theme.py, brief/storyboard/script templates, project.json) |
| `validate` | config + scene/class match + optional `--deep` import check |
| `preview` | fast 854×480 @ 15 fps render |
| `frames` | extract inspection PNGs (`--at 0.1,0.5,…` fractions or `--count N`) |
| `render` | final 1920×1080 @ 60 fps |
| `report` | runs, outputs, current state, next actions |
| `deliver` | package video + source + frames + REPRODUCE.md |
| `audio` | generate stage narration WAVs (Kokoro TTS) + duration manifest |

Every command accepts `--json` (before the subcommand) and returns
`{ok, status, outputs, errors, error_excerpt, next_actions}`. Exit codes:
`0` ok · `1` failure · `2` config error · `3` timeout. Full logs land in
`<project>/runs/<id>/log.txt` and are never deleted — they are the revision
history.

**A3. The spec-driven layout engine** (`animkit/layout/`). Instead of
hand-placing objects, a scene declares a `SceneSpec`: components (matrices,
equations, text, highlights, navigation) with lifecycle per stage, plus
relationships ("three aligned columns", "result below operands"). The engine
then:

1. builds and measures every component (real rendered dimensions),
2. solves positions with direct arithmetic or kiwisolver (coupled linear
   constraints: equal centre spacing, shared centrelines, minimum gaps,
   region containment),
3. validates geometry (containment, unintended overlap, alignment tolerance,
   readability floors, label attachment) — **infeasible or violating layouts
   abort loudly with numbers, never silently overlap**,
4. animates the lifecycle (entering / leaving / changing / persistent /
   temporary; unmentioned components leave implicitly; owned labels and
   highlights ride their owners),
5. writes `layout_report.json`, `stage_times.json`, `contact_sheet.png`.

**A4. Regions.** The frame is divided into bands — title / nav / main /
annotation / caption — with margins; unused bands collapse back into `main`.
Eight templates cover common compositions (`single_center`, `two_columns`,
`three_columns`, `input_op_output`, `operands_result`, `main_callout`,
`equation_explanation`, plus a `custom` escape hatch that still passes
validation).

**A5. Validation layers.** Geometry checks run before rendering (cheap gate).
Rendered checks run after preview: boundary-frame extraction, contact sheet,
pixel heuristics (edge clipping, contrast, clutter). Path-collision
estimation warns when a moving component sweeps through another mid-transition.

**A6. Equations.** Unicode math via Pango (default, zero dependencies) or
real LaTeX, opt-in, per equation: `"mode": "tex"`. The build's TeX traps
(per-part colouring cache bug, unmatched `\left/\right` masquerading as a
stale DVI, poisoned tex cache) are handled inside the component library and
documented in `skill/references/manimgl-style.md`.

**A7. The skill + cross-agent docs.** `skill/SKILL.md` (indexed references)
is the operating manual for file-capable agents. `AGENTS.md` (auto-read by
Codex CLI, Cursor, Windsurf, Gemini CLI) and `CLAUDE.md` (Claude Code) sit at
the repo root. `docs/animkit-portable-guide.md` is a single self-contained
file for chat-only models, defining a chat-mode contract (the model authors;
you render). A script-first workflow makes *your* script the source of truth,
and thin requests get a drafted script for approval before any code.

**A8. Narration (TTS).** Stages can declare spoken narration
(`narration=` on a StageSpec — the script-first `Say:` lines). The Kokoro
provider (hexgrad/Kokoro-82M, English `a` / British `b`, configurable voice
and speed) loads the pipeline once per process, synthesizes chunks in order
(never overwriting earlier chunk files), combines them into one WAV per
stage, measures duration, and caches by content hash. `animkit audio`
generates everything up front; preview/render extend each stage's hold to fit
its measured narration (+0.35 s pad), so the video never outpaces the speech.
Enable per project (`"audio": {"enabled": true}` in project.json) or per spec
(`spec.audio = {...}`).

**A9. Examples** (all committed with sources and deliverable videos):
`equal-area-shapes` (labels/timing), `linear-transform-2d` (verified matrix
landings), `signal-pipeline` (real numpy FFT), `transformer-attention` v1 vs
`transformer-attention-v2` (the spec rewrite that fixed five real alignment /
lifecycle defects), `transformer-architecture` (full block math),
`gaussian-sum` (script-first demo), `tex-demo` (opt-in LaTeX), `layout-demo`
(minimal engine slice).

---

## PART B — setup specification

Prerequisites: Python ≥ 3.10, a GPU with wgpu support (any modern one), git.
Windows steps shown; Linux/macOS equivalents in parentheses. No admin rights
required anywhere.

**B1. Choose a parent directory** to hold two sibling checkouts: `animkit`
(this repo) and `manim`. The sibling layout lets every launcher and scene
find the venv with zero configuration.

**B2. Clone animkit.**

```bat
git clone https://github.com/TOMMY-CODER28/animkit.git
cd animkit
```
*Check:* `dir AGENTS.md` finds the file.

**B3. Clone ManimGL next to it.**

```bat
git clone https://github.com/3b1b/manim.git ..\manim
```
*Check:* `..\manim\manimlib` exists.

**B4. Create the shared venv.**

```bat
python -m venv ..\manim\.venv
```
*Check:* `..\manim\.venv\Scripts\python.exe --version` prints 3.10 or newer.
(Linux/macOS: `python3 -m venv ../manim/.venv`.)

**B5. Install ManimGL into the venv.**

```bat
..\manim\.venv\Scripts\pip install -e ..\manim
```
*Check:* finishes without compiler errors. On Linux/macOS a C toolchain and
pango headers are needed first (`sudo apt install build-essential
libpango1.0-dev` / `brew install pango`); on Windows prebuilt wheels make
this step quiet.

**B6. Install the video stack into the same venv.**

```bat
..\manim\.venv\Scripts\pip install av imageio-ffmpeg
```
*Check:* `..\manim\.venv\Scripts\pip show av imageio-ffmpeg` lists both.
`imageio-ffmpeg` bundles the ffmpeg binary — no system ffmpeg needed.

**B7. Install animkit into the same venv.**

```bat
..\manim\.venv\Scripts\pip install -e .
```
*Check:* `..\manim\.venv\Scripts\animkit --version` prints a version.

**B8. (Optional) LaTeX.** Only needed if scenes will use `"mode": "tex"`
equations; Unicode-math scenes never touch it.

```bat
winget install MiKTeX.MiKTeX -e --silent
```
Then open MiKTeX Console → Settings → enable *install missing packages
on-the-fly*. *Check (new shell):* `animkit check` reports LaTeX available.
(Linux: `sudo apt install texlive-latex-extra texlive-fonts-recommended`.)

**B9. Run the environment audit.**

```bat
animkit check
```
*Check:* exits `[ok] success`. Every blocker listed comes with its fix.

**B10. Prove the full render chain.**

```bat
animkit check --smoke
```
*Check:* `[ok]` — this compiled a scene through GPU → ffmpeg → mp4. If it
passes, everything above it works.

**B11. Install the enforcement hooks** (failed required checks then block
commit/push mechanically):

```bat
git config core.hooksPath hooks
```
*Check:* `python tools\check.py --fast` passes, and `git commit` with a
broken test is rejected.

**B12. (Optional) Narration / TTS.** Requires the audio extra plus eSpeak NG
(English G2P fallback; first generation downloads the Kokoro-82M model,
~330 MB, from Hugging Face):

```bat
..\manim\.venv\Scripts\pip install -e .[audio]
winget install eSpeak-NG.eSpeak-NG
```
*Check:* `python -c "import kokoro, soundfile"` inside the venv prints
nothing, and `espeak-ng --version` resolves on PATH (new shell).

**B13. (Optional) Run the test suites.**

```bat
..\manim\.venv\Scripts\python tests\test_cli.py
..\manim\.venv\Scripts\python tests\test_layout.py
..\manim\.venv\Scripts\python tests\test_tex.py
..\manim\.venv\Scripts\python tests\test_no_local_paths.py
```
*Check:* all print OK / pass (TeX tests skip cleanly when no TeX is installed).

Setup is complete. Non-sibling layouts work too — set `ANIMKIT_PYTHON` to
the venv python, or `ANIMKIT_MANIMGL` to a manimgl.exe, or put an absolute
path in `animkit_config.json`; `animkit check` reports what it found.

---

## PART C — first animation, step by step

**C1. Scaffold.**

```bat
animkit new my-first --dir examples
```

**C2.** Open `examples\my-first\scene.py`. It is a complete spec-driven scene
(an identity matrix over two stages). Replace its components/stages with your
content: declare components (id, ctype, content), then stages (template,
lifecycle map, transitions, captions). Keep the class name equal to
`project.json`'s `"scene"`.

**C3. Dry-run the layout** (seconds, no GPU).

```bat
animkit check-layout examples\my-first
```
*Check:* `[ok]`. Infeasible layouts return exact numbers and causes —
shrink `entry_size`, drop the stage `caption`, split the stage, or set
`density: "compact"` as the message suggests.

**C4. Preview.**

```bat
animkit preview examples\my-first
```
*Check:* `[ok]` and an mp4 under `examples\my-first\media\`.

**C5. Inspect.**

```bat
animkit frames examples\my-first --at 0.3,0.7
```
Read the extracted PNGs. Check typography, alignment, labels, math.
Reports (`layout_report.json`, `stage_times.json`) sit in `media\`.

**C6. Revise** scene.py → repeat C3–C5. Bounded: stop after 3 cycles;
deliver the best state with honest notes.

**C7. (Optional) Narrate + render.** With narration declared on stages
(`narration=`) and audio enabled, generate speech before rendering:

```bat
animkit audio examples\my-first [--voice af_heart --speed 1.0]
animkit render  examples\my-first
```
`render` re-generates missing WAVs automatically when
`project.json` has `"audio": {"enabled": true}`; stage holds extend to fit
the measured narration. WAVs + manifest ship in the deliverable.

**C8. Final render + package.**

```bat
animkit render  examples\my-first
animkit deliver examples\my-first
```
*Check:* `examples\my-first\deliverables\my-first\` contains
`video\my-first.mp4`, `src\`, `frames\`, `REPRODUCE.md`.

---

## PART D — script-first workflow (you write, it animates)

**D1.** Write `script.md` in the project (template scaffolded by `animkit new`):
one `## Stage N — name` per stage, each with `Show:` (on-screen content,
verbatim), `Say:` (narration; short lines become captions), `Math:` (values
to compute). Pacing hints like `(hold 2s)` are honored.

**D2.** Tell your agent: *"Animate script.md faithfully — follow the
script-first rules."* The contract (`skill/references/scripts.md`): your
script is the source of truth; no added/dropped/reordered ideas; every number
computed with numpy and asserted; math contradictions stop the work and are
reported; delivery includes a stage-by-stage fidelity checklist.

**D3.** Request too thin? The agent drafts `script.md` for your approval
first — every inferred choice marked `[assumed: …]` — and writes no scene
code until you approve.

---

## PART E — connecting AI agents

**E1. Coding agents** (Claude Code, Codex CLI, Cursor, Windsurf, Gemini CLI):
work inside this repo; `AGENTS.md` / `CLAUDE.md` are auto-read. From another
folder, add one line to that project's instructions: *"Animation work: clone
https://github.com/TOMMY-CODER28/animkit and follow its AGENTS.md."*

**E2. Claude skill folders**: copy `skill/SKILL.md` + `skill/references/`
into a skill directory as `manim-animation-studio`.

**E3. Chat-only models**: paste `docs/animkit-portable-guide.md` (or its raw
GitHub URL) into Custom GPT instructions / a Claude Project. The model authors
`brief.md` + `storyboard.md` + a complete `scene.py`; you save them into
`examples\<name>\` and run C3–C7; paste errors back for it to fix.

**E4. Other tools / repos**: `pip install
git+https://github.com/TOMMY-CODER28/animkit.git` inside their ManimGL venv
exposes the `animkit` CLI and the `animkit.layout` Python API.

---

## PART F — verification model

**F0. Check enforcement.** Required checks run ONLY through
`python tools/check.py` (complete logs under `logs/`, real exit codes,
one-line summaries). Hooks make this mechanical: pre-commit runs the fast
set, pre-push the full set — a failed check blocks commit/push until it
passes. Production discipline (engine/animation separation, timing
semantics, visual/audio gates, evidence reporting) lives in
`skill/references/workflow.md`.

**F1.** 54 automated checks: CLI behaviour (config errors, render failures,
timeouts, packaging), layout engine (bracket orientation, centre spacing vs
gaps, determinism, stability of unchanged components, infeasible diagnostics,
lifecycle cleanup, implicit leaving, spec validation, region collapse,
custom-layout validation), conditional TeX health, and a no-local-paths
guard that keeps the repo machine-neutral.

**F2.** Per-animation verification is part of "done": dry-run geometry,
boundary-frame extraction, contact sheet, and honest reporting of what was
inspected versus what was not. A successful render alone is never "finished".

---

## PART G — troubleshooting, by symptom

**G1. `manimgl not found`** → venv not where the launcher looks. Set
`ANIMKIT_PYTHON`, or use the sibling layout of B1.

**G2. `No module named 'av'`** → repeat B6.

**G3. Render fails, log shows ffmpeg missing** → repeat B6
(`imageio-ffmpeg` provides the binary).

**G4. `Create is not defined` / `cannot be converted to an animation`** →
ManimCE-isms; use `ShowCreation` and `mob.animate.method(...)` — see
`skill/references/manimgl-style.md`.

**G5. Shape renders red despite `color=`** → pass `stroke_color=` /
`fill_color=` explicitly (build-specific default override).

**G6. TeX equations render as the wrong formula / garbled** → clear
ManimGL's tex disk cache (`%LOCALAPPDATA%\manim\manim\Cache`) and re-render;
never split `\left…\right` across equation parts.

**G7. `check-layout` reports widths exceed region** → shrink content, drop
the stage caption, split the stage, or `density: "compact"`.

**G8. Late video stages look missing in extracted frames** → fixed in
`extract_frames` (pts normalisation); if it recurs, sample by ink density.

**G9. TTS: words mispronounced / phonemizer errors** → install eSpeak NG
(`winget install eSpeak-NG.eSpeak-NG`) and open a new shell — Kokoro's English
G2P falls back to it. First generation also downloads the Kokoro-82M model;
offline machines cannot generate.

**G10. `audio` reports provider unavailable** → the audio extra is missing
from the venv: `pip install -e .[audio]` (pulls `kokoro` + `soundfile`;
torch is CPU by default).

---

## PART H — documentation map

| path | what |
|---|---|
| `skill/SKILL.md` | operating manual for AI agents (indexed references) |
| `skill/references/spec-scenes.md` | spec-driven authoring: templates, lifecycle, rules |
| `skill/references/scripts.md` | script-first contract + drafting rules |
| `skill/references/manimgl-style.md` | this build's verified API, incl. TeX traps |
| `skill/references/quality.md` · `inspection.md` | approval checklist · frame verification |
| `skill/references/briefs.md` · `recipes.md` · `troubleshooting.md` · `delivery.md` | briefs · building blocks · error tables · packaging |
| `AGENTS.md` · `CLAUDE.md` | agent entry points (auto-read) |
| `docs/animkit-portable-guide.md` | self-contained guide for chat models |

## PART I — honest limitations

2D screen composition only (3D rendering works, automatic layout does not
reason about depth). Frame inspection samples; it does not prove every frame.
No voiceover/subtitles yet (script `Say:` lines are captured for a future
voiceover). Graphviz/Penrose layout backends and an MCP wrapper are deferred
(the solver interface is ready for them). Example videos were rendered with
Windows fonts — non-Windows re-renders substitute glyphs unless
`TEXT_FONT`/`MATH_FONT` in `animkit/layout/components.py` are changed.
