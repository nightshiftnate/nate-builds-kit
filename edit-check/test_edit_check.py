"""Tests for edit_check.py. Builds tiny synthetic videos with ffmpeg. Needs ffmpeg on PATH.

Run: python3 test_edit_check.py
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import edit_check  # noqa: E402

# A sine tone at this gain lands near -14 LUFS (measured, not guessed).
TONE = "sine=f=440:d={d},volume=7.7dB"


def make(path, *, size="1080x1920", dur=4, audio=True, vfilter=None, afilter=None, extra=None):
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
           "testsrc2=s=%s:r=30:d=%s" % (size, dur)]
    if audio:
        cmd += ["-f", "lavfi", "-i", TONE.format(d=dur)]
    if vfilter:
        cmd += ["-vf", vfilter]
    if audio and afilter:
        cmd += ["-af", afilter]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
    cmd += ["-c:a", "aac"] if audio else ["-an"]
    cmd += (extra or []) + [path]
    subprocess.run(cmd, check=True)


def write(path, text):
    with open(path, "w") as f:
        f.write(text)


def status(results):
    return {r.name: r.status for r in results}


class EditCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.tmp.name
        cls.p = {k: os.path.join(d, k + ".mp4") for k in
                 ("good", "black", "silent", "small", "noaudio", "frozen", "long")}
        make(cls.p["good"])
        make(cls.p["black"], vfilter="drawbox=x=0:y=0:w=iw:h=ih:color=black:t=fill:enable='between(t,1,2)'")
        make(cls.p["silent"], afilter="volume=0:enable='between(t,0.5,3.5)'")
        make(cls.p["small"], size="1280x720")
        make(cls.p["noaudio"], audio=False)
        make(cls.p["frozen"], vfilter="tpad=stop_mode=clone:stop_duration=3", dur=3, extra=["-t", "6"])
        make(cls.p["long"], dur=6)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def cli(self, *args):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = edit_check.main(list(args))
        return code, buf.getvalue()

    def test_good_passes_everything(self):
        s = status(edit_check.check_video(self.p["good"]))
        for name, st in s.items():
            if name != "script match":
                self.assertEqual(st, "PASS", name)
        self.assertEqual(s["script match"], "SKIP")
        code, out = self.cli(self.p["good"])
        self.assertEqual(code, 0)
        self.assertIn("9/9 PASS", out)

    def test_black_segment_fails(self):
        s = status(edit_check.check_video(self.p["black"]))
        self.assertEqual(s["black frames"], "FAIL")
        self.assertEqual(s["silence"], "PASS")
        self.assertEqual(self.cli(self.p["black"])[0], 1)

    def test_long_silence_fails(self):
        s = status(edit_check.check_video(self.p["silent"]))
        self.assertEqual(s["silence"], "FAIL")
        self.assertEqual(s["black frames"], "PASS")
        self.assertEqual(self.cli(self.p["silent"])[0], 1)

    def test_wrong_resolution_fails(self):
        s = status(edit_check.check_video(self.p["small"]))
        self.assertEqual(s["resolution"], "FAIL")
        self.assertEqual(s["frame rate"], "PASS")
        self.assertEqual(self.cli(self.p["small"])[0], 1)

    def test_no_audio_fails_and_skips_audio_checks(self):
        s = status(edit_check.check_video(self.p["noaudio"]))
        self.assertEqual(s["has audio"], "FAIL")
        for n in ("loudness", "true peak", "silence"):
            self.assertEqual(s[n], "SKIP")
        code, out = self.cli(self.p["noaudio"])
        self.assertEqual(code, 1)
        self.assertIn("5/6 PASS", out)

    def test_frozen_tail_fails(self):
        s = status(edit_check.check_video(self.p["frozen"]))
        self.assertEqual(s["frozen video"], "FAIL")

    def test_duration_limit(self):
        s = status(edit_check.check_video(self.p["long"], max_duration=5))
        self.assertEqual(s["duration"], "FAIL")
        self.assertEqual(self.cli(self.p["long"], "--max-duration", "5")[0], 1)

    def test_loud_audio_fails(self):
        loud = os.path.join(self.tmp.name, "loud.mp4")
        make(loud, afilter="volume=12dB")
        s = status(edit_check.check_video(loud))
        self.assertEqual(s["loudness"], "FAIL")

    def test_true_peak_fails(self):
        hot = os.path.join(self.tmp.name, "hot.mp4")
        make(hot, afilter="volume=20dB")
        self.assertEqual(status(edit_check.check_video(hot))["true peak"], "FAIL")

    def test_film_frame_rate_passes(self):
        film = os.path.join(self.tmp.name, "film.mp4")
        make(film, extra=["-r", "24000/1001"])
        self.assertEqual(status(edit_check.check_video(film))["frame rate"], "PASS")

    def test_low_frame_rate_fails(self):
        slow = os.path.join(self.tmp.name, "slow.mp4")
        make(slow, extra=["-r", "15"])
        self.assertEqual(status(edit_check.check_video(slow))["frame rate"], "FAIL")

    def test_json_output(self):
        code, out = self.cli(self.p["small"], "--json")
        data = json.loads(out)
        self.assertEqual(code, 1)
        self.assertFalse(data["ok"])
        self.assertEqual([c for c in data["checks"] if c["check"] == "resolution"][0]["status"], "FAIL")

    def test_missing_file_exit_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(edit_check.main(["nope.mp4"]), 2)

    def test_script_skip_without_transcript(self):
        sc = os.path.join(self.tmp.name, "s.txt")
        write(sc, "hello there world")
        s = status(edit_check.check_video(self.p["good"], script=sc))
        self.assertEqual(s["script match"], "SKIP")

    def test_script_match_pass_and_fail(self):
        sc = os.path.join(self.tmp.name, "s.txt")
        write(sc, "Before I see a cut, a Python script checks it.")
        ok = os.path.join(self.tmp.name, "ok.txt")
        write(ok, "before I see a cut a python script checks it")
        bad = os.path.join(self.tmp.name, "bad.json")
        write(bad, json.dumps([{"word": w} for w in "after I see a cut a model grades it".split()]))
        self.assertEqual(status(edit_check.check_video(self.p["good"], sc, ok))["script match"], "PASS")
        self.assertEqual(status(edit_check.check_video(self.p["good"], sc, bad))["script match"], "FAIL")

    def test_sidecar_words_json(self):
        v = os.path.join(self.tmp.name, "side.mp4")
        make(v)
        sc = os.path.join(self.tmp.name, "side.txt")
        write(sc, "one two three")
        write(os.path.join(self.tmp.name, "side.words.json"),
              json.dumps({"words": [{"word": "one"}, {"word": "two"}, {"word": "three"}]}))
        self.assertEqual(status(edit_check.check_video(v, script=sc))["script match"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
