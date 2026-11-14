import os

AGENT_NAME = os.environ["AGENT_NAME"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

WORKDIR = os.environ.get("AGENT_WORKDIR", os.getcwd())

# "coder" (default - writes code, opens PRs, never merges) or "reviewer"
# (reviews/merges existing PRs, opens none itself). See roles/*.md.
AGENT_ROLE = os.environ.get("AGENT_ROLE", "coder")

# How the reviewer role pings the orchestrator bot when something needs
# its attention - a plain-text tag, same convention as @agent:<name>.
INSTINCT_MENTION = os.environ.get("INSTINCT_MENTION", "@Instinct")

# "claude" (Claude Code) or "codex" (OpenAI Codex CLI) - picks the command
# shape runner.py builds.
AGENT_KIND = os.environ.get("AGENT_KIND", "claude")
AGENT_BIN = os.environ.get("AGENT_BIN", AGENT_KIND)

_DEFAULT_SANDBOX_MODE = {"claude": "acceptEdits", "codex": "workspace-write"}
AGENT_SANDBOX_MODE = os.environ.get("AGENT_SANDBOX_MODE", _DEFAULT_SANDBOX_MODE.get(AGENT_KIND, "acceptEdits"))

TASK_TIMEOUT_SECONDS = int(os.environ.get("TASK_TIMEOUT_SECONDS", "1800"))

# Branch in the shared repo that AGENT_WORKDIR gets synced to before each task,
# and that finished work gets PR'd against.
BASE_BRANCH = os.environ.get("AGENT_BASE_BRANCH", "main")
