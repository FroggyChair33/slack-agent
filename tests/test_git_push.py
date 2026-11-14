import os
import shutil
import stat
import subprocess
import sys
import tempfile


def _rmtree(path):
    # git marks its object files read-only; Windows needs them writable
    # again before they can be deleted.
    def _on_error(func, p, exc_info):
        os.chmod(p, stat.S_IWRITE)
        func(p)

    shutil.rmtree(path, onerror=_on_error)

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
        _rmtree(workdir)

    assert found == {"scratch/clone", "scratch/worktree"}


def test_nested_git_paths_excludes_already_gitignored_ones():
    # Regression test: a nested-git path under a directory .gitignore
    # already excludes (e.g. .isolated/) must NOT come back from this
    # function. Naming an already-ignored path as a pathspec - even as an
    # :(exclude) - makes `git add` refuse the whole command with "paths
    # are ignored by .gitignore", which previously blocked every other
    # legitimate file change in the same commit (not just the gitlink).
    workdir = tempfile.mkdtemp()
    try:
        run = lambda *args: subprocess.run(["git", *args], cwd=workdir, capture_output=True, text=True)
        run("init", "-q")
        with open(os.path.join(workdir, ".gitignore"), "w") as f:
            f.write("/.isolated/\n")
        run("add", ".gitignore")
        run("commit", "-q", "-m", "init")

        os.makedirs(os.path.join(workdir, ".isolated", "ignored-clone", ".git"))
        os.makedirs(os.path.join(workdir, "scratch", "not-ignored-clone", ".git"))

        original_workdir = config.WORKDIR
        config.WORKDIR = workdir
        found = set(_nested_git_paths())
    finally:
        config.WORKDIR = original_workdir
        _rmtree(workdir)

    assert found == {"scratch/not-ignored-clone"}


if __name__ == "__main__":
    test_slug_basic()
    test_slug_truncates()
    test_slug_empty_falls_back()
    test_nested_git_paths_finds_nested_git_dir_and_git_file()
    test_nested_git_paths_excludes_already_gitignored_ones()
    print("All git_push tests passed.")
