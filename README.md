# Nate Builds starter kit

Working builds from the reels on Instagram at [@nightshiftnate](https://www.instagram.com/nightshiftnate/). If you commented KIT or a build keyword, this is the repo. Each folder is one build with its own README.

## Get it

```bash
git clone https://github.com/nightshiftnate/nate-builds-kit.git
cd nate-builds-kit
```

Every command below runs from this folder.

## Menu

| Keyword | Folder | What it does | Setup |
|---|---|---|---|
| NIGHT | [overnight/](overnight/) | A Claude Code skill. Plans your open projects before bed, asks for one approval, works until 06:15, and writes a morning summary. It's told to draft and park anything that would send, spend, or post. | `mkdir -p ~/.claude/skills/overnight && cp overnight/SKILL.md ~/.claude/skills/overnight/SKILL.md` |
| JOURNAL | [decision-journal/](decision-journal/) | Logs the calls your AI agent made on its own, so you can review each one later. | `python3 decision-journal/decision_journal.py --help` |
| CLIPS | [clip-variants/](clip-variants/) | Cuts one folder of clips into many short videos with different hooks, so you can test which hook works. | See [clip-variants/](clip-variants/#setup) (needs ffmpeg and a Python venv) |

More builds get added as each reel posts.

## Requirements

- Claude Code for `overnight`.
- Python 3.9 or newer for the other two.
- ffmpeg for `clip-variants` (on a Mac: `brew install ffmpeg`).
- Tested on macOS. Linux should work. Windows isn't tested.

## Credit

The humanizer skill from the reels is by blader: https://github.com/blader/humanizer. It's linked here, not copied, so get it from the source.

## License

MIT. See [LICENSE](LICENSE).
