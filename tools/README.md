# 5 free tools for Claude Code

The five tools from the "5 free tools for Claude Code" carousel. Each one is plain Python or a skill file, with no network calls. Open a folder for the full setup and what it does and doesn't cover.

Every command runs from the repo root, after you clone it:

```bash
git clone https://github.com/nightshiftnate/nate-builds-kit.git
cd nate-builds-kit
```

## 1. A sound when Claude finishes

A hook that plays a sound the second Claude is done, so you can work on something else. Setup: [chime/](../chime/)

```bash
mkdir -p ~/.claude/hooks && cp chime/chime.py ~/.claude/hooks/chime.py
```

Then add the `Stop` hook from [chime/](../chime/#setup).

## 2. Claude asks first before it emails anyone new

A hook that checks every email before it goes out. If a recipient isn't on your approved list, Claude Code stops and asks you. Setup: [send-guard/](../send-guard/)

```bash
mkdir -p ~/.claude/hooks/send-guard && cp send-guard/{send_guard.py,config.json,approved.txt} ~/.claude/hooks/send-guard/
```

Then add your addresses to `approved.txt` and the hook from [send-guard/](../send-guard/#setup).

## 3. Work while you sleep

A skill. Type `/overnight`, approve its plan once, and it works until 06:15, then leaves a summary. It drafts anything that would send, spend, or post and leaves it for your morning. Setup: [overnight/](../overnight/)

```bash
mkdir -p ~/.claude/skills/overnight && cp overnight/SKILL.md ~/.claude/skills/overnight/SKILL.md
```

## 4. Find the skills nobody uses

Counts each skill two ways from the transcripts Claude Code already keeps, so you only delete what both counts say is dead. Setup: [skill-usage/](../skill-usage/)

```bash
python3 skill-usage/skill_usage.py
```

## 5. Log the calls your agent made on its own

Each entry says what it picked, over what, and why. Review them later and mark each one confirmed or corrected. Setup: [decision-journal/](../decision-journal/)

```bash
python3 decision-journal/decision_journal.py --help
```
