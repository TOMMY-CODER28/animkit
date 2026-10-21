"""animkit.audio — narration generation for spec-driven scenes.

Providers turn a stage's narration text into one WAV file per stage and
report through animkit's standard result format
({ok, status, outputs, errors, next_actions}). Provider-specific code lives
here; scene composition never imports a provider directly — it consumes the
audio manifest (media/audio/audio_manifest.json) written by `animkit audio`.

Public API:
    generate_project_audio(spec, out_dir, config, force, log) -> dict
"""

import json
from pathlib import Path

from animkit.audio.kokoro_provider import KokoroProvider, KOKORO_SAMPLE_RATE

__all__ = ["KokoroProvider", "KOKORO_SAMPLE_RATE",
           "generate_project_audio", "generate_stage_audio"]

CACHE_FILE = "audio_manifest.json"


def generate_stage_audio(provider, stage_id, text, out_dir, force=False):
    """One stage -> one WAV. Returns provider result dict."""
    return provider.generate_stage(stage_id=stage_id, text=text,
                                   out_dir=out_dir, force=force)


def generate_project_audio(spec, out_dir, config=None, force=False, log=None):
    """Generate narration for every stage that declares narration text.

    spec:   SceneSpec (stages carry .narration)
    out_dir: directory for WAVs + manifest (typically <project>/media/audio)
    config: overrides for spec.audio {voice, speed, lang, pad}
    Returns animkit-style result dict with outputs.audio_manifest.
    """
    config = {**(spec.audio or {}), **(config or {})}
    stages = [(s.id, s.narration.strip()) for s in spec.stages
              if getattr(s, "narration", None) and s.narration.strip()]
    if not stages:
        return {"ok": False, "status": "config_error",
                "errors": ["no stage declares narration — add narration=... to "
                           "StageSpecs, or audio generation has nothing to do"],
                "next_actions": ["Set narration= on stages, or run without audio"]}

    from pathlib import Path
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        provider = KokoroProvider(lang=config.get("lang", "a"),
                                  voice=config.get("voice", "af_heart"),
                                  speed=float(config.get("speed", 1.0)))
    except Exception as exc:
        return {"ok": False, "status": "failure",
                "errors": [f"audio provider unavailable: {exc}"],
                "next_actions": [
                    "install the audio extra into the ManimGL venv: "
                    "pip install -e .[audio]  (or: pip install kokoro soundfile)",
                    "English G2P fallback needs eSpeak NG: "
                    "winget install eSpeak-NG.eSpeak-NG"]}

    manifest = {}
    errors = []
    for stage_id, text in stages:
        if log:
            log(f"[audio] {stage_id}: {len(text)} chars")
        res = provider.generate_stage(stage_id=stage_id, text=text,
                                      out_dir=out_dir, force=force)
        if not res.get("ok"):
            errors.extend(f"{stage_id}: {e}" for e in res.get("errors", []))
            continue
        manifest[stage_id] = res["outputs"]

    total = round(sum(m["duration_s"] for m in manifest.values()), 2)
    result = {
        "ok": not errors and bool(manifest),
        "status": "success" if (not errors and manifest) else "failure",
        "outputs": {
            "audio_dir": str(out_dir),
            "audio_manifest": manifest,
            "manifest_file": str(out_dir / CACHE_FILE),
            "total_narration_s": total,
        },
        "details": {"stages": len(stages), "generated": len(manifest),
                    "voice": config.get("voice", "af_heart"),
                    "speed": config.get("speed", 1.0),
                    "lang": config.get("lang", "a")},
        "errors": errors,
        "next_actions": (["run `animkit render <project>` — holds extend to fit "
                          "narration"] if not errors else
                         ["fix the errors above, re-run audio generation"]),
    }
    (out_dir / CACHE_FILE).write_text(json.dumps(
        {"config": {k: config.get(k) for k in ("voice", "speed", "lang", "pad")},
         "stages": manifest}, indent=2))
    return result


def build_narration_track(stage_times, manifest, out_dir, ffmpeg_exe=None):
    """Assemble one 24 kHz narration track aligned to the video timeline:
    silence until each stage's t_start, then that stage's WAV. Returns the
    track path and total duration. Requires soundfile + numpy only."""
    import numpy as np
    import soundfile as sf
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    track_path = out_dir / "narration_track.wav"

    sr = None
    total = 0.0
    segments = []
    for s in sorted(stage_times, key=lambda x: x["t_start"]):
        info = manifest.get(s["stage"])
        if not info:
            continue
        data, sr_i = sf.read(info["path"], dtype="float32")
        sr = sr or sr_i
        start_frame = int(round(s["t_start"] * sr))
        cursor_frame = int(round(total * sr))
        segments.append((start_frame, data))
        total = max(total, s["t_start"] + len(data) / sr)
    if sr is None:
        raise ValueError("no narration audio to assemble")

    n = int(round(total * sr)) + sr // 10  # +0.1 s tail
    track = np.zeros(n, dtype="float32")
    for start_frame, data in segments:
        end = min(start_frame + len(data), n)
        track[start_frame:end] += data[: end - start_frame]
    sf.write(str(track_path), track, sr)
    return {"path": str(track_path), "duration_s": round(n / sr, 3),
            "sample_rate": sr}


def mux_narration(video: str, narration_wav: str, ffmpeg_exe: str,
                  out_path: str | None = None) -> dict:
    """Mux the narration track into the rendered video (video stream copied,
    audio encoded AAC). Overwrites out_path (default: alongside the video)."""
    import subprocess
    from pathlib import Path
    video = Path(video)
    out = Path(out_path) if out_path else video.with_name(
        video.stem + "_narrated.mp4")
    proc = subprocess.run(
        [ffmpeg_exe, "-y", "-i", str(video), "-i", narration_wav,
         "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
         "-shortest", str(out)],
        capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        return {"ok": False, "status": "failure",
                "errors": [f"ffmpeg mux failed: {proc.stderr[-400:]}"],
                "next_actions": ["check the ffmpeg build supports aac"]}
    return {"ok": True, "status": "success",
            "outputs": {"narrated_video": str(out)},
            "errors": [], "next_actions": []}
