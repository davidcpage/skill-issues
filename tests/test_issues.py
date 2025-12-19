"""Tests for issues store with multi-user support."""

from unittest.mock import patch

import pytest

from skill_issues.issues.store import (
    next_id,
    parse_issue_id,
)


class TestParseIssueId:
    """Tests for parse_issue_id()."""

    def test_new_format_two_char_prefix(self):
        assert parse_issue_id("dp-001") == ("dp", 1)

    def test_new_format_four_char_prefix(self):
        assert parse_issue_id("test-042") == ("test", 42)

    def test_new_format_alphanumeric_prefix(self):
        assert parse_issue_id("ab1-007") == ("ab1", 7)

    def test_old_format(self):
        assert parse_issue_id("001") == (None, 1)

    def test_old_format_large_number(self):
        assert parse_issue_id("999") == (None, 999)

    def test_old_format_no_leading_zeros(self):
        assert parse_issue_id("88") == (None, 88)

    def test_invalid_format(self):
        assert parse_issue_id("invalid") == (None, None)

    def test_empty_string(self):
        assert parse_issue_id("") == (None, None)

    def test_prefix_too_short(self):
        # Single char prefix is invalid
        assert parse_issue_id("a-001") == (None, None)

    def test_prefix_too_long(self):
        # 5 char prefix is invalid
        assert parse_issue_id("abcde-001") == (None, None)

    def test_session_format_not_matched(self):
        # Session IDs (with 's') should not match issue format
        assert parse_issue_id("dp-s001") == (None, None)


class TestNextId:
    """Tests for next_id()."""

    def test_empty_issues_dict(self):
        with patch("skill_issues.issues.store.get_user_prefix", return_value=("dp", True)):
            assert next_id({}) == "dp-001"

    def test_increments_for_same_user(self):
        issues = {
            "dp-001": {"id": "dp-001"},
            "dp-002": {"id": "dp-002"},
        }
        with patch("skill_issues.issues.store.get_user_prefix", return_value=("dp", True)):
            assert next_id(issues) == "dp-003"

    def test_ignores_other_users_issues(self):
        issues = {
            "jb-001": {"id": "jb-001"},
            "jb-002": {"id": "jb-002"},
            "dp-001": {"id": "dp-001"},
        }
        with patch("skill_issues.issues.store.get_user_prefix", return_value=("dp", True)):
            assert next_id(issues) == "dp-002"

    def test_explicit_prefix_parameter(self):
        issues = {"dp-001": {"id": "dp-001"}}
        # Should use explicit prefix, not call get_user_prefix
        assert next_id(issues, prefix="jb") == "jb-001"

    def test_handles_gaps_in_numbers(self):
        issues = {
            "dp-001": {"id": "dp-001"},
            "dp-005": {"id": "dp-005"},
        }
        with patch("skill_issues.issues.store.get_user_prefix", return_value=("dp", True)):
            # Should use max, not fill gaps
            assert next_id(issues) == "dp-006"

    def test_ignores_old_format_issues(self):
        # Old format issues shouldn't affect new user's numbering
        issues = {
            "088": {"id": "088"},
            "dp-001": {"id": "dp-001"},
        }
        with patch("skill_issues.issues.store.get_user_prefix", return_value=("dp", True)):
            assert next_id(issues) == "dp-002"

    def test_mixed_old_and_new_format(self):
        # When there are only old-format issues, new user starts at 001
        issues = {
            "001": {"id": "001"},
            "088": {"id": "088"},
        }
        with patch("skill_issues.issues.store.get_user_prefix", return_value=("dp", True)):
            assert next_id(issues) == "dp-001"
