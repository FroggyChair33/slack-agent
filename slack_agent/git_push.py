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
    return subprocess.run(args, cwd=config.WORKDIR, capture_output=True, text=True)


def sync_to_base():
    """Reset the shared workdir to a clean copy of the base branch before a task
    runs, so every task starts from the same known-good state."""
    checkout = _run(["git", "checkout", config.BASE_BRANCH])
    if checkout.returncode != 0:
        return False, checkout.stderr.strip() or checkout.stdout.strip()
    pull = _run(["git", "pull", "--ff-only", "origin", config.BASE_BRANCH])
    if pull.returncode != 0:
        return False, pull.stderr.strip() or pull.stdout.strip()
    return True, ""


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
