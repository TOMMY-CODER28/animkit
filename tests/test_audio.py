"""Audio provider tests. Real Kokoro generation needs the model + eSpeak NG;
these tests exercise provider logic offline via a stub pipeline, so the suite
stays fast and hermetic. Marked audio-integration checks that DO need the
model are skipped unless kokoro imports cleanly AND a run flag is set."""

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))


def _fake_audio_chunk(samples=2400):
    import numpy as np
    return np.zeros(samples, dtype="float32")


class FakePipeline:
    """Mimics KPipeline: yields (gs, ps, audio) per sentence-ish chunk."""
    def __init__(self, chunks_per_call=2):
        self.chunks_per_call = chunks_per_call
        self.calls = []

    def __call__(self, text, voice=None, speed=None):
        self.calls.append(text)
        for _ in range(self.chunks_per_call):
            yield None, None, _fake_audio_chunk()


class TestKokoroProviderOffline(unittest.TestCase):
    def setUp(self):
        import soundfile as sf  # required dep for the provider
        assert sf is not None
        from animkit.audio.kokoro_provider import KokoroProvider
        self.provider = KokoroProvider(lang="a", voice="af_heart", speed=1.0)
        self.out = self._tmp()

    def _tmp(self):
        import tempfile
        d = Path(tempfile.mkdtemp(prefix="animkit_audio_"))
        self.addCleanup(lambda: __import__("shutil").rmtree(d, ignore_errors=True))
        return d

    def test_chunks_combined_into_one_wav(self):
        """Long narration -> multiple chunks -> ONE combined wav per stage."""
        fake = FakePipeline(chunks_per_call=3)
        with mock.patch("animkit.audio.kokoro_provider.get_pipeline",
                        return_value=fake):
            res = self.provider.generate_stage("s1", "long text " * 20,
                                               self.out)
        self.assertTrue(res["ok"], res.get("errors"))
        self.assertEqual(res["outputs"]["chunks"], 3)
        wavs = list(self.out.glob("*.wav"))
        self.assertEqual([p.name for p in wavs if "chunk" not in p.name],
                         [Path(res["outputs"]["path"]).name],
                         "exactly one combined wav per stage")
        self.assertFalse(any("chunk" in p.name for p in self.out.glob("*")),
                         "chunk files cleaned after successful combine")
        self.assertGreater(res["outputs"]["duration_s"], 0.05)

    def test_cache_hit_skips_generation(self):
        fake = FakePipeline()
        with mock.patch("animkit.audio.kokoro_provider.get_pipeline",
                        return_value=fake):
            first = self.provider.generate_stage("s1", "hello", self.out)
            self.assertFalse(first["outputs"]["cached"])
            second = self.provider.generate_stage("s1", "hello", self.out)
        self.assertTrue(second["outputs"]["cached"])
        self.assertEqual(second["outputs"]["path"], first["outputs"]["path"])
        self.assertEqual(len(fake.calls), 1, "cached result must not re-synthesize")

    def test_different_text_never_overwrites(self):
        """Different narration -> different cache key -> different file;
        the earlier stage's wav must survive."""
        fake = FakePipeline()
        with mock.patch("animkit.audio.kokoro_provider.get_pipeline",
                        return_value=fake):
            r1 = self.provider.generate_stage("stage", "first narration",
                                              self.out)
            r2 = self.provider.generate_stage("stage", "second narration",
                                              self.out)
        self.assertNotEqual(r1["outputs"]["path"], r2["outputs"]["path"])
        self.assertTrue(Path(r1["outputs"]["path"]).is_file())

    def test_force_regenerates(self):
        fake = FakePipeline()
        with mock.patch("animkit.audio.kokoro_provider.get_pipeline",
                        return_value=fake):
            self.provider.generate_stage("s", "text", self.out)
            forced = self.provider.generate_stage("s", "text", self.out,
                                                  force=True)
        self.assertFalse(forced["outputs"]["cached"])
        self.assertEqual(len(fake.calls), 2)

    def test_generation_error_reported(self):
        def boom(*a, **k):
            raise RuntimeError("pipeline exploded")
        with mock.patch("animkit.audio.kokoro_provider.get_pipeline",
                        side_effect=boom):
            res = self.provider.generate_stage("s", "text", self.out)
        self.assertFalse(res["ok"])
        self.assertIn("pipeline exploded", res["errors"][0])
        self.assertTrue(res["next_actions"], "errors carry next actions")


if __name__ == "__main__":
    unittest.main()
