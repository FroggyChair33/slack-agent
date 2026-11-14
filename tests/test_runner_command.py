import os
import sys

os.environ.setdefault("AGENT_NAME", "test-agent")
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")
os.environ.setdefault("SLACK_APP_TOKEN", "xapp-test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from slack_agent import config, runner


def test_claude_command():
    config.AGENT_KIND = "claude"
    config.AGENT_BIN = "claude"
    config.AGENT_SANDBOX_MODE = "acceptEdits"
    assert runner.build_command("fix the bug") == [
        "claude", "-p", "fix the bug", "--output-format", "text", "--permission-mode", "acceptEdits",
    ]


def test_codex_command():
    config.AGENT_KIND = "codex"
    config.AGENT_BIN = "codex"
    config.AGENT_SANDBOX_MODE = "workspace-write"
    assert runner.build_command("fix the bug") == [
        "codex", "exec", "fix the bug", "--sandbox", "workspace-write", "--skip-git-repo-check",
    ]


def test_codex_yolo_command():
    config.AGENT_KIND = "codex"
    config.AGENT_BIN = "codex"
    config.AGENT_SANDBOX_MODE = "yolo"
    assert runner.build_command("merge PR #3") == [
        "codex", "exec", "merge PR #3", "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check",
    ]


if __name__ == "__main__":
    test_claude_command()
    test_codex_command()
    test_codex_yolo_command()
    print("All runner command tests passed.")
