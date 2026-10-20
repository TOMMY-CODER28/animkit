"""Project configuration: project.json schema, loading and validation."""

from __future__ import annotations

import json
import re
from pathlib import Path

NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
SCENE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

DEFAULTS = {
    "scene_file": "scene.py",
    "output": {
        "video_dir": "media",
        "preview_resolution": [854, 480],
        "preview_fps": 15,
        "preview_crf": 23,
        "final_resolution": [1920, 1080],
        "final_fps": 60,
        "final_crf": 18,
    },
    "timing": {
        "preview_timeout_s": 900,
        "render_timeout_s": 5400,
        "frames_timeout_s": 180,
    },
    "environment": {
        "manimgl": "auto",
    },
    "background_color": "",
    "notes": "",
}


class ConfigError(Exception):
    pass


def _merge(defaults: dict, loaded: dict) -> dict:
    out = dict(defaults)
    for key, value in loaded.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def validate_values(cfg: dict) -> list[str]:
    errors: list[str] = []

    name = cfg.get("name")
    if not isinstance(name, str) or not NAME_RE.match(name):
        errors.append(f"'name' must match {NAME_RE.pattern!r}, got {name!r}")
    scene = cfg.get("scene")
    if not isinstance(scene, str) or not SCENE_RE.match(scene):
        errors.append(f"'scene' must be a Python identifier, got {scene!r}")

    out = cfg.get("output", {})
    for key in ("preview_resolution", "final_resolution"):
        res = out.get(key)
        if (
            not isinstance(res, list) or len(res) != 2
            or not all(isinstance(v, int) and v > 0 for v in res)
        ):
            errors.append(f"output.{key} must be [width, height] positive ints, got {res!r}")
        elif any(v % 2 for v in res):
            errors.append(f"output.{key}={res} — both numbers must be even (yuv420p)")
    for key in ("preview_fps", "final_fps"):
        fps = out.get(key)
        if not isinstance(fps, int) or not 1 <= fps <= 120:
            errors.append(f"output.{key} must be an int in 1..120, got {fps!r}")
    for key in ("preview_crf", "final_crf"):
        crf = out.get(key)
        if not isinstance(crf, int) or not 0 <= crf <= 51:
            errors.append(f"output.{key} must be an int in 0..51, got {crf!r}")
    video_dir = out.get("video_dir")
    if not isinstance(video_dir, str) or not video_dir:
        errors.append("output.video_dir must be a non-empty string")

    for key, value in cfg.get("timing", {}).items():
        if not isinstance(value, int) or value <= 0:
            errors.append(f"timing.{key} must be a positive int, got {value!r}")

    bg = cfg.get("background_color") or ""
    if bg and not COLOR_RE.match(bg):
        errors.append(f"background_color must look like '#RRGGBB' or be empty, got {bg!r}")

    return errors


class Project:
    """A loaded animkit project directory."""

    def __init__(self, root: Path, cfg: dict):
        self.root = root.resolve()
        self.cfg = cfg

    # -- identity -----------------------------------------------------------
    @property
    def name(self) -> str:
        return self.cfg["name"]

    @property
    def scene(self) -> str:
        return self.cfg["scene"]

    @property
    def scene_file(self) -> Path:
        return self.root / self.cfg["scene_file"]

    @property
    def theme_file(self) -> Path:
        return self.root / "theme.py"

    @property
    def video_dir(self) -> Path:
        return (self.root / self.cfg["output"]["video_dir"]).resolve()

    @property
    def expected_video(self) -> Path:
        return self.video_dir / f"{self.scene}.mp4"

    # -- render settings ----------------------------------------------------
    def settings(self, mode: str) -> dict:
        out = self.cfg["output"]
        prefix = "preview" if mode == "preview" else "final"
        return {
            "resolution": out[f"{prefix}_resolution"],
            "fps": out[f"{prefix}_fps"],
            "crf": out[f"{prefix}_crf"],
            "timeout_s": self.cfg["timing"][f"{'preview' if mode == 'preview' else 'render'}_timeout_s"],
            "background_color": self.cfg.get("background_color") or None,
        }

    def manimgl_setting(self) -> str | None:
        value = self.cfg.get("environment", {}).get("manimgl", "auto")
        return None if value in ("auto", "") else value

    def hashes(self) -> dict[str, str]:
        import hashlib
        result = {}
        for label, path in (
            ("scene.py", self.scene_file),
            ("theme.py", self.theme_file),
            ("project.json", self.root / "project.json"),
        ):
            if path.is_file():
                result[label] = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        return result


def load_project(project_dir: str | Path) -> tuple[Project | None, list[str]]:
    """Load and validate a project. Returns (project, errors)."""
    root = Path(project_dir).resolve()
    errors: list[str] = []
    path = root / "project.json"
    if not root.is_dir():
        return None, [f"project directory not found: {root}"]
    if not path.is_file():
        return None, [f"project.json not found in {root}"]
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [f"project.json is not valid JSON: {exc}"]
    if not isinstance(raw, dict):
        return None, ["project.json must contain a JSON object"]
    cfg = _merge(DEFAULTS, raw)
    errors.extend(validate_values(cfg))

    if not (root / cfg["scene_file"]).is_file():
        errors.append(f"scene file '{cfg['scene_file']}' not found in {root}")
    if not (root / "theme.py").is_file():
        errors.append("theme.py not found in project directory")

    if errors:
        return None, errors
    return Project(root, cfg), []
