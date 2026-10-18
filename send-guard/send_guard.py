#!/usr/bin/env python3
"""send-guard: a Claude Code PreToolUse hook that checks outgoing email.

Claude Code runs this before a tool runs and sends it JSON on stdin.
If the tool looks like an email send and any recipient is not on your
approved list, or a recipient can't be read, this prints an "ask"
decision, so Claude Code stops and asks you. Otherwise it prints nothing
and exits 0, which leaves Claude Code's normal permission flow in charge.
It never prints "allow", because "allow" would skip the prompts you
already rely on.

When in doubt it asks: bad input, a missing or empty approved list, a
recipient it can't read, recipients it can't see (a reply, a saved draft,
a shell variable, a file), or any error while checking all end in "ask".

Python 3.9+, standard library only. No network.

Settings (all optional):
  SEND_GUARD_APPROVED  path to the approved list (default: approved.txt next to this file)
  SEND_GUARD_CONFIG    path to the config file (default: config.json next to this file)
"""
import json
import os
import re
import shlex
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# One plain address, matched against a whole value, never searched for inside
# one: "x!you@example.com" is a different mailbox from "you@example.com".
ADDR = re.compile(r"[A-Za-z0-9._%+\-']+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)*\.[A-Za-z]{2,}")
# Things that mean the real recipients come from somewhere this hook can't read.
# Program names are matched ignoring case: macOS disks usually ignore case,
# so XARGS, Mutt and SendMail run the real programs.
HIDDEN = [
    (re.compile(r"\$"), "a shell variable or $( )"),
    (re.compile(r"`"), "backticks"),
    (re.compile(r"\bxargs\b", re.I), "xargs"),
]
# Flags whose next word is the sender or a login, not a recipient. That
# address is still checked, but it never counts as "found a recipient".
SENDER_FLAGS = {"-f", "-r", "-F", "-u", "--from", "--mail-from", "--sender",
                "--envelope-from", "--user", "--auth-user"}
LOGIN_FLAGS = {"-u", "--user", "--auth-user"}  # value is user:password
# A word that runs as a shell script of its own: bash -c "...", sh -lc '...'.
SCRIPT_FLAG = re.compile(r"-[A-Za-z]*c|eval")
ENV_SET = re.compile(r"[A-Z_][A-Z0-9_]*\+?=")
# Shell words that set variables or settings a mail program run later may read.
SETS_STATE = {"export", "declare", "typeset", "readonly", "alias", "source", "."}
# A heredoc start: <<EOF, <<-EOF, <<'EOF', <<"EOF" (not the <<< here-string).
HEREDOC = re.compile(r"(?<!<)<<(?!<)(-?)[ \t]*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\2")
# Where the shell's delimiter word can end. Anything else (END-MSG, EOF.txt)
# means the word is longer than the match, so the match isn't the delimiter.
# Only space and tab: bash reads \r, \v, \f or a no-break space as part of the word.
WORD_END = re.compile(r"$|[ \t;|&()<>]")
# A line where a heredoc body could run as code instead of being a message.
RUNS_SCRIPT = re.compile(r"(?:^|[\s;|&(/])(?:ba|z|k|da|c|tc|fi)?sh\b|\beval\b|\bsource\b"
                         r"|(?:^|[\s;|&])\.\s|\bpython|\bperl\b|\bruby\b|\bnode\b|\bphp\b"
                         r"|\bosascript\b|\bxargs\b", re.I)
# Unquoted, these make the shell rewrite words after the hook has read them:
# braces ({a,b} -> a b), globs (* ? [ ]), subshells and zsh glob modifiers
# ( ), and zsh number ranges (<1-9>).
EXPANDS = re.compile(r"[{}*?\[\]()]|<\d*-\d*>")

