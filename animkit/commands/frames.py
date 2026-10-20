"""`animkit frames` — extract representative frames from a rendered video.

Pipeline position: INSPECTION. The AI (or a human) reads the PNGs to judge
typography, layout, labels and pacing before a final render.

Frame extraction uses PyAV in-process (no ffprobe needed).
"""

from __future__ import annotations

from pathlib import Path

from animkit.config import load_project
from animkit.runs import Run, read_index


def _find_video(project_dir: Path, video_arg: str | None, video_dir: Path | None) -> Path | None:
    if video_arg:
        p = Path(video_arg)
        return p if p.is_file() else None
    # newest video mentioned by a successful run index entry
    index = read_index(project_dir)
    for entry in reversed(index.get("runs", [])):
        video = entry.get("video")
        if video and Path(video).is_file():
            return Path(video)
    # fallback: newest mp4 under the video dir
    if video_dir and video_dir.is_dir():
        mp4s = sorted(video_dir.rglob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True)
        return mp4s[0] if mp4s else None
    return None


def run(args) -> tuple[int, dict]:
    project, errors = load_project(args.project)
    if project is None:
        return 2, {
            "ok": False, "status": "config_error", "command": "frames",
            "errors": errors, "next_actions": ["Fix project.json first"],
        }

    video = _find_video(project.root, getattr(args, "video", None), project.video_dir)
    if not video:
        return 1, {
            "ok": False, "status": "failure", "command": "frames", "project": project.name,
            "errors": ["no rendered video found for this project"],
            "next_actions": [f"Run `animkit preview {project.root}` first"],
        }

    run = Run(project.root, "frames")
    try:
        try:
            import av
        except ImportError:
            result = {
                "ok": False, "status": "failure", "command": "frames",
                "errors": ["PyAV (av) not importable — run animkit with the manim venv python"],
                "next_actions": ["Re-run using the wrapper animkit.cmd or the venv python"],
            }
            result = run.write_result(result)
            run.update_index(result)
            return 1, result

        run.log_line(f"[animkit] probing {video}")
        container = av.open(str(video))
        stream = container.streams.video[0]
        duration = float(container.duration) / 1e6
        meta = {
            "video": str(video),
            "width": stream.codec_context.width,
            "height": stream.codec_context.height,
            "duration_s": round(duration, 2),
            "fps": round(float(stream.average_rate), 2),
        }

        if getattr(args, "at", None):
            fractions = [float(x) for x in args.at.split(",")]
        else:
            n = max(2, int(getattr(args, "count", 6)))
            fractions = [0.05 + 0.9 * i / (n - 1) for i in range(n)]
        targets = [min(max(f, 0.0), 1.0) * duration for f in fractions]

        out_dir = run.dir / "frames"
        out_dir.mkdir(parents=True, exist_ok=True)
        frames_out: list[dict] = []
        targets_iter = iter(list(enumerate(targets)))
        pending = dict(targets_iter)
        saved = {}
        run.log_line(f"[animkit] extracting frames at t={[round(t, 2) for t in targets]}")
        for frame in container.decode(video=0):
            t = float(frame.pts * frame.time_base)
            for idx, target in list(pending.items()):
                if t >= target - 1e-6:
                    path = out_dir / f"frame_{idx:02d}_t{target:05.2f}s.png"
                    frame.to_image().save(path)
                    saved[idx] = path
                    del pending[idx]
                    run.log_line(f"[animkit] saved {path.name} (t={t:.2f}s)")
            if not pending:
                break
        container.close()

        # a video may end before the last target; keep whatever was saved
        frames_out = [
            {"index": idx, "t_s": round(targets[idx], 2), "fraction": round(fractions[idx], 3),
             "path": str(saved[idx]), "size_bytes": saved[idx].stat().st_size}
            for idx in sorted(saved)
        ]
        result = {
            "ok": bool(frames_out), "status": "success" if frames_out else "failure",
            "command": "frames", "project": project.name,
            "outputs": {"frames": [f["path"] for f in frames_out]},
            "details": {"video_meta": meta, "frames": frames_out},
            "errors": [] if frames_out else ["no frames could be extracted"],
            "next_actions": [
                "Inspect each frame PNG (Read them) against the quality checklist in the skill",
                "If issues are found: fix scene.py, re-preview, re-extract frames",
                "If frames pass: `animkit render " + str(project.root) + "`",
            ],
        }
    except Exception as exc:
        result = {
            "ok": False, "status": "failure", "command": "frames", "project": project.name,
            "errors": [f"frame extraction failed: {exc}"],
            "error_excerpt": run.error_excerpt(),
            "next_actions": ["Check that the video file is valid; re-render if in doubt"],
        }
    finally:
        run.close()
    result = run.write_result(result)
    run.update_index(result)
    return (0 if result["ok"] else 1), result
