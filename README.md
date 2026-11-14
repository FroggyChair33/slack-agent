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
Before each task, the workdir fetches every branch's latest refs
(`git fetch origin`), then resets to a clean copy of the base branch
(`git checkout <base> && git pull --ff-only`) - so every task starts from
the same state, and a review task can see other branches' latest commits
even outside the `gh pr` commands that fetch on their own. Tasks that
don't touch any files (e.g. answering a question) just skip the push
silently.

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

## Slack app setup - once per teammate, not once per team

**Each teammate needs their own Slack app (own bot token, own app-level
token) - don't reuse one set of tokens across machines.** Slack's Socket
Mode load-balances events across connections that share the same
app-level token rather than delivering to all of them, so two people
sharing one app could have a task silently delivered to the wrong
person's process and never run. Separate apps don't have this problem -
each one independently gets its own copy of every channel event. Routing
still works the same way (`@agent:<name>`); this only changes how many
Slack apps exist, not the protocol.

Repeat this whole section for every teammate running an agent.

**Fastest path - paste this manifest** at https://api.slack.com/apps ->
"Create New App" -> "From scratch" -> "Paste a manifest". Copy it
straight from this file on GitHub (not through Slack, Notes, Word, etc. -
those can silently swap the straight quotes for curly ones and break the
parser). Change `name`/`display_name` to something unique per teammate
before creating it:

```yaml
display_information:
  name: hackathon-coding-agent-codex
features:
  bot_user:
    display_name: hackathon-coding-agent-codex
    always_online: true
oauth_config:
  scopes:
    bot:
      - "chat:write"
      - "channels:history"
      - "groups:history"
settings:
  event_subscriptions:
    bot_events:
      - "message.channels"
      - "message.groups"
  interactivity:
    is_enabled: false
  org_deploy_enabled: false
  socket_mode_enabled: true
  token_rotation_enabled: false
```

Then, on the created app's settings page:

1. **Socket Mode**: already enabled by the manifest - generate an
   app-level token with the `connections:write` scope -> this is
   `SLACK_APP_TOKEN` (`xapp-...`).
2. **OAuth & Permissions**: click **Install to Workspace** (scopes are
   already set by the manifest) -> copy the Bot User OAuth Token, this is
   `SLACK_BOT_TOKEN` (`xoxb-...`).
3. Invite the bot to the channel: `/invite @your-bot-name`.
4. Keep these tokens to yourself - don't share them with other teammates.
   Each person who repeats this section ends up with their own
   `SLACK_BOT_TOKEN`/`SLACK_APP_TOKEN` pair for their own app.

**Manual path (no manifest):** create the app "From scratch" with no
manifest, then set the same things by hand - Socket Mode on with an
app-level token (`connections:write`), bot scopes `chat:write` +
`channels:history`/`groups:history` under OAuth & Permissions, and
`message.channels`/`message.groups` under Event Subscriptions - before
installing and inviting the bot.

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

## Running a task's toolchain inside WSL2 (Windows only)

Some tasks need a toolchain that's only installed inside WSL2 (e.g. Rust/
Solana/Anchor) - installing it there doesn't put it on native Windows'
`PATH`, so an agent running natively on Windows can't see it even though the
toolchain exists on the same machine. Installing the toolchain in a
*separate* WSL2 terminal from the one the agent's own commands run in does
not fix this - the agent's own process has to actually run inside WSL2, so
its internal tool-use shell (bash, not `cmd.exe`) is the one that inherits
that `PATH`.

Set `AGENT_RUN_IN_WSL=true` (and `AGENT_WSL_DISTRO`, default `Ubuntu`) to
have `runner.py` wrap the CLI invocation through `wsl.exe` instead of
running it natively. `AGENT_WORKDIR` stays a normal Windows path - it's
translated to its `/mnt/c/...` equivalent for the `cd` inside WSL2, so
`git_push.py`'s own git/gh calls (which still run natively) and the task's
CLI invocation (which now runs inside WSL2) operate on the exact same
checkout. Requires, inside that WSL2 distro specifically (separate from
anything installed on native Windows): the CLI itself (`claude`/`codex`)
installed and logged in, plus `git`/`gh` if the model falls back to running
them itself mid-task.

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
  regex is anchored to the start of the message, and every reply template
  starts with an emoji rather than `@agent:` - so a reply can never parse
  as a new task, from this agent or any other. That's the real loop guard;
  it holds for bot-authored messages too, which matters since Instinct (the
  orchestrator) is itself a bot and needs to be able to assign tasks. An
  agent additionally ignores messages from its *own* `bot_id` specifically,
  as a belt-and-suspenders check - but not other bots in general.
- Tasks run in a background thread, not inside the Slack event handler.
  Running a 30-minute `claude -p` call synchronously in the handler would
  stop Bolt from acking Slack in time, causing Socket Mode to redeliver
  the same event and run the task again in parallel - `_work()` is
  dispatched via `threading.Thread` specifically to avoid that.
- A small in-memory `SeenGuard` (`dedupe.py`) also rejects any message
  `ts` already acted on, as a belt-and-suspenders check if a redelivery
  still slips through.

## Other notes / risks

- `AGENT_SANDBOX_MODE=acceptEdits` (the claude-kind default) auto-approves
  file edits but still prompts for other tool use (e.g. bash), which will
  hang a headless run. If tasks need bash/tool access to complete
  unattended, switch it to `bypassPermissions` - only do that if you trust
  everything this channel will hand your agent (see `roles/reviewer.md`
  for why that matters most for the reviewer role).
- Each teammate has their own Slack app now (see "Slack app setup"
  above), so each one's process only sees its own app's events - no
  cross-filtering needed. If two agents are ever pointed at the *same*
  Slack app/tokens anyway, remember Socket Mode load-balances across
  their connections rather than fanning out, so don't do that.
- No de-duplication across agents on `@agent:all` - if two teammates are
  both listening for `all`, both will run it (intentional - that's what
  broadcast means here, but worth knowing).
- The `SeenGuard` is in-memory and per-process - restarting a script
  forgets what it already handled.
