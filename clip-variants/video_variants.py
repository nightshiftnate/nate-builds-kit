#!/usr/bin/env python3
"""
Video Variants: turn a folder of clips into many short videos for hook testing.

You shoot footage once. This cuts N vertical 9:16 videos, each with its own
hook line, clip order, trims, and small visual changes. Post them on YOUR OWN
account to see which hook performs. Do not use this to post duplicates across
many accounts. That breaks Instagram's terms.

Needs ffmpeg and ffprobe on PATH, plus Pillow for text (see README for the venv setup).
No network, no API calls.

Usage:
    python3 video_variants.py --clips DIR --hooks hooks.txt --out DIR
    python3 video_variants.py --clips DIR --hooks hooks.txt --out DIR \
        --count 20 --length 15 --cta "Link in bio" --music DIR --seed 7
    python3 video_variants.py ... --dry-run     # print the plan only
    python3 video_variants.py ... --mirror       # also flip about half the videos
    python3 video_variants.py ... --overwrite    # reuse an --out folder that has videos

hooks.txt: one hook per line (blank lines and lines starting with # skipped).
Hooks are dealt round-robin, so every hook gets the same number of variants.

Output: v01_h1.mp4, v02_h2.mp4, ... plus manifest.json and manifest.csv that
record which hook, clips, trims and tweaks each file got. Keep the manifest.
When a video does well, its id tells you which hook to make more of.

Gotchas:
- Some ffmpeg builds have no drawtext (no libfreetype), so text is rendered to
  a transparent PNG with Pillow and laid over with the overlay filter.
- Every variant is re-encoded with metadata stripped, so your phone's location
  and device tags never ship with the video.
- A real run refuses an --out folder that already holds this tool's videos or
  manifest. --overwrite deletes those old files first (exact names only, like
  v01_h1.mp4 and manifest.json; other files are left alone), so the folder
  only ever holds one run's output. --out can't be the --clips folder. The
  manifest is written before rendering, so a failed run still says which hook
  each finished video got.
- Clips shorter than their planned slot are used whole. The real length is
  recorded in the manifest and the CTA timing follows it.
"""

import argparse
import csv
import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
from pathlib import Path

W, H, FPS = 1080, 1920, 30
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".webm"}
AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".aac"}
FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Impact.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]
HOOK_SECS = 3.0
CTA_SECS = 2.0
MIN_SEG = 2.0
# The exact names this tool writes (v01_h1.mp4, manifest.json, manifest.csv).
# --overwrite deletes only these, so a user's vlog_hike.mp4 or manifest.txt is never touched.
# Case-insensitive because macOS treats Manifest.json and manifest.json as one file.
OWN_OUTPUT = re.compile(r"v\d{2,}_h\d+\.mp4|manifest\.(json|csv)", re.IGNORECASE)


def is_own_output(name):
    return OWN_OUTPUT.fullmatch(name) is not None


