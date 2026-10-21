"""Kokoro TTS provider (hexgrad/Kokoro-82M) — the reference animkit audio
provider. Kept strictly inside this module: scene composition consumes only
the WAV files + manifest this writes, never this code.

Guarantees required by the audio module spec:
  - the KPipeline is loaded once per generation process (lru_cache on the
    lang_code; first use downloads hexgrad/Kokoro-82M from Hugging Face),
  - long narration produces multiple chunks; chunk files are numbered so
    earlier chunks are never overwritten,
  - chunks are combined into ONE WAV per stage,
  - the combined file is cached (content hash of text+voice+speed+lang),
  - every failure surfaces as an animkit-style result dict.

English (`lang_code="a"`) uses misaki's G2P with an eSpeak NG fallback —
install eSpeak NG or some words will phonemize incorrectly.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

KOKORO_SAMPLE_RATE = 24000  # Kokoro-82M outputs 24 kHz


def _espeak_path_prefix() -> str:
    """Best-effort: put known eSpeak NG install locations on PATH so misaki's
    G2P fallback finds espeak-ng without requiring a new shell."""
    extra = []
    for cand in (r"C:\Program Files\eSpeak NG",
                 os.path.join(os.environ.get("LOCALAPPDATA", ""),
                              "Programs", "eSpeak NG")):
        if os.path.isfile(os.path.join(cand, "espeak-ng.exe")):
            extra.append(cand)
    return os.pathsep.join(extra)


def _kokoro_env() -> dict:
    env = dict(os.environ)
    prefix = _espeak_path_prefix()
    if prefix:
        env["PATH"] = prefix + os.pathsep + env.get("PATH", "")
    return env


_PIPELINES: dict[str, object] = {}


def get_pipeline(lang_code: str = "a"):
    """Load the Kokoro pipeline once per process per language."""
    if lang_code not in _PIPELINES:
        os.environ["PATH"] = _kokoro_env()["PATH"]
        from kokoro import KPipeline  # heavy import: torch etc.
        _PIPELINES[lang_code] = KPipeline(lang_code=lang_code)
    return _PIPELINES[lang_code]


class KokoroProvider:
    def __init__(self, lang: str = "a", voice: str = "af_heart",
                 speed: float = 1.0):
        self.lang = lang
        self.voice = voice
        self.speed = speed

    # ---------------------------------------------------------------- api --
    def generate_stage(self, stage_id: str, text: str, out_dir,
                       force: bool = False) -> dict:
        """Synthesize one stage's narration -> one combined WAV.

        Returns {"ok", "status", "outputs": {path, sample_rate, duration_s,
        cached, chunks}, "errors", "next_actions"}."""
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        key = self._cache_key(text)
        wav_path = out_dir / f"{stage_id}-{key}.wav"

        if wav_path.is_file() and wav_path.stat().st_size > 44 and not force:
            info = self._measure(wav_path)
            return {"ok": True, "status": "success",
                    "outputs": {**info, "cached": True, "chunks": 0},
                    "errors": [], "next_actions": []}

        try:
            chunks = self._synthesize(text)
        except Exception as exc:
            return self._failure(
                exc,
                ["check the toolchain: pip install -e .[audio] (kokoro, "
                 "soundfile) and eSpeak NG (winget install eSpeak-NG.eSpeak-NG)",
                 "first generation downloads hexgrad/Kokoro-82M (~330 MB) — "
                 "ensure internet access; re-run afterwards"])

        if not chunks:
            return self._failure("pipeline produced no audio chunks",
                                 ["check narration text is not empty"])

        # numbered chunk files: earlier chunks are never overwritten
        chunk_paths = []
        try:
            import soundfile as sf
            for i, audio in enumerate(chunks):
                cp = out_dir / f"{wav_path.stem}.chunk{i:03d}.wav"
                sf.write(str(cp), audio, KOKORO_SAMPLE_RATE)
                chunk_paths.append(cp)
            combined, sr = self._combine(chunk_paths)
            sf.write(str(wav_path), combined, sr)
        except Exception as exc:
            return self._failure(exc, ["keep partial chunk files for diagnosis "
                                       f"({len(chunk_paths)} written)"])

        # clean chunk files only after the combined write succeeded
        for cp in chunk_paths:
            cp.unlink(missing_ok=True)

        info = self._measure(wav_path)
        return {"ok": True, "status": "success",
                "outputs": {**info, "cached": False, "chunks": len(chunks)},
                "errors": [], "next_actions": []}

    # ----------------------------------------------------------- internals --
    def _cache_key(self, text: str) -> str:
        material = f"{self.lang}|{self.voice}|{self.speed}|{text}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]

    def _synthesize(self, text: str) -> list:
        """Run the pipeline once per process; yield numpy chunks in order."""
        import numpy as np
        pipeline = get_pipeline(self.lang)
        chunks = []
        for _gs, _ps, audio in pipeline(text, voice=self.voice,
                                        speed=self.speed):
            if hasattr(audio, "numpy"):
                audio = audio.numpy()
            chunks.append(np.asarray(audio, dtype="float32"))
        return chunks

    @staticmethod
    def _combine(chunk_paths: list[Path]):
        import soundfile as sf
        import numpy as np
        data, sr = [], None
        for p in chunk_paths:
            d, s = sf.read(str(p), dtype="float32")
            data.append(d)
            sr = sr or s
            if s != sr:
                raise ValueError(f"sample rate changed mid-stage: {sr} -> {s}")
        return (np.concatenate(data) if len(data) > 1 else data[0]), sr

    @staticmethod
    def _measure(path: Path) -> dict:
        import soundfile as sf
        info = sf.info(str(path))
        return {"path": str(path), "sample_rate": info.samplerate,
                "duration_s": round(info.frames / info.samplerate, 3)}

    @staticmethod
    def _failure(exc, next_actions: list[str]) -> dict:
        return {"ok": False, "status": "failure",
                "errors": [str(exc)], "next_actions": next_actions}
