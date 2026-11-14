import threading


class SeenGuard:
    """Tracks message ts values already acted on, so a Slack/Socket Mode
    redelivery of the same event doesn't run the same task twice."""

    def __init__(self):
        self._lock = threading.Lock()
        self._seen = set()

    def already_handled(self, key: str) -> bool:
        with self._lock:
            if key in self._seen:
                return True
            self._seen.add(key)
            return False
