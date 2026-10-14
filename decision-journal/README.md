# decision-journal (keyword: JOURNAL)

A small log for the calls your AI agent makes without asking you. Each entry says: decided X over Y because Z. Later you review them and mark each one confirmed, corrected, or noted.

Why: if an agent works alone, you need a way to check its judgment after the fact. Confirmed calls become rules you can hand to the agent. Corrected calls tell you where it guessed wrong.

One Python file. Standard library only. No network.

## Setup

From the repo root:

```bash
python3 decision-journal/decision_journal.py --help
```

Nothing to install. By default the journal lives at `~/.decision-journal/journal.json`. Change that with `--file PATH` or the `DECISION_JOURNAL_FILE` environment variable.

## Usage example

Log a call:

```bash
python3 decision-journal/decision_journal.py log \
  --context "Two APIs could fetch the data" \
  --decided "Used the free one" \
  --over "The paid one" \
  --because "Same output, no cost" \
  --area build --novelty routine
```

See what is waiting for review:

```bash
python3 decision-journal/decision_journal.py show
```

Review one (copy the uid from the output):

```bash
python3 decision-journal/decision_journal.py review --uid "build:2026-01-01T00:00:00+00:00:0" --verdict confirmed --note "Good call"
```

Other commands: `list`, `count`, `json`, `prune`.

## Tell your agent to use it

Add this to your project's `CLAUDE.md`:

```
When you make a consequential call on your own that is not obvious, log it right away:
python3 /path/to/decision_journal.py log --context ... --decided ... --over ... --because ...
Do not log routine steps.
```

## Notes

- Entries marked `irreversible`, not surfaced to you, and reasoned by the agent get a warning. Those are the riskiest rows.
- `show` prints nothing when there is nothing to review.
- Writes are atomic, so a crash won't corrupt the file. On macOS and Linux they're also locked, so two agents logging at once won't lose entries. Windows writes aren't locked.
- The journal file is readable only by your user.
- If the file is damaged (a bad hand edit, say), every command stops with an error and exit code 2 instead of starting a fresh journal over your history.
- If a write fails, the command says so and exits 2. It never prints `logged` for an entry it didn't save.
