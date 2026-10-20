"""Linear Transform 2D — a shear matrix M = [[1,1],[0,1]] acting on the plane.
Basis vectors, the unit square, and a sample vector all land exactly where
linear algebra says (positions computed from M, never hand-placed).
Render with:  animkit preview .   /   animkit render .
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np

from manimlib import *
from theme import *

M = np.array([[1.0, 1.0],
              [0.0, 1.0]])          # shear: det = 1, area preserved
I_HAT_LANDS = M @ np.array([1, 0])  # (1, 0)
J_HAT_LANDS = M @ np.array([0, 1])  # (1, 1)
V = np.array([2.0, 1.0])
V_LANDS = M @ V                     # (3, 1)


def coord_txt(v):
    return f"({v[0]:g}, {v[1]:g})"


class LinearTransform2d(Scene):
    def construct(self):
        # ---- shot 1: the grid and its basis -------------------------------
        title = heading("A linear transformation, visually")
        plane = NumberPlane(
            x_range=(-7, 7, 1), y_range=(-4, 4, 1),
            background_line_style=dict(stroke_color=BLUE_D, stroke_width=2, stroke_opacity=0.8),
        )
        i_hat = Vector(I_HAT_LANDS * 0 + np.array([1, 0]))  # starts at (1,0)
        i_hat.set_stroke(ACCENT_WARM, width=6)
        j_hat = Vector(np.array([0, 1]))
        j_hat.set_stroke(HILITE, width=6)
        i_lab = pin_label(i_hat, "î", UP + LEFT, buff=0.1, math=True, color=ACCENT_WARM, size=LABEL)
        j_lab = pin_label(j_hat, "ĵ", UP + RIGHT, buff=0.1, math=True, color=HILITE, size=LABEL)

        square = Polygon(ORIGIN, [1, 0, 0], [1, 1, 0], [0, 1, 0])
        square.set_stroke(INK, width=2)
        square.set_fill(INK_MUTED, opacity=0.2)

        self.play(FadeIn(plane, lag_ratio=0.05), run_time=1.2)
        self.play(GrowFromPoint(i_hat, ORIGIN), GrowFromPoint(j_hat, ORIGIN), run_time=1.0)
        self.play(FadeIn(i_lab), FadeIn(j_lab), DrawBorderThenFill(square), run_time=0.8)
        self.play(FadeIn(title, shift=0.3 * DOWN), run_time=FADE)
        self.wait(1.5)

        # ---- shot 2: name the matrix --------------------------------------
        mat = matrix_label([["1", "1"], ["0", "1"]], size=BODY)
        mat.to_corner(UR, buff=0.6)
        mat_lab = label_for(mat, "M", LEFT, buff=0.3, math=True, color=INK)
        self.play(FadeIn(mat, scale=0.7), FadeIn(mat_lab), run_time=0.8)
        self.wait(1.5)

        # ---- shot 3: shear the whole plane --------------------------------
        v_vec = Vector(V)
        v_vec.set_stroke(PLUM, width=6)
        v_lab = pin_label(v_vec, "v = (2, 1)", DOWN + LEFT, buff=0.1, math=True, color=PLUM, size=LABEL)
        self.play(GrowFromPoint(v_vec, ORIGIN), FadeIn(v_lab), run_time=0.8)
        self.wait(1.25)

        i_lab_clear = i_lab.copy().clear_updaters()
        j_lab_clear = j_lab.copy().clear_updaters()
        v_lab_clear = v_lab.copy().clear_updaters()
        self.play(
            FadeOut(title),
            plane.animate.apply_matrix(M),
            square.animate.apply_matrix(M),
            i_hat.animate.apply_matrix(M),
            j_hat.animate.apply_matrix(M),
            v_vec.animate.apply_matrix(M),
            run_time=3.0,
        )
        i_lab.clear_updaters(); j_lab.clear_updaters(); v_lab.clear_updaters()
        i_land = label_for(i_hat, f"î → {coord_txt(I_HAT_LANDS)}", UP + LEFT, buff=0.15, math=True, color=ACCENT_WARM, size=LABEL)
        j_land = label_for(j_hat, f"ĵ → {coord_txt(J_HAT_LANDS)}", UP + RIGHT, buff=0.15, math=True, color=HILITE, size=LABEL)
        v_land = label_for(v_vec, f"v → {coord_txt(V_LANDS)}", DOWN + LEFT, buff=0.15, math=True, color=PLUM, size=LABEL)
        self.play(
            ReplacementTransform(i_lab_clear, i_land),
            ReplacementTransform(j_lab_clear, j_land),
            ReplacementTransform(v_lab_clear, v_land),
            run_time=0.8,
        )
        self.wait(1.5)

        # ---- shot 5: the rule ----------------------------------------------
        rule = caption("Mv = x·(new î) + y·(new ĵ)    det M = 1: areas preserved")
        self.play(FadeIn(rule, shift=0.2 * UP), run_time=FADE)
        self.wait(2.5)
        self.play(*[FadeOut(m) for m in self.mobjects])
        self.wait(END_PAUSE)
