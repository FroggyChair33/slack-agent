# slack-agent

Connects a local coding agent (Claude Code) to a shared Slack channel so a
Slack-based orchestrator (human or bot) can hand out tasks and get results
back in-thread. Runs over Socket Mode - no public URL/webhook needed, so it
works straight from a laptop for the hackathon.

## Roles

`AGENT_ROLE` picks what a running agent is for:

- [`roles/coder.md`](./roles/coder.md) (default) - writes code, opens PRs, never merges.
- [`roles/reviewer.md`](./roles/reviewer.md) - reviews/merges existing PRs, opens none itself. Needs a much more permissive sandbox setting to actually merge - read that file's warning before enabling it.

## Landing finished work

Each successful task gets committed on a fresh branch
(`agent/<name>/<slugified-task>-<timestamp>`) and opened as a PR against
`AGENT_BASE_BRANCH` (default `main`) via `gh pr create` - nothing is ever
pushed straight to main. The PR link is posted back in the Slack thread.
Before each task, the workdir is reset to a clean copy of the base branch
(`git checkout <base> && git pull --ff-only`) so every task starts from
the same state. Tasks that don't touch any files (e.g. answering a
question) just skip the push silently.

Requires `git` and `gh` installed and authenticated (`gh auth login`) on
each teammate's machine, and `AGENT_WORKDIR` must be a clone of the shared
repo with push access. Tasks for the same agent are serialized (one at a
time) specifically because they share one working tree - running two at
once would stomp on each other's files and git state.

## Task protocol

Full spec in [PROTOCOL.md](./PROTOCOL.md) - the contract every agent
(Claude Code, Codex, Instinct, anything else) must follow for routing and
status reporting to stay consistent. Summary:

- **Assign a task:** post `@agent:<name> <task description>` as a plain
  message in the channel. Use `@agent:all` to broadcast to every running
  agent.
- **Pickup ack:** the matching agent replies in-thread with
  `:hourglass_flowing_sand: ... picked this up, working...`
- **Result:** the agent replies in the same thread with
  `:white_check_mark: ... done.` plus output, or `:x: ... failed.` plus the
  error.

Anyone - including the OpenAI orchestrator - just needs to read the thread
to follow status. Each teammate runs their own copy of this script under
their own `AGENT_NAME`.

## One-time Slack app setup (whoever has workspace admin - can be reused for everyone)

1. Create an app at https://api.slack.com/apps -> "From scratch".
2. **Socket Mode**: enable it, generate an app-level token with the
   `connections:write` scope -> this is `SLACK_APP_TOKEN` (`xapp-...`).
3. **OAuth & Permissions**: add bot token scopes `chat:write` and
   `channels:history` (or `groups:history` if it's a private channel).
4. **Event Subscriptions**: enable, and under "Subscribe to bot events" add
   `message.channels` (or `message.groups` for a private channel).
5. Install the app to the workspace -> copy the Bot User OAuth Token, this
   is `SLACK_BOT_TOKEN` (`xoxb-...`).
6. Invite the bot to the channel: `/invite @your-bot-name`.
7. Share `SLACK_BOT_TOKEN` and `SLACK_APP_TOKEN` with every teammate running
   this script (same app/bot identity for everyone is fine - agents are
   distinguished by `AGENT_NAME`, not by Slack identity).

## Per-teammate setup

```
cd slack-agent
pip install -r requirements.txt
cp .env.example .env   # fill in SLACK_BOT_TOKEN, SLACK_APP_TOKEN, AGENT_NAME, AGENT_WORKDIR
python -m slack_agent.bot
```

`AGENT_WORKDIR` should point at your local checkout of the project the task
refers to - that's where `claude -p` will run.

## Agent kinds

One codebase, two CLIs - set `AGENT_KIND` in `.env`:

- `AGENT_KIND=claude` (default) - runs `claude -p "<task>" --output-format text --permission-mode <AGENT_SANDBOX_MODE>`
- `AGENT_KIND=codex` - runs `codex exec "<task>" --sandbox <AGENT_SANDBOX_MODE> --skip-git-repo-check`

Everything else (the `@agent:<name>` protocol, threading, dedupe) is
identical either way. For a codex agent: run `codex login` locally first
(same idea as `claude login`), then set `AGENT_KIND=codex`,
`AGENT_SANDBOX_MODE=workspace-write` (or `read-only` / `danger-full-access`),
and `AGENT_WORKDIR` to that teammate's checkout.

Not yet verified: whether `codex exec`'s exit code reliably signals success
vs. failure in plain-text mode the way Claude Code's does - worth a quick
smoke test before relying on it; if it doesn't, switch to `--json` and check
for a `turn.failed`/`error` event instead of the exit code.

## Self-check

```
python tests/test_protocol.py
python tests/test_dedupe.py
python tests/test_runner_command.py
python tests/test_git_push.py
python tests/test_roles.py
```

## Loop / duplicate-execution protection

- Matching is plain-text (`@agent:<name> ...`), not a real Slack
  `@mention` - there's no shared per-agent Slack identity to mention. The
  regex is anchored to the start of the message, and any message posted
  by a bot (`bot_id` set - including this script's own acks/results) is
  ignored outright, so an agent can never re-trigger itself off its own
  reply.
- Tasks run in a background thread, not inside the Slack event handler.
  Running a 30-minute `claude -p` call synchronously in the handler would
  stop Bolt from acking Slack in time, causing Socket Mode to redeliver
  the same event and run the task again in parallel - `_work()` is
  dispatched via `threading.Thread` specifically to avoid that.
- A small in-memory `SeenGuard` (`dedupe.py`) also rejects any message
  `ts` already acted on, as a belt-and-suspenders check if a redelivery
  still slips through.

## Other notes / risks

- `CLAUDE_PERMISSION_MODE=acceptEdits` (the default) auto-approves file
  edits but still prompts for other tool use (e.g. bash), which will hang
  a headless run. If tasks need bash/tool access to complete unattended,
  switch it to `bypassPermissions` - only do that if you trust everything
  this channel will hand your agent.
- All teammates sharing one Slack bot token means every script sees every
  message; each just ignores tasks not addressed to its `AGENT_NAME`. Fine
  at hackathon scale.
- No de-duplication across agents on `@agent:all` - if two teammates are
  both listening for `all`, both will run it (intentional - that's what
  broadcast means here, but worth knowing).
- The `SeenGuard` is in-memory and per-process - restarting a script
  forgets what it already handled.
