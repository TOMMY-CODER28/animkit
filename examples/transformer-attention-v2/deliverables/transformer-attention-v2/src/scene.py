"""Transformer Attention V2 — the spec-driven rewrite.

Declares content and relationships; animkit.layout solves coordinates,
manages the lifecycle (what stays/changes/enters/leaves), and validates the
result before and after rendering. This is the regression example for the
five v1 defects:
  1. title overlapped navigation   -> separate title/nav bands
  2. matrix brackets faced outward -> TextMatrix inward ticks
  3. the input matrix survived     -> X is lifecycle 'leaving' in 'project'
  4. the old X label lingered      -> the label is owned by X's component
  5. row-sum tag overlapped entries -> owned placement + geometry gate
"""

import sys
from pathlib import Path
import animkit  # resolved via pip install -e . or ANIMKIT_ROOT

import numpy as np

from manimlib import *
from animkit.layout import SceneSpec, StageSpec, ComponentSpec, SpecScene

# ---------------- the math (single source of truth) -------------------------
X = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
W_K = np.array([[1.0, 1.0], [0.0, 1.0]])
W_V = np.array([[2.0, 0.0], [0.0, 1.0]])
Q, K, V = X, X @ W_K, X @ W_V
S = Q @ K.T
A = np.exp(S / np.sqrt(2))
A = A / A.sum(axis=1, keepdims=True)
OUT = A @ V
assert S[2, 2] == 3.0 and np.allclose(A.sum(axis=1), 1.0)
assert np.allclose(OUT[0], A[0] @ V)

ACCENT, HILITE, WARM = "#58C4DD", "#5CD0B3", "#F4D345"
GOOD, PLUM, INK = "#83C167", "#CAA3E8", "#ECECEC"

STAGES = ["Embed", "Project", "Score", "Softmax", "Mix"]


def mat(cid, values, label, color, nd=0, label_side="above", entry_size=30):
    return ComponentSpec(
        id=cid, ctype="matrix",
        content={"values": values, "nd": nd, "label": label, "color": color,
                 "label_side": label_side, "entry_size": entry_size},
    )


def build_spec() -> SceneSpec:
    spec = SceneSpec(name="transformer-attention-v2", aspect=16 / 9,
                     density="comfortable",
                     output_dir=str(Path(__file__).parent / "media"))
    spec.components = {
        "title": ComponentSpec(id="title", ctype="title",
                               content={"text": "Attention, algebraically"}),
        "nav": ComponentSpec(id="nav", ctype="nav",
                             content={"stages": STAGES, "active": 0}),
        # embed
        "X": mat("X", X.tolist(), "X", INK, label_side="left"),
        # project
        "Q": mat("Q", Q.tolist(), "Q", ACCENT),
        "K": mat("K", K.tolist(), "K", HILITE),
        "V": mat("V", V.tolist(), "V", WARM),
        # score
        "KT": mat("KT", K.T.tolist(), "Kᵀ", HILITE),
        "S": mat("S", S.tolist(), "S = QKᵀ", INK),
        "hq3": ComponentSpec(id="hq3", ctype="highlight", owner="Q",
                             content={"target": "Q", "part": ["row", 2], "color": ACCENT}),
        "hk3": ComponentSpec(id="hk3", ctype="highlight", owner="KT",
                             content={"target": "KT", "part": ["col", 2], "color": HILITE}),
        "hs33": ComponentSpec(id="hs33", ctype="highlight", owner="S",
                              content={"target": "S", "part": ["entry", 2, 2], "color": WARM}),
        "exemplar": ComponentSpec(id="exemplar", ctype="text", owner="S",
                                  content={"text": "Sᵢⱼ = qᵢ·kⱼ, e.g. q₃·k₃ = 1·1 + 1·2 = 3",
                                           "side": "right",
                                           "font_size": 24, "color": WARM}),
        # softmax
        "A": mat("A", A.tolist(), "A = softmax(S/√dₖ)", GOOD, nd=2, entry_size=30),
        "rowtag": ComponentSpec(id="rowtag", ctype="text", owner="A",
                                content={"text": "each row sums to 1", "side": "below",
                                         "font_size": 24, "color": GOOD}),
        # mix
        "V2": mat("V2", V.tolist(), "V", WARM),   # V returns: a new object
        "Out": mat("Out", OUT.tolist(), "Out = A·V", PLUM, nd=2, entry_size=30),
        "eq": ComponentSpec(id="eq", ctype="equation", owner="Out", region="annotation",
                            content={"side": "below", "font_size": 30, "parts": [
                                ("Attn(", INK), ("Q", ACCENT), (", ", INK), ("K", HILITE),
                                (", ", INK), ("V", WARM), (") = softmax(QKᵀ/√dₖ)·V", INK),
                            ]}),
    }

    def stage(sid, tpl, comps, trans=None, timing=None, caption=None, overlaps=None, **kw):
        return StageSpec(id=sid, template=tpl, components=comps,
                         transition=trans or {}, timing=timing or
                         {"enter": 0.9, "move": 1.1, "exit": 0.5, "hold": 1.1},
                         caption=caption, permitted_overlaps=overlaps or [], **kw)

    spec.stages = [
        stage("embed", "single_center",
              {"title": "persistent", "nav": "persistent", "X": "entering"},
              trans={"title": "static", "nav": "static", "X": "fade_in"},
              caption="X: 3 tokens, each a 2-vector"),
        stage("project", "three_columns",
              {"title": "persistent", "nav": "persistent", "X": "leaving",
               "Q": "entering", "K": "entering", "V": "entering"},
              trans={"nav": "static", "X": "fade_in",
                     "Q": "fade_in", "K": "fade_in", "V": "fade_in"},
              caption="Q, K, V: three aligned projections of the same X"),
        stage("score", "operands_result",
              {"nav": "persistent", "Q": "changing", "K": "leaving", "V": "leaving",
               "KT": "entering", "S": "entering",
               "hq3": "entering", "hk3": "entering", "hs33": "entering",
               "exemplar": "entering"},
              trans={"Q": "move", "K": "fade_in", "V": "fade_in", "nav": "static",
                     "KT": "fade_in", "S": "fade_in", "hq3": "fade_in",
                     "hk3": "fade_in", "hs33": "fade_in", "exemplar": "fade_in"},
              operands=["Q", "KT"], result="S", min_gap=0.45),
        stage("softmax", "single_center",
              {"nav": "persistent", "S": "leaving",
               "hq3": "leaving", "hk3": "leaving", "hs33": "leaving",
               "exemplar": "leaving",
               "A": "entering", "rowtag": "entering"},
              trans={"nav": "static", "S": "fade_in", "hq3": "fade_in",
                     "hk3": "fade_in", "hs33": "fade_in", "exemplar": "fade_in",
                     "A": "fade_in", "rowtag": "fade_in"},
              caption="scale by 1/√dₖ, then softmax each row"),
        stage("mix", "input_op_output",
              {"nav": "persistent", "A": "changing", "rowtag": "leaving",
               "V2": "entering", "Out": "entering", "eq": "entering"},
              trans={"nav": "static", "A": "move", "V2": "fade_in", "rowtag": "fade_in",
                     "Out": "fade_in", "eq": "fade_in"},
              caption="each output token mixes all value vectors"),
    ]
    return spec


class TransformerAttentionV2(SpecScene):
    def setup(self):
        self.spec = build_spec()
        super().setup()
