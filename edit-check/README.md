# edit-check (keyword: EDIT)

A Python script that checks a rendered video before you watch it. Not a model grading itself. Each check measures the file with ffmpeg and prints PASS or FAIL with the number it measured and the limit it was held to.

Why: "make sure the audio is fine" is an instruction. This is a measurement. Claude Code runs it after every render, fixes what fails, and runs it again. You only see the cut once the numbers pass, and then you give notes one sentence at a time ("captions bigger", "tighten that pause").

This is a simpler version of what I run on my own reels. Mine has eleven checks, and some of them (like captions staying inside the frame) only work with my render setup. These ten work with any video. Nine read the file itself, and the tenth, script match, needs a transcript you supply.

One Python file, standard library only. It calls `ffmpeg` and `ffprobe`. No pip installs, no network, no AI model.

## Requirements

- Python 3.9 or newer.
- ffmpeg (includes ffprobe). On a Mac: `brew install ffmpeg`.
- Claude Code, if you want it to run the checks and fix failures for you. The script works fine on its own without it.

## Usage

From the repo root:

```bash
python3 edit-check/edit_check.py video.mp4
```

Options:

- `--script script.txt` also compares what's said in the video to your script (see below).
- `--transcript words.txt` the transcript to compare. Plain text, or JSON as a list of words, a list of `{"word": "..."}`, or `{"words": [...]}`.
- `--max-duration 60` changes the length limit for this run.
- `--json` prints the results as JSON instead of text.

Exit code is 0 only if every check that ran passed, 1 if any failed, 2 if the video couldn't be read. A broken transcript file stops it with an error.

Example output:

```
PASS  duration      41.2s  (limit: <= 90s)
PASS  resolution    1080x1920  (limit: 1080x1920)
PASS  frame rate    30.00 fps  (limit: 23.9 to 60 fps)
PASS  has audio     aac stream  (limit: 1 audio stream)
FAIL  loudness      -19.8 LUFS  (limit: -16 to -12 LUFS)
PASS  true peak     -3.1 dBTP  (limit: < -1 dBTP)
FAIL  silence       12.4s for 1.9s  (limit: no silence over 1.5s)
PASS  black frames  none over 0.5s  (limit: no black over 0.5s)
PASS  frozen video  none over 2s  (limit: no freeze over 2s)
SKIP  script match  no --script given
7/9 PASS
```

The `silence` line reads "starts at 12.4 seconds, lasts 1.9 seconds".

## The checks

| Check | Passes when | How it's measured |
|---|---|---|
| duration | 90 seconds or less | ffprobe |
| resolution | exactly 1080x1920 | ffprobe |
| frame rate | 23.9 to 60 fps (so 23.976 passes) | ffprobe |
| has audio | the file has an audio stream | ffprobe |
| loudness | -14 LUFS, give or take 2 | ffmpeg `ebur128`, integrated |
| true peak | below -1 dBTP | ffmpeg `ebur128` with peak on |
| silence | no silent stretch over 1.5 seconds | ffmpeg `silencedetect` at -50 dB |
| black frames | no black stretch over 0.5 seconds | ffmpeg `blackdetect` |
| frozen video | no frozen picture over 2 seconds | ffmpeg `freezedetect` |
| script match | 95% or more of the words match your script | Python `difflib`, only with `--script` |

If the file has no audio, the loudness, true peak and silence checks print SKIP (the missing audio already fails "has audio"). SKIP lines aren't counted in the N/M total.

### Script match

Add `--script script.txt` and give it a transcript of what the video actually says, either with `--transcript` or as a file next to the video named `video.words.json` (for `video.mp4`). It compares the two word lists, ignoring case and punctuation, and fails below 95%. With no transcript it prints SKIP. This script doesn't transcribe anything. Use whatever speech-to-text you already have to make the transcript.

### Change the limits

All thresholds are constants at the top of `edit_check.py`, each with a comment. They're set for a vertical short-form video. A horizontal video, a longer cut, or a different loudness target means editing those lines.

## Use it with Claude Code

1. Copy `CLAUDE.md` into your video project. If the project already has a `CLAUDE.md`, paste its contents in at the bottom.
2. Put `edit_check.py` in the same project folder.
3. Render something and tell Claude Code to make a cut.

From then on Claude Code is told to check every render, fix any FAIL, and re-run until everything passes before it shows you the cut. Then you give notes one sentence at a time, and it applies just that change, re-renders, and re-checks.

The snippet also tells Claude not to edit the thresholds to get a pass. That's an instruction, not a lock. If you need it enforced, make `edit_check.py` read-only (`chmod a-w edit_check.py`).

## Limits

- The checks measure the file. They can't judge taste: whether the captions look good, whether the pacing works, whether the hook lands. That's still your eyes.
- A pass means "none of these problems were measured", not "this is a good video".
- Silence and black detection use fixed noise and brightness cutoffs. A video with quiet room tone, or a dark scene that is meant to be dark, can trip them. The thresholds are in the constants if that happens.
- The frozen-video check will flag a deliberate long still image (a title card held for 3 seconds).
- Loudness is measured on the whole file, so one very loud or very quiet section can be hidden by the average.
- Script match compares words, not timing, and it's only as good as the transcript you give it.
- Tested on macOS with ffmpeg 9. Linux should work. Windows isn't tested.

## Tests

```bash
python3 edit-check/test_edit_check.py
```

They build small test videos with ffmpeg (a good one, plus ones with a black segment, a long silence, the wrong size, no audio, a frozen tail, too-loud audio, a clipping peak, and 23.976 and 15 fps), then check that the right checks fail and the exit codes are right. About 15 seconds.

## Undo

Delete the `CLAUDE.md` text you pasted in and the `edit_check.py` file. Nothing else was installed.

## Pairs with

`send-guard/`. Same idea one step later: edit-check measures the video before you see it, send-guard checks the recipient before anything is sent.
