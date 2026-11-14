import re
import subprocess
import time

from . import config


class PushResult:
    def __init__(self, pushed: bool, pr_url: str = None, note: str = None):
        self.pushed = pushed
        self.pr_url = pr_url
        self.note = note


def _slug(text: str, limit: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:limit] or "task"


def _run(args):
    # encoding/errors explicit, not just text=True: Windows otherwise decodes
    # with the system codepage (e.g. cp1252), which crashes on Unicode bytes
    # git/gh commonly print (smart quotes, etc.) and leaves stdout/stderr as
    # None instead of raising cleanly.
    return subprocess.run(args, cwd=config.WORKDIR, capture_output=True, encoding="utf-8", errors="replace")


def sync_to_base():
    """Reset the shared workdir to a clean copy of the base branch before a
    task runs, and refresh remote-tracking refs for every branch - not just
    the base - so a review task can see other branches' latest commits even
    if it falls back to plain git instead of gh's API-backed PR commands."""
    fetch = _run(["git", "fetch", "origin"])
    if fetch.returncode != 0:
        return False, fetch.stderr.strip() or fetch.stdout.strip()

    checkout = _run(["git", "checkout", config.BASE_BRANCH])
    if checkout.returncode != 0:
        return False, checkout.stderr.strip() or checkout.stdout.strip()
    pull = _run(["git", "pull", "--ff-only", "origin", config.BASE_BRANCH])
    if pull.returncode != 0:
        return False, pull.stderr.strip() or pull.stdout.strip()
    return True, ""


def _unstage_gitlinks():
    """A task's own scratch work can leave a directory with its own .git
    inside the workdir (e.g. a nested clone it made to test something).
    `git add -A` stages that as a gitlink (mode 160000) instead of its files,
    which looks like a submodule reference - but with no .gitmodules entry,
    that breaks any later `git submodule` command, including the one
    actions/checkout runs during its own cleanup. Drop any such path from
    the index (left alone on disk) before committing."""
    staged = _run(["git", "diff", "--cached", "--raw"])
    gitlink_paths = [
        line.split("\t", 1)[1]
        for line in staged.stdout.splitlines()
        if " 160000 " in line
    ]
    for path in gitlink_paths:
        _run(["git", "rm", "-r", "--cached", "--quiet", path])


def push_changes(description: str) -> PushResult:
    """Commit any changes the task made onto a new branch, push it, and open a
    PR against BASE_BRANCH. No-ops if the workdir has no changes. Leaves the
    workdir back on BASE_BRANCH either way, ready for the next task."""
    status = _run(["git", "status", "--porcelain"])
    if not status.stdout.strip():
        return PushResult(pushed=False, note="no changes to push")

    branch = f"agent/{config.AGENT_NAME}/{_slug(description)}-{int(time.time())}"
    for step in (
        ["git", "checkout", "-b", branch],
        ["git", "add", "-A"],
        ["git", "commit", "-m", f"[{config.AGENT_NAME}] {description[:72]}"],
        ["git", "push", "-u", "origin", branch],
    ):
        if step[1] == "commit":
            _unstage_gitlinks()
        result = _run(step)
        if result.returncode != 0:
            _run(["git", "checkout", config.BASE_BRANCH])
            return PushResult(
                pushed=False,
                note=f"`{' '.join(step)}` failed: {result.stderr.strip() or result.stdout.strip()}",
            )

    pr = _run(
        [
            "gh", "pr", "create",
            "--title", f"[{config.AGENT_NAME}] {description[:72]}",
            "--body", f"Opened automatically by the Slack agent `{config.AGENT_NAME}` for task:\n\n> {description}",
            "--head", branch,
            "--base", config.BASE_BRANCH,
        ]
    )
    _run(["git", "checkout", config.BASE_BRANCH])

    if pr.returncode != 0:
        return PushResult(pushed=True, note=f"pushed `{branch}` but PR creation failed: {pr.stderr.strip() or pr.stdout.strip()}")
    return PushResult(pushed=True, pr_url=pr.stdout.strip())
