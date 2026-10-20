"""Regression checks for the layout/lifecycle/validation system.

Run with the manim venv python (needs manimlib for component construction):
  <manim-venv>\\Scripts\\python.exe tests\\test_layout.py

Logic tests run against a FakeScene (no GPU); rendered verification of the
attention rewrite is a separate preview step (see README).
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from animkit.layout.geom import Box, plan_regions
from animkit.layout.spec import (SceneSpec, StageSpec, ComponentSpec, validate_spec)
from animkit.layout.templates import solve_stage, choose_template
from animkit.layout.components import TextMatrix, Component, make_nav_component
from animkit.layout.registry import StageRegistry, FakeScene


def boxes_of(**dims):
    """Fixed test boxes: id=(w,h)"""
    return {cid: Box(0, 0, w, h) for cid, (w, h) in dims.items()}


def nav_comp_active(reg):
    return reg.components["nav"].parts["nav"].active


def qkv_boxes(wq=2.0, wk=2.0, wv=2.0, h=1.6):
    return {"Q": Box(0, 0, wq, h), "K": Box(0, 0, wk, h), "V": Box(0, 0, wv, h)}


class TestRegions(unittest.TestCase):
    def test_collapse_gives_space_back(self):
        full = plan_regions(16/9, {"title", "nav", "caption"})
        bare = plan_regions(16/9, set())
        self.assertGreater(bare.get("main").box.h, full.get("main").box.h + 1.0)

    def test_no_title_no_band(self):
        p = plan_regions(16/9, {"nav"})
        self.assertNotIn("title", p.regions)
        self.assertIn("title", p.collapsed)

    def test_aspect_changes_width_only(self):
        wide = plan_regions(16/9, set()).get("main").box
        squarish = plan_regions(4/3, set()).get("main").box
        self.assertAlmostEqual(wide.h, squarish.h, places=6)
        self.assertGreater(wide.w, squarish.w)

    def test_annotation_right_side(self):
        p = plan_regions(16/9, {"title", "annotation"}, annotation_side="right")
        main = p.get("main").box
        ann = p.get("annotation").box
        self.assertGreater(ann.right, main.right - 1e-6, "annotation column sits right of main")
        self.assertLess(main.w, plan_regions(16/9, {"title"}).get("main").box.w,
                        "main narrows when the annotation column is present")


class TestThreeColumns(unittest.TestCase):
    def test_equal_centre_spacing_and_centreline(self):
        regions = plan_regions(16/9, {"title", "nav", "caption"})
        stage = StageSpec(id="s", template="three_columns",
                          components={"Q": "entering", "K": "entering", "V": "entering"})
        res = solve_stage(stage, qkv_boxes(), regions, {})
        self.assertEqual(res.status, "solved", res.diagnostics)
        xs = [res.positions[i][0] for i in ("Q", "K", "V")]
        ys = [res.positions[i][1] for i in ("Q", "K", "V")]
        self.assertAlmostEqual(xs[1] - xs[0], xs[2] - xs[1], places=6)
        self.assertEqual(len(set(ys)), 1)
        for (x, y) in res.positions.values():
            mb = regions.get("main").box
            self.assertTrue(mb.left <= x <= mb.right and mb.bottom <= y <= mb.top)

    def test_unequal_widths_keep_centre_spacing(self):
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="three_columns",
                          components={"Q": "entering", "K": "entering", "V": "entering"})
        res = solve_stage(stage, qkv_boxes(wq=3.4, wk=1.4, wv=2.6), regions, {})
        self.assertEqual(res.status, "solved", res.diagnostics)
        xs = [res.positions[i][0] for i in ("Q", "K", "V")]
        self.assertAlmostEqual(xs[1] - xs[0], xs[2] - xs[1], places=6)
        # visible gaps are NOT equal (centre spacing chosen) — verify gap difference
        b = {i: boxes_of(Q=0, K=0, V=0) for i in []}  # noqa: unused
        g1 = (xs[1] - 0.7) - (xs[0] + 1.7)
        g2 = (xs[2] - 1.3) - (xs[1] + 0.7)
        self.assertGreater(abs(g2 - g1), 1e-6)

    def test_deterministic(self):
        regions = plan_regions(16/9, {"nav"})
        stage = StageSpec(id="s", template="three_columns",
                          components={"Q": "entering", "K": "entering", "V": "entering"})
        r1 = solve_stage(stage, qkv_boxes(), regions, {})
        r2 = solve_stage(stage, qkv_boxes(), regions, {})
        self.assertEqual(r1.positions, r2.positions)

    def test_prev_positions_stable(self):
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="three_columns",
                          components={"Q": "persistent", "K": "persistent", "V": "persistent"})
        prev = {"Q": (-4.0, 0.5), "K": (0.0, 0.5), "V": (4.0, 0.5)}
        res = solve_stage(stage, qkv_boxes(), regions, prev)
        self.assertEqual(res.status, "solved", res.diagnostics)
        for cid, p in prev.items():
            self.assertAlmostEqual(res.positions[cid][0], p[0], places=3,
                                   msg="unchanged comps should keep their positions")

    def test_two_columns_reversed_order_not_contradictory(self):
        """Regression: two_columns used to emit min_gap_x in declaration order
        AND order_x in picked order — contradictory when reversed."""
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="two_columns",
                          components={"X": "persistent", "A": "entering"})
        prev = {"X": (3.26, -0.85)}          # X was on the RIGHT last stage
        res = solve_stage(stage, boxes_of(X=(2.6, 2.0), A=(2.6, 2.0)), regions, prev)
        self.assertEqual(res.status, "solved", res.diagnostics)
        self.assertGreater(res.positions["X"][0], res.positions["A"][0],
                           "X keeps its previous side (stable order)")

    def test_spacing_chain_follows_picked_order(self):
        """Regression: equal_spacing chained declaration order while order_x
        used picked order — contradictory when a persistent comp changes side."""
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="input_op_output",
                          components={"X": "persistent", "A": "entering", "Xp": "entering"})
        prev = {"X": (2.5, 0.0), "A": (-2.5, 0.0)}   # order becomes A < Xp < X
        res = solve_stage(stage, boxes_of(X=(2.6, 2.0), A=(2.6, 2.0), Xp=(2.8, 2.1)),
                          regions, prev)
        self.assertEqual(res.status, "solved", res.diagnostics)
        xs = {k: v[0] for k, v in res.positions.items()}
        self.assertLess(xs["A"], xs["Xp"] < xs["X"])
        self.assertAlmostEqual(xs["Xp"] - xs["A"], xs["X"] - xs["Xp"], places=6)

    def test_infeasible_reports_diagnostically(self):
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="three_columns",
                          components={"Q": "entering", "K": "entering", "V": "entering"})
        huge = qkv_boxes(wq=6.0, wk=6.0, wv=6.0, h=7.0)
        res = solve_stage(stage, huge, regions, {})
        self.assertEqual(res.status, "infeasible")
        self.assertTrue(res.diagnostics, "infeasible solves must explain themselves")

    def test_input_op_output_never_stacks(self):
        """Regression: equal centre spacing alone is satisfiable stacked;
        the template must also order left-to-right with a real gap."""
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="input_op_output",
                          components={"A": "entering", "op": "entering", "out": "entering"})
        res = solve_stage(stage, boxes_of(A=(2.0, 2.4), op=(2.0, 2.4), out=(2.0, 2.4)),
                          regions, {})
        self.assertEqual(res.status, "solved", res.diagnostics)
        b = {cid: Box(*res.positions[cid], 2.0, 2.4) for cid in res.positions}
        self.assertGreaterEqual(b["op"].gap_x(b["A"]), 0.0)
        self.assertGreaterEqual(b["out"].gap_x(b["op"]), 0.0)

    def test_operands_result_separates_operands(self):
        """Regression: operands on the top row must not overlap each other."""
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="operands_result",
                          components={"A": "entering", "V": "entering", "Out": "entering"},
                          operands=["A", "V"], result="Out")
        res = solve_stage(stage, boxes_of(A=(2.2, 2.9), V=(2.1, 2.6), Out=(2.4, 2.2)),
                          regions, {})
        self.assertEqual(res.status, "solved", res.diagnostics)
        b = {cid: Box(*res.positions[cid], w, h)
             for cid, (w, h) in {"A": (2.2, 2.9), "V": (2.1, 2.6), "Out": (2.4, 2.2)}.items()}
        self.assertGreaterEqual(b["V"].gap_x(b["A"]), 0.0, "operands must be side by side")


class TestOtherTemplates(unittest.TestCase):
    def test_single_center(self):
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="single_center", components={"m": "entering"})
        res = solve_stage(stage, boxes_of(m=(3, 2)), regions, {})
        mb = regions.get("main").box
        self.assertEqual(res.status, "solved", res.diagnostics)
        self.assertAlmostEqual(res.positions["m"][0], mb.x, places=6)

    def test_operands_result(self):
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="operands_result",
                          components={"A": "entering", "V": "entering", "Out": "entering"},
                          operands=["A", "V"], result="Out")
        res = solve_stage(stage, boxes_of(A=(2, 1.6), V=(2, 1.6), Out=(2.4, 1.8)), regions, {})
        self.assertEqual(res.status, "solved", res.diagnostics)
        self.assertGreater(res.positions["Out"][1], res.positions["A"][1] - 3)
        # result centred under operands
        mean_x = (res.positions["A"][0] + res.positions["V"][0]) / 2
        self.assertAlmostEqual(res.positions["Out"][0], mean_x, places=6)

    def test_equation_explanation(self):
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="equation_explanation",
                          components={"eq": "entering", "expl": "entering"},
                          equation="eq")
        res = solve_stage(stage, boxes_of(eq=(6, 0.8), expl=(5, 1.0)), regions, {})
        self.assertEqual(res.status, "solved", res.diagnostics)
        self.assertGreater(res.positions["eq"][1], res.positions["expl"][1])

    def test_custom_escape_hatch(self):
        regions = plan_regions(16/9, set())
        stage = StageSpec(id="s", template="custom",
                          components={"a": "entering", "b": "entering"},
                          custom_x={"a": -4.0, "b": 4.0}, custom_y={"a": 0.0, "b": 0.0})
        res = solve_stage(stage, boxes_of(a=(2, 2), b=(2, 2)), regions, {})
        self.assertEqual(res.status, "solved", res.diagnostics)
        self.assertEqual(res.positions["a"], (-4.0, 0.0))


class TestBrackets(unittest.TestCase):
    def test_ticks_point_inward(self):
        tm = TextMatrix([[1, 0], [0, 1]], nd=0)
        left, right = tm.brackets[0], tm.brackets[1]
        rows_left, rows_right = tm.rows.get_left()[0], tm.rows.get_right()[0]
        # left bracket = [vertical stroke, top tick, bottom tick]; ticks run
        # from the stroke toward +x (inward, toward the entries)
        stroke, top_tick, bot_tick = left
        self.assertLess(stroke.get_x(), rows_left + 1e-6, "left bracket sits left of entries")
        self.assertGreater(top_tick.get_end()[0], top_tick.get_start()[0],
                           "left bracket's top tick must point inward (+x)")
        self.assertGreater(bot_tick.get_end()[0], bot_tick.get_start()[0],
                           "left bracket's bottom tick must point inward (+x)")
        # right bracket mirrored: ticks point toward -x (inward)
        stroke_r, top_r, bot_r = right
        self.assertGreater(stroke_r.get_x(), rows_right - 1e-6, "right bracket sits right of entries")
        self.assertLess(top_r.get_end()[0], top_r.get_start()[0],
                        "right bracket's top tick must point inward (-x)")
        self.assertLess(bot_r.get_end()[0], bot_r.get_start()[0],
                        "right bracket's bottom tick must point inward (-x)")

    def test_addressable_parts(self):
        tm = TextMatrix([[1.5, 2.25], [0, 1]], nd=2)
        self.assertEqual(len(tm.get_rows()), 2)
        self.assertEqual(len(tm.get_columns()), 2)
        self.assertEqual(len(tm.get_entries()), 4)


class TestSpecValidation(unittest.TestCase):
    def _base(self):
        return SceneSpec(name="t", stages=[], components={})

    def test_unknown_template(self):
        spec = self._base()
        spec.components["m"] = ComponentSpec(id="m", ctype="matrix",
                                             content={"values": [[1, 2], [3, 4]]})
        spec.stages.append(StageSpec(id="s1", template="nope", components={"m": "entering"}))
        errors, _ = validate_spec(spec)
        self.assertTrue(any("template" in e for e in errors))

    def test_ragged_matrix_rejected(self):
        spec = self._base()
        spec.components["m"] = ComponentSpec(id="m", ctype="matrix",
                                             content={"values": [[1, 2], [3]]})
        spec.stages.append(StageSpec(id="s1", template="single_center", components={"m": "entering"}))
        errors, _ = validate_spec(spec)
        self.assertTrue(any("same length" in e for e in errors))

    def test_reentry_rejected(self):
        spec = self._base()
        spec.components["m"] = ComponentSpec(id="m", ctype="text", content={"text": "x"})
        spec.stages += [
            StageSpec(id="s1", template="single_center", components={"m": "leaving"}),
            StageSpec(id="s2", template="single_center", components={"m": "entering"}),
        ]
        errors, _ = validate_spec(spec)
        self.assertTrue(any("re-enters" in e for e in errors))

    def test_permitted_overlap_must_reference_stage(self):
        spec = self._base()
        spec.components.update({
            "a": ComponentSpec(id="a", ctype="text", content={"text": "a"}),
            "b": ComponentSpec(id="b", ctype="text", content={"text": "b"}),
        })
        spec.stages.append(StageSpec(id="s1", template="two_columns",
                                     components={"a": "entering", "b": "entering"},
                                     permitted_overlaps=[("a", "ghost")]))
        errors, _ = validate_spec(spec)
        self.assertTrue(any("permitted_overlap" in e for e in errors))


class TestRegistryLifecycle(unittest.TestCase):
    def _spec(self):
        spec = SceneSpec(name="t")
        spec.components.update({
            "nav": ComponentSpec(id="nav", ctype="nav",
                                 content={"stages": ["One", "Two"], "active": 0}),
            "m": ComponentSpec(id="m", ctype="matrix",
                               content={"values": [[1, 0], [0, 1]], "nd": 0, "label": "M"}),
            "note": ComponentSpec(id="note", ctype="text", content={"text": "temp note"},
                                  owner="m"),
        })
        spec.stages = [
            StageSpec(id="s1", template="single_center",
                      components={"nav": "persistent", "m": "entering", "note": "temporary"},
                      transition={"nav": "static"}, timing={"hold": 0.1}),
            StageSpec(id="s2", template="single_center",
                      components={"nav": "persistent", "m": "leaving"},
                      transition={"nav": "static"}, timing={"hold": 0.1}),
        ]
        return spec

    def test_temp_and_owned_children_removed(self):
        spec = self._spec()
        reg = StageRegistry(spec)
        scene = FakeScene()
        stage1 = spec.stages[0]
        # stub animations: registry calls FadeOut/Write etc. — FakeScene handles
        # FadeOut removal; entering uses FadeIn (identity object add).
        positions = {"nav": (0.0, 3.0), "m": (0.0, 0.0), "note": (2.0, -2.0)}
        reg.apply_stage(scene, stage1, positions, {"enter": 0.1, "move": 0.1, "exit": 0.1, "hold": 0.1})
        self.assertIn("m", reg.components)
        self.assertIn("note", reg.components)
        # note is owned/attached: it lives inside its own group, registered too
        reg.end_stage(scene, stage1)
        self.assertNotIn("note", reg.components, "temporary must be removed at stage end")
        stage2 = spec.stages[1]
        reg.apply_stage(scene, stage2, {"nav": (0.0, 3.0), "m": (0.0, 0.0)},
                        {"enter": 0.1, "move": 0.1, "exit": 0.1, "hold": 0.1})
        self.assertNotIn("m", reg.components, "leaving must drop the registry entry")
        reg.end_stage(scene, stage2)
        self.assertEqual(reg.components.keys(), {"nav"})

    def test_repeated_transitions_stay_clean(self):
        spec = self._spec()
        spec.stages = [
            StageSpec(id=f"s{i}", template="single_center",
                      components={"nav": "persistent", "m": "changing" if i else "entering"},
                      transition={"m": "move", "nav": "static"},
                      timing={"hold": 0.05}) for i in range(4)
        ]
        reg = StageRegistry(spec)
        scene = FakeScene()
        for stage in spec.stages:
            reg.apply_stage(scene, stage, {"nav": (0.0, 3.0), "m": (1.5 * (spec.stages.index(stage) - 1.5), 0.0)},
                            {"enter": 0.1, "move": 0.1, "exit": 0.1, "hold": 0.05})
            reg.end_stage(scene, stage)
        self.assertEqual(set(reg.components), {"nav", "m"})
        self.assertEqual(reg.stale_report, [])
        # m moved/entered in every stage; nav clamped to its last chip with a note
        self.assertEqual(nav_comp_active(reg), 1)
        self.assertTrue(any("clamping" in i for s in reg.stage_log for i in s["issues"]))

    def test_unmentioned_components_leave_implicitly(self):
        """Regression: a component absent from a later stage must leave —
        nothing lingers across an unmentioned stage boundary."""
        spec = self._spec()
        spec.components["m2"] = ComponentSpec(id="m2", ctype="matrix",
                                              content={"values": [[5]], "nd": 0})
        spec.stages = [
            StageSpec(id="s1", template="single_center",
                      components={"nav": "persistent", "m": "entering", "m2": "entering"},
                      transition={"nav": "static"}, timing={"hold": 0.05}),
            StageSpec(id="s2", template="single_center",
                      components={"nav": "persistent", "m": "entering"},
                      transition={"nav": "static", "m": "fade_in"}, timing={"hold": 0.05}),
        ]
        reg = StageRegistry(spec)
        scene = FakeScene()
        for stage in spec.stages:
            reg.apply_stage(scene, stage,
                            {"nav": (0, 3), "m": (0, 0), "m2": (3, 0)},
                            {"enter": 0.1, "move": 0.1, "exit": 0.1, "hold": 0.05})
            reg.end_stage(scene, stage)
        self.assertEqual(set(reg.components), {"nav", "m"})
        self.assertTrue(any("implicit leave: ['m2']" in a
                            for s in reg.stage_log for a in s["actions"]))

    def test_nav_tracks_stages(self):
        spec = self._spec()
        reg = StageRegistry(spec)
        scene = FakeScene()
        stage1, stage2 = spec.stages
        reg.apply_stage(scene, stage1, {"nav": (0, 3), "m": (0, 0), "note": (2, -2)},
                        {"enter": 0.1, "move": 0.1, "exit": 0.1, "hold": 0.1})
        nav_comp = reg.components["nav"]
        self.assertEqual(nav_comp.parts["nav"].active, 0)
        reg.end_stage(scene, stage1)
        reg.apply_stage(scene, stage2, {"nav": (0, 3), "m": (0, 0)},
                        {"enter": 0.1, "move": 0.1, "exit": 0.1, "hold": 0.1})
        self.assertEqual(nav_comp.parts["nav"].active, 1)


class TestChooser(unittest.TestCase):
    def test_recommendations(self):
        self.assertEqual(choose_template(1), "single_center")
        self.assertEqual(choose_template(2), "two_columns")
        self.assertEqual(choose_template(3, ["input", "op", "output"]), "input_op_output")
        self.assertEqual(choose_template(3, ["q", "k", "v"]), "input_op_output")


if __name__ == "__main__":
    unittest.main(verbosity=2)
