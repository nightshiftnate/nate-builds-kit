# chime (keyword: CHIME)

A Claude Code hook that plays a sound when Claude finishes. Hand Claude a task, switch to something else, and come back the second it chimes.

The Claude desktop app already sends a notification when a task finishes and you aren't looking. In VS Code and the terminal, this hook does the same job with a sound.

It stays quiet when Claude isn't really done or nobody is listening:

- background work is still running (the turn ended, but Claude will pick it back up),
- Claude Code was started headless (`claude -p` or the SDK), for example from a script or a schedule.

One Python file. Standard library only, Python 3.9 or newer. No network.

## Setup

1. Copy the script:

```bash
mkdir -p ~/.claude/hooks && cp chime/chime.py ~/.claude/hooks/chime.py
```

2. Add the hook to `~/.claude/settings.json` (every project) or `.claude/settings.json` (one project). If the file already has a `"hooks"` block, add the `"Stop"` entry inside it.

```json
{
  "hooks": {
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "python3 ~/.claude/hooks/chime.py", "timeout": 10 }
        ]
      }
    ]
  }
}
```

3. Start a new Claude Code session (hooks load at start).

Or ask Claude to do it:

> Copy chime/chime.py from this repo to ~/.claude/hooks/chime.py, then add it as a Stop hook in my ~/.claude/settings.json without removing any hooks I already have. Show me the settings diff before you save it.

## What you'll see

Ask Claude anything. When it finishes, you hear the Mac "Glass" sound. If it started background work and will come back on its own, no sound until it's actually done.

Test it without waiting on Claude:

```bash
echo '{"background_tasks":[]}' | python3 ~/.claude/hooks/chime.py
```

You should hear the chime. Add `CHIME_DRY=1` in front to print the decision instead of playing it.

## Pick your sound

Set `CHIME_SOUND` to any sound file. On a Mac, the built-in ones are in `/System/Library/Sounds/`:

```json
{ "type": "command", "command": "CHIME_SOUND=/System/Library/Sounds/Hero.aiff python3 ~/.claude/hooks/chime.py", "timeout": 10 }
```

## How it decides

- Started with `-p` / `--print`, or from the SDK: quiet.
- Claude Code reports background tasks still in flight: quiet.
- Anything else: chime. If it can't read what Claude Code sent, it chimes anyway, because a missed chime is the worse mistake.

## Limits

- Mac uses `afplay`. Linux tries `paplay`, `pw-play`, then `aplay` with the freedesktop "complete" sound. Windows isn't supported.
- It stays quiet the whole time any background task is running, even one that has nothing to do with this turn.
- It's a sound, not a notification. If your Mac is muted or your headphones are off, you won't hear it.

## Tests

```bash
python3 -m pytest chime
```

or without pytest: `python3 chime/test_chime.py`. They test the decision only, no sound plays.

## Undo

Remove the `"Stop"` entry from your settings file and delete `~/.claude/hooks/chime.py`.

## Pairs with

`overnight/`. Kick off a long run, go do something else, and the chime tells you when it stops.
