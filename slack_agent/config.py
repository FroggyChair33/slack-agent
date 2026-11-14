import os

AGENT_NAME = os.environ["AGENT_NAME"]
SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_APP_TOKEN = os.environ["SLACK_APP_TOKEN"]

WORKDIR = os.environ.get("AGENT_WORKDIR", os.getcwd())

# "claude" (Claude Code) or "codex" (OpenAI Codex CLI) - picks the command
# shape runner.py builds.
AGENT_KIND = os.environ.get("AGENT_KIND", "claude")
AGENT_BIN = os.environ.get("AGENT_BIN", AGENT_KIND)

_DEFAULT_SANDBOX_MODE = {"claude": "acceptEdits", "codex": "workspace-write"}
AGENT_SANDBOX_MODE = os.environ.get("AGENT_SANDBOX_MODE", _DEFAULT_SANDBOX_MODE.get(AGENT_KIND, "acceptEdits"))

TASK_TIMEOUT_SECONDS = int(os.environ.get("TASK_TIMEOUT_SECONDS", "1800"))
