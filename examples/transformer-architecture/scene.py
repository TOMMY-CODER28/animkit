"""Transformer Architecture — the full block, mathematically, spec-driven.

Embeddings + sinusoidal positional encoding -> multi-head attention ->
Add & Norm -> position-wise FFN -> the assembled block -> stacking.
Every displayed number is computed by numpy at import time (with asserts).
Render with:  animkit preview .   /   animkit render .
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
    sys.path.insert(0, _root or (str(_anc[0]) if _anc else ""))

import numpy as np

from manimlib import *
from animkit.layout import SceneSpec, StageSpec, ComponentSpec, SpecScene

# ---------------- the math (single source of truth) -------------------------
N, D = 3, 2                                    # 3 tokens, model dim 2 (readable)
E = np.array([[0.10, -0.20],                   # learned token embeddings
              [0.50, 0.30],
              [-0.40, 0.60]])
POS = np.arange(N)
PE = np.stack([np.sin(POS / (10000 ** (0 / D))),
               np.cos(POS / (10000 ** (0 / D)))], axis=1)   # d=2: sin(p), cos(p)
X = E + PE                                     # input to block 1

def softmax_rows(m):
    e = np.exp(m)
    return e / e.sum(axis=1, keepdims=True)

A = softmax_rows(X @ X.T / np.sqrt(D)) @ X     # one head, identity projections
def ln(m):                                     # LayerNorm, gamma=1, beta=0
    mu = m.mean(axis=1, keepdims=True)
    sd = m.std(axis=1, keepdims=True)
    return (m - mu) / sd
XP = ln(X + A)                                 # after attention sublayer
assert np.allclose(XP.mean(axis=1), 0, atol=1e-9)
assert np.allclose(XP.std(axis=1), 1, atol=1e-9)

rng = np.random.default_rng(7)
W1 = rng.normal(0, 0.6, (D, 4))                # d -> d_ff = 4
W2 = rng.normal(0, 0.6, (4, D))
H = np.maximum(0, XP @ W1)                     # ReLU hidden layer
XPP = H @ W2                                   # back to d
assert XPP.shape == (N, D) and np.all(np.isfinite(XPP))

INK, MUT = "#ECECEC", "#AAB2BA"
ACCENT, HILITE, WARM, GOOD, PLUM = "#58C4DD", "#5CD0B3", "#F4D345", "#83C167", "#CAA3E8"

STAGES = ["Embed", "MHA", "+Norm", "FFN", "Block", "Stack"]


def mat(cid, values, label, color, nd=2, label_side="above", entry_size=28):
    return ComponentSpec(
        id=cid, ctype="matrix",
        content={"values": values, "nd": nd, "label": label, "color": color,
                 "label_side": label_side, "entry_size": entry_size},
    )


def eq(cid, parts, region="main", font_size=28, owner=None, side="below"):
    return ComponentSpec(id=cid, ctype="equation", region=region, owner=owner,
                         content={"parts": parts, "font_size": font_size, "side": side})


def build_spec() -> SceneSpec:
    spec = SceneSpec(name="transformer-architecture", aspect=16 / 9,
                     density="comfortable",
                     output_dir=str(Path(__file__).parent / "media"))
    spec.components = {
        "title": ComponentSpec(id="title", ctype="title",
                               content={"text": "The Transformer, mathematically"}),
        "nav": ComponentSpec(id="nav", ctype="nav",
                             content={"stages": STAGES, "active": 0}),

        # ---- embed ----
        "E":  mat("E", E.tolist(), "E (learned)", INK),
        "PE": mat("PE", PE.tolist(), "PE (position)", MUT),
        "X":  mat("X", X.tolist(), "X = E + PE", ACCENT),

        # ---- mha ----
        "mha_eq": eq("mha_eq", [
            ("A = softmax(", INK), ("X", ACCENT), ("X", ACCENT), ("ᵀ", INK),
            ("/√2)·", INK), ("X", ACCENT),
            ("   one head, identity projections", MUT)], font_size=26,
            owner="A", side="above"),
        "A": mat("A", A.tolist(), "A", HILITE),
        "heads_note": ComponentSpec(id="heads_note", ctype="text", owner="A",
                                    content={"text": "h heads in parallel → concat → Wo",
                                             "side": "below", "font_size": 22, "color": MUT}),

        # ---- +Norm ----
        "Xp": mat("Xp", XP.tolist(), "X′ = LN(X + A)", GOOD, entry_size=26),
        "ln_eq": eq("ln_eq", [
            ("LN(x) = γ ⊙ (x − μ) / σ + β", INK),
            ("   per token: rows of X′ have mean 0, std 1", MUT)], region="annotation",
            owner="Xp", font_size=26),

        # ---- ffn ----
        "H":  mat("H", H.tolist(), "ReLU(X′W₁)  (d → 4)", WARM, entry_size=24),
        "Xpp": mat("Xpp", XPP.tolist(), "X″", PLUM, entry_size=28),
        "ffn_eq": eq("ffn_eq", [
            ("FFN(x) = ReLU(xW₁)W₂", INK),
            ("   position-wise, d → 4 → d", MUT)], region="annotation", font_size=26),

        # ---- block ----
        "block_eq": eq("block_eq", [
            ("X′ = LN(", INK), ("X", ACCENT), (" + ", INK), ("MHA(X)", HILITE),
            (")      X″ = LN(", INK), ("X′", GOOD), (" + ", INK), ("FFN(X′)", WARM),
            (")", INK)], font_size=26),
        "stack_note": ComponentSpec(id="stack_note", ctype="text", region="annotation",
                                    content={"text": "one encoder block — each block has its own "
                                                     "Wq Wk Wv Wo W₁ W₂, γ, β",
                                             "font_size": 24, "color": MUT}),

        # ---- stack ----
        "mult": ComponentSpec(id="mult", ctype="text",
                              content={"text": "× L blocks", "font_size": 60, "color": INK}),
    }

    def stage(sid, tpl, comps, trans=None, caption=None, **kw):
        return StageSpec(id=sid, template=tpl, components=comps,
                         transition=trans or {}, caption=caption,
                         timing={"enter": 0.9, "move": 1.1, "exit": 0.5, "hold": 1.2},
                         **kw)

    F = {"enter": 0.9, "move": 1.1, "exit": 0.5, "hold": 1.2}
    spec.stages = [
        stage("embed", "input_op_output",
              {"title": "persistent", "nav": "persistent",
               "E": "entering", "PE": "entering", "X": "entering"},
              trans={"title": "static", "nav": "static", "E": "fade_in",
                     "PE": "fade_in", "X": "fade_in"},
              caption="tokens become vectors: X = E + PE (sin/cos of position)"),
        stage("mha", "two_columns",
              {"nav": "persistent", "X": "changing",
               "mha_eq": "entering", "A": "entering", "heads_note": "entering"},
              trans={"nav": "static", "X": "move", "mha_eq": "fade_in",
                     "A": "fade_in", "heads_note": "fade_in"},
              caption="attention: every token mixes every other"),
        stage("resnorm", "input_op_output",
              {"nav": "persistent", "X": "persistent", "A": "persistent",
               "mha_eq": "leaving", "heads_note": "leaving",
               "Xp": "entering", "ln_eq": "entering"},
              trans={"nav": "static", "X": "move", "A": "move",
                     "Xp": "fade_in", "ln_eq": "fade_in"},
              caption="Add & Norm: residual, then LayerNorm"),
        stage("ffn", "input_op_output",
              {"nav": "persistent", "Xp": "persistent",
               "ln_eq": "leaving", "X": "leaving", "A": "leaving",
               "H": "entering", "Xpp": "entering", "ffn_eq": "entering"},
              trans={"nav": "static", "Xp": "move", "H": "fade_in",
                     "Xpp": "fade_in", "ffn_eq": "fade_in"},
              caption="position-wise MLP: expand, ReLU, project back"),
        stage("block", "equation_explanation",
              {"nav": "persistent", "Xp": "leaving", "H": "leaving", "Xpp": "persistent",
               "ffn_eq": "leaving", "block_eq": "entering", "stack_note": "entering"},
              trans={"nav": "static", "Xpp": "move", "block_eq": "fade_in",
                     "stack_note": "fade_in"},
              equation="block_eq"),
        stage("stack", "single_center",
              {"nav": "persistent", "Xpp": "leaving", "block_eq": "leaving",
               "stack_note": "leaving", "mult": "entering"},
              trans={"nav": "static", "mult": "fade_in"},
              caption="then the decoder: masked self-attention + cross-attention"),
    ]
    return spec


class TransformerArchitecture(SpecScene):
    def setup(self):
        self.spec = build_spec()
        super().setup()
