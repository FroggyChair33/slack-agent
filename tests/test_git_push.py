import os
import sys

os.environ.setdefault("AGENT_NAME", "test-agent")
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")
os.environ.setdefault("SLACK_APP_TOKEN", "xapp-test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from slack_agent.git_push import _slug


def test_slug_basic():
    assert _slug("Fix the login bug!!") == "fix-the-login-bug"


def test_slug_truncates():
    assert len(_slug("a" * 100)) <= 40


def test_slug_empty_falls_back():
    assert _slug("!!!") == "task"


if __name__ == "__main__":
    test_slug_basic()
    test_slug_truncates()
    test_slug_empty_falls_back()
    print("All git_push tests passed.")
