"""Tests for send_guard.py. Run: python3 -m pytest send-guard  (or python3 send-guard/test_send_guard.py)

Feeds fake hook JSON to the script on stdin, the way Claude Code does.
All addresses are made up.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "send_guard.py")


def run(stdin_text, approved="you@example.com\n@example.org\n"):
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "approved.txt")
        with open(path, "w") as f:
            f.write(approved)
        env = dict(os.environ, SEND_GUARD_APPROVED=path)
        env.pop("SEND_GUARD_CONFIG", None)
        p = subprocess.run([sys.executable, SCRIPT], input=stdin_text,
                           capture_output=True, text=True, env=env)
    out = json.loads(p.stdout) if p.stdout.strip() else None
    return p.returncode, out


def event(tool_name, tool_input):
    return json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool_name,
                       "tool_input": tool_input})


def decision(out):
    return out["hookSpecificOutput"]["permissionDecision"] if out else None


def test_approved_recipient_passes_silently():
    code, out = run(event("mcp__gmail__send_message", {"to": ["you@example.com"], "subject": "hi"}))
    assert code == 0 and out is None


def test_approved_domain_passes():
    code, out = run(event("mcp__gmail__send_message", {"to": "a@example.org"}))
    assert code == 0 and out is None


def test_unknown_recipient_asks():
    code, out = run(event("mcp__gmail__send_message", {"to": ["stranger@elsewhere.com"]}))
    assert code == 0 and decision(out) == "ask"
    assert out["hookSpecificOutput"]["hookEventName"] == "PreToolUse"
    assert "stranger@elsewhere.com" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_capitalised_connector_names_match():
    for n in ("mcp__claude_ai_Gmail__send_message", "mcp__claude_ai_Gmail__reply",
              "mcp__claude_ai_Gmail__forward"):
        code, out = run(event(n, {"to": ["stranger@elsewhere.com"]}))
        assert decision(out) == "ask", n


def test_one_bad_cc_among_good_recipients_asks():
    code, out = run(event("mcp__gmail__send_message",
                          {"to": ["you@example.com"], "cc": "Pat <pat@elsewhere.com>"}))
    assert decision(out) == "ask"


def test_no_recipient_found_asks():
    code, out = run(event("mcp__gmail__send_message", {"subject": "no recipient"}))
    assert decision(out) == "ask"


def test_address_case_does_not_matter():
    code, out = run(event("mcp__gmail__send_message", {"to": "YOU@Example.COM"}))
    assert out is None


def test_unrelated_tool_is_left_alone():
    code, out = run(event("Read", {"file_path": "/tmp/x"}))
    assert code == 0 and out is None
    code, out = run(event("mcp__gmail__search_threads", {"query": "from:stranger@elsewhere.com"}))
    assert out is None


def test_bash_sender_with_unknown_recipient_asks():
    code, out = run(event("Bash", {"command": "echo hi | sendmail stranger@elsewhere.com"}))
    assert decision(out) == "ask"


def test_bash_sender_with_approved_recipient_passes():
    code, out = run(event("Bash", {"command": "echo hi | mail -s test you@example.com"}))
    assert out is None


def test_bash_non_email_command_is_left_alone():
    code, out = run(event("Bash", {"command": "ls -la && echo stranger@elsewhere.com"}))
    assert out is None


def test_bash_sender_with_no_address_asks():
    code, out = run(event("Bash", {"command": "sendmail -t < draft.eml"}))
    assert decision(out) == "ask"


def test_malformed_json_asks():
    code, out = run("{not json")
    assert code == 0 and decision(out) == "ask"


def test_empty_input_asks():
    code, out = run("")
    assert decision(out) == "ask"


def test_wrong_shape_asks():
    for bad in ('[]', '"hi"', '{"tool_name": 5}', '{"tool_name": "Bash", "tool_input": "x"}',
                '{"tool_name": "Bash", "tool_input": {"command": 7}}'):
        code, out = run(bad)
        assert decision(out) == "ask", bad


def test_missing_approved_file_asks_for_a_send():
    env = dict(os.environ, SEND_GUARD_APPROVED="/nonexistent/approved.txt")
    p = subprocess.run([sys.executable, SCRIPT],
                       input=event("mcp__gmail__send_message", {"to": "you@example.com"}),
                       capture_output=True, text=True, env=env)
    assert decision(json.loads(p.stdout)) == "ask"


def reason(out):
    return out["hookSpecificOutput"]["permissionDecisionReason"] if out else ""


# Review pass 1 (2026-10-18). Each test below failed on the first version.

def test_reply_with_approved_bcc_still_asks():
    # A reply also goes to the original sender, who is not in any field.
    for fields in ({"messageId": "m1", "body": "here", "bcc": ["you@example.com"]},
                   {"messageId": "m1", "replyAll": True, "to": ["you@example.com"]}):
        code, out = run(event("mcp__claude_ai_Gmail__reply", fields))
        assert decision(out) == "ask", fields


def test_sending_a_draft_asks_even_with_an_approved_to():
    # The draft goes out as it is addressed; the "to" field is ignored.
    for key in ("draftId", "draft_id"):
        code, out = run(event("mcp__claude_ai_Gmail__send_message",
                              {key: "r-abc", "to": ["you@example.com"]}))
        assert decision(out) == "ask", key


def test_forward_to_approved_still_passes():
    code, out = run(event("mcp__claude_ai_Gmail__forward",
                          {"messageId": "m1", "to": ["you@example.com"]}))
    assert out is None


def test_bash_hidden_recipients_ask_even_with_an_approved_sender():
    for cmd in ("sendmail -f you@example.com -t < draft.eml",
                "msmtp --from=you@example.com --read-recipients < draft.eml",
                'mail -r you@example.com -s hi "$TO" < body.txt',
                'swaks --from you@example.com --to "$(cat list.txt)" --server smtp.example.com',
                "mail -r you@example.com -s hi `cat list.txt` < body.txt",
                "cat list.txt | xargs mail -r you@example.com -s hi",
                "mutt -H draft.eml -e 'set from=you@example.com'",
                "mail -r you@example.com -s hi < body.txt"):
        code, out = run(event("Bash", {"command": cmd}))
        assert decision(out) == "ask", cmd


def test_address_glued_to_other_characters_asks():
    for to in (["x!you@example.com"], ["a/you@example.com"], ["you@example.com@elsewhere.com"]):
        code, out = run(event("mcp__gmail__send_message", {"to": to}))
        assert decision(out) == "ask", to
    for cmd in ("echo hi | sendmail x!you@example.com", "echo hi | sendmail a/you@example.com"):
        code, out = run(event("Bash", {"command": cmd}))
        assert decision(out) == "ask", cmd


def test_unreadable_recipient_beside_an_approved_one_asks():
    for extra in ({"bcc": "team-all"}, {"cc": ["Pat"]}, {"cc": 42},
                  {"cc": ["stranger@bücher.de"]}, {"cc": "root@localhost"},
                  {"cc": {"name": "Pat"}}):
        fields = dict({"to": "you@example.com"}, **extra)
        code, out = run(event("mcp__gmail__send_message", fields))
        assert decision(out) == "ask", extra


def test_readable_recipient_shapes_pass():
    for to in ("You <you@example.com>", '"Doe, You" <you@example.com>',
               "you@example.com, a@example.org", "you@example.com; a@example.org",
               [{"email": "you@example.com", "name": "You"}]):
        code, out = run(event("mcp__gmail__send_message", {"to": to, "cc": "", "bcc": []}))
        assert out is None, to


def test_monitor_tool_is_checked_like_bash():
    code, out = run(event("Monitor", {"command": "echo hi | sendmail stranger@elsewhere.com"}))
    assert decision(out) == "ask"


def test_missing_list_leaves_non_sends_alone_and_says_why_on_a_send():
    env = dict(os.environ, SEND_GUARD_APPROVED="/nonexistent/approved.txt")
    env.pop("SEND_GUARD_CONFIG", None)

    def go(ev):
        p = subprocess.run([sys.executable, SCRIPT], input=ev, capture_output=True, text=True, env=env)
        return json.loads(p.stdout) if p.stdout.strip() else None

    assert go(event("Bash", {"command": "ls -la"})) is None
    assert go(event("mcp__gmail__search_threads", {"query": "x"})) is None
    out = go(event("mcp__gmail__send_message", {"to": "you@example.com"}))
    assert decision(out) == "ask" and "/nonexistent/approved.txt" in reason(out)


def test_the_word_mail_in_an_ordinary_command_is_left_alone():
    for cmd in ('git commit -m "fix mail parser"', "cd mail-service && npm test",
                "grep -r mail src/"):
        code, out = run(event("Bash", {"command": cmd}))
        assert out is None, cmd


def test_mail_run_in_other_ways_is_still_caught():
    for cmd in ('bash -c "mail -s hi stranger@elsewhere.com"', "/usr/bin/mail stranger@elsewhere.com",
                "cd x && mail -s hi stranger@elsewhere.com < b.txt", "sudo sendmail stranger@elsewhere.com",
                "echo sendmail stranger@elsewhere.com"):
        code, out = run(event("Bash", {"command": cmd}))
        assert decision(out) == "ask", cmd


def test_quoted_approved_address_in_bash_passes():
    code, out = run(event("Bash", {"command": "echo hi | mail -s test 'you@example.com'"}))
    assert out is None


def test_long_command_finishes_fast():
    import time
    t = time.time()
    run(event("Bash", {"command": "sendmail you@example.com " + "a" * 200000}))
    assert time.time() - t < 5


# Review pass 2 (2026-10-18). Each test below failed on the pass-2 version.

def test_shell_word_with_a_mailbox_prefix_asks():
    # The shell keeps x=you@example.com whole, which is a different mailbox.
    for cmd in ("echo hi | sendmail 'x=you@example.com'", "echo hi | sendmail x=you@example.com",
                "echo hi | sendmail \"o'you@example.com\"", "echo hi | sendmail 'x&you@example.com'",
                "echo hi | sendmail 'x|you@example.com'", "echo hi | sendmail 'x{you@example.com'",
                "echo hi | sendmail 'x}you@example.com'", "echo hi | sendmail x\\|you@example.com",
                "echo hi | sendmail 'x;you@example.com'", "echo hi | sendmail \"x you\"@example.com"):
        code, out = run(event("Bash", {"command": cmd}))
        assert decision(out) == "ask", cmd


def test_read_recipients_flag_in_any_spelling_asks():
    for cmd in ("sendmail -it you@example.com < draft.eml", "sendmail -ti you@example.com < draft.eml",
                "sendmail -oi -t you@example.com < draft.eml",
                "sendmail '-t' you@example.com < draft.eml", 'sendmail "-t" you@example.com < draft.eml',
                'sendmail "-"t you@example.com < draft.eml', "sendmail -\\t you@example.com < draft.eml",
                "mutt -Hdraft.eml you@example.com", "mutt -H'draft.eml' you@example.com",
                "msmtp --read-rec you@example.com < draft.eml", "msmtp --rea you@example.com < draft.eml",
                "sendmail -bs you@example.com < session.txt",
                'bash -c "sendmail -t you@example.com < draft.eml"'):
        code, out = run(event("Bash", {"command": cmd}))
        assert decision(out) == "ask", cmd


def test_recipients_from_a_settings_file_ask():
    for cmd in ("mutt -F ./rc -s hi you@example.com < b.txt",
                "mutt -e 'source ./rc' -s hi you@example.com < b.txt",
                "MUTTRC=./rc mutt -s hi you@example.com < b.txt",
                "curl smtp://smtp.example.com --mail-rcpt you@example.com -K ./cfg -T m.txt",
                "curl smtp://smtp.example.com --mail-rcpt you@example.com --config ./cfg -T m.txt"):
        code, out = run(event("Bash", {"command": cmd}))
        assert decision(out) == "ask", cmd


def test_padded_recipient_value_finishes_fast_and_asks():
    import time
    for to in (" " * 20000 + "x", " " * 20000 + "<x", '"' + " " * 20000 + "x",
               "a@" + "a." * 20000 + "!", "a" * 50000 + "@", "<" * 20000 + "x"):
        t = time.time()
        code, out = run(event("mcp__gmail__send_message", {"to": to}))
        assert time.time() - t < 5, repr(to[:30])
        assert decision(out) == "ask", repr(to[:30])
    t = time.time()
    code, out = run(event("mcp__gmail__send_message", {"to": " " * 20000 + "<you@example.com>"}))
    assert time.time() - t < 5 and out is None


def test_long_shell_sends_finish_fast():
    import time
    for cmd in ("|" * 100000 + " mail you@example.com", "sendmail you@example.com " + "'a b' " * 20000,
                "sendmail you@example.com " + "-" * 100000, "mail " + "a mail " * 20000):
        t = time.time()
        run(event("Bash", {"command": cmd}))
        assert time.time() - t < 5, cmd[:30]


def test_ordinary_shell_sends_still_pass():
    for cmd in ('echo done | mail -s "it\'s done" you@example.com',
                "mail -s 'Weekly report' you@example.com,a@example.org < r.txt",
                "swaks --to you@example.com --from you@example.com --server smtp.example.com",
                "swaks --to=you@example.com --from=you@example.com --server smtp.example.com",
                'sendmail -F "Pat Smith" -f you@example.com you@example.com < m.txt',
                "sendmail -fyou@example.com you@example.com < m.txt",
                "curl smtp://smtp.example.com --mail-from you@example.com --mail-rcpt a@example.org -T m.txt",
                "sendmail you@example.com <<'EOF'\nSubject: hi\n\nI don't know yet\nEOF",
                'bash -c "mail -s hi you@example.com < b.txt"'):
        code, out = run(event("Bash", {"command": cmd}))
        assert out is None, cmd


def test_shell_sender_not_on_the_list_asks():
    for cmd in ("sendmail -f stranger@elsewhere.com you@example.com < m.txt",
                "sendmail -fstranger@elsewhere.com you@example.com < m.txt",
                "swaks --to you@example.com --from=stranger@elsewhere.com --server smtp.example.com"):
        code, out = run(event("Bash", {"command": cmd}))
        assert decision(out) == "ask", cmd


# Review pass 3 (2026-10-18). Each test below failed on the pass-3 version.

def asks_all(cmds):
    for cmd in cmds:
        code, out = run(event("Bash", {"command": cmd}))
        assert decision(out) == "ask", cmd


def test_brace_and_glob_expansion_asks():
    # The shell builds -t, --read-recipients or a new address after the hook reads the words.
    asks_all(["sendmail -{t,i} you@example.com < d.eml", "sendmail {-t,-i} you@example.com < d.eml",
              "msmtp --{read-recipients,} you@example.com < d.eml",
              "mutt {-H,draft.eml} you@example.com", "mutt {-F,./rc} -s hi you@example.com < b.txt",
              "echo hi | sendmail {,you@example.com,}.elsewhere.com",
              "echo hi | sendmail you@example.co?", "echo hi | sendmail you@example.co[m]",
              'bash -c "sendmail -{t,i} you@example.com < d.eml"',
              "bash <<'EOF'\nsendmail {,you@example.com,}.elsewhere.com < m.txt\nEOF"])


def test_zsh_glob_modifier_asks():
    asks_all(["echo hi | sendmail you@example.com(:s/example.com/elsewhere.com/)"])


def test_sendmail_modes_ask():
    asks_all(["sendmail -b s you@example.com < session.txt",
              "sendmail -ibs you@example.com < session.txt"])


def test_settings_set_before_the_mail_program_ask():
    asks_all(["MUTTRC+=./rc mutt -s hi you@example.com < b.txt",
              "printf -v MUTTRC ./rc; export MUTTRC; mutt -s hi you@example.com < b.txt",
              ". ./env.sh; mutt -s hi you@example.com < b.txt"])


def test_unknown_flags_ask():
    asks_all(["mail -S sendmail=/tmp/x -s hi you@example.com < b.txt",
              "sendmail -C ./cf you@example.com < m.txt",
              "sendmail -oA./aliases you@example.com < m.txt",
              "msmtp --file=./rc you@example.com < m.txt",
              "mail -X 'alias you@example.com team' -s hi you@example.com < b.txt",
              'mail -s "a; b" -X x you@example.com < b.txt'])


def test_more_ordinary_shell_sends_pass():
    for cmd in ("mail -s hi you@example.com <<EOF\nCan we meet (after 5)? Bring [notes] -ok\nEOF",
                "curl -sS --ssl-reqd --url smtps://smtp.example.com:465 --user 'you@example.com:pw' "
                "--mail-from you@example.com --mail-rcpt a@example.org --upload-file m.txt",
                "swaks --to you@example.com --server smtp.example.com --h-Subject hi --body 'see you'",
                "printf 'Subject: hi\\n\\nok\\n' | msmtp -a default you@example.com"):
        code, out = run(event("Bash", {"command": cmd}))
        assert out is None, cmd


# Review pass 4 (2026-10-18). Each test below failed on the pass-1r version.

def test_program_names_in_any_case_ask():
    # A Mac disk usually ignores case, so these run the real programs.
    asks_all([
        "Mutt -e 'my_hdr Bcc: stranger@elsewhere.com' -s hi you@example.com < r.txt",
        "MUTT -F ./rc -s hi you@example.com < r.txt",
        "SendMail -b s you@example.com",
        "sendmail -oi you@example.com < /dev/null; BASH <<'EOF'\nexport MUTTRC=./rc\nEOF",
    ])


def test_settings_words_still_ask_when_quoted_or_nested():
    # Passed before too. It guards the settings check now that it skips mail text.
    asks_all([
        "\\export X=1; mutt -s hi you@example.com < r.txt",
        "\"source\" ./env.sh; mutt -s hi you@example.com < r.txt",
        "bash -c \"MUTTRC=./rc mutt -s hi you@example.com < r.txt\"",
        "MUTTRC=./rc mutt -s hi you@example.com < r.txt",
    ])


def test_mail_text_and_quoted_subjects_do_not_ask():
    for cmd in ("sendmail -oi you@example.com <<'EOF'\nSubject: hi\n\nSTATUS=green, see sheet (attached).\n"
                "export done, alias fixed\n-Kate\n.\nEOF",
                "mail -s \"Report (final).\" you@example.com < r.txt",
                "mail -s \"STATUS=green\" you@example.com < r.txt"):
        code, out = run(event("Bash", {"command": cmd}))
        assert out is None, (cmd, reason(out))


def test_mutt_draft_and_sendmail_queue_ask():
    asks_all(["mutt -p you@example.com", "sendmail -q you@example.com"])


def test_address_only_in_message_text_is_not_a_recipient():
    code, out = run(event("Bash", {"command": "mail -s hi team <<'EOF'\nCall you@example.com\nEOF"}))
    assert "found no recipient" in reason(out)
    code, out = run(event("Bash", {"command": "mail -s hi you@example.com <<'EOF'\ncc stranger@elsewhere.com\nEOF"}))
    assert "stranger@elsewhere.com" in reason(out)


def test_missing_list_names_the_path_on_every_send():
    env = dict(os.environ, SEND_GUARD_APPROVED="/nonexistent/approved.txt")
    env.pop("SEND_GUARD_CONFIG", None)
    for ev in (event("mcp__gmail__reply_message", {"to": "you@example.com"}),
               event("mcp__gmail__send_message", {"draftId": "d1"}),
               event("Bash", {"command": "sendmail -t < msg.txt"}),
               event("Bash", {"command": "mail -X x you@example.com"})):
        p = subprocess.run([sys.executable, SCRIPT], input=ev, capture_output=True, text=True, env=env)
        assert "/nonexistent/approved.txt" in reason(json.loads(p.stdout)), ev


# Review pass 5 (2026-10-18). The first test failed on the pass-2r version;
# the rest pin branches no test covered (each fails if its line is removed).

def test_heredoc_marker_in_quotes_or_comment_hides_nothing():
    asks_all([
        "mail -s \"<<EOF\" you@example.com\nsendmail -t < msg.txt\nEOF",
        "mail -s hi you@example.com < r.txt # <<EOF\nsendmail -t < msg.txt\nEOF",
        "mail -s '<<EOF' you@example.com < r.txt\nexport MUTTRC=./rc\nmutt -s hi you@example.com < r.txt\nEOF",
        "mail -s '<<EOF' you@example.com < r.txt\nmutt -F ./rc -s hi you@example.com < r.txt\nEOF",
        "mail -s \"it's <<EOF you@example.com\nsendmail -t < msg.txt\nEOF",
    ])


def test_new_branches_are_pinned():
    asks_all([
        "printf you@example.com | XARGS mail -s hi",
        "true;MUTTRC=./rc mutt -s hi you@example.com < r.txt",
        "'source' ./rc; mutt -s hi you@example.com < r.txt; echo it's",
        "mail -s hi you@example.com <<'EOF'\nx=stranger@elsewhere.com\nEOF",
    ])


# Review pass 6 (2026-10-18). Each test below failed on the pass-3r version.

def test_quote_from_an_earlier_line_hides_nothing():
    asks_all([
        "mail -s 'a\nmail -s <<EOF ' you@example.com '\n' ; sendmail -t < msg.txt\nEOF",
        "mail -s \"a\nmail -s <<EOF \" you@example.com \"\n\" ; mutt -F ./rc -s hi you@example.com < r.txt\nEOF",
        # After a << it can't place, a later real mail heredoc drops nothing either.
        "cat <<A \"<<B\"\nmail -s x you@example.com <<EOF\nA\nsendmail -t < msg.txt\nEOF",
    ])


def test_tab_trimming_heredoc_passes():
    cmd = "mail -s hi you@example.com <<-EOF\n\tIndented body line\n\t-Kate\n\tEOF"
    code, out = run(event("Bash", {"command": cmd}))
    assert out is None, reason(out)


# Review pass 7 (2026-10-18). Each test below failed on the pass-4r version.

def test_delimiter_line_with_spaces_does_not_end_the_body():
    asks_all([
        "mail -s hi you@example.com <<EOF\n  EOF\nit's\nEOF\necho 'x\n"
        "mail -s y you@example.com <<EOF\n' ; sendmail -t < msg.txt\nEOF",
        "mail -s hi you@example.com <<EOF\n  EOF\nit's\nEOF\necho 'x\n"
        "mail -s y you@example.com <<EOF\n' ; mutt -F ./rc -s hi you@example.com < r.txt\nEOF",
    ])


def test_delimiter_longer_than_a_plain_word_hides_nothing():
    asks_all([
        "mail -s hi you@example.com <<END-MSG\nHi\nEND-MSG\nsendmail -t < msg.txt",
        "mail -s hi you@example.com <<EOF.txt\nHi\nEOF.txt\nsendmail -t < msg.txt",
    ])


def test_plain_and_spaced_delimiters_still_pass():
    for cmd in ["mail -s hi you@example.com <<EOF\nIt's done.\n-Kate\nEOF",
                "mail -s hi you@example.com << 'EOF'\nIt's done.\n-Kate\nEOF\n"]:
        code, out = run(event("Bash", {"command": cmd}))
        assert out is None, reason(out)


# Review pass 8 (2026-10-18). Each test below failed on the pass-5r version.

def test_unreadable_heredoc_or_continued_line_hides_nothing():
    asks_all([
        "cat <<\\X\nmail -s hi you@example.com <<EOF\nX\nsendmail -t < msg.txt\nEOF",
        "mail -s hi you@example.com <<EOF \\\n; sendmail -t < msg.txt\nHi\nEOF",
    ])


# Review pass 9 (2026-10-18). The first test below failed on the pass-6r version.

def test_backslash_at_the_end_of_a_body_line_hides_nothing():
    asks_all([
        "mail -s hi you@example.com <<EOF\nabc\\\nEOF\nmail -s hi you@example.com <<EOG\n"
        "EOF\nsendmail -t < msg.txt\nEOG",
    ])


def test_delimiter_with_an_odd_space_character_hides_nothing():
    # Bash ends a word only at a space or tab, so <<EOF\rX waits for "EOF\rX".
    asks_all([
        "mail -s hi you@example.com <<EOF%sX\nbody\nEOF%sX\nsendmail -t < msg.txt\nEOF" % (c, c)
        for c in ["\r", "\v", "\f", "\x1c", " "]
    ])


# Review pass 10 (2026-10-18). The first test below failed on the pass-8r version.

def test_escaped_character_before_a_hash_hides_nothing():
    asks_all([
        "mail -s hi you@example.com <<EOF a\\ #'\n'; sendmail -t < msg.txt\nbody\nEOF",
        "mail -s hi you@example.com <<EOF a\\;#'\n'; sendmail -t < msg.txt\nbody\nEOF",
        # A # in the middle of a word is no comment; the quote after it is real.
        "mail -s hi you@example.com <<EOF a#'\n'; sendmail -t < msg.txt\nbody\nEOF",
    ])


def test_comment_line_before_a_mail_heredoc_passes():
    cmd = "# the weekly one \\\nmail -s hi you@example.com <<EOF\nIt's done.\n-Kate\nEOF"
    code, out = run(event("Bash", {"command": cmd}))
    assert out is None, reason(out)


def test_backslash_in_a_quoted_heredoc_body_passes():
    # With <<'EOF' the shell joins nothing, so the body ends at the first EOF.
    cmd = "mail -s hi you@example.com <<'EOF'\nC:\\temp\\\nEOF"
    code, out = run(event("Bash", {"command": cmd}))
    assert out is None, reason(out)


def test_shipped_config_matches_the_built_in_defaults():
    # The tests run against config.json; an old copy would quietly undo a fix.
    sys.path.insert(0, HERE)
    import send_guard
    with open(os.path.join(HERE, "config.json")) as f:
        assert json.load(f) == send_guard.DEFAULT_CONFIG


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("ok  ", name)
            except Exception:
                fails += 1
                print("FAIL", name)
    sys.exit(1 if fails else 0)
