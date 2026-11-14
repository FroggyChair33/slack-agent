import threading

from dotenv import load_dotenv

load_dotenv()

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from . import config, dedupe, git_push, protocol, roles, runner

app = App(token=config.SLACK_BOT_TOKEN)
_guard = dedupe.SeenGuard()
# AGENT_WORKDIR is one shared git working tree - serialize tasks so two
# messages addressed to this agent can't run git/CLI ops in it at once.
_workdir_lock = threading.Lock()


def _work(description: str, thread_ts: str, say):
    # Last-resort net: anything unexpected (not just the failure paths we
    # already handle below) must still reach the thread. Before this, an
    # uncaught exception here just killed the background thread silently -
    # Slack showed the pickup ack and then nothing, forever.
    try:
        say(text=protocol.picked_up_message(config.AGENT_NAME), thread_ts=thread_ts)

        with _workdir_lock:
            synced, sync_note = git_push.sync_to_base()
            if not synced:
                say(
                    text=protocol.failure_message(
                        config.AGENT_NAME, f"couldn't sync workdir to {config.BASE_BRANCH}: {sync_note}"
                    ),
                    thread_ts=thread_ts,
                )
                return

            task_prompt = roles.augment_description(description, config.AGENT_ROLE)
            result = runner.run_task(task_prompt)
            if not result.success:
                say(text=protocol.failure_message(config.AGENT_NAME, result.output), thread_ts=thread_ts)
                return

            summary = result.output
            if config.AGENT_ROLE == "coder":
                # Reviewer tasks act on PRs that already exist - they don't open
                # new ones on themselves, so this step only applies to coders.
                push = git_push.push_changes(description)
                if push.pushed and push.pr_url:
                    summary += f"\n\nPR: {push.pr_url}"
                elif push.pushed:
                    summary += f"\n\n(pushed, but {push.note})"
                elif push.note != "no changes to push":
                    summary += f"\n\n(not pushed: {push.note})"
            say(text=protocol.success_message(config.AGENT_NAME, summary), thread_ts=thread_ts)
    except Exception as exc:
        try:
            say(
                text=protocol.failure_message(
                    config.AGENT_NAME, f"unexpected error, needs a human to look: {exc!r}"
                ),
                thread_ts=thread_ts,
            )
        except Exception:
            print(f"[{config.AGENT_NAME}] also failed to report this error to Slack: {exc!r}")


@app.event("message")
def handle_message(event, say):
    # Ignore bot-originated messages (including our own acks/results) and edits/deletes.
    if event.get("bot_id") or event.get("subtype"):
        return

    # event.get("text", "") only falls back when the key is missing - some
    # message types (e.g. blocks/attachments with no plain text) send it as
    # an explicit null, which "or """ catches too.
    parsed = protocol.parse_task(event.get("text") or "")
    if not parsed:
        return

    target, description = parsed
    if not protocol.is_for_me(target, config.AGENT_NAME):
        return

    ts = event.get("ts")
    if _guard.already_handled(ts):
        return

    # Hand the task off to a background thread so this handler returns
    # immediately and Bolt can ack Slack within its window. A 30-minute task
    # blocking here would otherwise make Slack redeliver the same event and
    # run it again in parallel.
    threading.Thread(target=_work, args=(description, ts, say), daemon=True).start()


if __name__ == "__main__":
    print(f"[{config.AGENT_NAME}] listening for '@agent:{config.AGENT_NAME}' / '@agent:all' tasks via Socket Mode...")
    SocketModeHandler(app, config.SLACK_APP_TOKEN).start()
