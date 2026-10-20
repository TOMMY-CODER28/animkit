"""Gaussian Sum — animated from script.md (script-first workflow).

Every stage maps 1:1 to a stage in script.md; every number on screen is
computed below and asserted against the script's claims.
Render with:  animkit preview .   /   animkit render .
"""

import sys
from pathlib import Path
import animkit  # resolved via pip install -e . or ANIMKIT_ROOT

import numpy as np

from manimlib import *
from animkit.layout import SceneSpec, StageSpec, ComponentSpec, SpecScene

# ---- script Math: lines, computed and asserted -----------------------------
N = 100
PAIRS = [(k, N + 1 - k) for k in range(1, 4)]          # (1,100), (2,99), (3,98)
PAIR_SUM = N + 1                                       # 101 — every pair sums to this
for a, b in PAIRS:
    assert a + b == PAIR_SUM
N_PAIRS = N // 2                                       # 50
TOTAL = N * (N + 1) // 2                               # 5050
assert TOTAL == N_PAIRS * PAIR_SUM
assert N * (N + 1) / 2 == 5050

INK, MUT = "#ECECEC", "#AAB2BA"
ACCENT, HILITE, WARM, GOOD = "#58C4DD", "#5CD0B3", "#F4D345", "#83C167"

STAGES = ["Claim", "Pair", "Count", "Formula"]


def eq(cid, parts, font_size=30, region="main", owner=None, side="below"):
    return ComponentSpec(id=cid, ctype="equation", region=region, owner=owner,
                         content={"parts": parts, "font_size": font_size,
                                  "side": side})


def build_spec() -> SceneSpec:
    spec = SceneSpec(name="gaussian-sum", aspect=16 / 9, density="comfortable",
                     output_dir=str(Path(__file__).parent / "media"))
    spec.components = {
        "title": ComponentSpec(id="title", ctype="title",
                               content={"text": "The Gauss pairing trick"}),
        "nav": ComponentSpec(id="nav", ctype="nav",
                             content={"stages": STAGES, "active": 0}),

        # stage 1 — the claim
        "claim": eq("claim", [
            ("1 + 2 + 3 + ⋯ + 100 = ?", INK)], font_size=34),

        # stage 2 — pair them up
        "pairing": eq("pairing", [
            ("(", INK), ("1", ACCENT), (" + ", INK), ("100", HILITE), (") + (", INK),
            ("2", ACCENT), (" + ", INK), ("99", HILITE), (") + (", INK),
            ("3", ACCENT), (" + ", INK), ("98", HILITE), (") + ⋯", INK)], font_size=30),
        "pair_note": ComponentSpec(id="pair_note", ctype="text", owner="pairing",
                                   content={"text": "every pair sums to 101",
                                            "side": "below", "font_size": 24, "color": MUT}),

        # stage 3 — count the pairs
        "count": eq("count", [
            ("50 pairs × 101", INK)], font_size=34),
        "count_note": ComponentSpec(id="count_note", ctype="text", owner="count",
                                    content={"text": "100 numbers → 50 pairs, each summing to 101",
                                             "side": "below", "font_size": 24, "color": MUT}),

        # stage 4 — the formula
        "formula": eq("formula", [
            ("1 + 2 + ⋯ + n = ", INK), ("n(n + 1) / 2", WARM)], font_size=32),
        "value": eq("value", [
            ("n = 100 → ", MUT), ("100 · 101 / 2 = ", INK), ("5050", GOOD)],
            font_size=30, owner="formula"),
    }

    def stage(sid, comps, trans, caption):
        return StageSpec(id=sid, template="single_center", components=comps,
                         transition=trans, caption=caption,
                         timing={"enter": 0.9, "move": 1.0, "exit": 0.5, "hold": 1.3})

    spec.stages = [
        stage("claim",
              {"title": "persistent", "nav": "persistent", "claim": "entering"},
              {"title": "static", "nav": "static", "claim": "write"},
              "how do you add the first hundred numbers?"),
        stage("pair",
              {"nav": "persistent", "claim": "leaving",
               "pairing": "entering", "pair_note": "entering"},
              {"nav": "static", "claim": "fade_in", "pairing": "fade_in",
               "pair_note": "fade_in"},
              "pair first and last — every pair sums to 101"),
        stage("count",
              {"nav": "persistent", "pairing": "leaving", "pair_note": "leaving",
               "count": "entering", "count_note": "entering"},
              {"nav": "static", "pairing": "fade_in", "pair_note": "fade_in",
               "count": "fade_in", "count_note": "fade_in"},
              "a hundred numbers make fifty pairs"),
        stage("formula",
              {"nav": "persistent", "count": "leaving", "count_note": "leaving",
               "formula": "entering", "value": "entering"},
              {"nav": "static", "count": "fade_in", "count_note": "fade_in",
               "formula": "write", "value": "fade_in"},
              "half of n, times n plus one"),
    ]
    return spec


class GaussianSum(SpecScene):
    def setup(self):
        self.spec = build_spec()
        super().setup()
