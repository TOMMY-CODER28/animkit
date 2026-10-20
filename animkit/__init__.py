"""animkit — a thin, provider-independent harness around ManimGL.

It turns "AI writes scene code" into a reliable pipeline:
brief -> validate -> preview -> frames -> inspect -> revise -> final render -> deliver.

Design rules:
  - Stdlib-only package code; heavy deps (av, Pillow, imageio_ffmpeg, yaml) are used
    only through the render environment's interpreter (the manim venv).
  - Every command returns a structured result (dict) and prints human or JSON output.
  - Exit codes: 0 success, 1 failure, 2 usage/config error, 3 timeout.
"""

__version__ = "0.2.0"
