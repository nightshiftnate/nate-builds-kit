# clip-variants (keyword: CLIPS)

Turns a folder of clips into many short vertical (9:16) videos for hook testing. Each video gets its own hook text, 2 to 4 clips in a different order, and a small zoom, speed, and brightness change so the set doesn't look like one video on repeat. Mirroring is off unless you ask for it. A manifest records which hook went on which video, so when one does well you know which hook to repeat.

## Use it on your own account only

Use this to test hooks on your own account. Do not use it to post duplicates across many accounts. That breaks Instagram's terms and can get accounts removed.

## Setup

You need ffmpeg (on a Mac: `brew install ffmpeg`) and Pillow, which draws the text. Install Pillow in a virtual environment, because newer Macs and Linux systems block a plain `pip install`. On Debian or Ubuntu you may need `sudo apt install python3-venv` first. From the repo root:

```bash
python3 -m venv .venv
.venv/bin/pip install pillow
.venv/bin/python clip-variants/video_variants.py --help
```

## Run

```bash
.venv/bin/python clip-variants/video_variants.py --clips ./my-clips --hooks clip-variants/hooks.txt --out ./out --count 10
```

Check the plan first without rendering:

```bash
.venv/bin/python clip-variants/video_variants.py --clips ./my-clips --hooks clip-variants/hooks.txt --out ./out --dry-run
```

## Options

- `--count N` number of videos (default 20)
- `--length S` target seconds per video (default 15)
- `--cta "text"` closing text for the last 2 seconds
- `--music DIR` folder of audio files to mix in at low volume
- `--mute-original` drop the clips' own audio
- `--mirror` flip about half the videos left to right (off by default)
- `--overwrite` delete this tool's old videos and manifest from `--out` first, then render
- `--seed N` same inputs and seed give the same plan
- `--dry-run` print the plan only

## Hooks file

`hooks.txt` has one hook per line. Lines starting with `#` are skipped. Hooks are dealt in order, so each gets the same number of videos. The sample file is a starting point. Replace it with your own.

## Output

`v01_h1.mp4`, `v02_h2.mp4`, and so on, plus `manifest.json` and `manifest.csv`. Keep the manifest. A new run won't write into a folder that already has this tool's videos or manifest unless you pass `--overwrite`, which deletes the old output first. It only deletes names this tool writes (`v01_h1.mp4` style videos, `manifest.json`, `manifest.csv`), so any other file in the folder stays. `--out` can't be your clips folder. The manifest is written before rendering starts. If a render fails partway, the tool tells you how many of the planned videos exist.

## Notes

- Clips shorter than their planned slot are used whole.
- Metadata is stripped from every output, so your phone's location and device tags don't ship with the video.
- Not tested on Windows.
