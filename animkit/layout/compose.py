"""SpecScene: runs a validated SceneSpec inside ManimGL.

construct() per stage:
  1. build & measure components (real rendered sizes, labels included)
  2. solve the layout for the stage's regions (direct or kiwi backend)
  3. validate geometry; errors abort the stage loudly, warnings are recorded
  4. estimate movement paths; collisions become warnings with fixes
  5. animate via the StageRegistry (leaving/transform/move/enter/temporary)
  6. record stage wall-clock timings (for boundary frame extraction)
  7. sweep for stale objects

At the end: writes <scene_dir>/layout_report.json (structured validation) and
stage_times.json (cumulative seconds per stage). With ANIMKIT_DEBUG=1 the
render additionally draws region boxes, component bounds, anchors and IDs —
a developer-only view (do not deliver debug renders).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from manimlib import *  # noqa: F401,F403

from animkit.layout.geom import Box, Region, plan_regions, FRAME_HEIGHT
from animkit.layout.spec import SceneSpec, validate_spec, derived_regions_used
from animkit.layout.templates import solve_stage, place_owned
from animkit.layout.registry import StageRegistry
from animkit.layout.validate import validate_stage_layout, summarise
from animkit.layout import paths as pathmod
from animkit.layout.components import (Component, INK_MUTED, ACCENT, BAD,
                                       math_text, body_text)

DEBUG = os.environ.get("ANIMKIT_DEBUG") == "1"


class SpecScene(Scene):
    spec: SceneSpec = None  # subclasses set this

    def setup(self):
        super().setup()
        errors, warnings = validate_spec(self.spec)
        if errors:
            raise ValueError(
                "Invalid scene spec:\n  - " + "\n  - ".join(errors)
            )
        self.warnings: list[str] = list(warnings)
        self.registry = StageRegistry(self.spec)
        self.stage_times: list[dict] = []
        self.geometry_reports: list = []
        self._t = 0.0
        aspect = self.spec.aspect
        self.frame_box = Box(0, 0, FRAME_HEIGHT * aspect, FRAME_HEIGHT)
        self._prev_positions: dict[str, tuple[float, float]] = {}
        self._prewarm_tex()

    def _prewarm_tex(self):
        """Compile every TeX equation BEFORE the first frame. manimlib caches
        compiled TeX by hash, so later builds are instant; without this, the
        compile stall lands mid-construct, the movie writer turns it into
        seconds of frozen video, and late stages get truncated."""
        from animkit.layout.components import MAKERS
        for cid, cs in self.spec.components.items():
            if cs.ctype == "equation" and cs.content.get("mode") == "tex":
                try:
                    MAKERS["equation"](cs)
                except Exception as exc:
                    raise RuntimeError(f"TeX component {cid!r} failed to compile: {exc}") from exc

    # -- helpers -------------------------------------------------------------
    def wait(self, t: float = 1.0):
        self._t += t
        super().wait(t)

    def play(self, *anims, **kw):
        self._t += kw.get("run_time", 1.0)
        super().play(*anims, **kw)

    def construct(self):
        for stage in self.spec.stages:
            self._run_stage(stage)
        self.registry.finish(self)
        self._write_reports()

    # -- the per-stage pipeline ---------------------------------------------
    def _run_stage(self, stage):
        t0 = self._t
        used = derived_regions_used(self.spec, stage)
        regions = plan_regions(self.spec.aspect, used, self.spec.density,
                               stage.annotation_side)

        # 1) build + measure (labels/highlights attached -> measured together);
        # two passes over insertion order so highlights can target same-stage
        # entering components
        boxes: dict[str, Box] = {}
        comp_meta: dict[str, Component] = {}
        fresh: dict[str, Component] = {}
        for cid, life in stage.components.items():
            if life == "leaving":
                comp = self.registry.components.get(cid)
                if comp is not None:
                    comp_meta[cid] = comp
                    boxes[cid] = comp.bounds(pad=0.05)
                continue
            comp = self.registry.build(cid, peers=fresh)
            fresh[cid] = comp
            comp_meta[cid] = comp
            boxes[cid] = comp.bounds(pad=0.05)

        # split pinned bands (title/nav/caption live in their own regions),
        # leaving components (fade out in place — never re-arranged), and
        # owned annotations (they ride their owner) from free template content
        leaving_ids = {cid for cid, life in stage.components.items() if life == "leaving"}
        pinned = {cid for cid, m in comp_meta.items() if m.ctype in ("title", "nav", "caption")}
        owned = {cid for cid, m in comp_meta.items()
                 if (m.owner or self.spec.components[cid].region == "annotation")
                 and cid not in pinned and cid not in leaving_ids}
        free_boxes = {cid: b for cid, b in boxes.items()
                      if cid not in pinned and cid not in owned and cid not in leaving_ids}
        positions: dict[str, tuple[float, float]] = {}
        for cid in pinned:
            rb = regions.get(comp_meta[cid].ctype).box
            positions[cid] = (rb.x, rb.y)

        # 2) solve free layout
        result = solve_stage(stage, free_boxes, regions, self._prev_positions)
        if result.status != "solved":
            self._abort_stage(stage, regions, result)
        positions.update(result.positions)

        # owned annotations: placed by the shared placement rule (or in the
        # annotation band when the spec assigns them there)
        place_owned(self.spec, comp_meta, boxes, positions, regions)
        all_boxes = {}
        for cid, b in boxes.items():
            if cid in positions:
                all_boxes[cid] = b.moved_to(*positions[cid])
            else:
                all_boxes[cid] = b  # leaving: stays where it is while fading out

        # 3) geometry validation (pre-animation gate; leaving comps — explicit
        # and implicit — are transient: they fade out and may legitimately
        # coexist with entering content)
        implicit_leavers = set(self.registry.components) - set(stage.components)
        guarantees = self._template_guarantees(stage, free_boxes, result)
        report = validate_stage_layout(stage, comp_meta, all_boxes, regions,
                                       stage.permitted_overlaps, self.frame_box,
                                       positions, guarantees,
                                       transient=leaving_ids | implicit_leavers)
        self.geometry_reports.append(report)
        if not report.ok:
            self._abort_stage(stage, regions, result, report)

        # 4) path estimation for movers
        moves = {}
        for cid, life in stage.components.items():
            if life in ("changing",) and stage.transition.get(cid, "move") == "move":
                start = self.registry.components[cid].group.get_center()[:2] \
                    if cid in self.registry.components else positions[cid]
                moves[cid] = (start, positions[cid])
            elif life == "persistent" and cid in self.registry.components:
                cur = self.registry.components[cid].group.get_center()[:2]
                tgt = positions[cid]
                if abs(cur[0] - tgt[0]) > 1e-3 or abs(cur[1] - tgt[1]) > 1e-3:
                    moves[cid] = (cur, tgt)
        notes = pathmod.check_paths(moves, all_boxes, stage.permitted_overlaps, comp_meta)
        self.warnings.extend(f"stage {stage.id}: {n}" for n in notes)

        # 5) animate
        timings = {
            "enter": stage.timing.get("enter", 0.8),
            "move": stage.timing.get("move", 1.0),
            "exit": stage.timing.get("exit", 0.5),
            "hold": stage.timing.get("hold", 0.8),
        }
        if DEBUG:
            self._add_debug_overlay(stage, regions, comp_meta, all_boxes)
        record = self.registry.apply_stage(scene=self, stage=stage,
                                           positions=positions,
                                           timings=timings)
        self._prev_positions.update(positions)
        self.warnings.extend(f"stage {stage.id}: {i}" for i in record["issues"])

        # caption shorthand
        cap_comp = None
        if stage.caption:
            cap_comp = Component(id=f"__cap_{stage.id}", ctype="caption",
                                 group=body_text(stage.caption, 22, INK_MUTED),
                                 region="caption")
            cap_comp.group.move_to([regions.get("caption").box.x,
                                    regions.get("caption").box.y, 0])
            self.add(cap_comp.group)

        hold = timings["hold"]
        if hold:
            self.wait(hold)

        # 6/7) caption out, then temps + stale sweep (caption must not be flagged)
        if cap_comp is not None:
            cap_comp.group.clear_updaters()
            self.play(FadeOut(cap_comp.group), run_time=0.4)
        stale = self.registry.end_stage(self, stage)
        self.warnings.extend(f"stage {stage.id}: {s}" for s in self.registry.stale_report[-len(stale):])
        self.stage_times.append({
            "stage": stage.id, "t_start": round(t0, 2),
            "t_end": round(self._t, 2),
            "template": stage.template,
            "solved_backend": result.backend,
            "actions": record["actions"],
        })
        if DEBUG:
            self.wait(0.6)

    def _abort_stage(self, stage, regions, result, report=None):
        msg = [f"stage {stage.id!r} aborted before animating:"]
        msg += [f"  solver({result.backend}): {d}" for d in result.diagnostics]
        if report is not None:
            msg += [f"  geometry: {e}" for e in report.errors]
        msg += ["  fix scene.py (shrink content, change template, density='compact', "
                "or split the stage) — nothing was rendered for this stage"]
        raise ValueError("\n".join(msg))

    def _template_guarantees(self, stage, boxes, result):
        """Relationships the chosen template claims, for re-checking. Row
        ordering comes from the SOLVED positions (declaration order may differ
        whenever previous positions reorder the row)."""
        ids = [cid for cid in boxes]
        t = stage.template
        if t in ("two_columns", "three_columns", "input_op_output") and len(ids) >= 2:
            by_x = sorted(ids, key=lambda c: result.positions.get(c, (0, 0))[0])
            checks = [("align_y", ids)]
            if t != "two_columns" and len(by_x) >= 3:
                checks.append(("equal_spacing_x", by_x, "centers"))
            return checks
        if t == "operands_result":
            top = [i for i in ids if i in stage.operands]
            return ([("align_y", top)] if len(top) > 1 else []) + \
                   ([("min_gap", stage.result, top[0], stage.min_gap)] if top else [])
        return []

    # -- debug view --------------------------------------------------------------
    def _add_debug_overlay(self, stage, regions, comp_meta, boxes):
        overlay = []
        for name, region in regions.regions.items():
            r = region.box
            rect = Rectangle(width=r.w, height=r.h).set_stroke(INK_MUTED, width=1)
            rect.set_stroke(color=ACCENT if name == "main" else INK_MUTED, width=1)
            lab = body_text(name, 14, INK_MUTED)
            lab.move_to([r.left + lab.get_width() / 2 + 0.1, r.top - 0.12, 0])
            overlay += [rect, lab]
        for cid, meta in comp_meta.items():
            b = boxes[cid]
            rect = Rectangle(width=b.w, height=b.h).set_stroke(BAD, width=1)
            rect.move_to([b.x, b.y, 0])
            dot = Dot([b.x, b.y, 0], radius=0.03).set_fill(ACCENT, 1).set_stroke(width=0)
            lab = body_text(cid, 12, BAD)
            lab.move_to([b.left + lab.get_width() / 2 + 0.05, b.top + 0.1, 0])
            overlay += [rect, dot, lab]
        self.add(VGroup(*overlay))

    # -- reports -------------------------------------------------------------------
    def _write_reports(self):
        out_dir = Path(self.spec.output_dir) if hasattr(self.spec, "output_dir") else Path(".")
        out_dir.mkdir(parents=True, exist_ok=True)
        report = {
            "spec": self.spec.name,
            "ok": all(r.ok for r in self.geometry_reports) and not self.registry.stale_report,
            "geometry": summarise(self.geometry_reports),
            "stale_objects": self.registry.stale_report,
            "warnings": self.warnings,
            "stage_log": self.registry.stage_log,
        }
        (out_dir / "layout_report.json").write_text(json.dumps(report, indent=2, default=str))
        (out_dir / "stage_times.json").write_text(json.dumps(self.stage_times, indent=2))
