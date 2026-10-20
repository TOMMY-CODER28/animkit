"""Layout templates: each turns measured component boxes + region bounds into
a solved arrangement, choosing ordering relationships explicitly.

Templates compose: they may use the direct backend (arithmetic, simple) or the
kiwi backend (coupled linear constraints). Every template also declares the
alignment relationships it *guarantees* so validation can re-check them.

Custom escape hatch: template "custom" places components at the coordinates
given in StageSpec.custom_x/custom_y (internal frame coords) and still runs
geometry validation afterwards.
"""

from __future__ import annotations

from animkit.layout.geom import Box, RegionPlan
from animkit.layout.solver import DirectSolver, KiwiSolver, SolveResult, _check_required


def _main_center(r: RegionPlan) -> tuple[float, float]:
    b = r.get("main").box
    return (b.x, b.y)


def solve_stage(stage, comp_boxes: dict[str, Box], regions: RegionPlan,
                prev_positions: dict[str, tuple[float, float]] | None = None,
                aspect_ratio_boxes: dict[str, Box] | None = None) -> SolveResult:
    """Dispatch on stage.template. comp_boxes are measured at scale 1 in main
    region coordinates (already includes labels/highlights attached)."""
    tpl = stage.template
    handlers = {
        "single_center": _single_center,
        "two_columns": _two_columns,
        "three_columns": _three_columns,
        "input_op_output": _input_op_output,
        "operands_result": _operands_result,
        "main_callout": _main_callout,
        "equation_explanation": _equation_explanation,
        "custom": _custom,
    }
    if tpl not in handlers:
        return SolveResult(status="error", diagnostics=[f"unknown template {tpl!r}"])
    return handlers[tpl](stage, comp_boxes, regions, prev_positions or {})


def try_fit(stage, build_and_measure, solve_fn, max_shrink=0.75, steps=(1.0, 0.9, 0.82, 0.75)):
    """Re-measure at uniformly reduced scale and re-solve until feasible.

    `build_and_measure(scale)` -> (boxes, rebuild_info); `solve_fn(boxes)` ->
    SolveResult. Never shrinks below max_shrink; if still infeasible the last
    diagnostics travel up (caller chooses another template / splits stages).
    """
    last = None
    for scale in steps:
        boxes, info = build_and_measure(scale)
        last = solve_fn(boxes)
        if last.status != "infeasible":
            return last, scale, info
    return last, max_shrink, info


# ---------------------------------------------------------------- templates --

def _single_center(stage, boxes, regions, prev):
    region = regions.get("main")
    if region is None:
        return SolveResult(status="error", diagnostics=["stage uses no main region"])
    targets = {}
    mb = region.box
    for cid in boxes:
        if cid in prev and stage.transition.get(cid) != "move":
            targets[cid] = prev[cid]
        else:
            targets[cid] = (mb.x, mb.y)
    constraints = [("contain", "main")]
    return DirectSolver().solve(boxes, targets, constraints, regions.regions)


def _two_columns(stage, boxes, regions, prev):
    """Two comps side by side, shared centreline, equal centre spacing is
    NOT forced (widths may differ — gap equality would distort); min gap +
    pair centred in main."""
    ids = _main_ids(stage, boxes)
    if len(ids) != 2:
        return SolveResult(status="error",
                           diagnostics=[f"two_columns needs exactly 2 main components, got {ids}"])
    a, b = ids
    con = [
        ("contain", "main"),
        ("align_y", ids),
    ]
    pref = [("stay", a), ("stay", b)]
    left, right = _pick_order(a, b, prev=prev)
    # order_x alone enforces the gap; a separate min_gap_x in declaration
    # order would contradict a picked order that reverses (regression: mha)
    con.append(("order_x", [left, right], _gap(stage)))
    return KiwiSolver().solve(boxes, con, pref, regions.regions, prev)


