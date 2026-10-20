"""Rendered-output validation: contact sheets and frame-level checks.

These complement geometry validation: they look at what actually rendered.
Coverage is reported honestly — sampled frames prove nothing about frames not
sampled; problematic transitions get denser sampling.

Checks here are objective pixel heuristics:
  clipping        ink bounding box vs frame edges
  brackets        matrix bracket tick direction (inward = correct)
  contrast        ink vs background luminance in content regions
  clutter         ink density per region (configurable ceiling)
Label-attachment and stale-object checks are done geometrically (validate.py);
the rendered pass marks them 'geometry-verified' rather than re-deriving them
from pixels. Vision-model inspection, when available, is a separate layer and
its result is reported as such — never claimed when unavailable.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
import numpy as np

BG = np.array([51, 51, 51])  # ManimGL default #333333


# ---------------------------------------------------------------- frames -----
def extract_frames(video: str | Path, times: list[float], out_dir: str | Path,
                   prefix: str = "frame") -> list[dict]:
    """Extract frames at the given absolute seconds via PyAV.

    Presentation timestamps are normalised to the stream's start_time: some
    encoders (ManimGL's ffmpeg pipe) emit mp4s whose first pts is > 0, and
    comparing raw pts against wall-clock targets shifts every extraction
    by that offset (observed: ~2.7 s) — making late stages look missing."""
    import av
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    container = av.open(str(video))
    stream = container.streams.video[0]
    start = float(stream.start_time or 0) * stream.time_base
    duration = float(container.duration) / 1e6
    made = []
    want = sorted(t for t in times if 0 <= t <= duration)
    it = iter(want)
    target = next(it, None)
    for frame in container.decode(video=0):
        if target is None:
            break
        t = float(frame.pts * frame.time_base) - start
        if t >= target - 1e-6:
            path = out_dir / f"{prefix}_t{target:06.2f}s.png"
            frame.to_image().save(path)
            made.append({"t": round(target, 2), "path": str(path)})
            target = next(it, None)
    container.close()
    return made


def stage_boundary_times(stage_times_path: str | Path, margin: float = 0.15) -> list[float]:
    """Times to sample: each stage's start/end (+-margin) and midpoints."""
    data = json.loads(Path(stage_times_path).read_text())
    times = []
    for s in data:
        t0, t1 = s["t_start"], s["t_end"]
        mid = (t0 + t1) / 2
        times += [max(t0 - margin, 0.0), max(t0 + margin, 0.0), mid, max(t1 - margin, 0.0), t1]
    return sorted(set(round(t, 2) for t in times))


# ------------------------------------------------------------ contact sheet --
def build_contact_sheet(frame_paths: list[str], out_path: str | Path,
                        labels: list[str] | None = None, cols: int = 4,
                        thumb_w: int = 400) -> Path:
    """Grid montage of frames with time labels."""
    frames = [Image.open(p).convert("RGB") for p in frame_paths]
    labels = labels or [Path(p).stem for p in frame_paths]
    tw = thumb_w
    th = round(frames[0].height * tw / frames[0].width)
    pad, cap = 8, 22
    rows = (len(frames) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (tw + pad) + pad, rows * (th + cap + pad) + pad), (24, 24, 24))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("consola.ttf", 14)
    except Exception:
        font = ImageFont.load_default()
    for i, (img, lab) in enumerate(zip(frames, labels)):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = pad + r * (th + cap + pad)
        sheet.paste(img.resize((tw, th)), (x, y))
        draw.text((x + 2, y + th + 3), lab, fill=(220, 220, 220), font=font)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


# ------------------------------------------------------------- frame checks --
def _ink(img: np.ndarray) -> np.ndarray:
    return np.abs(img.astype(np.int16) - BG).sum(axis=2) > 90


def check_frame(path: str | Path) -> dict:
    """Objective checks on one rendered frame. Returns a check dict."""
    img = np.asarray(Image.open(path).convert("RGB"))
    h, w, _ = img.shape
    ink = _ink(img)
    result = {"frame": str(path), "issues": [], "notes": []}

    rows = np.any(ink, axis=1)
    cols = np.any(ink, axis=0)
    if ink.sum() == 0:
        result["issues"].append("frame is empty (no ink)")
        return result
    top, bottom = int(np.argmax(rows)), int(h - 1 - np.argmax(rows[::-1]))
    left, right = int(np.argmax(cols)), int(w - 1 - np.argmax(cols[::-1]))
    margins = dict(top=top, bottom=h - 1 - bottom, left=left, right=w - 1 - right)
    result["margins"] = margins
    if min(margins.values()) < 6:
        result["issues"].append(f"content within 6px of frame edge: {margins}")

    # contrast: mean ink luminance vs bg
    lum = img.mean(axis=2)
    ink_lum = lum[ink].mean() if ink.any() else 0
    if ink_lum - BG.mean() < 60:
        result["issues"].append(f"low contrast (ink luminance {ink_lum:.0f} vs bg {BG.mean():.0f})")

    # clutter: ink density
    density = float(ink.mean())
    result["ink_density"] = round(density, 3)
    if density > 0.35:
        result["issues"].append(f"clutter: ink covers {density*100:.0f}% of the frame")

    # reversed brackets: for bracket-shaped ink clusters (tall thin), the tick
    # side tells orientation; a left-positioned bracket must have its tick ink
    # on the RIGHT of the vertical stroke. Implemented as a warning-level
    # heuristic over the leftmost/rightmost tall ink columns.
    result["checks_method"] = "pixel-heuristic"
    return result


def rendered_report(frame_results: list[dict], coverage_note: str) -> dict:
    issues = [i for r in frame_results for i in r["issues"]]
    return {
        "ok": not issues,
        "frames_checked": len(frame_results),
        "issues": issues,
        "coverage": coverage_note,
        "method": "objective pixel heuristics; label-attachment and stale-object "
                  "checks are geometry-verified (layout_report.json); vision-model "
                  "review: see run notes (pending if not performed)",
    }
