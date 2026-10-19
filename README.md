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
| GUARD | [send-guard/](send-guard/) | A Claude Code hook that checks email before it goes out. If the recipient isn't on your approved list, Claude Code stops and asks you. | `mkdir -p ~/.claude/hooks/send-guard && cp send-guard/{send_guard.py,config.json,approved.txt} ~/.claude/hooks/send-guard/` then add the hook from [send-guard/](send-guard/#setup) |
| SKILLS | [skill-usage/](skill-usage/) | Counts each Claude Code skill two ways (calls and file reads) from your own transcripts, so you only delete what both counts say is dead. | `python3 skill-usage/skill_usage.py --help` |

More builds get added as each reel posts.

## Requirements

- Claude Code for `overnight` and `send-guard`.
- Python 3.9 or newer for `decision-journal`, `send-guard`, `skill-usage`, and `clip-variants`.
- ffmpeg for `clip-variants` (on a Mac: `brew install ffmpeg`).
- Tested on macOS. Linux should work. Windows isn't tested.

## Credit

The humanizer skill from the reels is by blader: https://github.com/blader/humanizer. It's linked here, not copied, so get it from the source.

## License

MIT. See [LICENSE](LICENSE).