def _three_columns(stage, boxes, regions, prev):
    """'Show Q, K and V in three aligned columns, with their labels above them'
    — labels ride inside each matrix component; the template guarantees: order,
    EQUAL CENTRE SPACING (centres, not visible gaps — widths may differ),
    shared centreline, min gaps, containment."""
    ids = _main_ids(stage, boxes)
    if len(ids) != 3:
        return SolveResult(status="error",
                           diagnostics=[f"three_columns needs exactly 3 main components, got {ids}"])
    a, b, c = _pick_order(*ids, prev=prev)
    con = [
        ("contain", "main"),
        ("align_y", ids),
        # spacing chain follows the PICKED order — declaration order would
        # contradict order_x whenever previous positions reorder the row
        ("equal_spacing_x", [a, b, c], "centers"),
        ("order_x", [a, b, c], _gap(stage)),
    ]
    pref = [("stay", i) for i in ids]
    return KiwiSolver().solve(boxes, con, pref, regions.regions, prev)


def _input_op_output(stage, boxes, regions, prev):
    ids = _main_ids(stage, boxes)
    if len(ids) != 3:
        return SolveResult(status="error",
                           diagnostics=[f"input_op_output needs input/op/output (3 main comps), got {ids}"])
    a, b, c = _pick_order(*ids, prev=prev)
    con = [
        ("contain", "main"),
        ("align_y", ids),
        # spacing chain follows the PICKED order — declaration order would
        # contradict order_x whenever previous positions reorder the row
        ("equal_spacing_x", [a, b, c], "centers"),
        ("order_x", [a, b, c], _gap(stage)),
    ]
    pref = [("stay", i) for i in ids]
    return KiwiSolver().solve(boxes, con, pref, regions.regions, prev)


def _operands_result(stage, boxes, regions, prev):
    """Operands in a row ABOVE, result centred BELOW with clearance."""
    top = [cid for cid in _main_ids(stage, boxes) if cid in getattr(stage, "operands", [])] or \
          [cid for cid in _main_ids(stage, boxes) if cid not in getattr(stage, "result", [])]
    result = getattr(stage, "result", None)
    result = [i for i in _main_ids(stage, boxes) if i == result] if result else \
        [cid for cid in _main_ids(stage, boxes) if cid not in top]
    if len(result) != 1 or not top:
        return SolveResult(status="error",
                           diagnostics=[
                               f"operands_result needs N operands + 1 result; got top={top} result={result}. "
                               "Set stage.operands=[ids] and stage.result=id"])
    con = [
        ("contain", "main"),
        ("align_y", top),
        ("min_gap_y", result[0], top[0], _gap(stage)),
    ]
    if len(top) > 1:
        top_order = _pick_order(*top, prev=prev)
        con.append(("order_x", top_order, _gap(stage)))
    pref = [("stay", i) for i in top + result]
    res = KiwiSolver().solve(boxes, con, pref, regions.regions, prev)
    if res.status == "solved":
        # centre the result under the operands' mean x (required, so verify)
        mean_x = sum(res.positions[i][0] for i in top) / len(top)
        res.positions[result[0]] = (mean_x, res.positions[result[0]][1])
        fb = {cid: boxes[cid].moved_to(*p) for cid, p in res.positions.items()}
        viol = _check_required(fb, con, regions.regions)
        if viol:
            res.status = "infeasible"
            res.diagnostics.extend(viol)
    return res


def _main_callout(stage, boxes, regions, prev):
    main_ids = [cid for cid in _main_ids(stage, boxes) if cid not in _annot_ids(stage, boxes)]
    callouts = _annot_ids(stage, boxes)
    if not main_ids or not callouts:
        return SolveResult(status="error",
                           diagnostics=[f"main_callout needs >=1 main + >=1 callout; got {main_ids} + {callouts}"])
    con = [("contain", "main"), ("contain", "annotation", callouts)]
    pref = [("stay", i) for i in main_ids]
    for cid in main_ids:
        pref.append(("center_in", cid, "main", "y"))
    for cid in callouts:
        pref.append(("center_in", cid, "annotation", "xy"))
    return KiwiSolver().solve(boxes, con, pref, regions.regions, prev)


