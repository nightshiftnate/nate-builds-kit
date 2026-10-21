#!/usr/bin/env python3
"""chime (keyword: CHIME): a Claude Code Stop hook that plays a sound when Claude is done.

Claude Code runs Stop hooks every time Claude finishes answering. This one plays a sound so you
can work in another window and come back the second it's done.

It stays quiet when Claude isn't really done or nobody is watching:
- background work is still running (the turn ended, but Claude will pick it back up),
- Claude Code was started headless (`claude -p`, the SDK), for example from a script or a schedule.

Standard library only, Python 3.9 or newer. No network. Test without sound: CHIME_DRY=1.
Pick your own sound with CHIME_SOUND=/path/to/file.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

MAC_SOUND = "/System/Library/Sounds/Glass.aiff"
LINUX_SOUND = "/usr/share/sounds/freedesktop/stereo/complete.oga"
CLAUDE_NAMES = {"claude", "claude.exe"}
MAX_HOPS = 8


def launcher_argv(pid=None):
    """argv of the nearest parent process that is `claude`, or None. Hook chain: claude -> sh -> python3."""
    pid = pid or os.getppid()
    for _ in range(MAX_HOPS):
        try:
            out = subprocess.run(["ps", "-o", "ppid=,args=", "-p", str(pid)],
                                 capture_output=True, text=True, timeout=2).stdout.strip()
        except Exception:  # noqa: BLE001
            return None
        if not out:
            return None
        ppid, _, args = out.partition(" ")
        argv = args.split()
        if argv and os.path.basename(argv[0]) in CLAUDE_NAMES:
            return argv
        if not ppid.strip().isdigit() or int(ppid) <= 1:
            return None
        pid = int(ppid)
    return None


def decide(payload, entrypoint, argv):
    """(chime?, reason). Pure, so the tests don't need a speaker."""
    if entrypoint.startswith("sdk-"):
        return False, f"headless ({entrypoint})"
    if argv and ("-p" in argv or "--print" in argv):
        return False, "headless (claude -p)"
    if not isinstance(payload, dict):
        return True, "unreadable input, chime anyway"  # a missed chime is the worse mistake
    tasks = payload.get("background_tasks")
    if isinstance(tasks, list) and tasks:
        return False, f"{len(tasks)} background task(s) still running"
    return True, "done"


def sound_command():
    custom = os.environ.get("CHIME_SOUND")
    if shutil.which("afplay"):
        return ["afplay", custom or MAC_SOUND]
    for player in ("paplay", "pw-play", "aplay"):
        if shutil.which(player):
            return [player, custom or LINUX_SOUND]
    return None


def main():
    try:
        payload = json.load(sys.stdin)
    except Exception:  # noqa: BLE001
        payload = None
    chime, reason = decide(payload, os.environ.get("CLAUDE_CODE_ENTRYPOINT", ""), launcher_argv())
    if os.environ.get("CHIME_DRY"):
        print(f"chime={chime} reason={reason}")
        return 0
    cmd = sound_command() if chime else None
    if cmd:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        except Exception:  # noqa: BLE001 - a sound must never break Claude Code
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
