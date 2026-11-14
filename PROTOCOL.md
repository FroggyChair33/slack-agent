# Task protocol

The contract every agent in the channel - Claude Code, Codex, Instinct, or
anything else - must follow so routing and status reporting stay
consistent. If you're implementing a new agent (e.g. Instinct's side),
this file is the spec; `slack_agent/protocol.py` is the reference
implementation of it.

## 1. Task intake format

A task assignment is a **plain top-level message** in the shared channel
(not a thread reply) matching:

```
@agent:<name> <description>
```

- Must be the **start** of the message - no text before `@agent:`.
- `<name>` is a single token (no spaces): the receiving agent's
  `AGENT_NAME`, or the literal `all` to broadcast to every agent listening.
- `<description>` is everything after the first run of whitespace,
  trimmed. It may span multiple lines.
- Matching is exact and case-sensitive. There is no fuzzy matching and no
  real Slack `@mention` involved - agents don't have distinct Slack
  identities, so this is a plain-text tag by convention.

**Examples:**

```
@agent:stephen fix the null check in auth.py
@agent:all status check - reply with "ok" if you're listening
```

**Not a task** (ignored by every agent): any message that doesn't start
with `@agent:`, anything posted by a bot (`bot_id` set - this is what
stops agents from re-triggering off their own or each other's replies),
and message edits/deletes (Slack `subtype` set).

## 2. Output format

Every reply an agent sends is a **threaded reply** on the original
assignment message (`thread_ts` = that message's `ts`). There are exactly
three kinds, in order:

### Pickup ack (always sent first, immediately)

```
:hourglass_flowing_sand: `@agent:<name>` picked this up, working...
```

### Success

```
:white_check_mark: `@agent:<name>` done.
```
​```
<task output, truncated to 3000 chars>
```
​```

If the task changed files in the shared repo, a PR line is appended after
the output block - see "Git/PR behavior" below:

```
PR: https://github.com/<org>/<repo>/pull/<n>
```

If files changed but the push or PR creation itself failed, that's noted
instead of a PR link:

```
(pushed, but <reason>)
(not pushed: <reason>)
```

No file changes at all -> no push-related line is appended (clean no-op,
not an error).

### Failure

```
:x: `@agent:<name>` failed.
```
​```
<error message, truncated to 3000 chars>
```
​```

## 3. Git/PR behavior (part of the contract, not an implementation detail)

Before running a task, an agent resets its working directory to a clean
copy of `AGENT_BASE_BRANCH` (default `main`). After a successful task, if
the working directory has changes, the agent:

1. Commits them on a new branch: `agent/<name>/<slugified-task>-<unix-ts>`
2. Pushes that branch and opens a PR against `AGENT_BASE_BRANCH`
3. Returns to `AGENT_BASE_BRANCH` either way, so the next task starts clean

Nothing is ever pushed directly to the base branch. Anyone reading the
channel - human or Instinct - can treat a PR link in a success message as
"ready to review," not "already merged."

## 4. Invariants (why loops don't happen)

- An agent only ever reacts to a message that starts with `@agent:<name>`
  or `@agent:all` where `<name>` is its own - never to its own output.
- An agent never processes a message with `bot_id` set, so it can't be
  triggered by its own ack/success/failure replies, or another agent's.
- Every reply template above starts with an emoji, never with `@agent:` -
  structurally, a reply can never itself parse as a new task.
- Each agent serializes its own tasks (one at a time) since it has one
  working directory; a Slack/Socket Mode redelivery of the same assignment
  is also deduped by message `ts`, so the same task doesn't run twice.

Implementing Instinct (or anything else) against this file: as long as it
emits messages matching §1 and parses replies matching §2, it
interoperates with every agent in this repo with no code changes on their
side.
