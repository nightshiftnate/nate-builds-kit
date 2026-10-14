#!/usr/bin/env python3
"""Decision journal: a log of calls your AI agent made on its own.

The loop:
  1. The agent makes a real call without asking you (decided X over Y because Z).
  2. It logs the call here.
  3. You set aside a few minutes and review the unreviewed set.
  4. You confirm, correct, or note each one.
  5. Confirmed calls become standing rules. Corrected calls become counter-rules.
  Over time the "ask the human" surface shrinks to the real edge cases.

Log only calls that are consequential, autonomous, and not obvious. Logging
routine steps is noise and makes the review set not worth reading.

Python 3 standard library only. No network.

Storage: a JSON file. Path comes from, in order:
  1. --file PATH
  2. the DECISION_JOURNAL_FILE environment variable
  3. ~/.decision-journal/journal.json

Commands:
  log      add one decision
  show     list decisions awaiting review (default)
  list     list all decisions, or filter with --status
  review   record your verdict on one decision
  count    number awaiting review
  json     dump the raw file
  prune    drop reviewed decisions older than N days
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_PATH = Path.home() / ".decision-journal" / "journal.json"
ENV_VAR = "DECISION_JOURNAL_FILE"

VALID_NOVELTY = ("routine", "novel", "edge")
VALID_REVERSIBILITY = ("reversible", "irreversible")
VALID_AUTHOR = ("agent", "human")
VALID_VERDICTS = ("confirmed", "corrected", "noted")


def ledger_path(cli_path: str | None = None) -> Path:
    if cli_path:
        return Path(cli_path).expanduser()
    env = os.environ.get(ENV_VAR)
    if env:
        return Path(env).expanduser()
    return DEFAULT_PATH


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


class JournalError(Exception):
    """The journal could not be read or written. Nothing was changed."""


def load(path: Path) -> dict:
    """A missing file is an empty journal. A damaged file is an error, never
    silently treated as empty: the next write would erase your history."""
    if not path.exists():
        return {"decisions": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:  # ValueError covers bad JSON and bad encoding
        raise JournalError(f"cannot read {path}: {e}. Fix or move the file; "
                           f"nothing was written.") from e
    if not (isinstance(data, dict) and isinstance(data.get("decisions"), list)
            and all(isinstance(d, dict) for d in data["decisions"])):
        raise JournalError(f"{path} is not a decision journal (expected "
                           f'{{"decisions": [{{...}}, ...]}} with one object per decision). '
                           f"Nothing was written.")
    return data


def save(path: Path, data: dict) -> None:
    """Atomic write: unique temp file in the same folder, then rename."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(json.dumps(data, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, path)
    except OSError as e:
        with contextlib.suppress(Exception):
            os.unlink(tmp)
        raise JournalError(f"cannot write {path}: {e}") from e


@contextlib.contextmanager
def locked(path: Path):
    """Hold an exclusive lock for a read-modify-write, so two agents logging at
    the same moment cannot drop each other's entries. Uses a sidecar .lock file.
    On systems without fcntl (Windows) it runs unlocked."""
    try:
        import fcntl
    except ImportError:
        yield
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(path.with_name(path.name + ".lock"), "a")
    except OSError as e:
        raise JournalError(f"cannot lock {path}: {e}") from e
    with fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def log_decision(path, context, decided, over, because, *, area="general",
                 reversibility="reversible", novelty="novel", surfaced=False,
                 source="interactive", rationale_author="agent") -> dict:
    if reversibility not in VALID_REVERSIBILITY:
        reversibility = "reversible"
    if novelty not in VALID_NOVELTY:
        novelty = "novel"
    if rationale_author not in VALID_AUTHOR:
        rationale_author = "agent"
    with locked(path):
        data = load(path)
        now = _now()
        seq = sum(1 for d in data["decisions"] if d.get("area") == area)
        entry = _entry(area, now, seq, context, decided, over, because, reversibility,
                       novelty, surfaced, source, rationale_author)
        data["decisions"].append(entry)
        save(path, data)
    if reversibility == "irreversible" and rationale_author == "agent" and not surfaced:
        print(f"[decision-journal] {entry['uid']}: IRREVERSIBLE, unsurfaced, and the "
              f"agent wrote its own reason. Nothing outside the agent tested this. "
              f"Tell the human at the next exchange.", file=sys.stderr)
    return entry


def _entry(area, now, seq, context, decided, over, because, reversibility, novelty,
           surfaced, source, rationale_author) -> dict:
    return {
        "uid": f"{area}:{now}:{seq}",
        "ts": now,
        "area": area,
        "context": context,
        "decided": decided,
        "over": over,
        "because": because,
        "reversibility": reversibility,
        "novelty": novelty,
        "surfaced": bool(surfaced),
        "source": source,
        "rationale_author": rationale_author,
        "status": "logged",
        "verdict": None,
        "review_note": None,
        "reviewed_at": None,
    }


def mark_reviewed(path, uid, verdict, note=None):
    if verdict not in VALID_VERDICTS:
        return None
    with locked(path):
        data = load(path)
        for d in data["decisions"]:
            if d.get("uid") == uid and d.get("status") == "logged":
                d["status"] = "reviewed"
                d["verdict"] = verdict
                d["reviewed_at"] = _now()
                if note:
                    d["review_note"] = note
                save(path, data)
                return d
    return None


def pending(path) -> list:
    """Unreviewed rows. Edge and novel calls first, routine last."""
    order = {"edge": 0, "novel": 1, "routine": 2}
    rows = [d for d in load(path)["decisions"] if d.get("status") == "logged"]
    rows.sort(key=lambda d: (order.get(d.get("novelty"), 3), d.get("ts", "")))
    return rows


