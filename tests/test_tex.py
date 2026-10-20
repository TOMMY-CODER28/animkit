"""Conditional TeX test: exercised only when a TeX toolchain is present.

Verifies the two failure modes this setup actually hit:
  1. toolchain health  — a digit compiles with non-empty glyph defs
  2. per-part coloring — distinct tex parts produce distinct mobjects
     (guards against the tex_to_color_map cache bug in this ManimGL build)
"""

import os
import unittest

from animkit.env import find_latex, latex_path_env


@unittest.skipIf(find_latex() is None, "no TeX toolchain on this machine")
class TestTexEquations(unittest.TestCase):
    def _build(self, parts):
        from animkit.layout.spec import ComponentSpec
        from animkit.layout.components import make_equation_component
        cs = ComponentSpec(id="t", ctype="equation",
                           content={"parts": parts, "mode": "tex",
                                    "font_size": 34})
        return make_equation_component(cs)

    def test_digit_compiles_with_glyphs(self):
        g = self._build([("0", None)])
        self.assertGreater(g.group.get_width(), 0.05, "digit compiled to empty SVG — "
                           "dvisvgm/ghostscript/font-map problem; clear "
                           "ManimGL's tex disk cache and re-run")

    def test_distinct_parts_are_distinct_mobjects(self):
        """Regression: with tex_to_color_map, a second formula could come back
        with the first formula's cached geometry."""
        g = self._build([(r"\int_{-\infty}^{\infty} e^{-x^2}\,dx", "#ECECEC"),
                         (r" = \sqrt{\pi}", "#F4D345")])
        a = self._build([(r"\mathrm{Attn}", "#ECECEC"),
                         (r"(Q,", "#ECECEC"), (r"K", "#5CD0B3"),
                         (r") = \mathrm{softmax}\left(", "#ECECEC"),
                         (r"\frac{QK^{\top}}{\sqrt{d_k}}", "#58C4DD"),
                         (r"\right)V", "#ECECEC")])
        self.assertNotAlmostEqual(g.group.get_width(), a.group.get_width(), places=2,
                                  msg="two different TeX equations measured "
                                  "identically — the Tex cache is returning "
                                  "the wrong mobject")

    def test_unmatched_delimiters_sanitized(self):
        """\\left/\\right split across parts must still compile (animkit strips
        them per part; this build masks latex failures with stale DVIs)."""
        g = self._build([(r"\mathrm{Attn}\left(", None),
                         (r"\frac{QK^{\top}}{\sqrt{d_k}}", "#58C4DD"),
                         (r"\right)V", None)])
        self.assertGreater(g.group.get_width(), 1.0)


if __name__ == "__main__":
    unittest.main()
