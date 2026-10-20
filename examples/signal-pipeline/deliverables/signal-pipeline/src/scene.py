"""Signal Pipeline — sampling, DFT spectrum, ideal low-pass filter, and the
cleaned output. Every plotted value comes from numpy at import time: the
spectrum is abs(rfft(x)) and the output is irfft(X*H), so the animation *is*
the math. Render with:  animkit preview .   /   animkit render .
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np

from manimlib import *
from theme import *

# ---------------- signal + DSP (source of truth for every visual) -----------
FS = 32                    # sample rate, Hz
T_END = 2.0                # seconds
N = int(FS * T_END)        # 64 samples
T_CONT = np.linspace(0, T_END, 400)
X_CONT = np.sin(2 * np.pi * 1 * T_CONT) + 0.35 * np.sin(2 * np.pi * 7 * T_CONT)
T_SAMP = np.arange(N) / FS
X_SAMP = np.sin(2 * np.pi * 1 * T_SAMP) + 0.35 * np.sin(2 * np.pi * 7 * T_SAMP)
FREQS = np.fft.rfftfreq(N, 1 / FS)          # bin frequencies 0..16 Hz
SPEC = np.abs(np.fft.rfft(X_SAMP)) / (N / 2)  # magnitude, normalized
CUTOFF = 3.0
H = (FREQS <= CUTOFF).astype(float)         # ideal brick-wall filter
X_FILT = np.fft.irfft(np.fft.rfft(X_SAMP) * H, n=N)
X_CLEAN_CONT = np.sin(2 * np.pi * 1 * T_CONT)  # reference: the pure 1 Hz sine

assert FREQS[2] == 1.0 and FREQS[14] == 7.0            # peaks land on bins
assert np.isclose(SPEC[2], 1.0, atol=0.02)              # 1 Hz magnitude ~1
assert np.isclose(SPEC[14], 0.35, atol=0.02)            # 7 Hz magnitude ~0.35
assert SPEC[4] < 0.02 and SPEC[10] < 0.02               # leakage negligible
assert np.allclose(X_FILT[[8, 16, 24, 32, 40, 48]],     # filtered == pure sine
                   np.sin(2 * np.pi * T_SAMP[[8, 16, 24, 32, 40, 48]]), atol=0.01)

STAGES = ["Source", "Sample", "Spectrum", "Filter", "Output"]
CHIP_W, CHIP_H, CHIP_GAP = 2.35, 0.62, 0.35


class SignalPipeline(Scene):
    def construct(self):
        # ---- shared scaffolding: title + stage chips -----------------------
        title = heading("Cleaning a signal, step by step")
        chips, cursor = self.build_stage_row()

        self.play(FadeIn(title, shift=0.3 * DOWN), LaggedStart(
            *[FadeIn(c, scale=0.8) for c in chips], lag_ratio=0.12), run_time=1.2)
        self.play(FadeIn(cursor), run_time=FADE)
        self.wait(IDEA_PAUSE)

        # ---- stage 1: source ------------------------------------------------
        t_ax, curve = self.time_plot(X_CONT, T_CONT)
        src_lab = caption("x(t) = sin(2πt) + 0.35·sin(14πt)")
        self.move_cursor(cursor, chips, 0)
        self.play(ShowCreation(curve), FadeIn(t_ax), FadeIn(src_lab), run_time=1.6)
        self.wait(IDEA_PAUSE)

        # ---- stage 2: sample -------------------------------------------------
        dots = VGroup(*[
            Dot(t_ax.c2p(t, x), radius=0.055)
            .set_fill(GOOD, 1.0).set_stroke(width=0)
            for t, x in zip(T_SAMP, X_SAMP)
        ])
        fs_lab = caption("fs = 32 samples/s  (Nyquist: fs > 2·7 Hz)")
        self.move_cursor(cursor, chips, 1)
        self.play(LaggedStart(*[FadeIn(d, scale=0.5) for d in dots], lag_ratio=0.03),
                  FadeIn(fs_lab), run_time=1.8)
        self.wait(IDEA_PAUSE)

        # ---- stage 3: spectrum ------------------------------------------------
        self.move_cursor(cursor, chips, 2)
        bars, f_ax, bar_at = self.spectrum_plot(SPEC, FREQS)
        peak1 = label_for(bar_at[2], "1 Hz", UP, buff=0.12, size=CAPTION, color=ACCENT)
        peak2 = label_for(bar_at[14], "7 Hz", UP, buff=0.12, size=CAPTION, color=ACCENT)
        spec_lab = caption("X(f) = |DFT(x)|: two peaks, nothing in between")
        self.play(
            FadeOut(t_ax), FadeOut(curve), FadeOut(dots),
            FadeIn(f_ax), LaggedStart(*[GrowFromEdge(b, DOWN) for b in bars], lag_ratio=0.04),
            FadeIn(peak1), FadeIn(peak2), FadeOut(src_lab), FadeOut(fs_lab), FadeIn(spec_lab),
            run_time=1.8,
        )
        self.wait(1.75)

        # ---- stage 4: filter ---------------------------------------------------
        self.move_cursor(cursor, chips, 3)
        dead_idx = [i for i in bar_at if H[i] == 0]
        dead = VGroup(*[bar_at[i] for i in dead_idx])
        strike = VGroup(*[
            Line(bar_at[i].get_bottom() + 0.12 * LEFT, bar_at[i].get_top() + 0.12 * RIGHT)
            for i in dead_idx
        ]).set_stroke(BAD, width=4)
        filt_lab = caption("H(f): keep f ≤ 3 Hz — the 7 Hz peak must go")
        self.play(
            dead.animate.set_fill(BAD, opacity=0.35).set_stroke(BAD, width=2),
            ShowCreation(strike), FadeIn(filt_lab), FadeOut(peak2), FadeOut(spec_lab),
            run_time=1.4,
        )
        self.wait(IDEA_PAUSE)

        # ---- stage 5: output ----------------------------------------------------
        self.move_cursor(cursor, chips, 4)
        o_ax, clean_curve = self.time_plot(X_CLEAN_CONT, T_CONT, color=ACCENT_WARM)
        orig_curve = self.time_plot(X_CONT, T_CONT, color=INK_MUTED, opacity=0.35)[1]
        out_lab = caption("x̂(t): only the 1 Hz tone survives")
        self.play(
            FadeOut(f_ax), FadeOut(bars), FadeOut(strike), FadeOut(filt_lab),
            FadeIn(o_ax), FadeIn(orig_curve), ShowCreation(clean_curve), FadeIn(out_lab),
            run_time=1.8,
        )
        self.wait(2.5)

        # ---- closing -------------------------------------------------------------
        closer = caption("sample → transform → filter → invert")
        self.play(FadeIn(closer, shift=0.2 * UP), FadeOut(out_lab), run_time=FADE)
        self.wait(SECTION_PAUSE)
        self.play(*[FadeOut(m) for m in self.mobjects])
        self.wait(END_PAUSE)

    # -- helpers ----------------------------------------------------------------
    def build_stage_row(self):
        chips = VGroup()
        for i, name in enumerate(STAGES):
            chip = RoundedRectangle(width=CHIP_W, height=CHIP_H, corner_radius=0.12)
            chip.set_stroke(INK_MUTED, width=2)
            chip.set_fill(BLACK, opacity=0.0)
            lab = text(name, CAPTION, INK_MUTED)
            chip_lab = VGroup(chip, lab)
            chips.add(chip_lab)
        chips.arrange(RIGHT, buff=CHIP_GAP)
        chips.to_edge(UP, buff=1.05)
        cursor = RoundedRectangle(width=CHIP_W + 0.18, height=CHIP_H + 0.18, corner_radius=0.14)
        cursor.set_stroke(ACCENT, width=3)
        cursor.move_to(chips[0])
        # chip labels sit inside their rounded rects
        for group in chips:
            group[1].move_to(group[0])
        return chips, cursor

    def move_cursor(self, cursor, chips, idx):
        self.play(cursor.animate.move_to(chips[idx]), run_time=0.5)

    def time_plot(self, xs, ts, color=INK_MUTED, opacity=1.0):
        ax = Axes(
            x_range=[0, T_END, 0.5], y_range=[-1.6, 1.6, 1],
            width=9.5, height=3.4,
            axis_config=dict(stroke_color=INK_MUTED, stroke_width=2,
                             include_tip=False, tick_size=0.06),
        )
        ax.move_to(ORIGIN + 0.25 * DOWN)
        curve = ax.get_graph(lambda t: float(np.interp(t, ts, xs)), x_range=[0, T_END])
        curve.set_stroke(color, width=4, opacity=opacity)
        return ax, curve

    def spectrum_plot(self, spec, freqs):
        ax = Axes(
            x_range=[0, 16, 2], y_range=[0, 1.2, 0.5],
            width=9.5, height=3.4,
            axis_config=dict(stroke_color=INK_MUTED, stroke_width=2,
                             include_tip=False, tick_size=0.06),
        )
        ax.move_to(ORIGIN + 0.25 * DOWN)
        bars = VGroup()
        bar_at = {}
        for i, (f, mag) in enumerate(zip(freqs, spec)):
            if mag < 0.01:
                continue
            bottom = ax.c2p(f - 0.35, 0)
            bar = RoundedRectangle(
                width=0.62,
                height=max(mag * (ax.get_height() / 1.2), 0.03),
                corner_radius=0.03,
            )
            bar.set_fill(ACCENT, opacity=0.85)
            bar.set_stroke(ACCENT, width=1)
            bar.move_to(bottom, aligned_edge=DOWN)
            bars.add(bar)
            bar_at[i] = bar
        return bars, ax, bar_at
