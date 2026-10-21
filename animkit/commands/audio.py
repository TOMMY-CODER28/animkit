"""`animkit audio <project>` — generate stage narration with a TTS provider.

Reads the spec's StageSpec.narration texts, synthesizes one WAV per stage
(Kokoro provider by default), writes media/audio/audio_manifest.json with
measured durations. Preview/render read that manifest and extend stage holds
to fit — so speech is always generated BEFORE the video renders.
"""

from __future__ import annotations

from pathlib import Path

from animkit.config import load_project
from animkit.runs import Run


def _load_spec(scene_file: Path):
    import importlib.util
    import sys
    from animkit.env import animkit_root
    sys.path.insert(0, str(animkit_root()))
    spec = importlib.util.spec_from_file_location("scene_audio_check", scene_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "build_spec"):
        raise ValueError(
            "scene.py has no module-level build_spec() — narration lives on "
            "the SceneSpec stages")
    return module.build_spec()


def run(args) -> tuple[int, dict]:
    project, errors = load_project(args.project)
    if project is None:
        return 2, {"ok": False, "status": "config_error", "command": "audio",
                   "errors": errors, "next_actions": ["Fix project.json first"]}
    run_rec = Run(project.root, "audio")
    try:
        try:
            spec = _load_spec(project.scene_file)
        except Exception as exc:
            result = {"ok": False, "status": "failure", "command": "audio",
                      "project": project.name,
                      "errors": [f"could not load spec: {exc}"],
                      "next_actions": ["Ensure scene.py builds a SceneSpec"]}
            result = run_rec.write_result(result)
            return 1, result

        from animkit.audio import generate_project_audio
        overrides = {k: v for k, v in
                     (("voice", args.voice), ("speed", args.speed),
                      ("lang", args.lang)) if v is not None}
        config = {**(spec.audio or {}), **overrides}
        out_dir = Path(project.root) / "media" / "audio"
        result = generate_project_audio(
            spec, out_dir=out_dir, config=config, force=args.force,
            log=lambda m: run_rec.log_line(m))
        result.setdefault("command", "audio")
        result["project"] = project.name
        result = run_rec.write_result(result)
        return (0 if result["ok"] else 1), result
    finally:
        run_rec.close()
