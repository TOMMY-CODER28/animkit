# Delivery, revision, and connecting other agents

## What `animkit deliver` packages

```
deliverables/<name>/
  video/<name>.mp4          final render
  src/{scene.py, theme.py, project.json, brief.md, storyboard.md}
  frames/                   up to 6 latest inspection PNGs
  REPRODUCE.md              environment snapshot + exact commands + source hashes
```
Report to the user: the folder path, video duration/resolution, what was
inspected and how, and any open issues. The package is self-sufficient: a
future session (or another agent) can reproduce the video from it.

## Modifying an existing animation without losing its style

1. `animkit.cmd report <project>` — confirm current state (hashes, runs).
2. Read `brief.md` (intent) and `storyboard.md` (structure) *first*; edit the
   brief if the change alters intent, not just code.
3. Change scene.py minimally; keep the theme import and pacing constants —
   consistency comes from `theme.py`, not from discipline.
4. Full loop anyway: validate → preview → frames → inspect → render → deliver.
   Re-rendering is cheap; skipping inspection is how style drifts.
5. `runs/` accumulates the history — never prune it during revision; old
   videos in `media/` are overwritten by design (the run record keeps logs).

## Connecting another AI agent

The system is provider-independent. Any agent that can (a) read/write files
and (b) run shell commands can use it. Documentation exists in three forms:

- `<animkit>\AGENTS.md` — repo-root instructions auto-read by
  Codex CLI, Cursor, Windsurf, Gemini CLI, ZCode (and mirrored by `CLAUDE.md`
  for Claude Code).
- `skill\SKILL.md` + `references\` — the deep, indexed manual for agents with
  file access (copy into a skill folder, e.g.
  `%USERPROFILE%\.claude\skills\manim-animation-studio\` for Claude Code).
- `docs\animkit-portable-guide.md` — self-contained single file for chat-only
  models (paste into Custom GPT instructions or a Claude Project; defines the
  chat-mode contract where the model authors and the user renders).

Point an agent at any of these; the first thing it should run is
`animkit.cmd check`.

Platform notes for the skill itself: it is plain Markdown + relative paths;
moving it to macOS/Linux requires only (a) `animkit.sh` instead of
`animkit.cmd`, (b) re-running `animkit check` to re-locate manimgl/ffmpeg,
(c) different font availability in `theme.py` (Segoe UI/Cambria Math are
Windows fonts; substitutes: `DejaVu Sans`, `Latin Modern Math`).

If an agent environment **cannot** access local files or run commands
(e.g. a pure chat model), this workflow does not apply as-is. The required
connector is one of:
- a harness that executes the commands and relays outputs/files (what ZCode,
  Claude Code, Cursor etc. do), or
- an MCP server exposing `check/new/validate/preview/frames/render/report/
  deliver` as tools wrapping the same CLI (the CLI result JSON is already
  MCP-tool-shaped: status, outputs, errors, next_actions). Deferred, not
  built — add only if a chat-only integration becomes real.

## Sample instruction to give an agent

> Use the manim-animation-studio skill. Create a 20-second animation that
> explains why the determinant of a 2x2 matrix equals the area scale factor:
> show the unit square, apply [[2,0],[0,1]] and then [[2,1],[0,1]], display
> the unit square's area after each, and end on det = ad − bc. Follow the
> full workflow including frame inspection, and deliver the package.
