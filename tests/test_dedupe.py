import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from slack_agent.dedupe import SeenGuard


def test_blocks_repeat_key():
    guard = SeenGuard()
    assert not guard.already_handled("111.222")
    assert guard.already_handled("111.222")


def test_allows_different_keys():
    guard = SeenGuard()
    assert not guard.already_handled("111.222")
    assert not guard.already_handled("333.444")


if __name__ == "__main__":
    test_blocks_repeat_key()
    test_allows_different_keys()
    print("All dedupe tests passed.")