def prune(path, max_age_days=90) -> int:
    with locked(path):
        return _prune(path, max_age_days)


def _prune(path, max_age_days) -> int:
    data = load(path)
    cutoff = datetime.now(timezone.utc).timestamp() - max_age_days * 86400
    kept, removed = [], 0
    for d in data["decisions"]:
        if d.get("status") == "reviewed":
            try:
                ts = datetime.fromisoformat(d["reviewed_at"]).timestamp()
            except (KeyError, ValueError, TypeError):
                ts = 0
            if ts and ts < cutoff:
                removed += 1
                continue
        kept.append(d)
    if removed:
        data["decisions"] = kept
        save(path, data)
    return removed


def _age(ts: str) -> str:
    try:
        hours = (datetime.now(timezone.utc) - datetime.fromisoformat(ts)).total_seconds() / 3600
        return f"{hours:.0f}h"
    except (ValueError, TypeError):
        return "?"


def fmt(d: dict) -> str:
    flags = f"{d.get('novelty', '?')}/{d.get('reversibility', '?')}"
    if d.get("surfaced"):
        flags += "/surfaced"
    if d.get("rationale_author") == "agent":
        flags += "/agent-reasoned"
    out = f"  [{d.get('uid')}]  ({flags}, {_age(d.get('ts', ''))} ago, {d.get('source', '?')})"
    out += f"\n      context: {d.get('context', '')}"
    out += f"\n      decided: {d.get('decided', '')}"
    out += f"\n      over:    {d.get('over', '')}"
    out += f"\n      because: {d.get('because', '')}"
    if (d.get("reversibility") == "irreversible" and d.get("rationale_author") == "agent"
            and not d.get("surfaced")):
        out += "\n      ^^ IRREVERSIBLE and unsurfaced. Review this one first."
    if d.get("verdict"):
        out += f"\n      verdict: {d['verdict']}"
        if d.get("review_note"):
            out += f" - {d['review_note']}"
    return out


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="decision_journal.py",
        description="Log and review the calls your AI agent made on its own. "
                    f"Storage: --file, else ${ENV_VAR}, else ~/.decision-journal/journal.json.",
        epilog="Example:\n  python3 decision_journal.py log --context 'Two APIs fit' "
               "--decided 'Used the free one' --over 'The paid one' "
               "--because 'Same output, no cost'\n  python3 decision_journal.py show\n"
               "  python3 decision_journal.py review --uid <uid> --verdict confirmed",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--file", default=None, help="journal file path")
    sub = ap.add_subparsers(dest="cmd")

    lg = sub.add_parser("log", help="add one decision")
    lg.add_argument("--context", required=True, help="the situation that forced a choice")
    lg.add_argument("--decided", required=True, help="the option taken")
    lg.add_argument("--over", required=True, help="the option rejected")
    lg.add_argument("--because", required=True, help="why")
    lg.add_argument("--area", default="general", help="short label, e.g. build, infra, content")
    lg.add_argument("--reversibility", default="reversible", choices=VALID_REVERSIBILITY)
    lg.add_argument("--novelty", default="novel", choices=VALID_NOVELTY)
    lg.add_argument("--surfaced", action="store_true", help="the human was also told at the time")
    lg.add_argument("--source", default="interactive", help="where the call was made, e.g. overnight")
    lg.add_argument("--rationale-from", dest="rationale_author", default="agent",
                    choices=VALID_AUTHOR, help="whose words --because carries")

    rv = sub.add_parser("review", help="record your verdict on one decision")
    rv.add_argument("--uid", required=True)
    rv.add_argument("--verdict", required=True, choices=VALID_VERDICTS)
    rv.add_argument("--note", default=None)

    sub.add_parser("show", help="decisions awaiting review (default)")
    ls = sub.add_parser("list", help="all decisions")
    ls.add_argument("--status", choices=("logged", "reviewed"), default=None)
    sub.add_parser("count", help="number awaiting review")
    sub.add_parser("json", help="raw journal to stdout")
    pr = sub.add_parser("prune", help="drop reviewed decisions older than N days")
    pr.add_argument("--max-age-days", type=int, default=90)
    return ap


def main(argv: list[str]) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except JournalError as e:
        print(f"decision_journal: {e}", file=sys.stderr)
        return 2


def run(args) -> int:
    path = ledger_path(args.file)

    if args.cmd == "log":
        e = log_decision(path, args.context, args.decided, args.over, args.because,
                         area=args.area, reversibility=args.reversibility,
                         novelty=args.novelty, surfaced=args.surfaced,
                         source=args.source, rationale_author=args.rationale_author)
        print(f"logged {e['uid']}")
        return 0
    if args.cmd == "review":
        d = mark_reviewed(path, args.uid, args.verdict, args.note)
        print(f"reviewed {args.uid}: {args.verdict}" if d
              else f"not found or already reviewed: {args.uid}")
        return 0 if d else 1
    if args.cmd == "count":
        print(len(pending(path)))
        return 0
    if args.cmd == "json":
        print(json.dumps(load(path), indent=2, sort_keys=True))
        return 0
    if args.cmd == "prune":
        print(f"pruned {prune(path, args.max_age_days)} decision(s)")
        return 0
    if args.cmd == "list":
        rows = load(path)["decisions"]
        if args.status:
            rows = [d for d in rows if d.get("status") == args.status]
        for d in rows:
            print(fmt(d))
        return 0

    rows = pending(path)
    if rows:
        print(f"DECISION-JOURNAL: {len(rows)} decision(s) awaiting review")
        for d in rows:
            print(fmt(d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