DEFAULT_CONFIG = {
    "tool_patterns": [
        r"^mcp__.*(send|reply|forward).*(mail|message|gmail|draft).*$",
        r"^mcp__.*(mail|gmail|outlook|smtp|sendgrid|mailgun|postmark|resend).*(send|reply|forward).*$",
    ],
    # Replies go to people already on the thread, who are in no field.
    "reply_tool_patterns": [r"reply"],
    # A saved draft goes out as it is addressed; any "to" next to it is ignored.
    "draft_keys": ["draftId", "draft_id", "draft"],
    # Tools whose "command" is shell text. Any other non-mail tool with a
    # string "command" field is checked the same way.
    "shell_tools": ["Bash", "Monitor"],
    "bash_patterns": [
        # Rare words: match anywhere, so `echo sendmail x@y` (the wiring check) asks too.
        r"\bsendmail\b", r"\bmsmtp\b", r"\bmutt\b", r"\bswaks\b", r"\bmailsend\b", r"smtps?://",
        # "mail" is an everyday word: only where it runs as a command, or with mail-style arguments.
        r"(?:^|[|;&({\n]|\bsudo|\bexec|\bcommand|\bnohup|\bxargs|-c\s+['\"])\s*(?:\S{0,200}/)?mailx?\b",
        r"\bmailx?\s+(?:-[sbcrEaq]\b|[^\s@]+@)",
    ],
    # Flags allowed on a mail program's command line. Any other flag asks.
    # A group of these short flags (-sS, -oi) is fine too.
    "safe_flags": [
        # Not here on purpose: -p (mutt sends a postponed draft) and -q
        # (sendmail runs the mail queue), which send to people this can't see.
        "-s", "-a", "-c", "-b", "-i", "-v", "-f", "-r", "-F", "-u", "-T", "-k",
        "-n", "-e", "-E", "-oi", "-sS",
        "--to", "--from", "--cc", "--bcc", "--server", "--host", "--port", "--account",
        "--auth", "--auth-user", "--auth-password", "--tls", "--tls-on-connect", "--ssl",
        "--ssl-reqd", "--url", "--mail-from", "--mail-rcpt", "--mail-auth",
        "--upload-file", "--user", "--silent", "--show-error", "--verbose", "--insecure",
        "--netrc", "--subject", "--attach", "--sender", "--envelope-from", "--header",
        "--add-header", "--body", "--ehlo", "--helo", "--timeout", "--protocol",
    ],
    "recipient_keys": ["to", "cc", "bcc", "recipient", "recipients"],
    # When a recipient is an object, the address is under one of these.
    "address_keys": ["email", "address", "emailAddress"],
}


def ask(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "ask",
            "permissionDecisionReason": reason,
        }
    }


def load_config():
    path = os.environ.get("SEND_GUARD_CONFIG") or os.path.join(HERE, "config.json")
    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cfg.update(json.load(f))
    return cfg


def approved_path():
    return os.environ.get("SEND_GUARD_APPROVED") or os.path.join(HERE, "approved.txt")


def load_approved():
    """Return (exact addresses, domains), both lowercase, or None if the file is missing."""
    path = approved_path()
    if not os.path.exists(path):
        return None
    exact, domains = set(), set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip().lower()
            if not line or line.startswith("#"):
                continue
            if line.startswith("@"):
                domains.add(line)
            else:
                exact.add(line)
    return exact, domains


def is_approved(addr, exact, domains):
    addr = addr.lower()
    return addr in exact or "@" + addr.split("@", 1)[1] in domains


def one_address(part):
    """The address in "a@b.co", "Name <a@b.co>" or "\"Last, First\" <a@b.co>", else None.

    Plain string checks, no regex over the whole value: a pattern for
    "Name <addr>" backtracks badly on long runs of spaces, and a hook that
    runs past its timeout lets the send go ahead.
    """
    part = part.strip()
    if ADDR.fullmatch(part):
        return part
    if part.endswith(">") and "<" in part:
        i = part.rindex("<")
        name, addr = part[:i].strip(), part[i + 1:-1].strip()
        quoted = len(name) >= 2 and name[0] == name[-1] == '"' and '"' not in name[1:-1]
        # An unquoted name may not hold an @, so
        # "you@example.com <stranger@elsewhere.com>" can't pass as you.
        if (quoted or not re.search(r'["<>@,;]', name)) and ADDR.fullmatch(addr):
            return addr
    return None


