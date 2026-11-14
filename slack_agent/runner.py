import subprocess

from . import config


class TaskResult:
    def __init__(self, success: bool, output: str):
        self.success = success
        self.output = output


def build_command(description: str) -> list:
    """Build the headless CLI invocation for the configured agent kind."""
    if config.AGENT_KIND == "codex":
        if config.AGENT_SANDBOX_MODE == "yolo":
            # --approve-for-me (the flag that actually skips approval
            # prompts) can't be combined with --sandbox - they conflict.
            # The only flag confirmed to run every command unattended,
            # including bash/gh, is this one. Needed for the reviewer role
            # to actually complete `gh pr merge` instead of hanging on an
            # approval prompt nothing can answer.
            return [
                config.AGENT_BIN,
                "exec",
                description,
                "--dangerously-bypass-approvals-and-sandbox",
                "--skip-git-repo-check",
            ]
        return [
            config.AGENT_BIN,
            "exec",
            description,
            "--sandbox",
            config.AGENT_SANDBOX_MODE,
            # Codex refuses to run outside a git repo otherwise; keeps this
            # working even if AGENT_WORKDIR isn't a git checkout.
            "--skip-git-repo-check",
        ]
    return [
        config.AGENT_BIN,
        "-p",
        description,
        "--output-format",
        "text",
        "--permission-mode",
        config.AGENT_SANDBOX_MODE,
    ]


def run_task(description: str) -> TaskResult:
    """Run one task headlessly via the configured local CLI and capture its output."""
    try:
        proc = subprocess.run(
            build_command(description),
            cwd=config.WORKDIR,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=config.TASK_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return TaskResult(
            False,
            f"Timed out after {config.TASK_TIMEOUT_SECONDS}s - likely stuck waiting on an "
            f"approval/input that headless mode can't provide. Needs a human: either widen "
            f"AGENT_SANDBOX_MODE for this task or do it manually.",
        )
    except FileNotFoundError:
        return TaskResult(False, f"'{config.AGENT_BIN}' not found on PATH")

    if proc.returncode != 0:
        return TaskResult(False, proc.stderr.strip() or proc.stdout.strip() or f"exit code {proc.returncode}")
    return TaskResult(True, proc.stdout.strip())
