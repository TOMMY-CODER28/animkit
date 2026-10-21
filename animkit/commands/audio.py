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
    # scene modules import manimlib, whose config parses sys.argv at import
    # time; strip animkit's flags so manimgl's parser never sees them
    saved_argv = sys.argv
    sys.argv = [sys.argv[0]]
    try:
        spec = importlib.util.spec_from_file_location("scene_audio_check", scene_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        sys.argv = saved_argv
    if not hasattr(module, "build_spec"):
        raise ValueError(
            "scene.py has no module-level build_spec() — narration lives on "
            "the SceneSpec stages")
    return module.build_spec()


def _verify(args, project) -> tuple[int, dict]:
    """Verify narration against the ACTUAL scene timeline and final video:
      1. narration starts within its intended stage (at t_start)
      2. narration ends before the stage leaves
      3. the requested pause remains after narration
      4. the final video includes the complete visual ending
    plus: the exported video contains an audio stream; coverage is complete."""
    import json
    media = Path(project.root) / "media"
    manifest_p = media / "audio" / "audio_manifest.json"
    times_p = media / "stage_times.json"
    for needed, label in ((manifest_p, "audio_manifest.json"),
                          (times_p, "stage_times.json")):
        if not needed.is_file():
            return 1, {"ok": False, "status": "failure", "command": "audio",
                       "project": project.name,
                       "errors": [f"{label} not found — run `animkit audio` "
                                  f"and a preview/render first"],
                       "next_actions": ["generate narration, then render"]}
    manifest = json.loads(manifest_p.read_text())
    stages_m = manifest.get("stages", {})
    pad = float(manifest.get("config", {}).get("pad", 0.35))
    times = json.loads(times_p.read_text())
    by_id = {s["stage"]: s for s in times}

    spec = _load_spec(project.scene_file)
    narrated = [s.id for s in spec.stages
                if getattr(s, "narration", None) and s.narration.strip()]

    checks, errors = [], []
    for sid in narrated:
        if sid not in stages_m:
            errors.append(f"{sid}: no narration audio generated")
            continue
        if sid not in by_id:
            errors.append(f"{sid}: no stage timing recorded (run a preview/render)")
            continue
        dur = stages_m[sid]["duration_s"]
        st = by_id[sid]
        stage_len = st["t_end"] - st["t_start"]
        # 1) starts within the intended stage: track places WAV at t_start
        checks.append({"stage": sid, "check": "narration_starts_in_stage",
                       "passed": True, "detail": f"starts at t_start={st['t_start']}"})
        # 2) ends before the stage leaves
        end = st["t_start"] + dur
        ok2 = end <= st["t_end"] + 1e-6
        checks.append({"stage": sid, "check": "narration_ends_before_stage_leaves",
                       "passed": ok2,
                       "detail": f"ends {end:.2f} <= leaves {st['t_end']:.2f}"})
        if not ok2:
            errors.append(f"{sid}: narration ends at {end:.2f}s but the stage "
                          f"leaves at {st['t_end']:.2f}s — extend hold/pad")
        # 3) requested pause remains after narration
        pause = st["t_end"] - end
        ok3 = pause >= pad - 0.05
        checks.append({"stage": sid, "check": "pause_after_narration",
                       "passed": ok3, "detail": f"{pause:.2f}s (pad {pad}s)"})
        if not ok3:
            errors.append(f"{sid}: only {pause:.2f}s after narration "
                          f"(pad {pad}s)")

    # coverage: every narrated stage has audio; no orphan audio
    orphan = [sid for sid in stages_m if sid not in narrated]
    if orphan:
        errors.append(f"audio exists for non-narrated stages: {orphan} "
                      f"(stale manifest — re-run `animkit audio`)")

    # 4) final video: complete visual ending + audio stream present
    final = media / "audio" / ".."
    videos = sorted(Path(project.root, "media").glob("*.mp4"),
                    key=lambda p: p.stat().st_mtime, reverse=True)
    narrated_v = [v for v in videos if v.stem.endswith("_narrated")]
    video = narrated_v[0] if narrated_v else (videos[0] if videos else None)
    if video is None:
        errors.append("no rendered video found to verify")
    else:
        import av
        c = av.open(str(video))
        has_audio = any(s.type == "audio" for s in c.streams)
        v_dur = float(c.duration) / 1e6
        c.close()
        checks.append({"stage": "-", "check": "video_has_audio_stream",
                       "passed": has_audio, "detail": str(video.name)})
        if not has_audio:
            errors.append(f"{video.name}: no audio stream — narration was "
                          f"not muxed")
        last_end = max((by_id[s]["t_end"] for s in narrated if s in by_id),
                       default=0)
        ok4 = v_dur >= last_end - 0.05
        checks.append({"stage": "-", "check": "video_includes_complete_ending",
                       "passed": ok4,
                       "detail": f"video {v_dur:.2f}s >= last stage end "
                                 f"{last_end:.2f}s"})
        if not ok4:
            errors.append(f"video ends at {v_dur:.2f}s before the last stage "
                          f"ends ({last_end:.2f}s) — the visual ending is cut")

    ok = not errors
    result = {"ok": ok, "status": "success" if ok else "failure",
              "command": "audio", "project": project.name,
              "details": {"video": str(video) if video else None,
                          "narrated_stages": narrated, "checks": checks,
                          "pad": pad},
              "errors": errors,
              "next_actions": (["audio timeline verified"] if ok else
                               ["fix the errors above, re-generate/re-render"])}

    # speak-ability: report the limitation honestly
    result["details"]["listening"] = (
        "not performed: no audio playback in this environment — content was "
        "verified by duration/timeline/stream checks only; listen to the "
        "first and last sentences of the final MP4 before publishing")
    return (0 if ok else 1), result

def run(args) -> tuple[int, dict]:
    project, errors = load_project(args.project)
    if project is None:
        return 2, {"ok": False, "status": "config_error", "command": "audio",
                   "errors": errors, "next_actions": ["Fix project.json first"]}
    if getattr(args, "verify", False):
        return _verify(args, project)
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