def read_recipients(value, address_keys, addrs, unreadable):
    """Sort one recipient field into readable addresses and values it can't read."""
    if value is None:
        return
    if isinstance(value, str):
        for part in re.split(r"[,;]", value) if '"' not in value else [value]:
            if not part.strip():
                continue
            addr = one_address(part)
            if addr:
                addrs.append(addr)
            else:
                unreadable.append(part.strip()[:80])
    elif isinstance(value, (list, tuple)):
        for v in value:
            read_recipients(v, address_keys, addrs, unreadable)
    elif isinstance(value, dict):
        keys = [k for k in value if str(k) in address_keys]
        if not keys:
            unreadable.append(json.dumps(value)[:80])
        for k in keys:
            read_recipients(value[k], address_keys, addrs, unreadable)
    else:
        unreadable.append(repr(value)[:80])


def recipient_fields(tool_input, keys):
    """Values stored under recipient-like keys, at any depth."""
    found = []
    wanted = {k.lower() for k in keys}

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if str(k).lower() in wanted:
                    found.append(v)
                else:
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(tool_input)
    return found


def has_key(node, keys):
    wanted = {k.lower() for k in keys}
    if isinstance(node, dict):
        return any(str(k).lower() in wanted or has_key(v, keys) for k, v in node.items())
    if isinstance(node, list):
        return any(has_key(v, keys) for v in node)
    return False


def hidden_flag(word, mutt):
    """Why this word means the mail goes somewhere send-guard can't read, else None.

    `word` has had its quotes and backslashes taken off, the way the shell
    takes them off, so '-t', "-"t and -\\t all read as -t.
    """
    if word.startswith("--"):
        name = word[2:].split("=", 1)[0].lower()
        # msmtp takes any unique start of a long flag: --rea, --read-rec.
        if name.startswith("read") or (len(name) >= 3 and "read-recipients".startswith(name)):
            return "%s reads the recipients from the message" % word
        if name.startswith("conf"):
            return "%s reads settings from a file" % word
        return None
    if word.startswith("-"):
        letters = re.match(r"[A-Za-z]*", word[1:]).group(0)
        # -t anywhere in a group of short flags (-it, -oi -t), mutt -H draft,
        # sendmail -bs (recipients come in on stdin).
        if "t" in letters or "H" in letters or letters[:2] in ("bs", "bS"):
            return "%s reads the recipients from the message" % word
        # curl -K config; mutt -F muttrc and -e commands can add a Bcc.
        if "K" in letters or (mutt and ("F" in letters or "e" in letters)):
            return "%s reads settings from a file" % word
        return None
    return None


def state_change(code):
    """Why `code` sets something a mail program run later may read, else None.

    `code` has its mail heredoc text taken out. VAR=value only counts outside
    quotes (a quoted one is not an assignment); export, source and . count
    as the shell reads the words, so "export" and \\export still ask, but a
    "." inside a quoted subject does not.
    """
    for script in scripts(code):  # bash -c "MUTTRC=./rc mutt ..." too
        for w in re.split(r"[\s;|&()<>]+", unquoted(script)):
            if ENV_SET.match(w):
                return "%s sets an environment variable the mail program may read" % w
    for w in shell_words(code):
        w = re.sub(r"['\"\\]", "", w)
        if w in SETS_STATE:
            return "%s changes what the mail program reads" % w
    return None


def unknown_flag(word, safe):
    """The flag in `word` if it isn't on the safe list, else None.

    Mail programs have many flags that change where mail goes (alias files,
    config files, SMTP-on-stdin modes). Rather than chase every one, a flag
    on a mail program's command line has to be on `safe_flags` in
    config.json, or the send asks.
    """
    if word in ("-", "--") or word in safe:
        return None
    if word.startswith("--"):
        name = word.split("=", 1)[0]
        # swaks --h-Subject: sets a header. Envelope recipients come only from --to.
        return None if name in safe or name.startswith("--h-") else name
    if not re.match(r"-[A-Za-z]", word):
        return None
    if word[:2] in ("-f", "-r") and "@" in word:
        return None  # -fyou@example.com: the sender, checked as an address
    if re.fullmatch(r"-[A-Za-z]+", word) and all("-" + c in safe for c in word[1:]):
        return None  # a group of safe short flags, like -sS or -oi
    return word


