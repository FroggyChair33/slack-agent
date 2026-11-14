import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from slack_agent.roles import augment_description


def test_coder_unchanged():
    assert augment_description("fix the bug", "coder") == "fix the bug"


def test_reviewer_wraps_with_gh_instructions():
    out = augment_description("merge PR #3", "reviewer")
    assert out.endswith("merge PR #3")
    assert "gh pr merge" in out


def test_unknown_role_behaves_like_coder():
    assert augment_description("fix the bug", "something-else") == "fix the bug"


if __name__ == "__main__":
    test_coder_unchanged()
    test_reviewer_wraps_with_gh_instructions()
    test_unknown_role_behaves_like_coder()
    print("All role tests passed.")
