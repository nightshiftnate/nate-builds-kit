# render (keyword: RENDER)

How I set up HyperFrames with Claude Code to make the film in the "Stop wasting renders on one detail" reel, and how to re-render only the few seconds you changed instead of the whole film.

HyperFrames is free and open source, made by HeyGen, not me: [github.com/heygen-com/hyperframes](https://github.com/heygen-com/hyperframes). It renders on your own computer, so a re-render costs time, not credits.

## 1. Setup

You need Claude Code and Node.js (on a Mac: `brew install node`). Then install the HyperFrames skills into Claude Code:

```bash
npx hyperframes skills
```

Restart Claude Code after it finishes. The skills teach Claude Code how a HyperFrames project is laid out and which commands to run.

## 2. Make the film

Make an empty folder, open Claude Code in it, and describe the film: what's on screen, what moves, in what order, how long, and the size (1080 by 1920 for a vertical reel). Claude Code sets up the project, writes each scene as HTML, and renders it.

If you'd rather start the project yourself, this makes a vertical one:

```bash
npx hyperframes init my-film --resolution portrait
cd my-film
```

Then open Claude Code in `my-film` and describe what you want. To watch it in the browser while you work, ask Claude Code to run `npx hyperframes preview`. To render the whole film:

```bash
npx hyperframes render -o renders/full.mp4
```

## 3. Re-render one span

HyperFrames' render command now takes a start and an end time in seconds. After you change one scene, tell Claude Code which seconds to re-render. It runs:

```bash
npx hyperframes render --start 10 --end 13 -o renders/span.mp4
```

That writes only seconds 10 to 13, as a 3 second clip that starts at 0 and carries the audio of that span. From the HyperFrames help:

- `--start` renders from this second of the film. MP4 only.
- `--end` renders up to this second (default: the end). It needs MP4, a whole frame rate of 24, 25, 30 or 60, and SDR.

Check yours with `npx hyperframes render --help`. I used HyperFrames 0.8.223 for the timing below and 0.9.20 for this page.

## 4. Drop it back into the film

This puts the new seconds 10 to 13 into the old full render and keeps everything else. Change the three numbers (10, 13, and the file names) to match yours:

```bash
ffmpeg -i renders/full.mp4 -i renders/span.mp4 -filter_complex "[0:v]trim=end=10,setpts=PTS-STARTPTS[v0];[0:a]atrim=end=10,asetpts=PTS-STARTPTS[a0];[1:v]setpts=PTS-STARTPTS[v1];[1:a]asetpts=PTS-STARTPTS[a1];[0:v]trim=start=13,setpts=PTS-STARTPTS[v2];[0:a]atrim=start=13,asetpts=PTS-STARTPTS[a2];[v0][a0][v1][a1][v2][a2]concat=n=3:v=1:a=1[v][a]" -map "[v]" -map "[a]" -c:v libx264 -crf 16 -c:a aac renders/spliced.mp4
```

This needs ffmpeg (on a Mac: `brew install ffmpeg`). If your film has no audio, ask Claude Code to drop the audio parts. Or just ask Claude Code: "splice renders/span.mp4 into renders/full.mp4 at 10 to 13 seconds."

I tested this command on a short HyperFrames film before putting it here: the spliced file came out the same length as the original, and the spliced seconds matched the span render.

## My numbers

On my Mac, a 36.3 second vertical film (1080 by 1920) rendered in 1m 3.8s. Seconds 10 to 13 rendered alone in 22.0s. Spliced back in, the film was 36.27 seconds with nothing else changed.

The span render isn't 12 times faster than the full one, because every render has a startup cost before the first frame. The longer your film, the more you save.

## Cost

HyperFrames and ffmpeg are free. Claude Code is whatever plan you're already on.
