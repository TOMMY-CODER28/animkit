"""Transformer Attention — scaled dot-product attention, algebraically, on a
concrete 3-token example. Every displayed number is computed by numpy at
import time (with asserts), so the animation *is* the math.
Pipeline: Embed -> Project -> Score -> Softmax -> Mix.
Render with:  animkit preview .   /   animkit render .
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np

from manimlib import *
from theme import *

# ---------------- the math (single source of truth for every visual) --------
X = np.array([[1.0, 0.0],
              [0.0, 1.0],
              [1.0, 1.0]])            # tokens a, b, c; d_model = 2
W_Q = np.eye(2)
W_K = np.array([[1.0, 1.0],
                [0.0, 1.0]])
W_V = np.array([[2.0, 0.0],
                [0.0, 1.0]])
Q, K, V = X @ W_Q, X @ W_K, X @ W_V
D_K = 2.0
S = Q @ K.T                          # raw scores
S_SC = S / np.sqrt(D_K)              # scaled
A = np.exp(S_SC) / np.exp(S_SC).sum(axis=1, keepdims=True)   # row softmax
OUT = A @ V                          # attention output

# --- asserts: the relations the animation claims ---
assert np.allclose(Q, X) and np.allclose(K, X @ W_K) and np.allclose(V, X @ W_V)
assert S[2, 2] == 3.0                                  # exemplar dot product
assert np.allclose(A.sum(axis=1), 1.0, atol=1e-12)     # rows sum to one
assert np.allclose(OUT[0], A[0] @ V, atol=1e-12)       # output is weighted mix
assert A[2, 2] > 0.5                                   # token 3 attends to itself

STAGES = ["Embed", "Project", "Score", "Softmax", "Mix"]
CHIP_W, CHIP_H, CHIP_GAP = 2.2, 0.6, 0.4

C_Q, C_K, C_V = ACCENT, HILITE, ACCENT_WARM   # color code: Q blue, K teal, V yellow


def fmt(v, nd=2):
    """Format a float for a matrix cell: integers without decimals."""
    if nd == 0 or float(v).is_integer():
        return f"{v:g}"
    return f"{v:.{nd}f}"


class TransformerAttention(Scene):
    def construct(self):
        title = heading("Attention, algebraically")
        chips, cursor = self.build_stage_row()

        self.play(FadeIn(title, shift=0.3 * DOWN), run_time=DRAW)
        self.play(LaggedStart(*[FadeIn(c, scale=0.8) for c in chips], lag_ratio=0.1),
                  run_time=1.0)
        self.play(FadeIn(cursor), run_time=FADE)
        self.wait(IDEA_PAUSE)

        # ================= stage 1: Embed =====================================
        self.move_cursor(cursor, chips, 0)
        self.play(FadeOut(title))
        x_mat, x_cells = self.num_matrix(X, INK, nd=0)
        x_mat.move_to(ORIGIN + 0.3 * UP)
        x_lab = label_for(x_mat, "X", LEFT, buff=0.35, math=True, color=INK, size=HEADING)
        tok_labs = VGroup(*[
            pin_label(x_cells[i], t, LEFT, buff=0.3, size=LABEL, color=INK_MUTED)
            for i, t in enumerate(("a", "b", "c"))
        ])
        cap = caption("X: 3 tokens, each a 2-vector")
        self.play(FadeIn(x_mat, scale=0.85), FadeIn(x_lab), run_time=1.0)
        self.play(FadeIn(tok_labs), FadeIn(cap), run_time=FADE)
        self.wait(IDEA_PAUSE)

        # ================= stage 2: Project ===================================
        self.move_cursor(cursor, chips, 1)
        qm, _ = self.num_matrix(Q, C_Q, nd=0);  qm.scale(0.8).move_to(4.6 * LEFT + 0.2 * UP)
        km, _ = self.num_matrix(K, C_K, nd=0);  km.scale(0.8).move_to(ORIGIN + 0.2 * UP)
        vm, _ = self.num_matrix(V, C_V, nd=0);  vm.scale(0.8).move_to(4.6 * RIGHT + 0.2 * UP)
        ql = label_for(qm, "Q", UP, buff=0.25, math=True, color=C_Q, size=HEADING)
        kl = label_for(km, "K", UP, buff=0.25, math=True, color=C_K, size=HEADING)
        vl = label_for(vm, "V", UP, buff=0.25, math=True, color=C_V, size=HEADING)
        cap2 = caption("Q = XW_Q    K = XW_K    V = XW_V   (same X, three projections)")
        x_small = x_mat.copy().scale(0.55).to_corner(UL, buff=1.0)
        self.play(
            ReplacementTransform(x_mat, x_small), FadeOut(tok_labs), FadeOut(cap),
            run_time=0.8,
        )
        self.play(
            LaggedStart(
                FadeIn(qm, scale=0.7), FadeIn(km, scale=0.7), FadeIn(vm, scale=0.7),
                lag_ratio=0.25),
            FadeIn(ql), FadeIn(kl), FadeIn(vl), FadeIn(cap2),
            run_time=1.6,
        )
        self.wait(1.25)

        # ================= stage 3: Score =====================================
        self.move_cursor(cursor, chips, 2)
        q_left, q_cells = self.num_matrix(Q, C_Q, nd=0)
        q_left.move_to(4.8 * LEFT + 0.9 * UP)
        q_left_lab = label_for(q_left, "Q", UP, buff=0.2, math=True, color=C_Q, size=BODY)
        kt_right, kt_cells = self.num_matrix(K.T, C_K, nd=0)
        kt_right.move_to(4.8 * RIGHT + 0.9 * UP)
        kt_lab = label_for(kt_right, "Kᵀ (keys transposed)", UP, buff=0.2, math=True, color=C_K, size=LABEL)

        s_mat, s_cells = self.num_matrix(S, INK_MUTED, nd=0)
        s_mat.move_to(ORIGIN + 1.15 * DOWN)
        s_lab = label_for(s_mat, "S = QKᵀ", DOWN, buff=0.3, math=True, color=INK, size=BODY)

        hi_q3 = SurroundingRectangle(q_cells[2], buff=0.08, color=C_Q).set_stroke(width=3)
        col3 = VGroup(kt_cells[0][2], kt_cells[1][2])   # Kᵀ is 2 rows × 3 cols
        hi_k3 = SurroundingRectangle(col3, buff=0.08, color=C_K).set_stroke(width=3)
        hi_s33 = SurroundingRectangle(s_cells[2][2], buff=0.06, color=ACCENT_WARM).set_stroke(width=3)
        expl = math_text("q₃·k₃ = 1·1 + 1·2 = 3", BODY, INK)
        expl.next_to(s_mat, RIGHT, buff=1.1)

        cap3 = caption("scores: Sᵢⱼ = qᵢ·kⱼ — how much query i wants key j")
        self.play(
            FadeOut(qm), FadeOut(km), FadeOut(vm), FadeOut(ql), FadeOut(kl),
            FadeOut(vl), FadeOut(cap2), FadeOut(x_small),
            FadeIn(q_left), FadeIn(q_left_lab), FadeIn(kt_right), FadeIn(kt_lab),
            FadeIn(cap3),
            run_time=0.9,
        )
        self.play(FadeIn(s_mat, scale=0.8), FadeIn(s_lab), run_time=0.9)
        self.play(ShowCreation(hi_q3), ShowCreation(hi_k3), run_time=0.7)
        self.play(ShowCreation(hi_s33), FadeIn(expl), run_time=0.7)
        self.wait(1.5)
        self.play(FadeOut(hi_q3), FadeOut(hi_k3), FadeOut(hi_s33), FadeOut(expl))
        self.wait(IDEA_PAUSE)

        # ================= stage 4: Softmax ===================================
        self.move_cursor(cursor, chips, 3)
        s_small, _ = self.num_matrix(S, INK_MUTED, nd=0)
        s_small.scale(0.75).move_to(4.6 * LEFT + 0.3 * UP)
        s_small_lab = label_for(s_small, "S", UP, buff=0.2, math=True, color=INK_MUTED, size=BODY)
        a_mat, a_cells = self.num_matrix(A, GOOD, nd=2)
        a_mat.move_to(1.8 * RIGHT + 0.3 * UP)
        a_lab = label_for(a_mat, "A = softmax(S / √dₖ)", UP, buff=0.25, math=True, color=GOOD, size=BODY)
        arrow = Arrow(s_small.get_right() + 0.3 * RIGHT, a_mat.get_left() + 0.3 * LEFT,
                      buff=0.15).set_stroke(INK_MUTED, width=3)
        cap4 = caption("scale by 1/√dₖ, softmax each row → attention weights (each row sums to 1)")
        row1 = VGroup(a_cells[0][0], a_cells[0][1], a_cells[0][2])
        hi_row1 = SurroundingRectangle(row1, buff=0.05, color=GOOD).set_stroke(width=3)
        sum_tag = math_text("Σ = 1", LABEL, GOOD)
        sum_tag.next_to(row1, DOWN, buff=0.25)

        self.play(
            FadeOut(q_left), FadeOut(q_left_lab), FadeOut(kt_right), FadeOut(kt_lab),
            FadeOut(s_mat), FadeOut(s_lab), FadeOut(cap3),
            FadeIn(s_small), FadeIn(s_small_lab), FadeIn(cap4),
            run_time=0.9,
        )
        self.play(GrowFromEdge(arrow, LEFT), FadeIn(a_mat, scale=0.85), FadeIn(a_lab), run_time=1.0)
        self.play(ShowCreation(hi_row1), FadeIn(sum_tag), run_time=0.7)
        self.wait(1.5)
        self.play(FadeOut(hi_row1), FadeOut(sum_tag))
        self.wait(IDEA_PAUSE)

        # ================= stage 5: Mix =======================================
        self.move_cursor(cursor, chips, 4)
        a_left, _ = self.num_matrix(A, GOOD, nd=2)
        a_left.scale(0.75).move_to(4.6 * LEFT + 0.5 * UP)
        a_left_lab = label_for(a_left, "A", UP, buff=0.2, math=True, color=GOOD, size=BODY)
        v_right, _ = self.num_matrix(V, C_V, nd=0)
        v_right.scale(0.8).move_to(4.6 * RIGHT + 0.5 * UP)
        v_right_lab = label_for(v_right, "V", UP, buff=0.2, math=True, color=C_V, size=BODY)
        out_mat, out_cells = self.num_matrix(OUT, PLUM, nd=2)
        out_mat.move_to(ORIGIN + 1.5 * DOWN)
        out_lab = label_for(out_mat, "Out = A·V", DOWN, buff=0.3, math=True, color=PLUM, size=BODY)

        eq = self.final_equation().scale(0.85)
        eq.to_edge(UP, buff=1.5)   # sits between chips and the A/V matrices

        cap5 = caption("each output token = weighted mixture of all value vectors")
        self.play(
            FadeOut(s_small), FadeOut(s_small_lab), FadeOut(a_mat), FadeOut(a_lab),
            FadeOut(arrow), FadeOut(cap4),
            FadeIn(a_left), FadeIn(a_left_lab), FadeIn(v_right), FadeIn(v_right_lab),
            FadeIn(cap5),
            run_time=0.9,
        )
        self.play(FadeIn(out_mat, scale=0.8), FadeIn(out_lab), run_time=1.0)
        self.wait(1.0)
        self.play(Write(eq), run_time=1.8)
        self.wait(2.0)

        # ================= closing ============================================
        closer = caption("× h heads in parallel    ·    residual: x + Attn(x)    ·    then MLP")
        self.play(FadeOut(cap5), FadeIn(closer, shift=0.2 * UP), run_time=FADE)
        self.wait(SECTION_PAUSE)
        self.play(*[FadeOut(m) for m in self.mobjects])
        self.wait(END_PAUSE)

    # ------------------------------------------------------------------ helpers
    def build_stage_row(self):
        chips = VGroup()
        for name in STAGES:
            chip = RoundedRectangle(width=CHIP_W, height=CHIP_H, corner_radius=0.12)
            chip.set_stroke(INK_MUTED, width=2)
            lab = text(name, CAPTION, INK_MUTED)
            chips.add(VGroup(chip, lab))
        chips.arrange(RIGHT, buff=CHIP_GAP)
        chips.to_edge(UP, buff=1.25)   # below the title zone: never collides with heading()
        for group in chips:
            group[1].move_to(group[0])
        cursor = RoundedRectangle(width=CHIP_W + 0.18, height=CHIP_H + 0.18, corner_radius=0.14)
        cursor.set_stroke(ACCENT, width=3)
        cursor.move_to(chips[0])
        return chips, cursor

    def move_cursor(self, cursor, chips, idx):
        self.play(cursor.animate.move_to(chips[idx]), run_time=0.5)

    def num_matrix(self, arr, color, nd=2):
        """A bracketed numeric matrix. Returns (mobject, rows) where rows[i] is
        the VGroup of row i's cell Text objects (for highlighting)."""
        rows = VGroup(*[
            VGroup(*[math_text(fmt(v, nd), BODY, color) for v in row])
            .arrange(RIGHT, buff=0.42)
            for row in arr
        ]).arrange(DOWN, buff=0.32)
        w, h = rows.get_width() / 2, rows.get_height() / 2
        bb, foot = 0.22, 0.18
        brackets = VGroup(
            VGroup(
                Line([-w - bb, h + foot, 0], [-w - bb, -h - foot, 0]),
                Line([-w - bb, h + foot, 0], [-w - bb - foot, h + foot, 0]),
                Line([-w - bb, -h - foot, 0], [-w - bb - foot, -h - foot, 0]),
            ),
            VGroup(
                Line([w + bb, h + foot, 0], [w + bb, -h - foot, 0]),
                Line([w + bb, h + foot, 0], [w + bb + foot, h + foot, 0]),
                Line([w + bb, -h - foot, 0], [w + bb + foot, -h - foot, 0]),
            ),
        ).set_stroke(INK_MUTED, width=3)
        return VGroup(brackets, rows), rows

    def final_equation(self):
        """Attn(Q,K,V) = softmax(QKᵀ/√dₖ)·V, color-coded to match the stages."""
        parts = [
            math_text("Attn(", BODY, INK),
            math_text("Q", BODY, C_Q), math_text(", ", BODY, INK),
            math_text("K", BODY, C_K), math_text(", ", BODY, INK),
            math_text("V", BODY, C_V), math_text(")  =  softmax(", BODY, INK),
            math_text("Q", BODY, C_Q), math_text("K", BODY, C_K),
            math_text("ᵀ", BODY, INK),
            math_text(" / √dₖ) · ", BODY, INK),
            math_text("V", BODY, C_V),
        ]
        return VGroup(*parts).arrange(RIGHT, buff=0.03)
