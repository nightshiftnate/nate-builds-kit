import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chime import decide  # noqa: E402


def test_done_chimes():
    assert decide({"background_tasks": []}, "cli", ["claude"]) == (True, "done")


def test_missing_field_chimes():
    assert decide({}, "cli", None)[0] is True


def test_background_work_stays_quiet():
    assert decide({"background_tasks": [{"id": "a"}]}, "cli", ["claude"])[0] is False


def test_headless_print_stays_quiet():
    assert decide({}, "cli", ["claude", "-p", "do it"])[0] is False
    assert decide({}, "cli", ["claude", "--print"])[0] is False


def test_sdk_stays_quiet():
    assert decide({}, "sdk-py", None)[0] is False


def test_unreadable_input_chimes():
    assert decide(None, "cli", None)[0] is True


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
    print("all tests passed")
