"""`animkit check` — environment discovery and dependency report.

Pipeline position: DISCOVERY. Fast by default; --smoke additionally renders a
1-second scene to prove the full GPU -> ffmpeg -> mp4 path end to end.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from animkit import env


def _smoke_render() -> tuple[bool, list[str]]:
    scene = (
        "from manimlib import *\n\n"
        "class AnimkitSmoke(Scene):\n"
        "    def construct(self):\n"
        "        t = Text('animkit', font_size=48)\n"
        "        self.play(FadeIn(t, scale=0.8), run_time=0.6)\n"
        "        self.wait(0.4)\n"
    )
    manimgl, source = env.find_manimgl()
    ffmpeg, ff_source = env.find_ffmpeg(manimgl)
    if not manimgl or not ffmpeg:
        return False, [f"cannot smoke test: manimgl={manimgl}, ffmpeg={ffmpeg}"]
    with tempfile.TemporaryDirectory(prefix="animkit_smoke_") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "scene.py").write_text(scene, encoding="utf-8")
        cfg = tmp_path / "cfg.yml"
        cfg.write_text(
            "file_writer:\n"
            f"  ffmpeg_bin: \"{str(ffmpeg).replace(chr(92), '/')}\"\n"
            "  crf: 23\n",
            encoding="utf-8",
        )
        import subprocess
        try:
            proc = subprocess.run(
                [str(manimgl), "-w", "-l", "--config_file", str(cfg),
                 "--video_dir", str(tmp_path), str(tmp_path / "scene.py"), "AnimkitSmoke"],
                capture_output=True, text=True, timeout=300, cwd=str(tmp_path),
                encoding="utf-8", errors="replace",
            )
        except subprocess.TimeoutExpired:
            return False, ["smoke render timed out after 300s"]
        video = tmp_path / "AnimkitSmoke.mp4"
        if proc.returncode == 0 and video.is_file() and video.stat().st_size > 1000:
            return True, []
        tail = (proc.stdout + proc.stderr).strip().splitlines()[-12:]
        return False, tail or [f"exit code {proc.returncode}"]


def run(args) -> tuple[int, dict]:
    manimgl, gl_source = env.find_manimgl()
    ffmpeg, ff_source = env.find_ffmpeg(manimgl)
    latex = env.latex_status()

    blockers: list[str] = []
    warnings: list[str] = []
    next_actions: list[str] = []

    if not manimgl:
        blockers.append("manimgl executable not found")
        next_actions.append("Install ManimGL and point animkit_config.json or ANIMKIT_MANIMGL at manimgl.exe")
    if not ffmpeg:
        blockers.append("ffmpeg binary not found (needed by ManimGL's video writer)")
        next_actions.append("Run: <manim-venv-python> -m pip install imageio-ffmpeg")
    for module, label in (("av", "PyAV (video reading/inspection)"),
                          ("PIL", "Pillow (frame images)")):
        if not env.has_module(module):
            blockers.append(f"{label} not importable")
            next_actions.append(f"Run: <manim-venv-python> -m pip install {'av' if module == 'av' else 'pillow'}")
    if not latex["latex"]:
        warnings.append("LaTeX not found: Tex/MathTex and axes.get_axis_labels() are UNAVAILABLE; use Text with Unicode math")
        next_actions.append("Optional: install MiKTeX to enable LaTeX typesetting")
    if env.has_module("imageio_ffmpeg") and ff_source.startswith("imageio"):
        pass  # expected on this machine
    elif ff_source == "PATH":
        warnings.append("ffmpeg comes from PATH; rendering depends on that install staying put")

    smoke = None
    if args.smoke and not blockers:
        ok, detail = _smoke_render()
        smoke = {"ok": ok, "detail": detail[:8]}
        if not ok:
            blockers.append("smoke render failed — see detail")

    result = {
        "ok": not blockers,
        "command": "check",
        "status": "success" if not blockers else "failure",
        "environment": env.env_snapshot(manimgl, gl_source),
        "ffmpeg_source": ff_source,
        "latex": latex,
        "modules": {m: env.has_module(m) for m in ("av", "PIL", "yaml", "numpy")},
        "render_mode": "headless (manimgl -w, wgpu GPU renderer)",
        "smoke": smoke,
        "blockers": blockers,
        "warnings": warnings,
        "next_actions": next_actions or [
            "Environment ready — create a project: animkit new my-animation --dir projects"
        ],
    }
    return (0 if result["ok"] else 1), result
