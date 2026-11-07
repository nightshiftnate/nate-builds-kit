# studio (keyword: STUDIO)

The first prompt from the "Claude is now a video studio" reel. Claude Code writes a motion graphic as HTML, and HyperFrames turns that HTML into an mp4 on your own computer.

HyperFrames is free and open source, made by HeyGen, not me: [github.com/heygen-com/hyperframes](https://github.com/heygen-com/hyperframes).

## 1. Setup (one command)

You need Claude Code and Node.js (HyperFrames runs through `npx`, which comes with Node.js). On a Mac: `brew install node`.

In a terminal, run:

```bash
npx hyperframes skills
```

This installs the HyperFrames skills into your AI coding tools, Claude Code included. On my run it installed nine of them (hyperframes, hyperframes-cli, hyperframes-registry and six more). Restart Claude Code after it finishes.

You can also paste it straight into Claude Code with a `!` in front: `! npx hyperframes skills`.

## 2. The first prompt

Make an empty folder, open Claude Code in it, and paste this. It's word for word what I ran on screen:

```text
Make a 5 second motion graphic, 1080 by 920: the words one command, one sentence slam in one at a time in cream Montserrat on dark navy, then an orange play button pops in and pulses. Render it to video.mp4
```

The 1080 by 920 size is because the graphic filled the top part of my reel. For a full vertical video, change it to 1080 by 1920. For YouTube, 1920 by 1080.

Then swap in your own words, colors and motion. Describe it the way you'd describe it to a person: what's on screen, what moves, in what order, how long.

## What happened when I ran it

- Claude Code set up the project in the empty folder, wrote the graphic as HTML, and rendered it to `video.mp4` (1080 by 920, 5 seconds).
- Start to finish took about three minutes. Claude Code's own timer said 3m 14s.
- It previewed its own work and fixed two things before the final render: the pulse ring showed up before the button did, and "ONE COMMAND," ran past the safe area, so it made the text a little smaller.
- It left two check warnings it said were fine. One is that the first frame is empty, because the words slam in from nothing.

Your result won't match mine frame for frame. Same prompt, different run.

## Change it

Tell Claude Code one change at a time and have it render again: "slower slam", "bigger button", "make the background black". To preview in the browser before rendering, ask it to run `npx hyperframes preview`.

## Next

Once you have a film you like, see [render/](../render/) for re-rendering only the part you changed instead of the whole thing.

## Cost

HyperFrames is free. Claude Code is whatever plan you're already on. Nothing in this folder is paid.
