# 7 HyperFrames tricks

The seven items from the "7 HyperFrames tricks" carousel. HyperFrames is free and made by HeyGen. Each item comes from its installed docs or `npx hyperframes <command> --help` (v0.9.77). Setup for a first project: [studio/](../studio/) and [render/](../render/)

## 1. Re-render 3 seconds, not the whole film

```bash
npx hyperframes render --start 10 --end 13 -o renders/span.mp4
```

Source: `render --help`.

## 2. Fast drafts while you iterate

```bash
npx hyperframes render --quality draft -o draft.mp4
```

Source: the render docs.

## 3. Motion blur

Put `data-motion-blur="on"` on the composition root. Add `data-motion-blur-shutter` for a longer smear. The docs call a shutter value of 360 strong. Source: the motion docs, "Render-time blur".

## 4. Color grades side by side

```bash
npx hyperframes grade-compare --for frame.png --grades grades.json --out grade-compare.png
```

`grades.json` looks like this:

```json
[{ "label": "warm", "grading": { "adjust": { "temperature": 0.2, "contrast": 0.1 } } }]
```

Source: the compare docs.

## 5. 8 still frames from seconds 3 to 5

```bash
npx hyperframes snapshot --range 3,5 --frames 8
```

Source: the snapshot docs.

## 6. Render straight to a GIF

```bash
npx hyperframes render --format gif --fps 15 -o film.gif
```

The help says GIF is best at 15 fps.

## 7. Start from a ready made look

```bash
npx hyperframes init my-video --skip-skills --example warm-grain
```

Source: the init docs.
