"""`animkit deliver` — package video + editable source + reproduction steps.

Pipeline position: DELIVERY. Produces deliverables/<name>/ with everything a
person (or a future agent session) needs to re-create or modify the animation.
"""

from __future__ import annotations

import datetime
import json
import shutil
from pathlib import Path

from animkit import env
from animkit.config import load_project
from animkit.runs import read_index


def _find_final_video(project, run_id: str | None) -> tuple[Path | None, dict | None]:
    index = read_index(project.root)
    entries = index.get("runs", [])
    if run_id and run_id != "latest":
        entry = next((e for e in entries if e["id"] == run_id), None)
        candidates = [entry] if entry else []
    else:
        candidates = [e for e in reversed(entries) if e.get("command") == "final" and e.get("video")]
        if not candidates:
            candidates = [e for e in reversed(entries) if e.get("video")]
    for entry in candidates:
        video = entry.get("video")
        if video and Path(video).is_file():
            return Path(video), entry
    # last resort: newest mp4 on disk
    if project.video_dir.is_dir():
        mp4s = sorted(project.video_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        if mp4s:
            return mp4s[0], None
    return None, None


def run(args) -> tuple[int, dict]:
    project, errors = load_project(args.project)
    if project is None:
        return 2, {
            "ok": False, "status": "config_error", "command": "deliver",
            "errors": errors, "next_actions": ["Fix project.json first"],
        }

    video, run_entry = _find_final_video(project, getattr(args, "run", "latest"))
    if not video:
        return 1, {
            "ok": False, "status": "failure", "command": "deliver", "project": project.name,
            "errors": ["no rendered video found"],
            "next_actions": [f"Run `animkit render {project.root}` first"],
        }

    dest = Path(args.dest).resolve() if getattr(args, "dest", None) else project.root / "deliverables" / project.name
    src = dest / "src"
    frames_dir = dest / "frames"
    src.mkdir(parents=True, exist_ok=True)
    frames_dir.mkdir(parents=True, exist_ok=True)

    video_dest = dest / "video"
    video_dest.mkdir(parents=True, exist_ok=True)
    shutil.copy2(video, video_dest / (project.name + ".mp4"))
    for f in ("scene.py", "theme.py", "project.json", "brief.md", "storyboard.md"):
        p = project.root / f
        if p.is_file():
            shutil.copy2(p, src / f)
    # latest inspection frames, if any
    for png in sorted((project.root / "runs").glob("*/frames/*.png"))[-6:] if (project.root / "runs").is_dir() else []:
        shutil.copy2(png, frames_dir / png.name)

    manimgl, gl_source = env.find_manimgl(project.manimgl_setting())
    snapshot = env.env_snapshot(manimgl, gl_source)
    from animkit.env import animkit_root
    launcher = animkit_root() / "animkit.cmd"
    reproduce = (
        f"# Reproducing \"{project.name}\"\n\n"
        f"Packaged: {datetime.datetime.now().isoformat(timespec='seconds')}\n\n"
        f"## Environment\n"
        f"- ManimGL {snapshot['manimgl_version']} at `{snapshot['manimgl_path']}`\n"
        f"- Python {snapshot['python']} (`{snapshot['python_exe']}`)\n"
        f"- ffmpeg: `{snapshot['ffmpeg_path']}` ({snapshot['ffmpeg_source']})\n"
        f"- animkit {snapshot['animkit_version']}\n"
        f"- No LaTeX required by this animation\n\n"
        f"## Commands (Windows, any shell; quotes needed if paths contain spaces)\n\n"
        f"```\n"
        f"cd \"{project.root}\"\n"
        f"\"{launcher}\" validate .\n"
        f"\"{launcher}\" render .\n"
        f"```\n\n"
        f"## Source hashes at delivery\n"
        + "\n".join(f"- {k}: {v}" for k, v in project.hashes().items()) + "\n"
    )
    (dest / "REPRODUCE.md").write_text(reproduce, encoding="utf-8")

    files = sorted(str(p.relative_to(dest)) for p in dest.rglob("*") if p.is_file())
    result = {
        "ok": True, "status": "success", "command": "deliver", "project": project.name,
        "outputs": {
            "deliverable_dir": str(dest),
            "video": str(dest / "video" / (project.name + ".mp4")),
            "reproduce": str(dest / "REPRODUCE.md"),
        },
        "details": {"files": files, "source_video": str(video), "source_run": run_entry["id"] if run_entry else None},
        "next_actions": [f"Hand over the folder: {dest}"],
    }
    return 0, result
