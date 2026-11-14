REVIEWER_PREFIX_TEMPLATE = (
    "You are acting as a PR reviewer for this repository, not a feature "
    "author. Use `gh pr view`, `gh pr diff`, `gh pr review`, and `gh pr "
    "merge` as appropriate to accomplish the task below. Do not open new "
    "pull requests or make unrelated code changes. If you hit any problem "
    "completing the review or merge - conflicts, failing tests, missing "
    "permissions, anything unclear or unresolved - state it plainly in "
    "your final response and include {mention} so the orchestrator is "
    "notified. Do not silently drop a problem.\n\nTask: "
)


def augment_description(description: str, role: str, instinct_mention: str = "@Instinct") -> str:
    """Wrap the raw task text with role-specific framing for the CLI prompt."""
    if role == "reviewer":
        return REVIEWER_PREFIX_TEMPLATE.format(mention=instinct_mention) + description
    return description
