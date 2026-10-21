# Reproducing "tex-demo"

Packaged: 2026-10-21T17:09:06 (source revision 17d09eb)

## Environment
- ManimGL 1.7.2 (3b1b edition, in its own venv)
- Python 3.10.9
- ffmpeg: imageio-ffmpeg
- animkit 0.2.0
- LaTeX: not required by this animation

## Commands (from a clone of the animkit repo; run `animkit check` first)

```
animkit validate examples/tex-demo
animkit render examples/tex-demo
```

## Source hashes at delivery
- scene.py: 7f272761a475
- theme.py: 55230e4302df
- project.json: caa2dbe69ec2
