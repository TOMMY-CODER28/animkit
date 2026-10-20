"""Layout Demo — vertical slice of the spec-driven layout system.

Declares a SceneSpec (content + relationships); animkit.layout decides
coordinates, animates the lifecycle, and validates the result. Covers:
three_columns (equal centre spacing + centreline), nav tracking, a temporary
annotation, and a transform. Reports land next to the video.
"""

import sys
from pathlib import Path
try:
    import animkit  # noqa: F401  (pip install -e <animkit>)
except ImportError:
    import os as _os
    from pathlib import Path as _Path
    _root = _os.environ.get("ANIMKIT_ROOT")
    _anc = [a for a in _Path(__file__).resolve().parents
            if (a / "animkit" / "layout").is_dir()]
    sys.path.insert(0, _root or (str(_anc[0]) if _anc else ""))  # animkit package

from manimlib import *
from animkit.layout import (
    SceneSpec, StageSpec, ComponentSpec, SpecScene,
)

ACCENT, HILITE, WARM = "#58C4DD", "#5CD0B3", "#F4D345"


def build_spec() -> SceneSpec:
    spec = SceneSpec(name="layout-demo", aspect=16 / 9, density="comfortable",
                     output_dir=str(Path(__file__).parent / "media"))
    spec.components = {
        "title": ComponentSpec(id="title", ctype="title",
                               content={"text": "Three columns, solved"}),
        "nav": ComponentSpec(id="nav", ctype="nav",
                             content={"stages": ["Columns", "Transform"], "active": 0}),
        "Q": ComponentSpec(id="Q", ctype="matrix",
                           content={"values": [[1, 0], [0, 1]], "nd": 0,
                                    "label": "Q", "color": ACCENT}),
        "K": ComponentSpec(id="K", ctype="matrix",
                           content={"values": [[1, 1], [0, 1]], "nd": 0,
                                    "label": "K", "color": HILITE}),
        "V": ComponentSpec(id="V", ctype="matrix",
                           content={"values": [[2, 0], [0, 1], [2, 1]], "nd": 0,
                                    "label": "V", "color": WARM}),
        "note": ComponentSpec(id="note", ctype="text", owner="V",
                              content={"text": "V has 3 rows — spacing adapts"}),
        "K2": ComponentSpec(id="K2", ctype="matrix",
                            content={"values": [[1, 2], [3, 4]], "nd": 0,
                                     "label": "K → new", "color": HILITE}),
    }
    spec.stages = [
        StageSpec(
            id="columns", template="three_columns",
            components={"title": "persistent", "nav": "persistent",
                        "Q": "entering", "K": "entering", "V": "entering",
                        "note": "temporary"},
            transition={"title": "static", "nav": "static",
                        "Q": "fade_in", "K": "fade_in", "V": "fade_in",
                        "note": "fade_in"},
            timing={"enter": 1.0, "hold": 1.2, "exit": 0.4},
            permitted_overlaps=[],
        ),
        StageSpec(
            id="transform", template="three_columns",
            components={"title": "leaving", "nav": "persistent",
                        "Q": "persistent", "K": "changing", "V": "persistent"},
            transition={"nav": "static", "Q": "move", "K": "transform", "V": "move"},
            timing={"move": 1.2, "hold": 1.2, "exit": 0.5},
            caption="unchanged components hold their positions",
        ),
    ]
    return spec


class LayoutDemo(SpecScene):
    def setup(self):
        self.spec = build_spec()
        super().setup()
