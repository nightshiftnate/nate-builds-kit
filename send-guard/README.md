# send-guard (keyword: GUARD)

A Claude Code hook that checks email before it goes out. If the recipient isn't on your approved list, Claude Code stops and asks you. If everyone is approved, the hook stays quiet and Claude Code works as it normally does.

Why: telling Claude "don't send emails" is an instruction. This is a check on every send route you point it at. The script only looks at the addresses. It doesn't care how good Claude's reason sounds.

It's a seatbelt, not a vault. It checks the mail tools and shell mail commands it knows about. A route it doesn't know (a Python script you wrote that sends mail, an app with its own send button) isn't checked. See Limits.

It's a PreToolUse hook. Claude Code runs it before a tool runs. One Python file, standard library only, Python 3.9 or newer. No network.

## Setup

1. Put the folder somewhere stable. From the repo root:

```bash
mkdir -p ~/.claude/hooks/send-guard
cp send-guard/send_guard.py send-guard/config.json send-guard/approved.txt ~/.claude/hooks/send-guard/
```

2. Edit `~/.claude/hooks/send-guard/approved.txt`. One address per line, or a whole domain written as `@example.com`. Lines starting with `#` are skipped.

3. Add this to `~/.claude/settings.json` (merge it into any `hooks` you already have):

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Monitor|mcp__.*",
        "hooks": [
          {
            "type": "command",
            "command": "python3 ~/.claude/hooks/send-guard/send_guard.py"
          }
        ]
      }
    ]
  }
}
```

4. Restart Claude Code.

5. Check it's actually wired up. In Claude Code, ask Claude to run this exact command (it only prints text, nothing gets sent):

```bash
echo sendmail stranger@elsewhere.com
```

You should get a permission prompt that says `Not on your approved list: stranger@elsewhere.com`. No prompt means the hook isn't running. Check the path in step 3 and that `python3` works in your terminal.

## What you'll see

If Claude tries to email `stranger@elsewhere.com` and that address isn't approved, Claude Code shows a permission prompt with this reason: `Not on your approved list: stranger@elsewhere.com. Approve this send?` You say yes or no.

## How it decides

- A tool call is treated as an email send if the tool name matches a pattern in `config.json` (`tool_patterns`), or it's a Bash command that matches `bash_patterns`.
- For a tool, it reads the recipients from fields named `to`, `cc`, `bcc`, `recipient`, `recipients` (`recipient_keys`). Every value has to be a plain address, `Name <address>`, an object holding the address under `email`, `address` or `emailAddress` (`address_keys`), or a list of those. Anything else (a group name like `team-all`, a contact name, an address with odd characters) asks.
- A reply always asks, because it also goes to the people already on the thread and their addresses aren't in the call. Sending a saved draft (`draftId`) always asks, because the draft goes to whoever it's addressed to.
- For Bash (and Monitor), it reads the command the way the shell does, quotes and all, and checks every email address in it, including the sender and any address in the message text. The sender (`-f`, `-r`, `--from`) and addresses in the message text are checked but don't count as recipients. A word it can't read as a plain address (`x=you@example.com`, `"x you"@example.com`) asks.
- A shell send asks if the recipients come from somewhere it can't read: a variable (`$TO`), `$(...)` or backticks, `xargs`, or a flag that reads them from the message, in any spelling (`sendmail -t`, `-it`, `'-t'`, `sendmail -bs`, `msmtp --read-recipients` or `--read-rec`, `mutt -H draft`).
- It also asks when the command points the mail program at a settings file, because that file can add recipients: `mutt -F`, `mutt -e`, `curl -K` or `--config`, an environment variable set on the command (`MUTTRC=./rc mutt ...`), or `export`, `declare`, `source` and `.` in the same command.
- It asks when a shell send has `{ }`, `( )`, `*`, `?` or `[ ]` outside quotes, because the shell rewrites those words after the hook reads them (`sendmail -{t,i}` becomes `-t -i`). Quote them if they're in a subject. The message text of a mail heredoc (`mail ... <<EOF`) is left out of this check and the flag and settings checks, so a sign-off like `-Kate` or a `.` line doesn't ask. Its addresses are still checked.
- Every flag in a shell send has to be on the `safe_flags` list in `config.json`, or it asks. Mail programs have many flags that change where mail goes (`sendmail -C`, `mail -S`, `-b` modes), so the hook only lets through the common ones it knows are harmless. `-p` and `-q` are left off on purpose (`mutt -p` sends a saved draft, `sendmail -q` runs the mail queue). Program names count in any case (`Mutt`, `SENDMAIL`), because a Mac disk usually ignores case. If one of yours asks every time and you know it's harmless, add it to `safe_flags`.
- Any recipient not approved: ask. No recipient found on something that looks like a send: ask.
- Everything else: no output, so Claude Code's normal permission rules still apply. The hook never says "allow", because that would skip prompts you rely on.

## Make it fit your email tool

Open `config.json`.

- `tool_patterns`: regular expressions (case doesn't matter) matched against the tool name. Find your tool's name in Claude Code with `/mcp`. MCP tools are named `mcp__<server>__<tool>`. Add a pattern like `^mcp__myserver__send_email$`.
- `bash_patterns`: regular expressions matched against Bash commands. Add the command line sender you use, for example `\\bmyemailcli\\b`.
- `recipient_keys`: field names that hold recipients. If your tool calls it `addresses`, add that name.
- `safe_flags`: flags a shell send may use without asking. Long flags count with or without `=value`, and a group of listed short flags (`-sv`) counts too.
- `address_keys`: when a recipient is an object, the field names that hold its address.
- `reply_tool_patterns`: tool names that are replies (always ask). `draft_keys`: fields that mean "send this saved draft" (always ask).
- `shell_tools`: tools whose `command` field is shell text (`Bash`, `Monitor`).

Check it with fake input, no Claude needed:

```bash
echo '{"tool_name":"mcp__myserver__send_email","tool_input":{"to":"someone@elsewhere.com"}}' | python3 send-guard/send_guard.py
```

Prints an "ask" decision when the address isn't approved, nothing when it is.

## When in doubt it asks

Input it can't parse, a recipient it can't read, a missing approved list, or an error while checking all end in "ask". If you delete `approved.txt`, every email send asks and the prompt says where it looked for the list. Commands that don't name a mail program stay quiet. One that only names one (`which sendmail`, `man mutt`, `brew install msmtp`) asks with "found no recipient"; say yes.

One thing it can't cover from the inside: if Claude Code can't start the hook at all (wrong path, no `python3`) or the hook times out, Claude Code shows an error and carries on. That's why step 5 matters. Run it again after you move the folder or change Python.

## Limits

- It only sees tools you point it at. A send route the patterns don't cover isn't checked. Add a pattern for each route you use.
- A hook can be turned off by whoever can edit your settings. Keep the file in your own user settings.
- Bash matching is pattern based. It catches common senders (`sendmail`, `mail`, `mailx`, `mutt`, `msmtp`, `swaks`, `mailsend`, `smtp://` URLs), not every way to send mail. A `mailsend` send always asks, because its `-to` flag reads like `-t`. `python3 send_email.py` is not caught. Add a pattern for each script of your own that sends.
- A shell word without an `@` isn't read as a recipient. If your mail server turns a local name like `team` into a list, `mail you@example.com team` would pass on your address alone.
- The tool patterns also match chat tools named like `send_message` (Slack, Discord). Those ask with "found no recipient". Narrow `tool_patterns` if that gets noisy.
- `$` anywhere in a shell send asks, even a price in the message text. That's on purpose. So do `-t` or `-H` anywhere in the command (`curl -H`, `swaks -t`); use `swaks --to` instead. Any flag not on `safe_flags` asks too, even one that belongs to another program in the same command (`git log --oneline | mail ...`).
- It reads commands the way bash does. zsh has extra rewrites (glob modifiers, `=cmd`); the common ones ask because of the `( )` rule, but not every zsh feature is covered.
- A file a command writes and then runs (`cat > x.sh <<EOF ... EOF; sh x.sh`) isn't read. Treat scripts like that as a send route of their own and add a pattern for them.
- It doesn't see a mail program's own default settings files (`~/.muttrc`, `~/.mailrc`, `~/.msmtprc` aliases, `~/.curlrc`). If one of those adds a Bcc or rewrites an address, the hook can't tell. Keep Claude from editing them.
- A heredoc with an unmatched quote (an apostrophe in the message) is read word by word with the quotes left on. An address touching a quote then can't be read, so it asks.

## Tests

```bash
python3 -m pytest send-guard
```

or without pytest: `python3 send-guard/test_send_guard.py`. They feed fake hook JSON on stdin: approved recipients pass; unknown, unreadable or hidden recipients ask; replies and drafts ask; bad input asks; ordinary commands stay quiet.

## Undo

Remove the `PreToolUse` entry from `~/.claude/settings.json` and restart Claude Code. Then `rm -r ~/.claude/hooks/send-guard` if you want the files gone.

## Pairs with

`overnight/`. Its "never send" rule is an instruction. This is a check behind it.
