"""Internal coordinate system and region layout.

Convention (matches ManimGL): origin at frame centre, x right, y up, units =
manim units. The frame height is fixed at 8.0 (ManimGL `sizes.frame_height`);
width follows the project's aspect ratio.

Regions are horizontal bands computed from the frame box with margins. Bands
unused in a stage collapse (explicit policy): their height returns to `main`.

All boxes are centre-based: Box(x, y, w, h) with named anchors.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

FRAME_HEIGHT = 8.0
EPS = 1e-9

REGION_ORDER = ["title", "nav", "main", "annotation", "caption"]  # top -> bottom
REGION_NAMES = frozenset(REGION_ORDER)


@dataclass(frozen=True)
class Box:
    """Centre-based rectangle."""

    x: float
    y: float
    w: float
    h: float

    # -- bounds -------------------------------------------------------------
    @property
    def left(self) -> float:
        return self.x - self.w / 2

    @property
    def right(self) -> float:
        return self.x + self.w / 2

    @property
    def top(self) -> float:
        return self.y + self.h / 2

    @property
    def bottom(self) -> float:
        return self.y - self.h / 2

    # -- anchors ------------------------------------------------------------
    def anchor(self, name: str) -> tuple[float, float]:
        table = {
            "c": (self.x, self.y),
            "n": (self.x, self.top),
            "s": (self.x, self.bottom),
            "e": (self.right, self.y),
            "w": (self.left, self.y),
            "ne": (self.right, self.top),
            "nw": (self.left, self.top),
            "se": (self.right, self.bottom),
            "sw": (self.left, self.bottom),
        }
        if name not in table:
            raise ValueError(f"unknown anchor {name!r} (use one of {sorted(table)})")
        return table[name]

    def moved_to(self, x: float, y: float) -> "Box":
        return Box(x, y, self.w, self.h)

    def expanded(self, pad: float) -> "Box":
        return Box(self.x, self.y, self.w + 2 * pad, self.h + 2 * pad)

    def contains(self, other: "Box", margin: float = 0.0) -> bool:
        return (
            other.left >= self.left + margin - EPS
            and other.right <= self.right - margin + EPS
            and other.bottom >= self.bottom + margin - EPS
            and other.top <= self.top - margin + EPS
        )

    def overlaps(self, other: "Box", pad: float = 0.0) -> bool:
        a, b = self.expanded(pad), other.expanded(pad)
        return (
            a.left < b.right - EPS
            and b.left < a.right - EPS
            and a.bottom < b.top - EPS
            and b.bottom < a.top - EPS
        )

    def gap_x(self, other: "Box") -> float:
        """Positive horizontal gap between the boxes (negative = overlap)."""
        if self.right <= other.left:
            return other.left - self.right
        if other.right <= self.left:
            return self.left - other.right
        return -min(self.right, other.right) + max(self.left, other.left)

    def gap_y(self, other: "Box") -> float:
        if self.top <= other.bottom:
            return other.bottom - self.top
        if other.top <= self.bottom:
            return self.bottom - other.top
        return -min(self.top, other.top) + max(self.bottom, other.bottom)

    def is_finite(self) -> bool:
        return all(math.isfinite(v) for v in (self.x, self.y, self.w, self.h))


@dataclass(frozen=True)
class Region:
    """A named rectangular band (or block) available for content."""

    name: str
    box: Box


@dataclass
class RegionPlan:
    """Region bands for one stage, after the collapse policy is applied."""

    aspect: float
    density: str = "comfortable"
    regions: dict[str, Region] = field(default_factory=dict)
    collapsed: tuple[str, ...] = ()

    def get(self, name: str) -> Region:
        return self.regions[name]


# density presets: (outer margin, band gap, title h, nav h, caption h)
DENSITY = {
    "comfortable": dict(margin=0.55, gap=0.45, title=0.95, nav=0.85, caption=0.55, ann=1.6),
    "compact": dict(margin=0.35, gap=0.30, title=0.80, nav=0.70, caption=0.45, ann=1.2),
}


def plan_regions(
    aspect: float,
    used: set[str],
    density: str = "comfortable",
    annotation_side: str = "bottom",
) -> RegionPlan:
    """Compute region bands for a stage.

    `used` lists the band names the stage actually places content in; unused
    bands collapse and their height returns to `main` (collapse policy).
    `annotation` is a strip inside/beside main: 'bottom' = strip under main,
    'right' = column at the right of main.
    """
    if density not in DENSITY:
        raise ValueError(f"density must be one of {sorted(DENSITY)}, got {density!r}")
    d = DENSITY[density]
    width = FRAME_HEIGHT * aspect
    height = FRAME_HEIGHT
    frame = Box(0.0, 0.0, width, height)

    inner = frame.expanded(-d["margin"])  # content area inside outer margin

    heights: dict[str, float] = {}
    for band in ("title", "nav", "caption"):
        heights[band] = d[band if band != "annotation" else "ann"] if band in used else 0.0
    heights["annotation"] = d["ann"] if ("annotation" in used and annotation_side == "bottom") else 0.0

    regions: dict[str, Region] = {}
    y_top = inner.top
    for band in ("title", "nav"):
        if heights[band] > 0:
            regions[band] = Region(band, Box(0.0, y_top - heights[band] / 2, inner.w, heights[band]))
            y_top -= heights[band] + d["gap"]

    y_bottom = inner.bottom
    if heights["caption"] > 0:
        regions["caption"] = Region("caption", Box(0.0, y_bottom + heights["caption"] / 2, inner.w, heights["caption"]))
        y_bottom += heights["caption"] + d["gap"]
    if heights["annotation"] > 0:
        regions["annotation"] = Region(
            "annotation", Box(0.0, y_bottom + heights["annotation"] / 2, inner.w, heights["annotation"])
        )
        y_bottom += heights["annotation"] + d["gap"]

    main_h = y_top - y_bottom
    if main_h <= 0.5:
        raise ValueError(
            f"main region collapsed to {main_h:.2f} units — too many bands used for "
            f"density={density!r}; drop a band or use 'compact'"
        )
    if annotation_side == "right" and "annotation" in used:
        ann_w = d["ann"]
        regions["annotation"] = Region("annotation", Box(inner.right - ann_w / 2, (y_top + y_bottom) / 2, ann_w, main_h))
        main_w = inner.w - ann_w - d["gap"]
        regions["main"] = Region("main", Box(inner.left + main_w / 2, (y_top + y_bottom) / 2, main_w, main_h))
    else:
        regions["main"] = Region("main", Box(0.0, (y_top + y_bottom) / 2, inner.w, main_h))

    collapsed = tuple(b for b in REGION_ORDER if b not in used)
    return RegionPlan(aspect=aspect, density=density, regions=regions, collapsed=collapsed)
