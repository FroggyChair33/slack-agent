import threading

from dotenv import load_dotenv

load_dotenv()

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from . import config, dedupe, protocol, runner

app = App(token=config.SLACK_BOT_TOKEN)
_guard = dedupe.SeenGuard()


def _work(description: str, thread_ts: str, say):
    say(text=protocol.picked_up_message(config.AGENT_NAME), thread_ts=thread_ts)
    result = runner.run_task(description)
    if result.success:
        say(text=protocol.success_message(config.AGENT_NAME, result.output), thread_ts=thread_ts)
    else:
        say(text=protocol.failure_message(config.AGENT_NAME, result.output), thread_ts=thread_ts)


@app.event("message")
def handle_message(event, say):
    # Ignore bot-originated messages (including our own acks/results) and edits/deletes.
    if event.get("bot_id") or event.get("subtype"):
        return

    parsed = protocol.parse_task(event.get("text", ""))
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
