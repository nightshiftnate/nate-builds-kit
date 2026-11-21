# 10 hook tests from one clip folder

The six steps from the "10 hook tests from one clip folder" carousel. One folder of clips goes in, ten vertical videos come out with a different hook on each, so you can see which opening works. Full script docs: [clip-variants/](../clip-variants/)

Use it on your own account only. Posting copies across many accounts breaks Instagram's rules.

```bash
git clone https://github.com/nightshiftnate/nate-builds-kit.git
cd nate-builds-kit
```

## 1. Set up once

Pillow draws the hook text.

```bash
python3 -m venv .venv && .venv/bin/pip install pillow
```

## 2. See the plan first

Add `--dry-run` to the run command. It prints the plan and renders nothing.

## 3. Run it

```bash
.venv/bin/python clip-variants/video_variants.py --clips ./my-clips --hooks clip-variants/hooks.txt --out ./out --count 10
```

## 4. Add a closing line

Add `--cta "your text"` and the last 2 seconds show your closing line.

## 5. Add music

Add `--music ./music` to mix a folder of audio in at low volume. Add `--mute-original` to drop the clips' own audio.

## 6. Keep the log

Keep `out/manifest.csv`. It records which hook went on which video.
