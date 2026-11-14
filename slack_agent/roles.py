REVIEWER_PREFIX = (
    "You are acting as a PR reviewer for this repository, not a feature "
    "author. Use `gh pr view`, `gh pr diff`, `gh pr review`, and `gh pr "
    "merge` as appropriate to accomplish the task below. Do not open new "
    "pull requests or make unrelated code changes.\n\nTask: "
)


def augment_description(description: str, role: str) -> str:
    """Wrap the raw task text with role-specific framing for the CLI prompt."""
    if role == "reviewer":
        return REVIEWER_PREFIX + description
    return description
