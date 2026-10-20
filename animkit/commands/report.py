"""`animkit report` — what exists, what happened, what to do next.

Pipeline position: anytime. Reads runs/index.json + current outputs.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from animkit.config import load_project
from animkit.runs import read_index


def run(args) -> tuple[int, dict]:
    project, errors = load_project(args.project)
    if project is None:
        return 2, {
            "ok": False, "status": "config_error", "command": "report",
            "errors": errors, "next_actions": ["Fix project.json first"],
        }

    index = read_index(project.root)
    videos = []
    if project.video_dir.is_dir():
        for mp4 in sorted(project.video_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime):
            stat = mp4.stat()
            videos.append({
                "path": str(mp4),
                "size_bytes": stat.st_size,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="minutes"),
            })
    frames = sorted((project.root / "runs").glob("*/frames/*.png")) if (project.root / "runs").is_dir() else []

    last_render = next((e for e in reversed(index.get("runs", [])) if e.get("command") in ("preview", "final", "render") and e.get("ok")), None)

    result = {
        "ok": True, "status": "success", "command": "report", "project": project.name,
        "details": {
            "config": project.cfg,
            "hashes": project.hashes(),
            "run_count": len(index.get("runs", [])),
            "runs": index.get("runs", [])[-10:],
            "videos": videos,
            "frame_count": len(frames),
            "latest_frames_dir": str(frames[-1].parent) if frames else None,
            "last_successful_render": last_render,
        },
        "outputs": {"videos": [v["path"] for v in videos]},
        "next_actions": (
            ["Ready to package: animkit deliver " + str(project.root)]
            if last_render else
            ["No successful render yet: animkit preview " + str(project.root)]
        ),
    }
    return 0, result
