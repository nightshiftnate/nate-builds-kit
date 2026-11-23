# desk (keyword: DESK)

The 7 prompts and the rules file from the "7 prompts to Claude Code, Blender never opened" reel. Each prompt becomes a Python script that Blender runs headless: it builds the desk, adds the one new object, and renders a short clip. Every clip in the reel is Claude's own render.

You need Claude Code and Blender (free, [blender.org](https://www.blender.org/download/)). Claude runs Blender from the terminal with `blender -b`, so the `blender` command has to work in your terminal. On a Mac, if it doesn't, add this line to your `~/.zshrc`:

```bash
alias blender="/Applications/Blender.app/Contents/MacOS/Blender"
```

## 1. The rules file

Make an empty folder and save this in it as `CLAUDE.md`:

```markdown
# Night desk scene

- Run Blender headless only (`blender -b -P script.py`). Never open the Blender window.
- The scene lives in desk.blend. Each request gets its own script in steps/ (01_desk.py, 02_monitor.py, ...) that opens desk.blend (step 1 creates it), adds what was asked, and saves.
- After every step, render renders/NN.mp4: 1080x1920, 24 fps, 36 frames, EEVEE, H.264. In Blender 5.x set image_settings.media_type = 'VIDEO' before choosing FFMPEG. Also save the last frame as renders/NN.png.
- In that clip, only the new thing animates in during the first 12 frames: objects drop in with a small bounce, lights and screens switch on. Everything already there stays still, except steam, which always drifts.
- Camera: set it once in step 1 and never move it. Vertical frame, so get close: the desktop fills the frame edge to edge, seen from a little above, slightly turned. Leave the upper third for the wall where a window will go later, centered behind the desk.
- Add only what each request asks for. Never add an object a later request might ask for (no lamp, monitor, mug, plant or window until asked).
- Look: a dark room at night. Use AgX with a high-contrast look. Step 1 is lit only by a soft, dim cool fill from above-front plus a faint cool rim light from behind, enough to read the desk and its grain clearly. After that, light comes from what gets added: the monitor glow, then the lamp, which turns the scene warm. The room falls off into shadow around the desk.
- Screens show something real, like a dark code editor with colored lines of text, never a flat color.
- Materials have some texture: fine, natural, irregular wood grain on the desk (never even stripes or ridges), a little roughness on the wall.
- After each render, open NN.png and look at it. If anything is too dark, clipped, floating, or out of frame, fix the script and render again before you answer.
```

## 2. The 7 prompts

Open Claude Code in that folder (`claude`) and send these one at a time. Wait for each render before the next:

1. `Make a wooden desk in a dark room`
2. `add a monitor, screen glowing`
3. `add a keyboard`
4. `add a desk lamp, warm light`
5. `add a mug with steam`
6. `add a small plant`
7. `add a night window behind it, then render a slow orbit of the finished desk`

Your clips land in `renders/` (01.mp4 to 07.mp4). Join them in any editor, or ask Claude to join them with ffmpeg.

## What I learned

- Keep the "add only what each request asks for" line. In an earlier take, a lighting rule made Claude add a lamp at step 1 to light the desk, before the lamp prompt ever came.

Your desk won't match mine frame for frame. Same prompts, different run.
