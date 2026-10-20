"""Layout solvers.

Backend interface: given fixed measured boxes, region bounds, and constraints,
return solved centre positions + status + actionable diagnostics.

Two backends:
  DirectSolver  — arithmetic placement for simple templates (clear, fast).
  KiwiSolver    — kiwisolver for coupled linear constraint systems
                  (equal centre spacing, shared centrelines, order+gaps).

Dimensions are fixed during a solve. If a solve is infeasible the diagnostics
name the violated constraints and by how much; the caller may uniformly
resize, re-measure, and re-solve (see templates.try_fit).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from animkit.layout.geom import Box, Region, EPS

# Constraint tuples (see spec.py docstring). Everything is expressed on
# centres of fixed-size boxes, so the system is linear in (x, y).


@dataclass
class SolveResult:
    positions: dict[str, tuple[float, float]] = field(default_factory=dict)
    status: str = "solved"                    # solved | infeasible | error
    diagnostics: list[str] = field(default_factory=list)
    backend: str = ""


def _check_required(boxes: dict[str, Box], constraints: list, regions: dict[str, Region]) -> list[str]:
    """Post-solve verification of every required constraint. Returns violation
    messages (empty = all satisfied within tolerance)."""
    tol = 1e-6
    violations = []
    for con in constraints:
        kind = con[0]
        if kind == "contain":
            region_name = con[1]
            ids = con[2] if len(con) > 2 else None
            r = regions.get(region_name)
            if r is None:
                continue
            for cid, b in boxes.items():
                if ids is not None and cid not in ids:
                    continue
                if not r.box.contains(b):
                    violations.append(
                        f"containment {cid!r} in {region_name!r}: box "
                        f"x[{b.left:.2f},{b.right:.2f}] y[{b.bottom:.2f},{b.top:.2f}] "
                        f"escapes x[{r.box.left:.2f},{r.box.right:.2f}] y[{r.box.bottom:.2f},{r.box.top:.2f}]"
                    )
        elif kind == "align_y":
            _, ids = con[0], con[1]
            ys = [boxes[i].y for i in ids if i in boxes]
            if ys and (max(ys) - min(ys)) > 1e-3 + tol:
                violations.append(f"align_y {ids}: spread {max(ys)-min(ys):.3f} > 0.001")
        elif kind == "equal_spacing_x":
            _, ids, mode = con[0], con[1], con[2]
            seq = [boxes[i] for i in ids if i in boxes]
            if len(seq) >= 3:
                if mode == "centers":
                    gaps = [seq[i + 1].x - seq[i].x for i in range(len(seq) - 1)]
                else:  # gaps between visible edges
                    gaps = [seq[i + 1].gap_x(seq[i]) for i in range(len(seq) - 1)]
                spread = max(gaps) - min(gaps)
                if spread > 1e-3 + tol:
                    violations.append(f"equal_spacing_x {ids} ({mode}): spread {spread:.3f} > 0.001")
        elif kind == "min_gap_x":
            _, a, b, g = con
            if a in boxes and b in boxes and boxes[a].gap_x(boxes[b]) < g - 1e-3:
                violations.append(f"min_gap_x {a}->{b}: gap {boxes[a].gap_x(boxes[b]):.3f} < {g:.3f}")
        elif kind == "min_gap_y":
            _, a, b, g = con
            if a in boxes and b in boxes and boxes[a].gap_y(boxes[b]) < g - 1e-3:
                violations.append(f"min_gap_y {a}->{b}: gap {boxes[a].gap_y(boxes[b]):.3f} < {g:.3f}")
        elif kind == "order_x":
            _, ids, g = con
            for i in range(len(ids) - 1):
                a, b = ids[i], ids[i + 1]
                if a in boxes and b in boxes and boxes[b].left - boxes[a].right < g - 1e-3:
                    violations.append(f"order_x {a}<{b}: gap {boxes[b].left - boxes[a].right:.3f} < {g:.3f}")
    return violations


class DirectSolver:
    """Arithmetic placement. Consumes a narrow instruction set produced by
    simple templates: explicit target positions and a few sanity constraints."""

    name = "direct"

    def solve(self, boxes: dict[str, Box], targets: dict[str, tuple[float, float]],
              constraints: list, regions: dict[str, Region]) -> SolveResult:
        placed = {cid: (targets[cid][0], targets[cid][1]) for cid in boxes if cid in targets}
        missing = [cid for cid in boxes if cid not in targets]
        result = SolveResult(positions=placed, backend=self.name)
        if missing:
            result.status = "error"
            result.diagnostics.append(f"DirectSolver received no target for: {missing}")
            return result
        final_boxes = {cid: boxes[cid].moved_to(*pos) for cid, pos in placed.items()}
        violations = _check_required(final_boxes, constraints, regions)
        if violations:
            result.status = "infeasible"
            result.diagnostics.extend(violations)
            result.diagnostics.append(
                "direct placement violates constraints — shrink content, change template, "
                "or switch this stage to the kiwi backend"
            )
        return result


class KiwiSolver:
    """Coupled linear constraints via kiwisolver (installed with matplotlib).

    Required constraints use kiwi's REQUIRED strength; preferred ones
    (stay near previous position, centre in region) use weak strengths so
    required always wins. Post-solve verification reports anything violated.
    """

    name = "kiwi"

    def solve(self, boxes: dict[str, Box], constraints: list, preferred: list,
              regions: dict[str, Region], prev: dict[str, tuple[float, float]] | None = None
              ) -> SolveResult:
        import kiwisolver as kiwi
        result = self._solve_inner(boxes, constraints, preferred, regions, prev, kiwi)
        if result is not None:
            return result  # infeasible with diagnostics
        return self._verify(boxes, constraints, regions, prev, kiwi)

    def _solve_inner(self, boxes, constraints, preferred, regions, prev, kiwi):
        """Build constraints and solve. Returns an infeasible SolveResult early
        if kiwi raises UnsatisfiableConstraint during construction/solve."""
        try:
            self._build_and_run(boxes, constraints, preferred, regions, prev, kiwi)
        except kiwi.UnsatisfiableConstraint:
            return SolveResult(
                status="infeasible",
                diagnostics=[
                    "kiwi could not satisfy the required constraints together",
                    *self._conflict_hint(boxes, regions),
                ],
                backend=self.name,
            )
        return None

    def _build_and_run(self, boxes, constraints, preferred, regions, prev, kiwi) -> None:
        solver = kiwi.Solver()
        vars_: dict[str, dict] = {}
        for cid, box in boxes.items():
            vars_[cid] = {
                "x": kiwi.Variable(f"{cid}.x"),
                "y": kiwi.Variable(f"{cid}.y"),
            }
        STRONG = kiwi.strength.strong
        WEAK = kiwi.strength.weak
        REQUIRED = kiwi.strength.required

        def add(expr, op, rhs, strength=REQUIRED):
            if op == "==":
                c = expr == rhs
            elif op == "<=":
                c = expr <= rhs
            else:
                c = expr >= rhs
            solver.addConstraint(c | strength)

        # containment in the frame-ish union of regions: constrain against the
        # region named by each component's "contain" constraint
        for con in constraints:
            kind = con[0]
            if kind == "contain":
                region = regions[con[1]]
                ids = con[2] if len(con) > 2 else list(boxes)
                for cid in ids:
                    if cid not in boxes:
                        continue
                    b, r = boxes[cid], region.box
                    add(vars_[cid]["x"] - b.w / 2, ">=", r.left)
                    add(vars_[cid]["x"] + b.w / 2, "<=", r.right)
                    add(vars_[cid]["y"] - b.h / 2, ">=", r.bottom)
                    add(vars_[cid]["y"] + b.h / 2, "<=", r.top)
            elif kind == "align_y":
                _, ids = con[0], con[1]
                ids = [i for i in ids if i in boxes]
                for cid in ids[1:]:
                    add(vars_[cid]["y"], "==", vars_[ids[0]]["y"])
            elif kind == "equal_spacing_x":
                _, ids, mode = con[0], con[1], con[2]
                ids = [i for i in ids if i in boxes]
                for i in range(len(ids) - 2):
                    a, b, c = ids[i], ids[i + 1], ids[i + 2]
                    if mode == "centers":
                        add(vars_[b]["x"] - vars_[a]["x"], "==", vars_[c]["x"] - vars_[b]["x"])
                    else:  # equal visible gaps: centre distance differs by half-width sums
                        wa = boxes[a].w / 2 + boxes[b].w / 2
                        wb = boxes[b].w / 2 + boxes[c].w / 2
                        add(vars_[b]["x"] - vars_[a]["x"] - wa, "==", vars_[c]["x"] - vars_[b]["x"] - wb)
            elif kind == "min_gap_x":
                _, a, b, g = con
                if a in boxes and b in boxes:
                    add(vars_[b]["x"] - vars_[a]["x"], ">=", boxes[a].w / 2 + boxes[b].w / 2 + g)
            elif kind == "min_gap_y":
                _, a, b, g = con
                if a in boxes and b in boxes:
                    add(vars_[b]["y"] - vars_[a]["y"], ">=", boxes[a].h / 2 + boxes[b].h / 2 + g)
            elif kind == "order_x":
                _, ids, g = con
                ids = [i for i in ids if i in boxes]
                for i in range(len(ids) - 1):
                    a, b = ids[i], ids[i + 1]
                    add(vars_[b]["x"] - vars_[a]["x"], ">=", boxes[a].w / 2 + boxes[b].w / 2 + g)

        # preferred: stay near previous / near given point; centre in region
        for pref in preferred:
            kind = pref[0]
            if kind == "stay" and prev:
                cid = pref[1]
                if cid in boxes and cid in prev:
                    add(vars_[cid]["x"], "==", prev[cid][0], WEAK)
                    add(vars_[cid]["y"], "==", prev[cid][1], WEAK)
            elif kind == "near":
                _, cid, px, py = pref
                if cid in boxes:
                    add(vars_[cid]["x"], "==", px, WEAK)
                    add(vars_[cid]["y"], "==", py, WEAK)
            elif kind == "center_in":
                _, cid, region_name, axes = pref
                if cid in boxes and region_name in regions:
                    r = regions[region_name].box
                    if "x" in axes:
                        add(vars_[cid]["x"], "==", (r.left + r.right) / 2, WEAK)
                    if "y" in axes:
                        add(vars_[cid]["y"], "==", (r.bottom + r.top) / 2, WEAK)

        # give the system an anchor: pull everything weakly toward region centres
        for cid in boxes:
            contain_region = next(
                (c[1] for c in constraints if c[0] == "contain" and (len(c) < 3 or cid in c[2])),
                None,
            )
            if contain_region and contain_region in regions:
                r = regions[contain_region].box
                add(vars_[cid]["x"], "==", (r.left + r.right) / 2, WEAK)
                add(vars_[cid]["y"], "==", (r.bottom + r.top) / 2, WEAK)
            else:
                add(vars_[cid]["x"], "==", 0.0, WEAK)
                add(vars_[cid]["y"], "==", 0.0, WEAK)

        solver.updateVariables()
        try:
            positions = {cid: (v["x"].value(), v["y"].value()) for cid, v in vars_.items()}
        except Exception:  # pragma: no cover
            positions = {}

        if not positions or not all(
            all(_finite(v) for v in p) for p in positions.values()
        ):
            return None

        self._positions = positions

    def _verify(self, boxes, constraints, regions, prev, kiwi) -> SolveResult:
        positions = getattr(self, "_positions", None)
        if not positions:
            return SolveResult(
                status="infeasible",
                diagnostics=[
                    "kiwi could not satisfy the required constraints together",
                    *self._conflict_hint(boxes, regions),
                ],
                backend=self.name,
            )

        final_boxes = {cid: boxes[cid].moved_to(*pos) for cid, pos in positions.items()}
        violations = _check_required(final_boxes, constraints, regions)
        result = SolveResult(positions=positions, backend=self.name)
        if violations:
            result.status = "infeasible"
            result.diagnostics.extend(violations)
            total_needed = sum(boxes[c].w for c in boxes)
            widest_region = max((r.box.w for r in regions.values()), default=0)
            if total_needed > widest_region:
                result.diagnostics.append(
                    f"content widths sum to {total_needed:.2f} but the widest region is "
                    f"{widest_region:.2f} — shrink content, split stages, or use 'compact' density"
                )
        return result

    def _conflict_hint(self, boxes: dict[str, Box], regions: dict[str, Region]) -> list[str]:
        total_w = sum(b.w for b in boxes.values())
        total_h = max((b.h for b in boxes.values()), default=0)
        main = regions.get("main")
        hints = []
        if main:
            mb = main.box
            n = len(boxes)
            hints.append(f"{n} components totalling {total_w:.2f} units wide "
                         f"(main region is {mb.w:.2f} wide, {mb.h:.2f} tall)")
            if total_w + 0.55 * (n - 1) > mb.w:
                hints.append("widths + required gaps exceed the main width — "
                             "shrink entry_size/font_size, drop a component, "
                             "split the stage, or set density='compact'")
        return hints


def _finite(v) -> bool:
    v = float(v)
    return v == v and abs(v) != float("inf")