def _equation_explanation(stage, boxes, regions, prev):
    ids = _main_ids(stage, boxes)
    eq = [cid for cid in ids if cid == getattr(stage, "equation", None)]
    rest = [cid for cid in ids if cid not in eq]
    if len(eq) != 1 or len(rest) != 1:
        return SolveResult(status="error",
                           diagnostics=[
                               f"equation_explanation needs exactly 2 main comps; set "
                               f"stage.equation=<id>. Got eq={eq} rest={rest} (ids: {ids})"])
    con = [
        ("contain", "main"),
        ("min_gap_y", rest[0], eq[0], _gap(stage)),
    ]
    targets = {}
    mb = regions.get("main").box
    eq_box, rest_box = boxes[eq[0]], boxes[rest[0]]
    block_h = eq_box.h + _gap(stage) + rest_box.h
    y_top = mb.y + block_h / 2
    targets[eq[0]] = (mb.x, y_top - eq_box.h / 2)
    targets[rest[0]] = (mb.x, y_top - eq_box.h - _gap(stage) - rest_box.h / 2)
    return DirectSolver().solve(boxes, targets, con, regions.regions)


def _custom(stage, boxes, regions, prev):
    if not stage.custom_x or not stage.custom_y:
        return SolveResult(status="error", diagnostics=["custom template needs custom_x/custom_y"])
    targets = {}
    for cid in boxes:
        if cid not in stage.custom_x or cid not in stage.custom_y:
            return SolveResult(status="error",
                               diagnostics=[f"custom layout: no position given for {cid!r}"])
        targets[cid] = (float(stage.custom_x[cid]), float(stage.custom_y[cid]))
    con = [("contain", "main")]  # custom layouts still respect containment
    return DirectSolver().solve(boxes, targets, con, regions.regions)


# ---------------------------------------------------------------- helpers ----

def place_owned(spec, comp_meta, boxes: dict, positions: dict, regions) -> None:
    """Position owned annotations (labels/callouts/notes) relative to their
    owner's SOLVED box — or in the annotation band when the spec assigns them
    there (owner optional; band-centred without one). Shared by SpecScene and
    check-layout so they cannot drift."""
    for cid, meta in comp_meta.items():
        if cid in positions:
            continue  # already placed by a template
        cs = spec.components.get(cid)
        if cs is None or (meta.owner is None and cs.region != "annotation"):
            continue  # not an annotation
        if meta.owner is not None and meta.owner in positions:
            ox, oy = positions[meta.owner]
        else:
            ox = None
        b = boxes[cid]
        if cs.region == "annotation" and "annotation" in regions.regions:
            ab = regions.get("annotation").box
            x = ab.x if ox is None else min(max(ox, ab.left + b.w / 2), ab.right - b.w / 2)
            positions[cid] = (x, ab.y)
            continue
        if ox is None:
            continue
        ob = boxes[meta.owner]
        side = cs.content.get("side", "below")
        if side == "below":
            positions[cid] = (ox, oy - ob.h / 2 - 0.45 - b.h / 2)
        elif side == "above":
            positions[cid] = (ox, oy + ob.h / 2 + 0.45 + b.h / 2)
        elif side == "left":
            positions[cid] = (ox - ob.w / 2 - 0.4 - b.w / 2, oy)
        else:
            positions[cid] = (ox + ob.w / 2 + 0.4 + b.w / 2, oy)


def _gap(stage, default=0.55):
    return float(getattr(stage, "min_gap", default))


def _main_ids(stage, boxes):
    return [cid for cid in boxes]


def _annot_ids(stage, boxes):
    return [cid for cid in boxes if getattr(stage, "callouts", None) and cid in stage.callouts]


def _pick_order(*ids, prev):
    """Stable left-to-right order: previous x positions first, then declaration
    order — so repeated stages don't shuffle columns."""
    def key(i):
        p = prev.get(i)
        return (p[0] if p else 0.0, ids.index(i))
    return sorted(ids, key=key)


def choose_template(n_main: int, roles: list[str] | None = None) -> str:
    """Recommendation helper for AI authoring (spec may still name any template)."""
    roles = [r.lower() for r in (roles or [])]
    if n_main == 1:
        return "single_center"
    if n_main == 2:
        return "two_columns"
    if n_main == 3 and all(r in ("q", "k", "v", "input", "op", "output", "left", "mid", "right") for r in roles):
        return "three_columns" if not roles else "input_op_output"
    if {"equation"} & set(roles):
        return "equation_explanation"
    if {"callout"} & set(roles):
        return "main_callout"
    if {"result"} & set(roles):
        return "operands_result"
    return "two_columns"
