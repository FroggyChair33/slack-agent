# Role: coder

`AGENT_ROLE=coder` (the default - existing `.env` files with no
`AGENT_ROLE` set behave exactly as before).

## What it does

On a matching `@agent:<name> <task>` (see [PROTOCOL.md](../PROTOCOL.md)):

1. Syncs `AGENT_WORKDIR` to a clean copy of `AGENT_BASE_BRANCH`.
2. Runs the task description, verbatim, through the configured CLI
   (`claude -p` or `codex exec`).
3. If that left any file changes, commits them on a new branch and opens
   a PR against `AGENT_BASE_BRANCH` - see "Git/PR behavior" in
   PROTOCOL.md.
4. Never merges anything. It only ever proposes changes via PR.

## Sandbox / permissions

Use the normal defaults - `AGENT_SANDBOX_MODE=acceptEdits` (Claude) or
`workspace-write` (Codex). A coder only needs to edit files; it doesn't
need unrestricted bash. Don't widen this role's permissions to run
`gh pr merge` or similar - that's the reviewer role's job, specifically
so the two responsibilities (writing changes vs. deciding what lands)
stay separated and auditable.

## What to send it

Task descriptions that describe a change to make - a bug to fix, a
feature to add, a file to create. Not "review PR #3" or "merge this" -
route those to a reviewer-role agent instead.
