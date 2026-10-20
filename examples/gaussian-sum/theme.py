"""Shared visual theme for animkit projects (ManimGL 1.7.2-dev, no LaTeX).

Import from scene.py:  from theme import *

Rules encoded here (see skill references/quality.md for the reasoning):
  - One palette, one type scale, consistent spacing, deliberate pacing.
  - Colors are passed as stroke_color=/fill_color= — in this ManimGL build a
    generic color= kwarg is overridden by shape defaults (e.g. Circle pins
    stroke_color=RED), so color= is unreliable for shapes.
  - No Tex/MathTex anywhere: this machine has no LaTeX. Use text()/math_text()
    with Unicode (pi, subscripts) instead.
"""

from manimlib import *

# ---------------------------------------------------------------- palette ---
INK = "#ECECEC"          # primary text / lines
INK_MUTED = "#AAB2BA"    # secondary text, captions, axis labels
ACCENT = "#58C4DD"       # primary highlight (3b1b blue)
ACCENT_WARM = "#F4D345"  # secondary highlight (soft yellow)
GOOD = "#83C167"         # confirmation / signal
BAD = "#FC6255"          # error / noise / rejection
HILITE = "#5CD0B3"       # teal emphasis
PLUM = "#CAA3E8"         # tertiary category color

# ------------------------------------------------------------ type scale ---
# font_size in ManimGL is scaled by font_size_for_unit_height=144 in config.
TITLE = 52
HEADING = 42
BODY = 30
LABEL = 26
CAPTION = 22
MATH = 34

TEXT_FONT = "Segoe UI"        # Windows system font; Pango falls back if absent
MATH_FONT = "Cambria Math"    # better Unicode math glyph coverage (pi, ₀, ²)

# ------------------------------------------------- layout / safe framing ---
# Frame is 14.22 x 8.0 manim units. Keep content inside this smaller box so
# nothing is clipped at the edge or crowded against the border.
SAFE_HALF_W = FRAME_WIDTH / 2 - 0.8   # ~6.3
SAFE_HALF_H = FRAME_HEIGHT / 2 - 0.5  # 3.5

# ---------------------------------------------------------------- pacing ---
DRAW = 1.0        # draw/create one object
FADE = 0.5        # quick fade
MORPH = 1.5       # transforms between meaningfully different states
IDEA_PAUSE = 0.75 # hold after each idea so it registers
SECTION_PAUSE = 1.25
END_PAUSE = 1.5

# ------------------------------------------------------------- factories ---
def text(txt, size=BODY, color=INK, font=TEXT_FONT, **kwargs):
    return Text(txt, font=font, font_size=size, color=color, **kwargs)


def math_text(txt, size=MATH, color=INK, **kwargs):
    """Math-look text without LaTeX: uses Unicode symbols and Cambria Math."""
    return Text(txt, font=MATH_FONT, font_size=size, color=color, **kwargs)


def heading(txt, color=INK):
    h = text(txt, HEADING, color)
    h.to_edge(UP, buff=0.45)
    return h


def caption(txt, color=INK_MUTED):
    c = text(txt, CAPTION, color)
    c.to_edge(DOWN, buff=0.35)
    return c


def label_for(mobject, txt, direction=DOWN, buff=0.25, size=LABEL,
              color=INK_MUTED, math=False):
    """A label placed next to a mobject. Static: reposition if the object moves."""
    lab = math_text(txt, size, color) if math else text(txt, size, color)
    lab.next_to(mobject, direction, buff=buff)
    return lab


def pin_label(mobject, txt, direction=DOWN, buff=0.25, **kwargs):
    """A label that follows its mobject through animations (updater-based).
    Call `label.clear_updaters()` before removing either object."""
    lab = label_for(mobject, txt, direction, buff, **kwargs)
    lab.add_updater(lambda m: m.next_to(mobject, direction, buff=buff))
    return lab


def axis_label(axes, txt, axis="x", color=INK_MUTED, size=CAPTION):
    """Axis end labels built from Text (axes.get_axis_labels needs LaTeX!)."""
    ax = axes.get_x_axis() if axis == "x" else axes.get_y_axis()
    lab = math_text(txt, size, color)
    if axis == "x":
        lab.next_to(ax.get_end(), RIGHT, buff=0.25)
    else:
        lab.next_to(ax.get_end(), UP, buff=0.25)
    return lab


def matrix_label(rows, color=INK, size=MATH, bracket_buff=0.22):
    """A bracketed matrix built from Text, e.g. matrix_label([['1','1'],['0','1']]).
    Returns a VGroup centered at its own origin — move it with next_to/to_corner."""
    cells = VGroup(*[
        math_text(cell, size, color)
        for row in rows for cell in row
    ])
    ncols = len(rows[0])
    grid = VGroup(*[
        VGroup(*cells[i * ncols:(i + 1) * ncols]).arrange(RIGHT, buff=0.4)
        for i in range(len(rows))
    ]).arrange(DOWN, buff=0.3)

    w, h = grid.get_width() / 2, grid.get_height() / 2
    foot = 0.18
    left = VGroup(
        Line([-w - bracket_buff, h + foot, 0], [-w - bracket_buff, -h - foot, 0]),
        Line([-w - bracket_buff, h + foot, 0], [-w - bracket_buff - foot, h + foot, 0]),
        Line([-w - bracket_buff, -h - foot, 0], [-w - bracket_buff - foot, -h - foot, 0]),
    )
    right = VGroup(
        Line([w + bracket_buff, h + foot, 0], [w + bracket_buff, -h - foot, 0]),
        Line([w + bracket_buff, h + foot, 0], [w + bracket_buff + foot, h + foot, 0]),
        Line([w + bracket_buff, -h - foot, 0], [w + bracket_buff + foot, -h - foot, 0]),
    )
    brackets = VGroup(left, right).set_stroke(color=INK_MUTED, width=3)
    return VGroup(brackets, grid)


# ------------------------------------------------------------- geometry ----
def in_safe_area(mobject, margin=0.0) -> bool:
    """True if the mobject's bounding box sits inside the safe frame."""
    return (
        mobject.get_right()[0] <= SAFE_HALF_W - margin
        and mobject.get_left()[0] >= -SAFE_HALF_W + margin
        and mobject.get_top()[1] <= SAFE_HALF_H - margin
        and mobject.get_bottom()[1] >= -SAFE_HALF_H + margin
    )
