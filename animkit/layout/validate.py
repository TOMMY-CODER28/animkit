"""Geometry validation: check the SOLVED layout before anything animates.

Checks (first pass = bounding boxes, padded where strokes matter):
  containment   frame + assigned region, with margins
  separation    unintended overlap between unrelated visible components
                (parent-child containment, declared overlaps, arrows/
                highlights/connectors on their targets are exempt)
  alignment     template-declared centrelines / equal spacing within tolerance
  readability   text height above minimum; scale floors
  attachment    owned labels/highlights adjacent to their targets
  finiteness    all coordinates finite
A stage passes when there are no errors; warnings travel to the report.

Rendered-output validation (frames, contact sheet, visual checks) lives in
rendered.py and is run AFTER a preview exists; geometry validation is the
cheap gate before spending GPU time.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from animkit.layout.geom import Box, FRAME_HEIGHT

ALIGN_TOL = 1e-3
ATTACH_TOL = 0.20
STROKE_PAD = 0.05


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""
    severity: str = "error"        # error | warning


@dataclass
class GeometryReport:
    stage_id: str
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not any(not c.passed and c.severity == "error" for c in self.checks)

    @property
    def errors(self) -> list[str]:
        return [f"{c.name}: {c.detail}" for c in self.checks if not c.passed and c.severity == "error"]

    @property
    def warnings(self) -> list[str]:
        return [f"{c.name}: {c.detail}" for c in self.checks if not c.passed and c.severity == "warning"]

    def add(self, name, passed, detail="", severity="error"):
        self.checks.append(CheckResult(name, passed, detail, severity))


def validate_stage_layout(stage, comp_meta: dict[str, "Component"], boxes: dict[str, Box],
                          regions, declared_overlaps: list, frame_box: Box,
                          solved_positions: dict | None = None,
                          template_guarantees: list | None = None,
                          transient: set | None = None) -> GeometryReport:
    rep = GeometryReport(stage_id=stage.id)
    declared = {frozenset(p) for p in declared_overlaps}

    visible = {cid: m for cid, m in comp_meta.items()
               if cid in boxes and cid not in (transient or set())}

    # -- finiteness -----------------------------------------------------------
    bad = [cid for cid, b in boxes.items() if not b.is_finite()]
    rep.add("finite_geometry", not bad, f"non-finite boxes: {bad}" if bad else "all finite")

    # -- containment ----------------------------------------------------------
    for cid, meta in visible.items():
        if meta.overlap_class in ("highlight", "arrow", "connector"):
            continue  # attach to their targets; containment checked via target
        region = regions.get(meta.region)
        box = boxes[cid]
        if region and not region.box.contains(box):
            r = region.box
            rep.add(
                "region_containment", False,
                f"{cid!r} ({meta.region}) box x[{box.left:.2f},{box.right:.2f}] "
                f"y[{box.bottom:.2f},{box.top:.2f}] escapes region "
                f"x[{r.left:.2f},{r.right:.2f}] y[{r.bottom:.2f},{r.top:.2f}]",
            )
        if not frame_box.contains(box, margin=0.15):
            rep.add("frame_containment", False, f"{cid!r} closer than 0.15 to the frame edge")

    # -- separation -------------------------------------------------------------
    ids = list(visible)
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            ma, mb = visible[a], visible[b]
            if {ma.overlap_class, mb.overlap_class} & {"highlight", "arrow", "connector"}:
                continue
            if ma.owner and (ma.owner == b or ma.owner == mb.owner):
                continue
            if mb.owner and mb.owner == a:
                continue
            if frozenset((a, b)) in declared:
                continue
            if boxes[a].overlaps(boxes[b], pad=STROKE_PAD):
                rep.add(
                    "unintended_overlap", False,
                    f"{a!r} and {b!r} bounding boxes overlap; if intentional, add "
                    f"permitted_overlaps [({a!r}, {b!r})] to stage {stage.id!r}",
                )

    # -- template guarantees (alignment / spacing) ------------------------------
    for g in template_guarantees or []:
        kind = g[0]
        if kind == "align_y":
            _, ids_g = g[0], g[1]
            ys = [boxes[i].y for i in ids_g if i in boxes]
            if ys and max(ys) - min(ys) > ALIGN_TOL:
                rep.add("alignment", False, f"centreline {ids_g}: y spread {max(ys)-min(ys):.4f}")
        elif kind == "equal_spacing_x":
            _, ids_g, mode = g[0], g[1], g[2]
            seq = [boxes[i] for i in ids_g if i in boxes]
            if len(seq) >= 3:
                gaps = ([seq[k + 1].x - seq[k].x for k in range(len(seq) - 1)] if mode == "centers"
                        else [seq[k + 1].gap_x(seq[k]) for k in range(len(seq) - 1)])
                if max(gaps) - min(gaps) > ALIGN_TOL:
                    rep.add("equal_spacing", False, f"{ids_g} ({mode}): spread {max(gaps)-min(gaps):.4f}")
        elif kind == "min_gap":
            _, a, b, gap = g
            if a in boxes and b in boxes:
                actual = max(boxes[a].gap_x(boxes[b]), boxes[a].gap_y(boxes[b]))
                if actual < gap - ALIGN_TOL:
                    rep.add("min_gap", False, f"{a}->{b}: {actual:.3f} < {gap:.3f}")

    # -- readability --------------------------------------------------------------
    for cid, meta in visible.items():
        if meta.ctype in ("matrix",) and "tm" in meta.parts:
            e = meta.parts["tm"].get_entries()[0]
            if e.get_height() < 0.14:
                rep.add("readability", False,
                        f"{cid!r}: matrix entries render at {e.get_height():.2f} units — "
                        f"increase entry_size or split the matrix", severity="warning")
        b = boxes[cid]
        if b.h < 0.10 or b.w < 0.10:
            rep.add("readability", False, f"{cid!r} is only {b.w:.2f}x{b.h:.2f} units",
                    severity="warning")

    # -- attachment ---------------------------------------------------------------
    for cid, meta in visible.items():
        if meta.owner and meta.owner in boxes and meta.overlap_class in ("label", "highlight", "connector"):
            tb = boxes[meta.owner]
            gap = max(tb.gap_x(boxes[cid]), tb.gap_y(boxes[cid]))
            attached = boxes[cid].overlaps(tb) or gap <= ATTACH_TOL
            if not attached:
                rep.add("attachment", False,
                        f"{cid!r} drifted {gap:.2f} from its owner {meta.owner!r}",
                        severity="warning")

    return rep


def summarise(reports: list[GeometryReport]) -> dict:
    return {
        "stages": [r.stage_id for r in reports],
        "ok": all(r.ok for r in reports),
        "errors": {r.stage_id: r.errors for r in reports if r.errors},
        "warnings": {r.stage_id: r.warnings for r in reports if r.warnings},
        "checks_run": sum(len(r.checks) for r in reports),
    }
