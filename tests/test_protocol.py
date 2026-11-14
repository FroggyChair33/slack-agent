import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from slack_agent import protocol


def test_parse_task_for_me():
    assert protocol.parse_task("@agent:stephen fix the login bug") == ("stephen", "fix the login bug")


def test_parse_task_broadcast():
    assert protocol.parse_task("@agent:all status check") == ("all", "status check")


def test_parse_task_none():
    assert protocol.parse_task("just chatting, no task here") is None


def test_is_for_me():
    assert protocol.is_for_me("stephen", "stephen")
    assert protocol.is_for_me("all", "stephen")
    assert not protocol.is_for_me("jordan", "stephen")


def test_multiline_description():
    assert protocol.parse_task("@agent:stephen line one\nline two") == ("stephen", "line one\nline two")


if __name__ == "__main__":
    test_parse_task_for_me()
    test_parse_task_broadcast()
    test_parse_task_none()
    test_is_for_me()
    test_multiline_description()
    print("All protocol tests passed.")
