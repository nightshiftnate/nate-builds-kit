# overnight (keyword: NIGHT)

A Claude Code skill. Before bed you type `/overnight`. It checks what you have open, writes a plan for each project, and asks you for one approval. Then it works until 06:15 and leaves a summary of what got done and what needs you.

The skill tells the agent it can build all night but must not send, spend, or post anything. Anything like that gets drafted and parked for your morning. That rule is an instruction to the model, not a lock, so keep Claude Code's permission prompts on for anything that reaches the outside world.

## Setup

From the repo root:

```bash
mkdir -p ~/.claude/skills/overnight && cp overnight/SKILL.md ~/.claude/skills/overnight/SKILL.md
```

Then restart Claude Code.

## Use

1. Plug in your laptop and leave the lid open.
2. In Claude Code, type `/overnight` (or say "going to bed, keep working").
3. Read the plan table and answer it before you walk away: GO, FLOOR (the safe minimum only), or a mix per row. If you send a correction, Claude shows the updated table and asks again, so stay until you've answered GO or FLOOR. If you don't answer, nothing runs. Claude waits for your reply.
4. Allow the commands the plan needs. Claude Code stops at any permission prompt, and nobody is awake to click it. The skill lists the exact commands it expects (your test command, for example). Allow those exact commands in your Claude Code permission settings. Never allow a whole tool like `npm` or `git`, because that also allows `npm publish` and `git push`. And don't switch on a mode that skips all prompts. If an unexpected prompt shows up, the whole session stops there until you answer it, and no summary gets written.
5. Go to sleep.
6. In the morning, read `.overnight/<date>/summary.md` in each project.

## Change it

- Stop time: edit "06:15" in `SKILL.md`.
- Spend ceiling: the skill defaults to $0 for paid APIs. Edit the Money rule to raise it.
- Notifications: if you have a chat bot or push service, tell Claude to use it when you start. It sends one message with counts only.

## Pairs with

`decision-journal/`, which logs the calls the agent made on its own so you can review them later.
