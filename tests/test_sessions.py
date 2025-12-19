"""Tests for sessions store with multi-user support."""

from unittest.mock import patch

import pytest

from skill_issues.sessions.store import (
    filter_by_user,
    next_session_id,
    parse_session_id,
)


class TestParseSessionId:
    """Tests for parse_session_id()."""

    def test_new_format_two_char_prefix(self):
        assert parse_session_id("dp-s001") == ("dp", 1)

    def test_new_format_four_char_prefix(self):
        assert parse_session_id("test-s042") == ("test", 42)

    def test_new_format_alphanumeric_prefix(self):
        assert parse_session_id("ab1-s007") == ("ab1", 7)

    def test_old_format(self):
        assert parse_session_id("s001") == (None, 1)

    def test_old_format_large_number(self):
        assert parse_session_id("s999") == (None, 999)

    def test_invalid_format(self):
        assert parse_session_id("invalid") == (None, None)

    def test_empty_string(self):
        assert parse_session_id("") == (None, None)

    def test_prefix_too_short(self):
        # Single char prefix is invalid
        assert parse_session_id("a-s001") == (None, None)

    def test_prefix_too_long(self):
        # 5 char prefix is invalid
        assert parse_session_id("abcde-s001") == (None, None)


class TestNextSessionId:
    """Tests for next_session_id()."""

    def test_empty_sessions_list(self):
        with patch("skill_issues.sessions.store.get_user_prefix", return_value=("dp", True)):
            assert next_session_id([]) == "dp-s001"

    def test_increments_for_same_user(self):
        sessions = [
            {"id": "dp-s001", "user": "dp"},
            {"id": "dp-s002", "user": "dp"},
        ]
        with patch("skill_issues.sessions.store.get_user_prefix", return_value=("dp", True)):
            assert next_session_id(sessions) == "dp-s003"

    def test_ignores_other_users_sessions(self):
        sessions = [
            {"id": "jb-s001", "user": "jb"},
            {"id": "jb-s002", "user": "jb"},
            {"id": "dp-s001", "user": "dp"},
        ]
        with patch("skill_issues.sessions.store.get_user_prefix", return_value=("dp", True)):
            assert next_session_id(sessions) == "dp-s002"

    def test_explicit_prefix_parameter(self):
        sessions = [{"id": "dp-s001", "user": "dp"}]
        # Should use explicit prefix, not call get_user_prefix
        assert next_session_id(sessions, prefix="jb") == "jb-s001"

    def test_handles_gaps_in_numbers(self):
        sessions = [
            {"id": "dp-s001", "user": "dp"},
            {"id": "dp-s005", "user": "dp"},
        ]
        with patch("skill_issues.sessions.store.get_user_prefix", return_value=("dp", True)):
            # Should use max, not fill gaps
            assert next_session_id(sessions) == "dp-s006"

    def test_ignores_old_format_sessions(self):
        # Old format sessions shouldn't affect new user's numbering
        sessions = [
            {"id": "s049"},
            {"id": "dp-s001", "user": "dp"},
        ]
        with patch("skill_issues.sessions.store.get_user_prefix", return_value=("dp", True)):
            assert next_session_id(sessions) == "dp-s002"


class TestFilterByUser:
    """Tests for filter_by_user()."""

    def test_filters_by_user_field(self):
        sessions = [
            {"id": "dp-s001", "user": "dp"},
            {"id": "jb-s001", "user": "jb"},
            {"id": "dp-s002", "user": "dp"},
        ]
        with patch("skill_issues.sessions.store.get_user_prefix", return_value=("dp", True)):
            result = filter_by_user(sessions)
            assert len(result) == 2
            assert all(s["user"] == "dp" for s in result)

    def test_explicit_user_parameter(self):
        sessions = [
            {"id": "dp-s001", "user": "dp"},
            {"id": "jb-s001", "user": "jb"},
        ]
        result = filter_by_user(sessions, user="jb")
        assert len(result) == 1
        assert result[0]["user"] == "jb"

    def test_empty_result_for_unknown_user(self):
        sessions = [
            {"id": "dp-s001", "user": "dp"},
        ]
        result = filter_by_user(sessions, user="xx")
        assert result == []

    def test_legacy_sessions_without_user_field_parsed(self):
        # Legacy sessions should be matched by parsing their ID
        sessions = [
            {"id": "dp-s001"},  # No user field, but ID indicates dp
            {"id": "jb-s001", "user": "jb"},
        ]
        result = filter_by_user(sessions, user="dp")
        assert len(result) == 1
        assert result[0]["id"] == "dp-s001"

    def test_old_format_sessions_never_match(self):
        # Old format (s001) has no prefix, should never match any user
        sessions = [
            {"id": "s001"},  # Old format
            {"id": "dp-s001", "user": "dp"},
        ]
        result = filter_by_user(sessions, user="dp")
        assert len(result) == 1
        assert result[0]["id"] == "dp-s001"
