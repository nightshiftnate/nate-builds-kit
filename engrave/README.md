# engrave (keyword: ENGRAVE)

The install line and the exact prompt from the "My mug, drawn like a dollar bill" reel. draw-beautiful is a free, open-source Claude Code skill by [bumicodes](https://github.com/bumicodes/draw-beautiful) (MIT license, not mine). Give it a photo and it builds the object in 3D, lights it with one sun, and draws every shadow as lines of ink, like the engraving on a bank note.

## 1. Install (one line)

You need Claude Code and Node. Paste this into your terminal:

```bash
npx skills add bumicodes/draw-beautiful -g -a claude-code
```

No API keys and nothing else to install. If Claude Code was already open, restart it.

## 2. The prompt

Put your photo in a folder, open `claude` in that folder, and paste this. It's also in [prompt.txt](prompt.txt). Swap the file name and the object for yours.

```text
/draw-beautiful engrave this photo of my coffee mug: mug.jpg. Keep the background clean, just the mug and its shadow on the table.
```

## 3. What happened when I ran it

- One prompt, one try. It took about 10 minutes from sending the prompt to done, uncut. The clock in the reel is the real one.
- It wrote the scene as code (`scene.mjs`, `build.mjs`) plus pages you open in your browser: the engraving on paper and a dark version.
- The sun still moves after it's done. When it moves, only the ink and the shadows redraw.

## Tips

- Simple solid shapes work best: mugs, bottles, vases, buildings, anything turned or boxy. I also tried a photo of a sports car, and after two prompts it was still a generic wedge, so skip cars.
- It won't draw people or pets. The skill says so itself.
- One clear photo, the object filling most of the frame, plain background.
