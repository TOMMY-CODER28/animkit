# CLAUDE.md

See [AGENTS.md](AGENTS.md) — it is the operating manual for this repository
and applies to you unchanged.

Priority notes for Claude:

- The AI-facing skill for animation work lives at `skill/SKILL.md` with deep
  references in `skill/references/`. Read `spec-scenes.md` before writing any
  new scene; read `manimgl-style.md` before using any ManimGL API you have not
  used in this repo.
- Frame inspection is part of "done": extract frames (`animkit.cmd frames`),
  actually read the PNGs, and run the objective pixel checks from
  `references/inspection.md` when vision is unavailable.
- Never modify `<manim>` (the ManimGL checkout) — animkit
  only calls its venv's `manimgl.exe`.
