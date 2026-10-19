# skill-usage (keyword: SKILLS)

Counts each of your Claude Code skills two ways, from the transcripts Claude Code already keeps on your machine:

- CALLS: how often Claude used the Skill tool with that skill's name.
- READS: how often Claude opened that skill's `SKILL.md` file.

Then it lists every skill with both numbers and marks it `in use`, `dead by one only`, or `dead by both`.

Why: one count can call a skill dead when it isn't. A skill can have zero calls and still get opened all the time, because Claude reads its file as part of other work. If you delete off one count, you delete things you use. Delete only what both counts say nobody touches.

One Python file. Standard library only, Python 3.9 or newer. Read only: it never changes a transcript or a skill. It prints skill names and numbers, never what was said in a session. No network.

## Setup

From the repo root:

```bash
python3 skill-usage/skill_usage.py --help
```

Nothing to install.

## Use

```bash
python3 skill-usage/skill_usage.py
```

Example output (made-up skills):

```
SKILL     CALLS   READS  STATUS
old-tool      0       0  dead by both
reports       0     41  dead by one only
notes        12      9  in use

3 transcript files scanned, 3 skills listed.
dead by both: 1 | dead by one count only: 1 | in use: 1
```

Options:

- `--projects DIR` where the transcripts are (default `~/.claude/projects`).
- `--skills DIR` where your skills are (default `~/.claude/skills`). Repeat it to add more folders.
- `--json` print JSON instead of a table.

## How to read it

- `dead by both`: no calls and no file reads in your history. These are the only delete candidates. Look at each one before you remove it.
- `dead by one only`: one count is zero, the other isn't. The skill is still being used. Leave it.
- `in use`: both counts are above zero.

## Limits

- It only knows what's in the transcripts on this machine. Old sessions you deleted don't count, and a skill you just installed will show zero.
- A READS count can include times you or Claude opened the file to edit it, not only to follow it.
- Skills from plugins are matched by their short name. Skills that live in a project folder are listed if you pass that folder with `--skills`.

## Tests

```bash
python3 -m pytest skill-usage
```

or without pytest: `python3 skill-usage/test_skill_usage.py`. They build small made-up transcripts, so nothing real is read.

## Undo

Nothing to undo. It writes nothing. Delete the folder if you don't want it.

## Pairs with

`decision-journal/`. Log the "delete this skill" call there so you can review it later.
