# 7 Claude Code prompts for video and motion

Seven prompts from this kit, copied as they are. Paste one into Claude Code, then open its folder for the setup it needs.

## 1. Cut the pauses and add captions

Cuts the dead air out of a clip and burns in captions. Setup: [cut/](../cut/)

```text
Cut every pause longer than half a second out of clip.mp4 and burn in captions.
```

## 2. A motion graphic from one sentence

Gets you a 5 second motion graphic, rendered to an mp4. Setup: [studio/](../studio/)

```text
Make a 5 second motion graphic, 1080 by 1920: the words one command, one sentence slam in one at a time in cream Montserrat on dark navy, then an orange play button pops in and pulses. Render it to video.mp4
```

## 3. Video, music and sound effects in one clip

Gets you one clip with its own music and sound effects. Setup: [sound/](../sound/)

```text
Make me a five second vertical clip of a neon diner at night in the rain, with its own music and sound effects.
```

## 4. Your photo, drawn like a bank note

Gets you your photo drawn as an engraving. Setup: [engrave/](../engrave/)

```text
/draw-beautiful engrave this photo of my coffee mug: mug.jpg. Keep the background clean, just the mug and its shadow on the table.
```

## 5. Plan a camera move in Blender

Gets you a grey-box clip you can hand to an AI video tool as the camera reference. Setup: [blender/](../blender/)

```text
Using Blender, build a grey-box scene: a straight street with boxes on both sides as buildings, and an orange mannequin walking down the middle. Add one camera that starts low behind the mannequin and cranes up and around to its right side, always aimed at it. Five seconds, vertical. Render it to an mp4.
```

## 6. Fix three seconds without re-rendering the film

After you render only the seconds you changed, this puts them back into the full film. Setup: [render/](../render/)

```text
splice renders/span.mp4 into renders/full.mp4 at 10 to 13 seconds.
```

## 7. Find the openings that lost people

Reads your reel numbers through Metricool and shows which reels lost people fastest in the first three seconds. Setup: [stats/](../stats/)

```text
Which of my reels lost people fastest in the first three seconds?
```
