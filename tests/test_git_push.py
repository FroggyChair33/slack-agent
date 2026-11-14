import os
import shutil
import sys
import tempfile

os.environ.setdefault("AGENT_NAME", "test-agent")
os.environ.setdefault("SLACK_BOT_TOKEN", "xoxb-test")
os.environ.setdefault("SLACK_APP_TOKEN", "xapp-test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from slack_agent import config
from slack_agent.git_push import _nested_git_paths, _slug


def test_slug_basic():
    assert _slug("Fix the login bug!!") == "fix-the-login-bug"


def test_slug_truncates():
    assert len(_slug("a" * 100)) <= 40


def test_slug_empty_falls_back():
    assert _slug("!!!") == "task"


def test_nested_git_paths_finds_nested_git_dir_and_git_file():
    workdir = tempfile.mkdtemp()
    try:
        os.makedirs(os.path.join(workdir, "scratch", "clone", ".git"))
        os.makedirs(os.path.join(workdir, "scratch", "worktree"))
        with open(os.path.join(workdir, "scratch", "worktree", ".git"), "w") as f:
            f.write("gitdir: /elsewhere")
        os.makedirs(os.path.join(workdir, "normal", "dir"))

        original_workdir = config.WORKDIR
        config.WORKDIR = workdir
        found = set(_nested_git_paths())
    finally:
        config.WORKDIR = original_workdir
        shutil.rmtree(workdir)

    assert found == {"scratch/clone", "scratch/worktree"}


if __name__ == "__main__":
    test_slug_basic()
    test_slug_truncates()
    test_slug_empty_falls_back()
    test_nested_git_paths_finds_nested_git_dir_and_git_file()
    print("All git_push tests passed.")
