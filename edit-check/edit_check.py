#!/usr/bin/env python3
"""edit-check: measured checks on a rendered video. Python 3.9+, stdlib + ffmpeg/ffprobe only.

Usage:
  python3 edit_check.py video.mp4 [--script script.txt] [--transcript words.txt] [--json]

Every check measures the file with ffmpeg/ffprobe (or compares text with difflib)
and prints PASS or FAIL with the measured value and the threshold.
Exit code 0 only if every check that ran passed. SKIP lines don't count.
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

# ---- Thresholds. Change these to fit your format. ----
MAX_DURATION_S = 90.0        # longest allowed runtime in seconds (override with --max-duration)
REQUIRED_WIDTH = 1080        # vertical video: width...
REQUIRED_HEIGHT = 1920       # ...and height
TARGET_LUFS = -14.0          # integrated loudness target
LUFS_TOLERANCE = 2.0         # allowed distance from the target, in LU
MAX_TRUE_PEAK_DBTP = -1.0    # true peak must be below this
BLACK_MAX_S = 0.5            # longest allowed black stretch (fail if a stretch is longer)
BLACK_PIXEL_THRESHOLD = 0.10 # how dark a pixel counts as black (0 to 1)
SILENCE_MAX_S = 1.5          # longest allowed silent stretch
SILENCE_NOISE_DB = -50       # anything quieter than this counts as silence
FREEZE_MAX_S = 2.0           # longest allowed frozen picture
FREEZE_NOISE = 0.001         # how little change counts as frozen
FPS_MIN = 23.9               # frame rate floor (23.976 film exports pass)
FPS_MAX = 60.0               # frame rate ceiling
SCRIPT_MATCH_MIN = 0.95      # spoken words vs script, fraction that must match
# ------------------------------------------------------


class Result:
    def __init__(self, name, status, measured, threshold):
        self.name, self.status, self.measured, self.threshold = name, status, measured, threshold

    def as_dict(self):
        return {"check": self.name, "status": self.status,
                "measured": self.measured, "threshold": self.threshold}


def read_text(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def run(cmd):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    return p.returncode, p.stdout, p.stderr


def probe(path):
    rc, out, err = run(["ffprobe", "-v", "error", "-print_format", "json",
                        "-show_format", "-show_streams", path])
    if rc != 0:
        raise RuntimeError("ffprobe could not read the file: " + err.strip())
    return json.loads(out)


def parse_rate(s):
    try:
        a, b = s.split("/")
        return float(a) / float(b) if float(b) else 0.0
    except Exception:
        try:
            return float(s)
        except Exception:
            return 0.0


def ffmpeg_filter(path, kind, flt):
    """Run one analysis filter and return its stderr text. kind is 'v' or 'a'."""
    flag = "-vf" if kind == "v" else "-af"
    skip = "-an" if kind == "v" else "-vn"
    rc, _, err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, skip,
                      flag, flt, "-f", "null", "-"])
    if rc != 0:
        raise RuntimeError("ffmpeg failed on filter %s: %s" % (flt, err.strip()[-300:]))
    return err


def stretches(text, start_re, dur_re, total):
    """Collect (start, duration) pairs. A start with no end runs to the end of the file."""
    found, open_start = [], None
    for line in text.splitlines():
        m = re.search(start_re, line)
        if m:
            open_start = float(m.group(1))
        m = re.search(dur_re, line)
        if m:
            d = float(m.group(1))
            found.append((max(0.0, (open_start if open_start is not None else 0.0)), d))
            open_start = None
    if open_start is not None:
        found.append((open_start, max(0.0, total - open_start)))
    return found


def fmt_stretches(items):
    return ", ".join("%.1fs for %.1fs" % (s, d) for s, d in items)


def words_of(text):
    return re.findall(r"[a-z0-9']+", text.lower().replace("\u2019", "'"))


def load_transcript(path):
    """Accepts plain text, or JSON: a list of words, a list of {word|text}, or {words|segments|text}."""
    raw = read_text(path)
    if path.lower().endswith(".json"):
        data = json.loads(raw)
        def flat(x):
            if isinstance(x, str):
                return [x]
            if isinstance(x, list):
                return [w for i in x for w in flat(i)]
            if isinstance(x, dict):
                for k in ("word", "text"):
                    if k in x and isinstance(x[k], str):
                        return [x[k]]
                for k in ("words", "segments"):
                    if k in x:
                        return flat(x[k])
            return []
        return words_of(" ".join(flat(data)))
    return words_of(raw)


def find_transcript(video, explicit):
    if explicit:
        return explicit
    base = os.path.splitext(video)[0]
    for cand in (base + ".words.json", video + ".words.json"):
        if os.path.exists(cand):
            return cand
    return None


def check_video(path, script=None, transcript=None, max_duration=MAX_DURATION_S):
    info = probe(path)
    streams = info.get("streams", [])
    vs = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)
    results = []
    add = lambda *a: results.append(Result(*a))

    try:
        duration = float(info["format"]["duration"])
    except Exception:
        duration = float(vs.get("duration", 0)) if vs else 0.0
    add("duration", "PASS" if duration <= max_duration else "FAIL",
        "%.1fs" % duration, "<= %gs" % max_duration)

    if vs:
        w, h = vs.get("width"), vs.get("height")
        add("resolution", "PASS" if (w, h) == (REQUIRED_WIDTH, REQUIRED_HEIGHT) else "FAIL",
            "%sx%s" % (w, h), "%dx%d" % (REQUIRED_WIDTH, REQUIRED_HEIGHT))
        fps = parse_rate(vs.get("avg_frame_rate", "0/0")) or parse_rate(vs.get("r_frame_rate", "0/0"))
        add("frame rate", "PASS" if FPS_MIN <= fps <= FPS_MAX else "FAIL",
            "%.2f fps" % fps, "%g to %g fps" % (FPS_MIN, FPS_MAX))
    else:
        add("resolution", "FAIL", "no video stream", "%dx%d" % (REQUIRED_WIDTH, REQUIRED_HEIGHT))
        add("frame rate", "FAIL", "no video stream", "%g to %g fps" % (FPS_MIN, FPS_MAX))

    add("has audio", "PASS" if aud else "FAIL",
        ("%s stream" % aud.get("codec_name")) if aud else "no audio stream", "1 audio stream")

    if aud:
        err = ffmpeg_filter(path, "a", "ebur128=peak=true")
        summary = err.split("Summary:")[-1]
        mi = re.search(r"I:\s+(-?[\d.]+|-inf)\s+LUFS", summary)
        mp = re.search(r"Peak:\s+(-?[\d.]+|-inf)\s+dBFS", summary)
        lufs = float(mi.group(1)) if mi else float("-inf")
        peak = float(mp.group(1)) if mp else float("-inf")
        lo, hi = TARGET_LUFS - LUFS_TOLERANCE, TARGET_LUFS + LUFS_TOLERANCE
        add("loudness", "PASS" if lo <= lufs <= hi else "FAIL",
            "%.1f LUFS" % lufs, "%g to %g LUFS" % (lo, hi))
        add("true peak", "PASS" if peak < MAX_TRUE_PEAK_DBTP else "FAIL",
            "%.1f dBTP" % peak, "< %g dBTP" % MAX_TRUE_PEAK_DBTP)
        err = ffmpeg_filter(path, "a", "silencedetect=n=%ddB:d=%g" % (SILENCE_NOISE_DB, SILENCE_MAX_S))
        sil = stretches(err, r"silence_start:\s*(-?[\d.]+)", r"silence_duration:\s*([\d.]+)", duration)
        add("silence", "FAIL" if sil else "PASS",
            fmt_stretches(sil) if sil else "none over %gs" % SILENCE_MAX_S,
            "no silence over %gs" % SILENCE_MAX_S)
    else:
        for n in ("loudness", "true peak", "silence"):
            add(n, "SKIP", "no audio stream", "")

    if vs:
        err = ffmpeg_filter(path, "v", "blackdetect=d=%g:pix_th=%g" % (BLACK_MAX_S, BLACK_PIXEL_THRESHOLD))
        blk = [(float(a), float(c)) for a, c in re.findall(
            r"black_start:([\d.]+)\s+black_end:[\d.]+\s+black_duration:([\d.]+)", err)]
        blk = [(s, d) for s, d in blk if d > BLACK_MAX_S]
        add("black frames", "FAIL" if blk else "PASS",
            fmt_stretches(blk) if blk else "none over %gs" % BLACK_MAX_S,
            "no black over %gs" % BLACK_MAX_S)
        err = ffmpeg_filter(path, "v", "freezedetect=n=%g:d=%g" % (FREEZE_NOISE, FREEZE_MAX_S))
        frz = stretches(err, r"lavfi\.freezedetect\.freeze_start:\s*([\d.]+)",
                        r"lavfi\.freezedetect\.freeze_duration:\s*([\d.]+)", duration)
        add("frozen video", "FAIL" if frz else "PASS",
            fmt_stretches(frz) if frz else "none over %gs" % FREEZE_MAX_S,
            "no freeze over %gs" % FREEZE_MAX_S)
    else:
        add("black frames", "SKIP", "no video stream", "")
        add("frozen video", "SKIP", "no video stream", "")

    if script:
        tpath = find_transcript(path, transcript)
        if not tpath:
            add("script match", "SKIP", "no transcript (add video.words.json or --transcript)", "")
        else:
            want = words_of(read_text(script))
            got = load_transcript(tpath)
            ratio = difflib.SequenceMatcher(None, want, got, autojunk=False).ratio() if want or got else 1.0
            add("script match", "PASS" if ratio >= SCRIPT_MATCH_MIN else "FAIL",
                "%.1f%% of words" % (ratio * 100), ">= %g%%" % (SCRIPT_MATCH_MIN * 100))
    else:
        add("script match", "SKIP", "no --script given", "")
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description="Measured checks on a rendered video.")
    ap.add_argument("video")
    ap.add_argument("--script", help="script text file to compare the spoken words against")
    ap.add_argument("--transcript", help="transcript of the render (.txt, or .json word list)")
    ap.add_argument("--max-duration", type=float, default=MAX_DURATION_S,
                    help="longest allowed runtime in seconds (default %g)" % MAX_DURATION_S)
    ap.add_argument("--json", action="store_true", help="print results as JSON")
    a = ap.parse_args(argv)

    if not os.path.exists(a.video):
        print("File not found: " + a.video, file=sys.stderr)
        return 2
    try:
        results = check_video(a.video, a.script, a.transcript, a.max_duration)
    except (RuntimeError, OSError) as e:
        print("edit-check could not run: %s" % e, file=sys.stderr)
        return 2

    ran = [r for r in results if r.status != "SKIP"]
    passed = [r for r in ran if r.status == "PASS"]
    ok = len(passed) == len(ran)
    if a.json:
        print(json.dumps({"video": a.video, "passed": len(passed), "ran": len(ran),
                          "ok": ok, "checks": [r.as_dict() for r in results]}, indent=2))
    else:
        for r in results:
            line = "%-4s  %-13s %s" % (r.status, r.name, r.measured)
            if r.threshold:
                line += "  (limit: %s)" % r.threshold
            print(line)
        print("%d/%d PASS" % (len(passed), len(ran)))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
