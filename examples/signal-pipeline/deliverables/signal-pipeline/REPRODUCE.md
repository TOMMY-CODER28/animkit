# Reproducing "signal-pipeline"

Packaged: 2026-10-17T17:25:37

## Environment
- ManimGL 1.7.2 at `<manim-venv>\Scripts\manimgl.exe`
- Python 3.10.9 (`<manim-venv>\Scripts\python.exe`)
- ffmpeg: `<manim-venv>\lib\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe` (imageio-ffmpeg)
- animkit 0.1.0
- No LaTeX required by this animation

## Commands (Windows, any shell; quotes needed if paths contain spaces)

```
cd "<animkit>\examples\signal-pipeline"
"<animkit>\animkit.cmd" validate .
"<animkit>\animkit.cmd" render .
```

## Source hashes at delivery
- scene.py: 326ec3c59090
- theme.py: 55230e4302df
- project.json: cab4bf384633