def probe(path):
    """Return (duration_seconds, has_audio) for a media file."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    )
    data = json.loads(out.stdout)
    dur = float(data.get("format", {}).get("duration") or 0)
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))
    return dur, has_audio


def load_hooks(path):
    lines = Path(path).read_text().splitlines()
    hooks = [ln.strip() for ln in lines if ln.strip() and not ln.strip().startswith("#")]
    if not hooks:
        sys.exit(f"no hooks found in {path}")
    return hooks


def list_media(folder, exts):
    if not folder:
        return []
    return sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in exts)


def text_png(text, path, y_frac, font_size=72):
    """Transparent full-frame PNG with centered, wrapped, outlined text."""
    from PIL import Image, ImageDraw, ImageFont

    font = None
    for cand in FONT_CANDIDATES:
        if Path(cand).exists():
            font = ImageFont.truetype(cand, font_size)
            break
    if font is None:
        font = ImageFont.load_default()

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    lines = textwrap.wrap(text, width=22) or [text]
    stroke = max(3, font_size // 12)
    line_h = font_size + 14
    y = int(H * y_frac) - (len(lines) * line_h) // 2
    for ln in lines:
        box = draw.textbbox((0, 0), ln, font=font, stroke_width=stroke)
        x = (W - (box[2] - box[0])) // 2
        draw.text((x, y), ln, font=font, fill="white", stroke_width=stroke, stroke_fill="black")
        y += line_h
    img.save(path)


def plan_variants(clips, hooks, count, length, rng, music=None, allow_mirror=False):
    """Pure planning step: decide every variant's hook, segments and tweaks.

    clips: list of (path, duration, has_audio). Returns a list of dicts.
    """
    plans = []
    for i in range(count):
        hook_idx = i % len(hooks)
        k = rng.randint(min(2, len(clips)), min(4, max(2, len(clips))))
        order = rng.sample(clips, k) if k <= len(clips) else [rng.choice(clips) for _ in range(k)]
        weights = [rng.uniform(1.0, 2.0) for _ in range(k)]
        spare = max(0.0, length - MIN_SEG * k)
        durs = [MIN_SEG + spare * w / sum(weights) for w in weights]

        # Longest clips last, so time a short clip can't fill rolls forward into
        # a clip that can absorb it (keeps videos at the target length).
        pairs = sorted(zip(order, durs), key=lambda pd: pd[0][1])
        head = pairs[:-1]
        rng.shuffle(head)
        pairs = head + pairs[-1:]
        segs = []
        carry = 0.0
        for (path, src_dur, has_audio), dur in pairs:
            dur += carry
            carry = 0.0
            speed = round(rng.uniform(0.95, 1.08), 3)
            src_len = dur * speed
            if src_dur < src_len:
                src_len = src_dur
                carry = dur - src_dur / speed
                dur = src_dur / speed
            start = round(rng.uniform(0, max(0.0, src_dur - src_len)), 2)
            segs.append({
                "clip": str(path), "start": start, "src_len": round(src_len, 3),
                "out_len": round(dur, 3), "speed": speed, "has_audio": has_audio,
            })

        plans.append({
            "id": f"v{i + 1:02d}",
            "hook_index": hook_idx + 1,
            "hook": hooks[hook_idx],
            "segments": segs,
            "mirror": allow_mirror and rng.random() < 0.5,
            "zoom": round(rng.uniform(1.0, 1.12), 3),
            "brightness": round(rng.uniform(-0.03, 0.04), 3),
            "contrast": round(rng.uniform(0.97, 1.08), 3),
            "music": str(rng.choice(music)) if music else None,
            "length": round(sum(s["out_len"] for s in segs), 2),
        })
    return plans


def build_cmd(plan, hook_png, cta_png, out_path, keep_audio, music_vol):
    """ffmpeg command for one variant: trim, normalize, concat, overlay, mix."""
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for s in plan["segments"]:
        cmd += ["-ss", str(s["start"]), "-t", str(s["src_len"]), "-i", s["clip"]]
    n = len(plan["segments"])
    cmd += ["-loop", "1", "-i", str(hook_png)]
    hook_in = n
    cta_in = None
    if cta_png:
        cmd += ["-loop", "1", "-i", str(cta_png)]
        cta_in = n + 1
    music_in = None
    if plan["music"]:
        cmd += ["-stream_loop", "-1", "-i", plan["music"]]
        music_in = n + (2 if cta_png else 1)

    L = plan["length"]
    zw, zh = int(W * plan["zoom"]) // 2 * 2, int(H * plan["zoom"]) // 2 * 2
    flip = ",hflip" if plan["mirror"] else ""
    parts = []
    concat_in = ""
    for j, s in enumerate(plan["segments"]):
        parts.append(
            f"[{j}:v]setpts=(PTS-STARTPTS)/{s['speed']},"
            f"scale={zw}:{zh}:force_original_aspect_ratio=increase,crop={W}:{H}{flip},"
            f"eq=brightness={plan['brightness']}:contrast={plan['contrast']},"
            f"fps={FPS},format=yuv420p,setsar=1[v{j}]"
        )
        if keep_audio and s["has_audio"]:
            parts.append(
                f"[{j}:a]asetpts=PTS-STARTPTS,atempo={s['speed']},"
                f"aformat=sample_rates=44100:channel_layouts=stereo,"
                f"apad,atrim=0:{s['out_len']}[a{j}]"
            )
        else:
            parts.append(f"anullsrc=r=44100:cl=stereo,atrim=0:{s['out_len']}[a{j}]")
        concat_in += f"[v{j}][a{j}]"
    parts.append(f"{concat_in}concat=n={n}:v=1:a=1[vc][ac]")
    parts.append(f"[vc][{hook_in}:v]overlay=0:0:shortest=1:enable='between(t,0,{HOOK_SECS})'[vh]")
    vlast = "vh"
    if cta_in is not None:
        parts.append(f"[vh][{cta_in}:v]overlay=0:0:shortest=1:enable='gte(t,{max(0.0, L - CTA_SECS)})'[vo]")
        vlast = "vo"
    alast = "ac"
    if music_in is not None:
        parts.append(
            f"[{music_in}:a]aformat=sample_rates=44100:channel_layouts=stereo,atrim=0:{L},"
            f"afade=t=out:st={max(0.0, L - 1)}:d=1,volume={music_vol}[m]"
        )
        parts.append("[ac][m]amix=inputs=2:duration=first:normalize=0[am]")
        alast = "am"

    cmd += [
        "-filter_complex", ";".join(parts),
        "-map", f"[{vlast}]", "-map", f"[{alast}]",
        "-t", str(L), "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-map_metadata", "-1", "-movflags", "+faststart",
        str(out_path),
    ]
    return cmd


def write_manifest(out_dir, plans):
    (out_dir / "manifest.json").write_text(json.dumps(plans, indent=2))
    with open(out_dir / "manifest.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["id", "file", "hook_index", "hook", "length_s", "clips", "mirror", "music"])
        for p in plans:
            wr.writerow([
                p["id"], p["file"], p["hook_index"], p["hook"], p["length"],
                " | ".join(Path(s["clip"]).name for s in p["segments"]),
                p["mirror"], Path(p["music"]).name if p["music"] else "",
            ])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--clips", required=True, help="folder of video clips")
    ap.add_argument("--hooks", required=True, help="text file, one hook per line")
    ap.add_argument("--out", required=True, help="output folder")
    ap.add_argument("--count", type=int, default=20)
    ap.add_argument("--length", type=float, default=15.0, help="target seconds per video")
    ap.add_argument("--cta", default="", help="closing text for the last 2 seconds, e.g. 'Link in bio'")
    ap.add_argument("--music", help="folder of music tracks (optional)")
    ap.add_argument("--music-volume", type=float, default=0.3)
    ap.add_argument("--mute-original", action="store_true", help="drop the clips' own audio")
    ap.add_argument("--seed", type=int, default=None, help="repeatable output for the same inputs")
    ap.add_argument("--mirror", action="store_true", help="flip about half the videos left to right (off by default)")
    ap.add_argument("--overwrite", action="store_true", help="delete old videos and manifest in --out, then render")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"{tool} not found on PATH")

    clip_paths = list_media(args.clips, VIDEO_EXTS)
    if not clip_paths:
        sys.exit(f"no video clips in {args.clips}")
    clips = [(p, *probe(p)) for p in clip_paths]
    hooks = load_hooks(args.hooks)
    music = list_media(args.music, AUDIO_EXTS)
    rng = random.Random(args.seed)
    plans = plan_variants(clips, hooks, args.count, args.length, rng, music, args.mirror)

    out_dir = Path(args.out)
    # samefile, not path equality: on macOS ~/Clips and ~/clips are the same folder.
    if out_dir.exists() and out_dir.samefile(args.clips):
        sys.exit("--out must be a different folder from --clips.")
    if not args.dry_run and out_dir.is_dir():
        old = sorted(f for f in out_dir.iterdir() if is_own_output(f.name))
        if old and not args.overwrite:
            sys.exit(f"{out_dir} already has {len(old)} video/manifest file(s) from an earlier run. "
                     f"Pick a new --out folder, or pass --overwrite.")
        for f in old:
            f.unlink()
    if not args.dry_run:
        out_dir.mkdir(parents=True, exist_ok=True)
    for p in plans:
        p["file"] = f"{p['id']}_h{p['hook_index']}.mp4"

    if args.dry_run:
        for p in plans:
            print(f"{p['file']}: {p['length']}s, {len(p['segments'])} clips, hook: {p['hook']}")
        return 0

    write_manifest(out_dir, plans)  # first, so a failed run still maps videos to hooks
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        cta_png = None
        if args.cta:
            cta_png = tmp / "cta.png"
            # 0.62, not lower: TikTok/Reels captions and buttons cover the bottom ~25%.
            text_png(args.cta, cta_png, y_frac=0.62, font_size=80)
        for p in plans:
            hook_png = tmp / f"hook_{p['hook_index']}.png"
            if not hook_png.exists():
                text_png(p["hook"], hook_png, y_frac=0.22)
            cmd = build_cmd(p, hook_png, cta_png, out_dir / p["file"],
                            keep_audio=not args.mute_original, music_vol=args.music_volume)
            try:
                res = subprocess.run(cmd, capture_output=True, text=True)
            except KeyboardInterrupt:  # Ctrl-C: don't leave a truncated video behind
                (out_dir / p["file"]).unlink(missing_ok=True)
                done = sum(1 for q in plans if (out_dir / q["file"]).exists())
                print(f"\nstopped. {done} of {len(plans)} planned videos exist; "
                      f"manifest.json lists all {len(plans)}.", file=sys.stderr)
                return 130
            if res.returncode != 0:
                (out_dir / p["file"]).unlink(missing_ok=True)  # drop the half-written file
                done = sum(1 for q in plans if (out_dir / q["file"]).exists())
                sys.exit(f"ffmpeg failed on {p['file']}:\n{res.stderr[-2000:]}\n"
                         f"{done} of {len(plans)} planned videos exist; manifest.json lists all {len(plans)}.")
            print(f"{p['file']}  {p['length']}s  hook {p['hook_index']}")

    print(f"\n{len(plans)} videos + manifest.json/csv in {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
