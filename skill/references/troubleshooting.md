# Troubleshooting — error → cause → fix

All items below were either actually hit in this setup or are its known
failure modes. Full logs live at `<project>/runs/<id>/log.txt`; the JSON
result's `error_excerpt` carries the tail.

## Environment

| Symptom | Cause | Fix |
|---|---|---|
| `No module named 'av'` importing manimlib | interrupted venv setup | `<venv>\Scripts\python.exe -m pip install av` |
| `manimgl` not found | venv path changed | update `<animkit>\animkit_config.json` or set `ANIMKIT_MANIMGL`; re-run `animkit.cmd check` |
| render fails, log shows ffmpeg missing/failed | ffmpeg binary absent | `<venv>\Scripts\python.exe -m pip install imageio-ffmpeg` (animkit finds it automatically) |
| `pydub ... Couldn't find ffmpeg` warning | harmless (pydub probes PATH) | ignore |
| `animkit frames` says av not importable | ran with system python | use `animkit.cmd` / `animkit.sh` wrappers |
| Window pops up during render | manimgl called without `-w` | never call manimgl directly; animkit always passes `-w` |

## Scene code (this build)

| Error in log | Cause | Fix |
|---|---|---|
| `NameError: name 'Create' is not defined` | ManimCE name | use `ShowCreation` |
| `TypeError: Object <bound method ...> cannot be converted to an animation` | old method-animation syntax | `mob.animate.method(...)` |
| `TypeError`/crash inside `Tex(...)` / `get_axis_labels` | no LaTeX installed | `Text` + Unicode via `math_text()`; theme `axis_label()` |
| Shape renders red (or default grey) though you passed `color=` | shape pins `stroke_color` default | pass `stroke_color=`/`fill_color=` or `.set_stroke()` |
| `AttributeError: 'Axes' object has no attribute 'height'` | property doesn't exist | `ax.get_height()` |
| `IndexError: list index out of range` on `group[i]` | filtered group no longer aligns with data indices | keep an explicit dict `key -> mobject` |
| Scene renders but video missing | wrong scene name / class mismatch | `animkit.cmd validate <project>` catches it — run it first |
| Import of scene fails only at render (`validate --deep` catches) | module-level code (numpy asserts) failing | read the traceback line in `runs/<id>/log.txt` |

## Render process

| Symptom | Cause | Fix |
|---|---|---|
| `status: timeout` | scene longer than `timing.*_timeout_s` | shorten scene, or raise timeout in project.json |
| Video has 0 frames / tiny file | scene's construct exited immediately | check for early `return` / exception mid-scene in log |
| Stale video reported after a failed run | old file from previous run | animkit deletes the expected file pre-render; if you bypassed it, remove `media/` |
| Frame extraction finds video ended before last target | normal for `--at` fractions near 1.0 | use fractions ≤ 0.95 |

## GPU / wgpu

Headless `-w` rendering still uses the GPU via wgpu. If a machine has no
usable GPU adapter, renders fail at startup with a wgpu adapter error —
there is no tested CPU fallback in this setup; report it rather than
attempting workarounds.
