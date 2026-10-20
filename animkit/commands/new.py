"""`animkit new` — create a project from the bundled template.

Pipeline position: START. Copies animkit/project_template, substituting
{{NAME}}, {{SCENE}}, {{TITLE}} placeholders.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "project_template"


def _scene_class(name: str) -> str:
    return "".join(part.capitalize() for part in re.split(r"[-_ ]+", name) if part)


def _title(name: str) -> str:
    return re.sub(r"[-_]+", " ", name).strip().title()


def run(args) -> tuple[int, dict]:
    name = args.name
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]*$", name):
        return 2, {
            "ok": False, "status": "config_error", "command": "new",
            "errors": [f"name {name!r} must be alphanumeric/dash/underscore"],
            "next_actions": ["Choose a name like 'fourier-intro'"],
        }
    parent = Path(args.dir).resolve()
    target = parent / name
    if target.exists() and not args.force:
        return 2, {
            "ok": False, "status": "config_error", "command": "new",
            "errors": [f"target already exists: {target}"],
            "next_actions": ["Pick another name or pass --force"],
        }

    replacements = {
        "{{NAME}}": name,
        "{{SCENE}}": _scene_class(name),
        "{{TITLE}}": _title(name),
    }
    shutil.copytree(TEMPLATE_DIR, target)
    for path in target.rglob("*"):
        if path.is_file() and path.suffix in (".py", ".json", ".md"):
            text = path.read_text(encoding="utf-8")
            for old, new in replacements.items():
                text = text.replace(old, new)
            path.write_text(text, encoding="utf-8")
    # sanity: project.json must be valid JSON after substitution
    json.loads((target / "project.json").read_text(encoding="utf-8"))

    result = {
        "ok": True, "status": "success", "command": "new",
        "project": name,
        "outputs": {"project_dir": str(target)},
        "details": {
            "scene_class": _scene_class(name),
            "files": sorted(p.name for p in target.iterdir()),
        },
        "next_actions": [
            f"Edit the brief: {target / 'brief.md'}",
            f"Implement the scene: {target / 'scene.py'}",
            f"Validate: animkit validate {target}",
            f"Preview:  animkit preview {target}",
        ],
    }
    return 0, result
