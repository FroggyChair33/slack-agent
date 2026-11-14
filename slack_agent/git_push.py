import os
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


def _nested_git_paths():
    """Any directory under WORKDIR (other than the repo root itself) that
    contains a .git entry is a scratch clone or a linked worktree a task
    made for its own use. Git stages that as a gitlink (mode 160000) instead
    of its files, which looks like a submodule reference - but with no
    .gitmodules entry, that breaks any later `git submodule` command,
    including the one actions/checkout runs during its own cleanup.

    Only paths git wouldn't already skip on its own are worth returning:
    a path already covered by .gitignore (e.g. a scratch clone someone made
    under a directory like .isolated/, which .gitignore already excludes)
    is never touched by `git add -A` anyway - and explicitly naming an
    already-ignored path as a pathspec (even as an :(exclude)) makes git
    refuse the whole `add` with "paths are ignored by .gitignore", which
    blocks every other legitimate file change in the same commit too. Only
    a nested-git path git would otherwise actually stage needs excluding."""
    found = []
    for root, dirs, files in os.walk(config.WORKDIR):
        if root != config.WORKDIR and (".git" in dirs or ".git" in files):
            rel = os.path.relpath(root, config.WORKDIR).replace(os.sep, "/")
            if _run(["git", "check-ignore", "-q", rel]).returncode != 0:
                found.append(rel)
            dirs[:] = []
            continue
        if ".git" in dirs:
            dirs.remove(".git")
    return found


def _strip_committed_gitlinks():
    """A gitlink can also already be sitting in the index - inherited
    unchanged from the base branch, or left by an earlier task's commit on
    this same branch. `git add` never revisits a path that hasn't changed,
    so excluding nested paths from the add below can't catch these; drop
    any gitlink already tracked before adding anything new."""
    tracked = _run(["git", "ls-files", "-s"])
    for line in tracked.stdout.splitlines():
        if line.startswith("160000"):
            path = line.split("\t", 1)[1]
            _run(["git", "rm", "-r", "--cached", "--quiet", "--ignore-unmatch", path])


def push_changes(description: str) -> PushResult:
    """Commit any changes the task made onto a new branch, push it, and open a
    PR against BASE_BRANCH. No-ops if the workdir has no changes. Leaves the
    workdir back on BASE_BRANCH either way, ready for the next task."""
    status = _run(["git", "status", "--porcelain"])
    if not status.stdout.strip():
        return PushResult(pushed=False, note="no changes to push")

    branch = f"agent/{config.AGENT_NAME}/{_slug(description)}-{int(time.time())}"

    checkout = _run(["git", "checkout", "-b", branch])
    if checkout.returncode != 0:
        _run(["git", "checkout", config.BASE_BRANCH])
        return PushResult(
            pushed=False,
            note=f"`git checkout -b {branch}` failed: {checkout.stderr.strip() or checkout.stdout.strip()}",
        )

    _strip_committed_gitlinks()
    skip = _nested_git_paths()
    add = _run(["git", "add", "-A", "--", "."] + [f":(exclude){p}" for p in skip])
    if add.returncode != 0:
        _run(["git", "checkout", config.BASE_BRANCH])
        return PushResult(pushed=False, note=f"`git add` failed: {add.stderr.strip() or add.stdout.strip()}")

    # Belt-and-suspenders: if a gitlink is still staged despite the above
    # (an edge case neither step anticipated), refuse to commit rather than
    # silently ship a branch that will break actions/checkout downstream.
    staged = _run(["git", "diff", "--cached", "--raw"])
    if any(" 160000 " in line for line in staged.stdout.splitlines()):
        _run(["git", "reset"])
        _run(["git", "checkout", config.BASE_BRANCH])
        return PushResult(pushed=False, note="not pushed: a gitlink was still staged after cleanup, needs a human to look")

    for step in (
        ["git", "commit", "-m", f"[{config.AGENT_NAME}] {description[:72]}"],
        ["git", "push", "-u", "origin", branch],
    ):
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
