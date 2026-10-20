"""`animkit check-layout <project>` — dry-run the layout system.

Imports the project's scene.py, builds its SceneSpec, validates it, then
solves + geometry-checks every stage WITHOUT rendering. Fast (~seconds);
catches spec errors, infeasible layouts, and constraint violations before
spending GPU time. Exit 0 = all stages pass.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from animkit.config import load_project
from animkit.runs import Run


def _load_spec(scene_file: Path):
    """Import scene.py and return its SceneSpec (convention: module-level
    build_spec() function)."""
    from animkit.env import animkit_root
    sys.path.insert(0, str(animkit_root()))
    spec = importlib.util.spec_from_file_location("scene_layout_check", scene_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "build_spec"):
        raise ValueError(
            "scene.py has no module-level build_spec() — the layout dry-run and "
            "SpecScene both read the spec from there"
        )
    return module.build_spec()


def run(args) -> tuple[int, dict]:
    project, errors = load_project(args.project)
    if project is None:
        return 2, {"ok": False, "status": "config_error", "command": "check-layout",
                   "errors": errors, "next_actions": ["Fix project.json first"]}
    run_rec = Run(project.root, "check-layout")
    try:
        try:
            spec = _load_spec(project.scene_file)
        except Exception as exc:
            result = {"ok": False, "status": "failure", "command": "check-layout",
                      "project": project.name,
                      "errors": [f"could not load spec: {exc}"],
                      "next_actions": ["Ensure scene.py builds a SceneSpec in setup()"]}
            result = run_rec.write_result(result)
            return 1, result

        from animkit.layout.spec import validate_spec, derived_regions_used
        from animkit.layout.geom import plan_regions, Box, FRAME_HEIGHT
        from animkit.layout.templates import solve_stage
        from animkit.layout.validate import validate_stage_layout, summarise
        from animkit.layout.registry import StageRegistry

        spec_errors, warnings = validate_spec(spec)
        stage_reports = []
        if not spec_errors:
            registry = StageRegistry(spec)
            frame = Box(0, 0, FRAME_HEIGHT * spec.aspect, FRAME_HEIGHT)
            prev = {}
            for stage in spec.stages:
                used = derived_regions_used(spec, stage)
                try:
                    regions = plan_regions(spec.aspect, used, spec.density, stage.annotation_side)
                except ValueError as exc:
                    stage_reports.append({"stage": stage.id, "ok": False, "errors": [str(exc)]})
                    continue
                boxes, meta = {}, {}
                for cid in stage.components:
                    cs = spec.components[cid]
                    if cs.ctype == "highlight":
                        continue  # positioned by updater; skip in dry-run
                    comp = registry.build(cid)
                    if comp.ctype in ("title", "nav", "caption"):
                        comp.region = comp.ctype
                    meta[cid] = comp
                    boxes[cid] = comp.bounds(pad=0.05)
                positions = {}
                leaving = {cid for cid, life in stage.components.items() if life == "leaving"}
                pinned = {cid for cid, m in meta.items() if m.ctype in ("title", "nav", "caption")}
                owned = {cid for cid, m in meta.items()
                         if (m.owner or spec.components[cid].region == "annotation")
                         and cid not in pinned and cid not in leaving}
                free = {cid: b for cid, b in boxes.items()
                        if cid not in pinned and cid not in owned and cid not in leaving}
                for cid in pinned:
                    rb = regions.get(meta[cid].ctype).box
                    positions[cid] = (rb.x, rb.y)
                res = solve_stage(stage, free, regions, prev)
                if res.status != "solved":
                    stage_reports.append({"stage": stage.id, "ok": False,
                                          "backend": res.backend,
                                          "errors": res.diagnostics})
                    continue
                positions.update(res.positions)
                from animkit.layout.templates import place_owned
                place_owned(spec, meta, boxes, positions, regions)
                all_boxes = {cid: (b.moved_to(*positions[cid]) if cid in positions else b)
                             for cid, b in boxes.items()}
                report = validate_stage_layout(stage, meta, all_boxes, regions,
                                               stage.permitted_overlaps, frame,
                                               positions, transient=leaving | (set(registry.components) - set(stage.components)))
                stage_reports.append({
                    "stage": stage.id, "ok": report.ok, "template": stage.template,
                    "backend": res.backend,
                    "errors": report.errors, "warnings": report.warnings,
                })
                prev.update(positions)

        ok = not spec_errors and all(s["ok"] for s in stage_reports)
        result = {
            "ok": ok, "status": "success" if ok else "failure",
            "command": "check-layout", "project": project.name,
            "details": {
                "spec": spec.name,
                "stages": stage_reports,
                "summary": summarise([]) if spec_errors else {
                    "ok": ok,
                    "errors": {s["stage"]: s["errors"] for s in stage_reports if s.get("errors")},
                    "warnings": {s["stage"]: s["warnings"] for s in stage_reports if s.get("warnings")},
                },
            },
            "outputs": {},
            "errors": spec_errors if spec_errors else
                      [f"{s['stage']}: {e}" for s in stage_reports for e in s.get("errors", [])],
            "warnings": warnings,
            "next_actions": (["Layout is sound — render with `animkit preview " + str(project.root) + "`"]
                             if ok else
                             ["Fix the errors above in scene.py's spec, then re-run check-layout"]),
        }
        result = run_rec.write_result(result)
        return (0 if ok else 1), result
    finally:
        run_rec.close()
