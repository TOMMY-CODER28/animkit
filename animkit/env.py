"""Environment discovery: manimgl executable, ffmpeg binary, optional LaTeX.

Everything here distinguishes *observed* facts (probed at runtime) from
machine-local defaults (animkit_config.json). Nothing imports manimlib itself.
"""

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
import importlib.util
from pathlib import Path

from animkit import __version__

REPO_ROOT = Path(__file__).resolve().parent.parent
LOCAL_CONFIG = REPO_ROOT / "animkit_config.json"


def animkit_root() -> Path:
    """Where the animkit checkout lives. Resolution order:
    1. ANIMKIT_ROOT environment variable
    2. the package's own location (works for pip install -e and any clone)
    """
    env = os.environ.get("ANIMKIT_ROOT")
    if env and Path(env).is_dir():
        return Path(env).resolve()
    return REPO_ROOT


def load_local_config() -> dict:
    try:
        return json.loads(LOCAL_CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}


def find_manimgl(configured: str | None = None) -> tuple[Path | None, str]:
    """Return (path, source) for the manimgl executable, or (None, 'not found').

    Priority: explicit setting > ANIMKIT_MANIMGL env var > animkit_config.json
    > sibling of the running interpreter > PATH.
    """
    candidates: list[tuple[Path, str]] = []
    if configured:
        candidates.append((Path(configured), "project config"))
    env_var = os.environ.get("ANIMKIT_MANIMGL")
    if env_var:
        candidates.append((Path(env_var), "env ANIMKIT_MANIMGL"))
    local = load_local_config().get("manimgl")
    if local:
        candidates.append((Path(local), "animkit_config.json"))
    exe_dir = Path(sys.executable).resolve().parent
    candidates.append((exe_dir / "manimgl.exe", "interpreter dir"))
    candidates.append((exe_dir / "manimgl", "interpreter dir"))
    which = shutil.which("manimgl")
    if which:
        candidates.append((Path(which), "PATH"))
    for path, source in candidates:
        if path.is_file():
            return path.resolve(), source
    return None, "not found"


def manimgl_version(exe: Path, timeout: float = 30) -> str | None:
    try:
        out = subprocess.run(
            [str(exe), "--version"], capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
    except Exception:
        return None
    m = re.search(r"v(\d+\.\d+\.\d+)", out.stdout or "")
    return m.group(1) if m else None


def _python_for_manimgl(manimgl_exe: Path) -> Path:
    py = manimgl_exe.parent / "python.exe"
    return py if py.is_file() else Path(sys.executable)


def find_ffmpeg(manimgl_exe: Path | None) -> tuple[Path | None, str]:
    """Return (ffmpeg_path, source). Prefers a real ffmpeg on PATH, then the
    imageio-ffmpeg binary bundled inside the manim environment."""
    which = shutil.which("ffmpeg")
    if which:
        return Path(which), "PATH"
    try:
        import imageio_ffmpeg
        return Path(imageio_ffmpeg.get_ffmpeg_exe()), "imageio-ffmpeg"
    except Exception:
        pass
    if manimgl_exe:
        py = _python_for_manimgl(manimgl_exe)
        try:
            out = subprocess.run(
                [str(py), "-c", "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"],
                capture_output=True, text=True, timeout=60,
                encoding="utf-8", errors="replace",
            )
            if out.returncode == 0 and out.stdout.strip():
                return Path(out.stdout.strip()), "imageio-ffmpeg (subprocess)"
        except Exception:
            pass
    return None, "not found"


def ffmpeg_version(ffmpeg: Path | None) -> str | None:
    if not ffmpeg:
        return None
    try:
        out = subprocess.run(
            [str(ffmpeg), "-version"], capture_output=True, text=True,
            timeout=20, encoding="utf-8", errors="replace",
        )
        first = (out.stdout or "").strip().splitlines()
        return first[0] if first else None
    except Exception:
        return None


def has_module(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except Exception:
        return False


def latex_status() -> dict:
    bin_dir = find_latex()
    return {
        "latex": bin_dir is not None,
        "dvisvgm": bin_dir is not None,
        "bin_dir": str(bin_dir) if bin_dir else None,
    }


def find_latex() -> Path | None:
    """Locate a TeX toolchain (latex + dvisvgm) ManimGL's Tex can shell to.

    Order: PATH · ANIMKIT_TEX env var · user-scope MiKTeX · system MiKTeX ·
    TeX Live. Returns the bin directory or None.
    """
    if shutil.which("latex") and shutil.which("dvisvgm"):
        return Path(shutil.which("latex")).parent
    env_dir = os.environ.get("ANIMKIT_TEX")
    if env_dir and (Path(env_dir) / "latex.exe").is_file():
        return Path(env_dir)
    candidates = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "MiKTeX" / "miktex" / "bin" / "x64",
        Path("C:/Program Files/MiKTeX/miktex/bin/x64"),
        Path("C:/texlive") / "2024" / "bin" / "windows",
    ]
    for c in candidates:
        if (c / "latex.exe").is_file() and (c / "dvisvgm.exe").is_file():
            return c
    return None


def latex_path_env(base_env: dict | None = None) -> dict:
    """Env dict with the TeX bin dir prepended to PATH (for manimgl
    subprocesses and in-process Tex construction). No-op when absent."""
    env = dict(base_env if base_env is not None else os.environ)
    tex = find_latex()
    if tex and str(tex) not in env.get("PATH", ""):
        env["PATH"] = str(tex) + os.pathsep + env.get("PATH", "")
    return env


def env_snapshot(manimgl_exe: Path | None, source: str) -> dict:
    version = manimgl_version(manimgl_exe) if manimgl_exe else None
    ffmpeg, ff_source = find_ffmpeg(manimgl_exe)
    return {
        "animkit_version": __version__,
        "platform": platform.platform(),
        "python": sys.version.split()[0],
        "python_exe": sys.executable,
        "manimgl_path": str(manimgl_exe) if manimgl_exe else None,
        "manimgl_version": version,
        "manimgl_source": source,
        "ffmpeg_path": str(ffmpeg) if ffmpeg else None,
        "ffmpeg_source": ff_source,
        "ffmpeg_version": ffmpeg_version(ffmpeg),
    }
