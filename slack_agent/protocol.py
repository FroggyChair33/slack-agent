import re

# Task assignment convention (no existing convention from the orchestrator yet):
#   @agent:<name> <task description>
#   @agent:all    <task description>   (broadcast to every listening agent)
# Posted as a plain message in the channel; the matching agent replies in-thread.
TASK_PATTERN = re.compile(r"^@agent:(\S+)\s+(.+)$", re.DOTALL)

MAX_REPLY_CHARS = 3000


def parse_task(text: str):
    """Return (target_agent, description) if `text` assigns a task, else None."""
    match = TASK_PATTERN.match(text.strip())
    if not match:
        return None
    target, description = match.groups()
    return target, description.strip()


def is_for_me(target: str, agent_name: str) -> bool:
    return target == agent_name or target == "all"


def truncate(text: str, limit: int = MAX_REPLY_CHARS) -> str:
    return text if len(text) <= limit else text[:limit] + "\n... (truncated)"


def picked_up_message(agent_name: str) -> str:
    return f":hourglass_flowing_sand: `@agent:{agent_name}` picked this up, working..."


def success_message(agent_name: str, summary: str) -> str:
    return f":white_check_mark: `@agent:{agent_name}` done.\n```{truncate(summary)}```"


def failure_message(agent_name: str, error: str) -> str:
    return f":x: `@agent:{agent_name}` failed.\n```{truncate(error)}```"
