"""Tex Demo — spec-driven scene with real LaTeX equations (mode="tex")."""

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

from manimlib import *
from animkit.layout import SceneSpec, StageSpec, ComponentSpec, SpecScene

INK, MUT, ACCENT, HILITE, WARM = "#ECECEC", "#AAB2BA", "#58C4DD", "#5CD0B3", "#F4D345"
STAGES = ["Gauss", "Attention"]


def eq(cid, parts, mode="text", font_size=30, owner=None, side="below"):
    return ComponentSpec(id=cid, ctype="equation",
                         content={"parts": parts, "mode": mode,
                                  "font_size": font_size, "side": side},
                         owner=owner)


def build_spec() -> SceneSpec:
    spec = SceneSpec(name="tex-demo", aspect=16 / 9, density="comfortable",
                     output_dir=str(Path(__file__).parent / "media"))
    spec.components = {
        "title": ComponentSpec(id="title", ctype="title",
                               content={"text": "Real LaTeX, rendered"}),
        "nav": ComponentSpec(id="nav", ctype="nav",
                             content={"stages": STAGES, "active": 0}),
        "gauss": eq("gauss", [
            (r"\int_{-\infty}^{\infty} e^{-x^2}\,dx", INK),
            (r" = \sqrt{\pi}", WARM),
        ], mode="tex"),
        "attention": eq("attention", [
            (r"\mathrm{Attn}", INK),
            (r"(Q,", INK), (r"K", HILITE), (r",", INK), (r"V", WARM), (r") = \mathrm{softmax}\!\left(", INK),
            (r"\frac{QK^{\top}}{\sqrt{d_k}}", ACCENT),
            (r"\right)V", INK),
        ], mode="tex"),
    }
    spec.stages = [
        StageSpec(id="gauss", template="single_center",
                  components={"title": "persistent", "nav": "persistent",
                              "gauss": "entering"},
                  transition={"title": "static", "nav": "static", "gauss": "write"},
                  caption="the Gaussian integral, typeset by latex + dvisvgm"),
        StageSpec(id="attention", template="single_center",
                  components={"nav": "persistent", "gauss": "leaving",
                              "attention": "entering"},
                  transition={"nav": "static", "gauss": "fade_in",
                              "attention": "write"},
                  caption="scaled dot-product attention in real TeX"),
    ]
    return spec


class TexDemo(SpecScene):
    def setup(self):
        self.spec = build_spec()
        super().setup()
