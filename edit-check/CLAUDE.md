# Edit checks

After every render, check the file before showing me a cut.

1. Run `python3 edit_check.py <render>.mp4`. If the video has a script file, transcribe the render and add `--script script.txt --transcript <transcript>` so the words get checked too. If you can't make a transcript, say so when you show me the cut: the words weren't checked.
2. If any line says FAIL, fix the cause in the edit, re-render, and run the check again. Repeat until every check passes, up to three tries. If it still fails after three, stop and show me the FAIL lines and what you tried. Don't show me a cut that has a FAIL. If the check can't run at all (it exits with an error instead of PASS/FAIL lines), stop and tell me; that is not a pass.
3. Don't change the thresholds at the top of `edit_check.py`, and don't pass `--max-duration`, to make a check pass. If you think a threshold is wrong for this video, tell me and let me decide.
4. When you show me the cut, include the final `N/M PASS` line.

## How I give notes

I'll give notes one sentence at a time. Examples:

- "captions bigger"
- "tighten that pause after the hook"
- "cut the first two seconds"
- "music lower under the voice"

For each note: make only that change, re-render, run the check, then show me the cut. Don't bundle in other fixes. If a note is unclear, ask one question first.

## What the checks can and can't tell you

The checks measure the file (length, size, frame rate, audio, loudness, peak, silence, black frames, frozen video, and the script words if you gave it a transcript). They can't tell whether the cut looks good. That part is my call.
