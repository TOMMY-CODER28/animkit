"""`animkit validate` — check a project's config, files, and scene code.

Pipeline position: after creating/editing a project, before any render.
"""

from __future__ import annotations

import ast
import py_compile
from pathlib import Path

from animkit import env
from animkit.config import load_project


def scene_classes(path: Path) -> list[str]:
    """Names of Scene subclasses defined in a scene file (light AST walk)."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        raise ValueError(f"scene file has a syntax error: {exc}") from exc
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                name = getattr(base, "id", None) or getattr(base, "attr", None)
                if name and "Scene" in name:
                    names.append(node.name)
    return names


def run(args) -> tuple[int, dict]:
    project, errors = load_project(args.project)
    warnings: list[str] = []
    details: dict = {}

    if project is None:
        return 2, {
            "ok": False, "status": "config_error", "command": "validate",
            "errors": errors,
            "next_actions": ["Fix the issues above, or regenerate the project with `animkit new`"],
        }

    try:
        py_compile.compile(str(project.theme_file), doraise=True)
        details["theme_compiles"] = True
    except py_compile.PyCompileError as exc:
        errors.append(f"theme.py does not compile: {exc.msg}")

    try:
        found = scene_classes(project.scene_file)
        details["scene_classes"] = found
        if project.scene not in found:
            errors.append(
                f"project.json names scene '{project.scene}' but scene file defines: "
                f"{', '.join(found) if found else 'no Scene subclasses'}"
            )
        extra = [s for s in found if s != project.scene]
        if extra:
            warnings.append(f"additional Scene subclasses present (not rendered by default): {extra}")
    except ValueError as exc:
        errors.append(str(exc))

    manimgl, _ = env.find_manimgl(project.manimgl_setting())
    if not manimgl:
        errors.append("manimgl executable not found")
    else:
        details["manimgl"] = str(manimgl)
    ffmpeg, _ = env.find_ffmpeg(manimgl)
    if not ffmpeg:
        errors.append("ffmpeg binary not found")

    if getattr(args, "deep", False) and not errors:
        # Import the scene module in a subprocess: catches ImportError/NameError now
        # instead of mid-render. Runs with cwd = project root.
        import subprocess, sys
        code = (
            "import importlib.util, sys\n"
            f"spec = importlib.util.spec_from_file_location('scene_check', r'{project.scene_file}')\n"
            "module = importlib.util.module_from_spec(spec)\n"
            "spec.loader.exec_module(module)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], cwd=str(project.root),
            capture_output=True, text=True, timeout=120,
            encoding="utf-8", errors="replace",
        )
        details["deep_import"] = {"exit_code": proc.returncode}
        if proc.returncode != 0:
            errors.append("scene.py fails at import time: " + (proc.stderr or proc.stdout).strip().splitlines()[-1])

    result = {
        "ok": not errors,
        "command": "validate",
        "status": "success" if not errors else "failure",
        "project": project.name,
        "errors": errors,
        "warnings": warnings,
        "details": details,
        "next_actions": (
            ["Run `animkit preview " + str(project.root) + "`"]
            if not errors
            else ["Fix the errors above, then re-validate"]
        ),
    }
    return (0 if result["ok"] else 1), result
