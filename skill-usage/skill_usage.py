#!/usr/bin/env python3
"""skill-usage: count each Claude Code skill two ways, from your own transcripts.

  CALLS   how often Claude used the Skill tool with that skill's name
  READS   how often Claude opened that skill's SKILL.md file with the Read tool

A skill with zero of one count can still be in daily use by the other count.
This lists every skill with both counts and marks it:

  in use            both counts above zero
  dead by one only  one count is zero, the other is not (do NOT delete yet)
  dead by both      both counts are zero (safe to review for deleting)

Read only. It never changes a transcript or a skill. Python 3.9+, standard
library only, no network. It prints skill names and numbers, never
transcript text.

Transcripts: ~/.claude/projects/**/*.jsonl  (override with --projects)
Skills:      ~/.claude/skills/*/SKILL.md    (add more with --skills, repeatable)
"""
import argparse
import json
import sys
from pathlib import Path


def short(name):
    """'plugin:skill' and 'skill' count as the same skill."""
    return name.rsplit(":", 1)[-1].strip()


def tool_uses(path):
    """Yield (id, name, input) for every tool_use block in one transcript file.
    Lines that are not valid JSON are skipped."""
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                obj = json.loads(line)
            except ValueError:
                continue
            if not isinstance(obj, dict):
                continue
            msg = obj.get("message")
            content = msg.get("content") if isinstance(msg, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    inp = block.get("input")
                    yield block.get("id"), block.get("name"), inp if isinstance(inp, dict) else {}


def count_transcripts(projects_dir):
    """Return (calls, reads, files_scanned). Each tool_use id is counted once,
    because resumed sessions repeat earlier history in a new file."""
    calls, reads, seen, files = {}, {}, set(), 0
    for path in sorted(Path(projects_dir).rglob("*.jsonl")):
        files += 1
        for tid, name, inp in tool_uses(path):
            if tid:
                if tid in seen:
                    continue
                seen.add(tid)
            if name == "Skill" and isinstance(inp.get("skill"), str) and inp["skill"].strip():
                key = short(inp["skill"])
                calls[key] = calls.get(key, 0) + 1
            elif name == "Read" and isinstance(inp.get("file_path"), str):
                p = Path(inp["file_path"].replace("\\", "/"))
                if p.name == "SKILL.md" and p.parent.name:
                    reads[p.parent.name] = reads.get(p.parent.name, 0) + 1
    return calls, reads, files


def installed_skills(dirs):
    names = set()
    for d in dirs:
        d = Path(d).expanduser()
        if d.is_dir():
            for f in d.glob("*/SKILL.md"):
                names.add(f.parent.name)
    return names


def classify(c, r):
    if c and r:
        return "in use"
    if c or r:
        return "dead by one only"
    return "dead by both"


def build_rows(calls, reads, installed):
    rows = []
    for name in sorted(set(calls) | set(reads) | set(installed)):
        c, r = calls.get(name, 0), reads.get(name, 0)
        rows.append({"skill": name, "calls": c, "reads": r,
                     "installed": name in installed, "status": classify(c, r)})
    order = {"dead by both": 0, "dead by one only": 1, "in use": 2}
    rows.sort(key=lambda x: (order[x["status"]], -(x["calls"] + x["reads"]), x["skill"]))
    return rows


def render(rows, files):
    out = []
    w = max([5] + [len(r["skill"]) for r in rows])
    out.append("%-*s  %6s  %6s  %s" % (w, "SKILL", "CALLS", "READS", "STATUS"))
    for r in rows:
        note = "" if r["installed"] else "  (not installed here)"
        out.append("%-*s  %6d  %6d  %s%s" % (w, r["skill"], r["calls"], r["reads"], r["status"], note))
    n = lambda s: sum(1 for r in rows if r["status"] == s)
    out.append("")
    out.append("%d transcript files scanned, %d skills listed." % (files, len(rows)))
    out.append("dead by both: %d | dead by one count only: %d | in use: %d"
               % (n("dead by both"), n("dead by one only"), n("in use")))
    out.append("Only 'dead by both' is a delete candidate. A skill dead by one count is still being used.")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Count Claude Code skills by Skill-tool calls and SKILL.md reads.")
    ap.add_argument("--projects", default="~/.claude/projects", help="transcripts folder (default: %(default)s)")
    ap.add_argument("--skills", action="append", default=None,
                    help="skills folder, repeatable (default: ~/.claude/skills)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    a = ap.parse_args(argv)
    projects = Path(a.projects).expanduser()
    if not projects.is_dir():
        print("No transcripts folder at %s" % projects, file=sys.stderr)
        return 2
    calls, reads, files = count_transcripts(projects)
    rows = build_rows(calls, reads, installed_skills(a.skills or ["~/.claude/skills"]))
    print(json.dumps(rows, indent=2) if a.json else render(rows, files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
