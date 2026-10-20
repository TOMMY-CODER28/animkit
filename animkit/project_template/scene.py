"""{{TITLE}} — scene source (spec-driven). The class name must match
project.json ("scene"). Render with:  animkit preview .   (from this directory)
"""

# --- locate the animkit package: installed? env var? repo ancestor? ---------
import os
import sys
from pathlib import Path

try:
    import animkit                                    # pip install -e <animkit>
except ImportError:
    _root = os.environ.get("ANIMKIT_ROOT")
    _here = Path(__file__).resolve().parent
    _anc = [p for p in _here.parents if (p / "animkit" / "layout").is_dir()]
    sys.path.insert(0, _root or (str(_anc[0]) if _anc else str(_here.parents[2])))
# ----------------------------------------------------------------------------

import numpy as np

from manimlib import *
from animkit.layout import SceneSpec, StageSpec, ComponentSpec, SpecScene

INK, MUT = "#ECECEC", "#AAB2BA"
ACCENT = "#58C4DD"


def build_spec() -> SceneSpec:
    spec = SceneSpec(name="{{NAME}}", aspect=16 / 9, density="comfortable",
                     output_dir=str(Path(__file__).parent / "media"))
    spec.components = {
        "title": ComponentSpec(id="title", ctype="title",
                               content={"text": "{{TITLE}}"}),
        "nav": ComponentSpec(id="nav", ctype="nav",
                             content={"stages": ["One", "Two"], "active": 0}),
        "m": ComponentSpec(id="m", ctype="matrix",
                           content={"values": [[1, 0], [0, 1]], "nd": 0,
                                    "label": "M", "color": ACCENT}),
    }
    spec.stages = [
        StageSpec(id="one", template="single_center",
                  components={"title": "persistent", "nav": "persistent",
                              "m": "entering"},
                  transition={"title": "static", "nav": "static", "m": "fade_in"},
                  caption="replace this stage with your first idea"),
        StageSpec(id="two", template="single_center",
                  components={"nav": "persistent", "m": "changing"},
                  transition={"nav": "static", "m": "move"}),
    ]
    return spec


class {{SCENE}}(SpecScene):
    def setup(self):
        self.spec = build_spec()
        super().setup()
