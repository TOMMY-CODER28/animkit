"""Multiply a Matrix by a Vector — animated from script.md (script-first).

Every stage maps 1:1 to a script stage; every number is computed by numpy
below and asserted against the script's claims. Narration (the script's
Say: lines) is spoken via Kokoro and kept off-screen, per the script.
Render with:  animkit preview .   /   animkit render .
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

# ---- script Math: lines, computed and asserted ------------------------------
A = np.array([[1.0, 1.0],
              [0.0, 1.0]])
v = np.array([1.0, 2.0])

FIRST = A[0, 0] * v[0] + A[0, 1] * v[1]
SECOND = A[1, 0] * v[0] + A[1, 1] * v[1]
RESULT = A @ v

assert FIRST == 3.0, "script claims the first output value is 3"
assert SECOND == 2.0, "script claims the second output value is 2"
assert np.array_equal(RESULT, np.array([3.0, 2.0])), "script claims Av = [3, 2]"

# ---- palette (theme mirror) -------------------------------------------------
INK, MUT = "#ECECEC", "#AAB2BA"
ACCENT, HILITE, WARM, GOOD = "#58C4DD", "#5CD0B3", "#F4D345", "#83C167"

STAGES = ["Inputs", "Row 1", "Row 2", "Result"]


def mat(cid, values, label, color=INK, nd=0, label_side="above", entry_size=30):
    return ComponentSpec(id=cid, ctype="matrix",
                         content={"values": values, "nd": nd, "label": label,
                                  "color": color, "label_side": label_side,
                                  "entry_size": entry_size})


def build_spec() -> SceneSpec:
    spec = SceneSpec(name="matrix-vector-product", aspect=16 / 9,
                     density="comfortable",
                     output_dir=str(Path(__file__).parent / "media"),
                     audio={"voice": "af_heart", "speed": 0.9, "lang": "a",
                            "pad": 0.8})
    spec.components = {
        "nav": ComponentSpec(id="nav", ctype="nav",
                             content={"stages": STAGES, "active": 0}),
        "A": mat("A", A.tolist(), "A", ACCENT),
        "v": mat("v", v.reshape(-1, 1).tolist(), "v", HILITE),
        # stage 2 highlights: first row of A, both entries of v (= its column)
        "hA1": ComponentSpec(id="hA1", ctype="highlight", owner="A",
                             content={"target": "A", "part": ["row", 0],
                                      "color": ACCENT}),
        "hv1": ComponentSpec(id="hv1", ctype="highlight", owner="v",
                             content={"target": "v", "part": ["col", 0],
                                      "color": HILITE}),
        "calc1": eq_text("calc1", "1 × 1 + 1 × 2 = 3"),
        # stage 3 highlights: second row of A
        "hA2": ComponentSpec(id="hA2", ctype="highlight", owner="A",
                             content={"target": "A", "part": ["row", 1],
                                      "color": ACCENT}),
        "hv2": ComponentSpec(id="hv2", ctype="highlight", owner="v",
                             content={"target": "v", "part": ["col", 0],
                                      "color": HILITE}),
        "calc2": eq_text("calc2", "0 × 1 + 1 × 2 = 2"),
        # stage 4: the result
        "r": mat("r", RESULT.reshape(-1, 1).tolist(), "A·v", GOOD),
    }

    def stage(sid, tpl, comps, trans, hold, narration=None, **kw):
        return StageSpec(id=sid, template=tpl, components=comps,
                         transition=trans, caption=None, narration=narration,
                         timing={"enter": 0.9, "move": 1.0, "exit": 0.5,
                                 "hold": hold}, **kw)

    spec.stages = [
        # stage 1 — the inputs (hold 1s)
        stage("inputs", "two_columns",
              {"nav": "persistent", "A": "entering", "v": "entering"},
              {"nav": "static", "A": "fade_in", "v": "fade_in"},
              hold=1.0,
              narration="Let us multiply a matrix by a vector. Matrix A has "
                        "two rows and two columns. Our input vector has the "
                        "values one and two."),
        # stage 2 — first output value (hold 2s)
        stage("row-1", "two_columns",
              {"nav": "persistent", "A": "persistent", "v": "persistent",
               "hA1": "entering", "hv1": "entering", "calc1": "entering"},
              {"nav": "static", "hA1": "fade_in", "hv1": "fade_in",
               "calc1": "fade_in"},
              hold=2.0,
              narration="Start with the first row. Multiply one by one. Then "
                        "multiply one by two. Add the products. The first "
                        "output value is three."),
        # stage 3 — second output value (hold 2s)
        stage("row-2", "two_columns",
              {"nav": "persistent", "A": "persistent", "v": "persistent",
               "hA1": "leaving", "hv1": "leaving", "calc1": "leaving",
               "hA2": "entering", "hv2": "entering", "calc2": "entering"},
              {"nav": "static", "hA1": "fade_in", "hv1": "fade_in",
               "calc1": "fade_in", "hA2": "fade_in", "hv2": "fade_in",
               "calc2": "fade_in"},
              hold=2.0,
              narration="Now use the second row. Zero times one is zero. One "
                        "times two is two. Add the products. The second "
                        "output value is two."),
        # stage 4 — the result (keep visible until narration ends)
        stage("result", "operands_result",
              {"nav": "persistent", "A": "persistent", "v": "persistent",
               "hA2": "leaving", "hv2": "leaving", "calc2": "leaving",
               "r": "entering"},
              {"nav": "static", "hA2": "fade_in", "hv2": "fade_in",
               "calc2": "fade_in", "r": "fade_in"},
              hold=2.0,
              narration="The output vector is three, two. Each output value "
                        "comes from one row of the matrix. This completes "
                        "the multiplication.",
              operands=["A", "v"], result="r", min_gap=0.7),
    ]
    return spec


def eq_text(cid, txt):
    return ComponentSpec(id=cid, ctype="equation", owner="A",
                         content={"parts": [(txt, None)], "font_size": 32,
                                  "side": "below"})


class MatrixVectorProduct(SpecScene):
    def setup(self):
        self.spec = build_spec()
        super().setup()
