"""Reusable visual components with ownership, bounds and anchors.

Each builder returns a Component wrapping a ManimGL mobject group plus
metadata: id, ctype, owned children, named parts (rows/cols/entries for
matrices), and measured bounds. Components are built BEFORE layout so the
solver sees real rendered dimensions.

TextMatrix replaces hand-rolled matrices: entries are Pango Text (no LaTeX on
this machine — ManimGL's Matrix uses Tex and would crash), brackets are built
with ticks pointing INWARD (the "brackets face outward" defect), and rows/
columns/entries stay addressable like manimlib's Matrix API.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# scenes run from their project dir; make animkit (and theme) importable
_ANIMKIT_ROOT = str(Path(__file__).resolve().parents[2])
if _ANIMKIT_ROOT not in sys.path:
    sys.path.insert(0, _ANIMKIT_ROOT)

from manimlib import *  # noqa: F401,F403  (runs under the manim venv python)
from animkit.layout.geom import Box

# ---------------------------------------------------------------- palette ---
# Mirrors the project theme (kept in sync; theme import may not exist in tests)
INK = "#ECECEC"
INK_MUTED = "#AAB2BA"
ACCENT = "#58C4DD"
ACCENT_WARM = "#F4D345"
GOOD = "#83C167"
HILITE = "#5CD0B3"
PLUM = "#CAA3E8"
BAD = "#FC6255"

TEXT_FONT = "Segoe UI"
MATH_FONT = "Cambria Math"


def math_text(txt, size=34, color=INK, **kw):
    return Text(txt, font=MATH_FONT, font_size=size, color=color, **kw)


def body_text(txt, size=30, color=INK, **kw):
    return Text(txt, font=TEXT_FONT, font_size=size, color=color, **kw)


def fmt_num(v, nd=2):
    if nd == 0 or float(v).is_integer():
        return f"{float(v):g}"
    return f"{float(v):.{nd}f}"


@dataclass
class Component:
    """A laid-out visual component: identity + mobject + measured geometry."""

    id: str
    ctype: str
    group: object                              # manim VGroup-like
    owner: str | None = None
    overlap_class: str = "block"               # block | label | highlight | arrow | connector
    parts: dict = field(default_factory=dict)  # named sub-mobjects (rows, entries...)
    label: object | None = None
    target_id: str | None = None
    region: str = "main"

    def bounds(self, pad: float = 0.0) -> Box:
        g = self.group
        w, h = g.get_width(), g.get_height()
        return Box(g.get_center()[0], g.get_center()[1], w + 2 * pad, h + 2 * pad)

    def anchor(self, name: str) -> tuple[float, float]:
        return self.bounds().anchor(name)


# ---------------------------------------------------------------- matrices ---
def _bracket(height: float, side: str, color: str = INK_MUTED, stroke_w: float = 3.0) -> VGroup:
    """One square bracket. Left bracket ticks point RIGHT (inward), right
    bracket ticks point LEFT — never outward."""
    h2 = height / 2
    foot = min(0.18, height * 0.18)
    x = 0.0
    inward = 1.0 if side == "left" else -1.0
    back = VGroup(
        Line([x, h2, 0], [x, -h2, 0]),
        Line([x, h2, 0], [x + inward * foot, h2, 0]),
        Line([x, -h2, 0], [x + inward * foot, -h2, 0]),
    )
    back.set_stroke(color, width=stroke_w)
    return back


def _build_matrix(values, nd, color, entry_size, v_buff, h_buff):
    rows_v = VGroup()
    for row in values:
        cells = [math_text(fmt_num(v, nd), entry_size, color) for v in row]
        row_v = VGroup(*cells).arrange(RIGHT, buff=h_buff)
        rows_v.add(row_v)
    rows_v.arrange(DOWN, buff=v_buff)
    return rows_v


class TextMatrix:
    """A numeric matrix with correct brackets and addressable parts.

    Mirrors the addressable API of manimlib's Matrix (get_rows/get_columns/
    get_entries) without LaTeX.
    """

    def __init__(self, values, nd=2, color=INK, entry_size=34,
                 v_buff=0.32, h_buff=0.48, bracket_buff=0.22):
        self.values = values
        self.rows = _build_matrix(values, nd, color, entry_size, v_buff, h_buff)
        inner_w = self.rows.get_width()
        inner_h = self.rows.get_height()
        self.brackets = VGroup(
            _bracket(inner_h, "left"),
            _bracket(inner_h, "right"),
        )
        # left bracket: vertical stroke just left of the entries, ticks pointing
        # right (inward); right bracket mirrored.
        self.brackets[0].move_to([self.rows.get_left()[0] - bracket_buff - self.brackets[0].get_width() / 2, 0, 0])
        self.brackets[1].move_to([self.rows.get_right()[0] + bracket_buff + self.brackets[1].get_width() / 2, 0, 0])
        self.group = VGroup(self.brackets, self.rows)
        self.columns = VGroup(*[
            VGroup(*[self.rows[i][j] for i in range(len(self.rows))])
            for j in range(len(self.rows[0]))
        ])

    def get_rows(self):
        return self.rows

    def get_columns(self):
        return self.columns

    def get_entries(self):
        return VGroup(*[e for row in self.rows for e in row])

    def get_entry(self, i, j):
        return self.rows[i][j]

    def entry_box(self, i, j, pad=0.02) -> Box:
        e = self.get_entry(i, j)
        return Box(e.get_center()[0], e.get_center()[1], e.get_width() + 2 * pad, e.get_height() + 2 * pad)

    def part_box(self, kind, i=None, j=None, pad=0.06) -> Box:
        if kind == "row":
            g = self.rows[i]
        elif kind == "col":
            g = self.columns[j]
        else:
            return self.entry_box(i, j, pad)
        return Box(g.get_center()[0], g.get_center()[1], g.get_width() + 2 * pad, g.get_height() + 2 * pad)


def make_matrix_component(spec: Component, **_) -> Component:
    content = spec.content
    color = content.get("color") or INK
    label_txt = content.get("label")
    m = TextMatrix(
        content["values"], nd=content.get("nd", 2), color=color,
        entry_size=content.get("entry_size", 34),
    )
    parts = {"matrix": m.group}
    members = [m.group]
    label = None
    if label_txt:
        side = content.get("label_side", "above")
        label = math_text(label_txt, content.get("label_size", 34), color)
        attach = {"above": (UP, 0.28), "below": (DOWN, 0.28), "left": (LEFT, 0.3), "right": (RIGHT, 0.3)}[side]
        label.next_to(m.group, attach[0], buff=attach[1])
        members.append(label)
    group = VGroup(*members)
    return Component(
        id=spec.id, ctype="matrix", group=group, owner=spec.owner,
        parts={**parts, "tm": m}, label=label, region=spec.region,
    )


# ---------------------------------------------------------------- text/eq ----
def make_text_component(spec: Component, **_) -> Component:
    c = spec.content
    txt = body_text(c["text"], c.get("font_size", 30), c.get("color") or INK)
    return Component(id=spec.id, ctype="text", group=txt, owner=spec.owner, region=spec.region)


def make_equation_component(spec: Component, **_) -> Component:
    c = spec.content
    if c.get("mode") == "tex":
        group = _make_tex_equation(c)
    else:
        parts = [math_text(t, c.get("font_size", 34), col or INK) for t, col in c["parts"]]
        group = VGroup(*parts).arrange(RIGHT, buff=c.get("buff", 0.12))
    return Component(id=spec.id, ctype="equation", group=group, owner=spec.owner, region=spec.region)


def _make_tex_equation(c: dict):
    """Real LaTeX equation via manimlib's Tex (needs latex+dvisvgm; animkit
    injects the TeX bin dir into PATH).

    One Tex PER PART, arranged in a row. NB: this build's Tex has a cache bug
    where tex_to_color_map can return a previously-compiled mobject (observed:
    a second, different formula came back with the first formula's geometry),
    so per-part construction is the reliable coloring mechanism."""
    from animkit.env import latex_path_env
    import os
    os.environ["PATH"] = latex_path_env()["PATH"]
    from manimlib import Tex
    font = c.get("font_size", 34) * 144 // 60
    # Each part compiles as its OWN LaTeX document, so fragments must be
    # self-contained: \left/\right only pair within one part, and an unpaired
    # one makes latex fail — which this ManimGL build then MASKS by silently
    # returning the previous compile's DVI (wrong geometry, no error). Strip
    # them; plain delimiters typeset identically at this scale.
    sanitized = [
        (t.replace(r"\left", "").replace(r"\right", ""), col)
        for t, col in c["parts"] if t.strip()
    ]
    try:
        parts = [
            Tex(t, font_size=font).set_color(col or INK)
            for t, col in sanitized
        ]
    except Exception as exc:
        raise RuntimeError(
            f"TeX equation failed to compile ({exc}). LaTeX toolchain status: "
            f"install MiKTeX (winget install MiKTeX.MiKTeX), enable package "
            f"auto-install, and clear ManimGL's tex disk cache "
            f"(%LOCALAPPDATA%\\manim\\manim\\Cache) if it previously cached "
            f"broken SVGs — then re-run."
        ) from exc
    return VGroup(*parts).arrange(RIGHT, buff=c.get("buff", 0.07))


def make_title_component(spec: Component, **_) -> Component:
    c = spec.content
    txt = body_text(c["text"], c.get("font_size", 46), c.get("color") or INK)
    return Component(id=spec.id, ctype="title", group=txt, region=spec.region)


def make_caption_component(spec: Component, **_) -> Component:
    c = spec.content
    txt = body_text(c["text"], c.get("font_size", 22), c.get("color") or INK_MUTED)
    return Component(id=spec.id, ctype="caption", group=txt, region=spec.region)


# ---------------------------------------------------------------- nav --------
class StageNav:
    """Chip row + cursor; persistent across stages, 'changing' each stage."""

    def __init__(self, stage_names, active=0, font_size=22,
                 chip_fill=INK_MUTED, active_stroke=ACCENT):
        self.stage_names = list(stage_names)
        chips = VGroup()
        self._chip_rects = []
        for name in stage_names:
            lab = body_text(name, font_size, INK_MUTED)
            rect = RoundedRectangle(width=lab.get_width() + 0.55, height=0.58, corner_radius=0.11)
            rect.set_stroke(INK_MUTED, width=2)
            lab.move_to(rect)
            chips.add(VGroup(rect, lab))
            self._chip_rects.append(rect)
        chips.arrange(RIGHT, buff=0.32)
        self.group = chips
        self.cursor = RoundedRectangle(
            width=self._chip_rects[0].get_width() + 0.16,
            height=0.74, corner_radius=0.13,
        ).set_stroke(active_stroke, width=3)
        self.cursor.move_to(self._chip_rects[0])
        self.set_active(active)

    def set_active(self, idx: int):
        self.active = idx
        self.cursor.move_to(self._chip_rects[idx])

    def active_target(self):
        return self._chip_rects[self.active]


def make_nav_component(spec: Component, **_) -> Component:
    c = spec.content
    nav = StageNav(c["stages"], c.get("active", 0))
    return Component(
        id=spec.id, ctype="nav", group=VGroup(nav.group, nav.cursor),
        parts={"nav": nav}, region=spec.region,
    )


# ---------------------------------------------------------------- highlights / arrows / callouts
def make_highlight_component(spec: Component, target: Component, **_) -> Component:
    c = spec.content
    kind = c["part"][0]
    tm: TextMatrix = target.parts["tm"]
    if kind == "row":
        box = tm.part_box("row", c["part"][1])
    elif kind == "col":
        box = tm.part_box("col", j=c["part"][1])
    else:
        box = tm.part_box("entry", c["part"][1], c["part"][2])
    rect = RoundedRectangle(width=box.w, height=box.h, corner_radius=0.04)
    rect.set_stroke(c.get("color") or GOOD, width=3)
    rect.move_to([box.x, box.y, 0])
    # move with the target group when it later moves:
    rect.add_updater(lambda m: m.move_to(_target_part_center(target, c["part"])))
    return Component(
        id=spec.id, ctype="highlight", group=rect, owner=spec.owner or target.id,
        overlap_class="highlight", target_id=target.id, region=target.region,
    )


def _target_part_center(target: Component, part) -> np.ndarray:
    tm: TextMatrix = target.parts["tm"]
    kind = part[0]
    if kind == "row":
        g = tm.rows[part[1]]
    elif kind == "col":
        g = tm.columns[part[1]]
    else:
        g = tm.get_entry(part[1], part[2])
    return g.get_center()


def make_arrow_component(spec: Component, anchors: dict, **_) -> Component:
    """Built after layout: `anchors` maps id -> world anchor points."""
    c = spec.content
    start = np.array([*anchors[c["from"][0]], 0.0]) if isinstance(c["from"][0], str) else np.array(c["from"])
    end = np.array([*anchors[c["to"][0]], 0.0]) if isinstance(c["to"][0], str) else np.array(c["to"])
    arrow = Arrow(start, end, buff=0.12)
    arrow.set_stroke(c.get("color") or INK_MUTED, width=4)
    members = [arrow]
    label = None
    if c.get("label"):
        label = math_text(c["label"], c.get("label_size", 26), c.get("label_color") or INK)
        label.next_to(arrow, UP, buff=0.12)
        members.append(label)
    return Component(
        id=spec.id, ctype="arrow", group=VGroup(*members), owner=spec.owner,
        overlap_class="arrow", label=label, region=spec.region,
    )


def make_callout_component(spec: Component, target: Component, **_) -> Component:
    c = spec.content
    side = c.get("side", "right")
    txt = body_text(c["text"], c.get("font_size", 24), c.get("color") or INK)
    box = RoundedRectangle(width=txt.get_width() + 0.5, height=txt.get_height() + 0.4, corner_radius=0.1)
    box.set_stroke(c.get("stroke") or ACCENT, width=2)
    txt.move_to(box)
    group = VGroup(box, txt)
    group.next_to(target.group, RIGHT if side == "right" else LEFT, buff=0.4)
    connector = Line(
        target.group.get_edge_center(RIGHT if side == "right" else LEFT),
        box.get_edge_center(LEFT if side == "right" else RIGHT),
    ).set_stroke(c.get("stroke") or ACCENT, width=2)
    return Component(
        id=spec.id, ctype="callout", group=VGroup(group, connector),
        owner=spec.owner or target.id, overlap_class="connector",
        target_id=target.id, region=spec.region,
    )


MAKERS = {
    "matrix": make_matrix_component,
    "text": make_text_component,
    "equation": make_equation_component,
    "title": make_title_component,
    "caption": make_caption_component,
    "nav": make_nav_component,
}