def scripts(text, depth=0):
    """`text`, plus every script inside it run by bash -c "..." or eval, to depth 3."""
    out = [text]
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        words = list(lex)
    except ValueError:
        return out
    for i, w in enumerate(words):
        if i and SCRIPT_FLAG.fullmatch(words[i - 1]):
            if depth >= 3:
                out.append("{")  # too deep to read: forces an ask
            else:
                out.extend(scripts(w, depth + 1))
    return out


def strip_heredocs(text, cfg):
    """`text` without the bodies of heredocs that are a mail message.

    A body is dropped only when its << line runs a mail program and no
    shell or interpreter (bash <<EOF runs the body as a script, so that
    body stays), and every << on the line is outside quotes and comments.
    Quotes are followed from line to line, since one opened on an earlier
    line can hold a "<<EOF". Once a << it can't place turns up (in quotes,
    or on a line a quote runs across), nothing after it is dropped, because
    from there it can't tell body lines from commands. The same goes for any
    command line with a backslash or a # outside quotes (except a line that
    is only a comment), a << it can't read, a
    delimiter word the match doesn't cover whole (<<END-MSG) and for a line
    that is the delimiter only once spaces are trimmed ("  EOF"): the shell
    reads both differently from a plain match. A body ends only at a line
    that is exactly the delimiter (after leading tabs, for <<-), the same
    line the shell ends it at.
    """
    out, waiting, drop, quote, trust = [], [], False, None, True
    for line in text.split("\n"):
        if waiting:
            dash, quoted, word = waiting[0]
            if (line.lstrip("\t") if dash else line) == word:
                waiting.pop(0)
                out.append(line)
                continue
            if line.strip() == word or (not quoted and line.endswith("\\")):
                # The shell reads on past this line (with an unquoted
                # delimiter, a trailing backslash joins the next line on, so
                # "abc\" + "EOF" is "abcEOF"), so from here the hook can't
                # tell where the body ends: drop nothing more.
                waiting, trust = [], False
            if not drop or not trust:
                out.append(line)
            continue  # heredoc text: the shell reads no quotes in it
        out.append(line)
        if quote is None and line.lstrip(" \t").startswith("#"):
            # A whole comment line: bash and zsh skip all of it, a trailing
            # backslash or apostrophe included, so it changes nothing.
            continue
        starts = list(HEREDOC.finditer(line))
        before = quote
        spots, quote = code_spots(line, quote)
        # A backslash or a # outside quotes is where the hook's reading of
        # quotes and comments can part from the shell's (a\ #' opens a quote
        # the shell sees; a line ending in \ joins the next one on), so from
        # the first one on nothing is dropped. With neither on the line,
        # quotes simply open and close, and code_spots follows them exactly.
        if "\\" in line or any(line[p] == "#" for p in spots):
            trust = False
        # Every << on the line has to be one HEREDOC reads (<<"E"OF isn't).
        ops = {m.start() for m in re.finditer(r"(?<!<)<<(?!<)", line)}
        if ops and (before or quote or not all(m.start() in spots for m in starts)
                    or ops != {m.start() for m in starts}
                    or not all(WORD_END.match(line, m.end()) for m in starts)):
            trust = False
        if not trust:
            continue
        waiting = [(m.group(1), m.group(2), m.group(3)) for m in starts]
        drop = (bool(waiting) and any(re.search(p, line, re.I) for p in cfg["bash_patterns"])
                and not RUNS_SCRIPT.search(line))
    return "\n".join(out)


def code_spots(line, quote=None):
    """(positions in `line` the shell reads as code, the quote still open at its end).

    Code means outside quotes and before a # comment (the # itself counts,
    so a caller can see a comment was there). `quote` is the quote left open
    by the line before (' or "), or None.
    """
    spots, i, n = set(), 0, len(line)
    while i < n:
        c = line[i]
        if quote == "'":
            j = line.find("'", i)
            if j < 0:
                return spots, quote
            i, quote = j + 1, None
        elif quote == '"':
            while i < n and line[i] != '"':
                i += 2 if line[i] == "\\" else 1
            if i >= n:
                return spots, quote
            i, quote = i + 1, None
        elif c == "\\":
            spots.add(i)
            i += 2
        elif c in "'\"":
            i, quote = i + 1, c
        elif c == "#" and (i == 0 or line[i - 1] in " \t;|&()<>"):
            spots.add(i)
            return spots, None  # a comment runs to the end of the line
        else:
            spots.add(i)
            i += 1
    return spots, quote


