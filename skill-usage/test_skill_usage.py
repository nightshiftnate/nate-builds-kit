"""Tests for skill_usage.py. Run: python3 -m pytest skill-usage  (or python3 skill-usage/test_skill_usage.py)

Builds small made-up transcript and skills folders in a temp dir.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import skill_usage as su  # noqa: E402


def use(tid, name, **inp):
    return {"type": "assistant", "message": {"content": [
        {"type": "text", "text": "ignored words about skill alpha"},
        {"type": "tool_use", "id": tid, "name": name, "input": inp}]}}


def world(d, files, skills):
    proj = Path(d) / "projects" / "p1"
    proj.mkdir(parents=True)
    for fname, lines in files.items():
        with open(proj / fname, "w") as f:
            for ln in lines:
                f.write((ln if isinstance(ln, str) else json.dumps(ln)) + "\n")
    sk = Path(d) / "skills"
    for s in skills:
        (sk / s).mkdir(parents=True)
        (sk / s / "SKILL.md").write_text("x")
    return str(Path(d) / "projects"), str(sk)


def rows_for(files, skills):
    with tempfile.TemporaryDirectory() as d:
        projects, sk = world(d, files, skills)
        calls, reads, n = su.count_transcripts(projects)
        rows = su.build_rows(calls, reads, su.installed_skills([sk]))
        return {r["skill"]: r for r in rows}, n


def test_counts_both_ways():
    rows, n = rows_for({"a.jsonl": [
        use("t1", "Skill", skill="alpha"),
        use("t2", "Skill", skill="alpha", args="x"),
        use("t3", "Read", file_path="/home/you/.claude/skills/beta/SKILL.md"),
    ]}, ["alpha", "beta", "gamma"])
    assert rows["alpha"]["calls"] == 2 and rows["alpha"]["reads"] == 0
    assert rows["beta"]["calls"] == 0 and rows["beta"]["reads"] == 1
    assert n == 1


def test_status_labels():
    rows, _ = rows_for({"a.jsonl": [
        use("t1", "Skill", skill="alpha"),
        use("t2", "Read", file_path="/s/alpha/SKILL.md"),
        use("t3", "Read", file_path="/s/beta/SKILL.md"),
    ]}, ["alpha", "beta", "gamma"])
    assert rows["alpha"]["status"] == "in use"
    assert rows["beta"]["status"] == "dead by one only"
    assert rows["gamma"]["status"] == "dead by both"


def test_plugin_prefix_matches_plain_name():
    rows, _ = rows_for({"a.jsonl": [use("t1", "Skill", skill="someplugin:alpha")]}, ["alpha"])
    assert rows["alpha"]["calls"] == 1


def test_only_skill_md_reads_count():
    rows, _ = rows_for({"a.jsonl": [
        use("t1", "Read", file_path="/s/alpha/notes.md"),
        use("t2", "Read", file_path="/s/alpha/SKILL.md.bak"),
    ]}, ["alpha"])
    assert rows["alpha"]["reads"] == 0


def test_mentions_in_text_do_not_count():
    rows, _ = rows_for({"a.jsonl": [
        {"type": "user", "message": {"content": "please use the alpha skill"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Skill alpha"}]}},
    ]}, ["alpha"])
    assert rows["alpha"]["status"] == "dead by both"


def test_same_tool_use_in_two_files_counts_once():
    line = use("same-id", "Skill", skill="alpha")
    rows, n = rows_for({"a.jsonl": [line], "b.jsonl": [line]}, ["alpha"])
    assert rows["alpha"]["calls"] == 1 and n == 2


def test_bad_lines_are_skipped():
    rows, _ = rows_for({"a.jsonl": ["{broken", "", "[1,2]", '{"message": 5}',
                                    use("t1", "Skill", skill="alpha")]}, ["alpha"])
    assert rows["alpha"]["calls"] == 1


def test_skill_seen_but_not_installed_is_listed():
    rows, _ = rows_for({"a.jsonl": [use("t1", "Skill", skill="ghost")]}, ["alpha"])
    assert rows["ghost"]["installed"] is False and rows["ghost"]["status"] == "dead by one only"


def test_output_has_names_and_numbers_only():
    rows, _ = rows_for({"a.jsonl": [use("t1", "Skill", skill="alpha")]}, ["alpha"])
    text = su.render(list(rows.values()), 1)
    assert "ignored words" not in text and "dead by both: 0" in text


def test_missing_projects_folder_exits_2():
    assert su.main(["--projects", "/nonexistent/nowhere"]) == 2


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("ok  ", name)
            except AssertionError:
                fails += 1
                print("FAIL", name)
    sys.exit(1 if fails else 0)
