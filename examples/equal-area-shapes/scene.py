"""Equal Area Shapes — a square (side 2) and the circle enclosing the same
area, side by side, labelled. Demonstrates positioning, timing, and labels.
Render with:  animkit preview .   /   animkit render .
"""

import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from manimlib import *
from theme import *

R_EQUAL = 2 / math.sqrt(math.pi)  # pi r^2 = 4  =>  r = 2/sqrt(pi) ~ 1.1284


class EqualAreaShapes(Scene):
    def construct(self):
        # ---- shot 1: title -------------------------------------------------
        title = heading("Same area, different shapes")
        self.play(FadeIn(title, shift=0.3 * DOWN), run_time=DRAW)
        self.wait(IDEA_PAUSE)

        # ---- shot 2: square, left half -------------------------------------
        square = Square(side_length=2)
        square.set_stroke(ACCENT, width=4)
        square.set_fill(ACCENT, opacity=0.25)
        square.move_to(3.2 * LEFT)

        sq_side = label_for(square, "a = 2", DOWN, buff=0.45, math=True, color=INK)
        sq_area = label_for(square, "A = a² = 4", UP, buff=0.45, math=True, color=ACCENT)
        self.play(DrawBorderThenFill(square), run_time=1.2)
        self.play(FadeIn(sq_side, shift=0.1 * UP), Write(sq_area))
        self.wait(IDEA_PAUSE)

        # ---- shot 3: circle, right half ------------------------------------
        circle = Circle(radius=R_EQUAL)
        circle.set_stroke(HILITE, width=4)
        circle.set_fill(HILITE, opacity=0.25)
        circle.move_to(3.2 * RIGHT)

        ci_r = label_for(circle, "r = 2/√π ≈ 1.128", DOWN, buff=0.45, math=True, color=INK)
        ci_area = label_for(circle, "A = πr² = 4", UP, buff=0.45, math=True, color=HILITE)
        self.play(DrawBorderThenFill(circle), run_time=1.2)
        self.play(FadeIn(ci_r, shift=0.1 * UP), Write(ci_area))
        self.wait(IDEA_PAUSE)

        # ---- shot 4: emphasize the shared value ----------------------------
        self.play(
            sq_area.animate.set_color(ACCENT_WARM),
            ci_area.animate.set_color(ACCENT_WARM),
            run_time=0.6,
        )
        self.wait(0.6)
        self.play(
            sq_area.animate.set_color(ACCENT),
            ci_area.animate.set_color(HILITE),
            run_time=0.4,
        )

        # ---- shot 5: closing formula ---------------------------------------
        closer = caption("a² = πr² = 4   —   same area, different shapes")
        self.play(FadeIn(closer, shift=0.2 * UP), run_time=FADE)
        self.wait(SECTION_PAUSE)
        self.play(*[FadeOut(m) for m in self.mobjects])
        self.wait(END_PAUSE)