def unquoted(text):
    """The characters of `text` that sit outside quotes, or all of it if the quotes don't balance."""
    out, i, n = [], 0, len(text)
    while i < n:
        c = text[i]
        if c == "\\":
            i += 2
            continue
        if c == "'":
            j = text.find("'", i + 1)
            if j < 0:
                return text
            i = j + 1
            continue
        if c == '"':
            j = i + 1
            while j < n and text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            if j >= n:
                return text
            i = j + 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def shell_words(text, depth=0):
    """The words the shell would see, with quotes and backslashes taken off.

    A quoted word that is itself a script (bash -c "...") is read again as
    shell. Any other word that still holds a space after unquoting is kept
    whole, so "x you"@example.com stays one unreadable word.
    """
    try:
        lex = shlex.shlex(text, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        lex.commenters = ""
        words = list(lex)
    except ValueError:
        # Unbalanced quotes, often an apostrophe in a heredoc. Split on spaces
        # and keep the quotes on, so an address glued to a quote can't be read
        # and asks.
        words = text.split()
    out = []
    for i, w in enumerate(words):
        if re.search(r"\s", w) and i and SCRIPT_FLAG.fullmatch(words[i - 1]):
            if depth >= 3:
                out.append(w)
            else:
                out.extend(shell_words(w, depth + 1))
        else:
            out.append(w)
    return out


def check_shell(command, cfg):
    """Return (ask reason or None, recipient addresses, sender addresses) for shell text."""
    if not any(re.search(p, command, re.I) for p in cfg["bash_patterns"]):
        return None, None, None

    def hidden(what):
        return ("This command sends mail with recipients send-guard can't see (%s). "
                "Approve this send?" % what[:200]), None, None

    for pat, what in HIDDEN:
        if pat.search(command):
            return hidden(what)
    # The message text of a mail heredoc is not shell, so it is left out of
    # the flag, settings and expansion checks: "-Kate" signing off, a "."
    # line ending a sendmail message, or "(after 5)?" is not shell.
    code = strip_heredocs(command, cfg)
    # <<-EOF is a heredoc that trims tabs; its -EOF is a delimiter, not a flag.
    flags_in = re.sub(r"(?<!<)<<-(?=[ \t]*['\"]?[A-Za-z_])", "<< ", code)
    # Flags are looked for in a second, rougher split with every quote and
    # backslash removed, so no spelling of -t gets past.
    mutt = re.search(r"\bmutt\b", command, re.I) is not None
    sendmail = re.search(r"\bsendmail\b", command, re.I) is not None
    bare = re.sub(r"['\"\\]", "", flags_in)
    for w in re.split(r"[\s;|&()<>]+", bare):
        why = hidden_flag(w, mutt)
        if not why and sendmail and re.match(r"-[A-Za-z]*b", w):
            why = "%s picks a sendmail mode (-bs reads recipients from stdin)" % w
        if why:
            return hidden(why)
    why = state_change(code)
    if why:
        return hidden(why)
    for script in scripts(code):
        m = EXPANDS.search(unquoted(script))
        if m:
            return ("This command has %s outside quotes, so the shell can change the "
                    "addresses after send-guard reads them. Approve this send?"
                    % m.group(0)), None, None
    # Every flag anywhere in the command must be on safe_flags. The whole
    # command, not just the mail program's part: a quoted ; or | would make
    # "the mail program's part" easy to misjudge.
    safe = set(cfg["safe_flags"])
    for w in re.split(r"[\s;|&()<>]+", bare):
        flag = unknown_flag(w, safe)
        if flag:
            return ("send-guard doesn't know the flag %s, which may change where "
                    "this mail goes. Approve this send? (Add it to safe_flags in "
                    "config.json if it's harmless.)" % flag[:60]), None, None

    # Recipients come from the command without its mail heredoc text. Every
    # address anywhere, the message text included, is still checked against
    # the approved list; one only in the text just doesn't count as found.
    addrs, senders, bad = read_words(code)
    every, every_senders, every_bad = read_words(command)
    bad += every_bad
    if bad:
        return ("send-guard can't read %s as an email address. Approve this send?"
                % ", ".join(sorted(set(b.strip()[:80] for b in bad)))[:300]), None, None
    return None, addrs, senders + every + every_senders


def read_words(text):
    """(recipient addresses, sender addresses, unreadable words) in shell text."""
    addrs, senders, bad = [], [], []

    def take(value, into):
        for part in value.split(","):
            if "@" in part:
                (into if ADDR.fullmatch(part) else bad).append(part)

    sender_flag = None
    for w in shell_words(text):
        if sender_flag:
            take(w.split(":", 1)[0] if sender_flag in LOGIN_FLAGS else w, senders)
            sender_flag = None
        elif w in SENDER_FLAGS:
            sender_flag = w
        elif w.startswith("--") and "=" in w:
            flag, value = w.split("=", 1)
            take(value.split(":", 1)[0] if flag in LOGIN_FLAGS else value,
                 senders if flag in SENDER_FLAGS else addrs)
        elif w[:2] in ("-f", "-r") and "@" in w:
            take(w[2:], senders)  # -fyou@example.com
        elif re.search(r"\s", w):
            if "@" in w:
                bad.append(w)
        else:
            take(w, addrs)
    return addrs, senders, bad


def no_list():
    return ask("send-guard's approved list was not found at %s, so it is asking you." % approved_path())


def decide(event, cfg):
    """Return an ask dict, or None to stay out of the way."""
    name = event.get("tool_name")
    tool_input = event.get("tool_input")
    if not isinstance(name, str) or not isinstance(tool_input, dict):
        return ask("send-guard could not read this tool call, so it is asking you.")

    is_mail_tool = any(re.search(p, name, re.I) for p in cfg["tool_patterns"])
    senders = []
    if not is_mail_tool and (name in cfg["shell_tools"] or "command" in tool_input):
        command = tool_input.get("command")
        if not isinstance(command, str):
            if name in cfg["shell_tools"]:
                return ask("send-guard could not read this %s command, so it is asking you." % name)
            return None
        why, addrs, senders = check_shell(command, cfg)
        if why is None and addrs is None:
            return None
        if load_approved() is None:
            return no_list()
        if why:
            return ask(why)
        where = "%s command" % name
    elif is_mail_tool:
        if load_approved() is None:
            return no_list()
        if any(re.search(p, name, re.I) for p in cfg["reply_tool_patterns"]):
            return ask("%s is a reply. It also goes to the people already on the thread, "
                       "which send-guard can't see. Approve this send?" % name)
        if has_key(tool_input, cfg["draft_keys"]):
            return ask("%s sends a saved draft to whoever the draft is addressed to, "
                       "which send-guard can't see. Approve this send?" % name)
        addrs, unreadable = [], []
        for v in recipient_fields(tool_input, cfg["recipient_keys"]):
            read_recipients(v, cfg["address_keys"], addrs, unreadable)
        if unreadable:
            return ask("send-guard can't read %s as an email address. Approve this send?"
                       % ", ".join(unreadable)[:300])
        where = name
    else:
        return None

    approved = load_approved()
    if approved is None:
        return no_list()
    exact, domains = approved
    if not addrs:
        return ask("%s looks like an email send, but send-guard found no recipient to check." % where)
    unknown = sorted({a.lower() for a in addrs + senders if not is_approved(a, exact, domains)})
    if unknown:
        return ask("Not on your approved list: %s. Approve this send?" % ", ".join(unknown))
    return None


def main():
    try:
        event = json.loads(sys.stdin.read())
        if not isinstance(event, dict):
            raise ValueError("input is not a JSON object")
    except Exception:
        print(json.dumps(ask("send-guard got input it could not parse, so it is asking you.")))
        return 0
    try:
        result = decide(event, load_config())
    except Exception as e:
        result = ask("send-guard hit an error (%s), so it is asking you." % type(e).__name__)
    if result:
        print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
