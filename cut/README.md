# cut (keyword: CUT)

The exact prompt from the "How to edit a video with Claude Code" reel. One line, typed into Claude Code, turns a raw clip into a tighter cut with captions burned in.

## The prompt

```text
Cut every pause longer than half a second out of clip.mp4 and burn in captions.
```

It's also in [prompt.txt](prompt.txt) if you'd rather copy it from a file.

## How to use it

1. Make a folder and put your video in it. Name it `clip.mp4`, or change the file name in the prompt to match yours.
2. Open a terminal in that folder and start Claude Code: `claude`
3. Paste the prompt and press enter.
4. When it's done, the edited video is in the same folder. Watch it, then give notes one sentence at a time ("make the captions bigger", "leave a little more room after each sentence").

## Name the file

Keep the file name in the prompt. When I typed the short version, "Cut the silences and add captions.", Claude Code didn't edit anything. It asked which video I meant and three more questions. With the file name in, it went straight to work.

## What happened when I ran it

Plain Claude Code (Sonnet), one 14-second talking clip, this exact prompt:

- It cut 3 pauses. The clip went from 14.2 seconds to 12.2 seconds.
- It burned captions into the video.
- It took about 3 minutes.
- For the captions it used whisper.cpp, a free speech-to-text tool, and downloaded its English speech model (about 148 MB).

My Mac already had whisper.cpp and a full ffmpeg build installed. On a clean machine, install those first (see Requirements) or Claude Code will stop to sort them out.

Your run won't match mine step for step. Claude Code picks its own tools based on what's installed on your computer, so it may install something or ask before it does.

## Requirements

- Claude Code.
- An ffmpeg build that can burn in captions, plus whisper.cpp. On a Mac: `brew install ffmpeg-full whisper-cpp`. The plain `ffmpeg` formula can't burn in captions.
- About 150 MB of free space for the speech model.
