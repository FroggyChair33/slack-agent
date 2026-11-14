# Role: reviewer

`AGENT_ROLE=reviewer`

## What it does

On a matching `@agent:<name> <task>`, the task description is wrapped
with reviewer framing (see `slack_agent/roles.py`) before being handed to
the CLI - it's told to act as a reviewer, not an author, and to use
`gh pr view` / `gh pr diff` / `gh pr review` / `gh pr merge` as needed.
Unlike the coder role, **it does not sync/branch/commit/push afterward** -
a reviewer's job is to act on PRs that already exist, not open new ones.
The CLI's own output (whatever it printed while running those `gh`
commands) is reported back in the Slack thread as-is.

## Escalating to Instinct

Instinct (`@Instinct` by default, mentioned in Slack) is the orchestrator
that hands out review tasks, so it needs to hear about anything that
stops one - not just the people watching the channel. Two layers do this:

1. **The CLI's own judgment.** The prompt it receives explicitly tells it
   to state any problem plainly - conflicts, failing tests, anything
   unresolved - and include the `@Instinct` mention in its final response
   when it does. This covers things only the model can judge mid-review.
2. **Infra-level failures, automatically.** A sync failure, a timeout, or
   an unexpected crash in the agent's own code gets `@Instinct` appended
   by `bot.py` regardless of what the CLI said (or whether it ran at
   all) - these aren't things the model can self-report since they
   happen outside its run.

Override the handle with `INSTINCT_MENTION` in `.env` if it changes or
differs from `@Instinct`.

## What to send it

Specific, scoped instructions naming a PR: `@agent:<name> review PR #3,
merge it if the tests pass`. Avoid open-ended tasks like "review
everything" - it's one `gh` invocation per task, not a standing watcher.

## ⚠️ Sandbox / permissions - read before enabling

Running `gh pr merge` is a **bash command**, not a file edit. The normal
safe defaults (`acceptEdits` / `workspace-write`) will block or hang on
it, by design. For this role to actually merge anything, set
`AGENT_SANDBOX_MODE=bypassPermissions` (Claude) or
`AGENT_SANDBOX_MODE=yolo` (Codex). `yolo` maps to Codex's
`--dangerously-bypass-approvals-and-sandbox` - the one flag confirmed to
skip every approval prompt; `--approve-for-me` looked like a softer
option but it can't be combined with `--sandbox` at all (they conflict),
so there isn't a middle setting here for Codex.

That is a materially bigger blast radius than the coder role: an agent
with that sandbox setting can run **any** shell command unsupervised, not
just `gh` commands, and it's the one role that can land code in
`AGENT_BASE_BRANCH` without a human clicking merge. Nothing in this
codebase escalates permissions for you automatically - you opt into this
by setting `AGENT_SANDBOX_MODE` yourself. Before you do:

- Point this role's `AGENT_WORKDIR` at a clone you're comfortable with
  that risk in.
- Keep tasks scoped to a specific PR number rather than open-ended.
- Treat its Slack thread output as the audit trail - it's the only record
  of what it actually ran.
- If you're not ready for auto-merge yet, phrase tasks as "review and
  comment on PR #3" and leave merging out - the reviewer framing doesn't
  force a merge, it just permits one if the task asks for it and the
  sandbox allows it.
