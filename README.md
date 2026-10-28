# Nate Builds kit

The prompts and code behind the reels at [@nightshiftnate](https://www.instagram.com/nightshiftnate/). Every reel there is motion graphics or video built in Claude Code, and each one gets a folder here with the prompt, what broke along the way, and the command that renders it. If you commented a keyword on a reel, the folder with that keyword is the one you want.

## Get it

```bash
git clone https://github.com/nightshiftnate/nate-builds-kit.git
cd nate-builds-kit
```

Every command below runs from this folder.

## Motion and video

Folders land here as each motion reel posts.

| Keyword | Folder | What it does | Setup |
|---|---|---|---|
| CUT | [cut/](cut/) | The exact prompt from the "How to edit a video with Claude Code" reel. One line that cuts the pauses out of a clip and burns in captions, plus what happened when I ran it. | Put your video in a folder as `clip.mp4`, run `claude` there, and paste the prompt from [cut/](cut/) (needs ffmpeg-full and whisper.cpp) |
| EDIT | [edit-check/](edit-check/) | A Python script that checks a rendered video before you watch it: length, size, frame rate, audio, loudness, peak, silence, black frames, frozen video, and an optional script match. Each check measures the file and prints PASS or FAIL. Claude Code runs it after every render and fixes what fails. | Copy [edit_check.py](edit-check/edit_check.py) into your video project, then paste [edit-check/CLAUDE.md](edit-check/CLAUDE.md) into its `CLAUDE.md` (needs ffmpeg) |

## Earlier builds

These came from the account's first reels, before it went all in on motion. They still work and they're still free.

| Keyword | Folder | What it does | Setup |
|---|---|---|---|
| NIGHT | [overnight/](overnight/) | A Claude Code skill. Plans your open projects before bed, asks for one approval, works until 06:15, and writes a morning summary. It's told to draft and park anything that would send, spend, or post. | `mkdir -p ~/.claude/skills/overnight && cp overnight/SKILL.md ~/.claude/skills/overnight/SKILL.md` |
| JOURNAL | [decision-journal/](decision-journal/) | Logs the calls your AI agent made on its own, so you can review each one later. | `python3 decision-journal/decision_journal.py --help` |
| CLIPS | [clip-variants/](clip-variants/) | Cuts one folder of clips into many short videos with different hooks, so you can test which hook works. | See [clip-variants/](clip-variants/#setup) (needs ffmpeg and a Python venv) |
| GUARD | [send-guard/](send-guard/) | A Claude Code hook that checks email before it goes out. If the recipient isn't on your approved list, Claude Code stops and asks you. | `mkdir -p ~/.claude/hooks/send-guard && cp send-guard/{send_guard.py,config.json,approved.txt} ~/.claude/hooks/send-guard/` then add the hook from [send-guard/](send-guard/#setup) |
| SKILLS | [skill-usage/](skill-usage/) | Counts each Claude Code skill two ways (calls and file reads) from your own transcripts, so you only delete what both counts say is dead. | `python3 skill-usage/skill_usage.py --help` |
| CHIME | [chime/](chime/) | A Claude Code hook that plays a sound when Claude finishes, so you can work on something else and come back the second it's done. | `mkdir -p ~/.claude/hooks && cp chime/chime.py ~/.claude/hooks/chime.py` then add the hook from [chime/](chime/#setup) |
| OUTLIERS | [outliers/](outliers/) | Finds Instagram reels that beat a creator's normal views by 3x or more, from a watchlist you choose, using Instagram's official API. Search it in the terminal or ask your Claude Code through an MCP server. | `claude mcp add outliers -s user -- python3 "$PWD/outliers/mcp_server.py"` after the Meta setup in [outliers/](outliers/#setup) |

## Requirements

- Claude Code for `overnight`, `send-guard`, `edit-check` and `cut`.
- Python 3.9 or newer for `decision-journal`, `send-guard`, `skill-usage`, `clip-variants`, and `edit-check`.
- ffmpeg for `clip-variants` and `edit-check` (on a Mac: `brew install ffmpeg`).
- For `cut`: an ffmpeg build that can burn in captions, plus whisper.cpp (on a Mac: `brew install ffmpeg-full whisper-cpp`).
- Tested on macOS. Linux should work. Windows isn't tested.

## Credit

The humanizer skill from the reels is by blader: https://github.com/blader/humanizer. It's linked here, not copied, so get it from the source.

## License

MIT. See [LICENSE](LICENSE).
