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


class TestSessionsCLIUserFlag:
    """Tests for --user flag in sessions CLI."""

    @pytest.fixture
    def multi_user_sessions(self, tmp_path, monkeypatch):
        """Create a sessions file with multiple users."""
        from skill_issues.sessions import store

        memory_dir = tmp_path / ".memory"
        memory_dir.mkdir()
        sessions_file = memory_dir / "sessions.jsonl"
        sessions_file.write_text(
            '{"id":"dp-s001","user":"dp","date":"2025-01-01","topic":"dp topic 1","learnings":[],"open_questions":[],"next_actions":[],"issues_worked":[]}\n'
            '{"id":"jb-s001","user":"jb","date":"2025-01-01","topic":"jb topic 1","learnings":[],"open_questions":[],"next_actions":[],"issues_worked":[]}\n'
            '{"id":"dp-s002","user":"dp","date":"2025-01-02","topic":"dp topic 2","learnings":[],"open_questions":[],"next_actions":[],"issues_worked":[]}\n'
            '{"id":"jb-s002","user":"jb","date":"2025-01-02","topic":"jb topic 2","learnings":[],"open_questions":[],"next_actions":[],"issues_worked":[]}\n'
        )
        # Patch the module-level constant
        monkeypatch.setattr(store, "SESSIONS_FILE", sessions_file)
        return sessions_file

    def test_default_filters_to_current_user(self, multi_user_sessions, monkeypatch):
        """Default query should only show current user's sessions."""
        from skill_issues.sessions import store

        monkeypatch.setattr(store, "get_user_prefix", lambda: ("dp", True))

        # Load sessions and apply default filtering
        all_sessions = store.load_sessions()
        filtered = store.filter_by_user(all_sessions)

        assert len(filtered) == 2
        assert all(s["user"] == "dp" for s in filtered)

    def test_user_all_shows_all_users(self, multi_user_sessions):
        """--user all should show sessions from all users."""
        from skill_issues.sessions import store

        all_sessions = store.load_sessions()
        assert len(all_sessions) == 4

    def test_user_specific_filters_to_that_user(self, multi_user_sessions):
        """--user <prefix> should filter to that specific user."""
        from skill_issues.sessions import store

        all_sessions = store.load_sessions()
        filtered = store.filter_by_user(all_sessions, user="jb")

        assert len(filtered) == 2
        assert all(s["user"] == "jb" for s in filtered)

    def test_user_flag_combines_with_last(self, multi_user_sessions, monkeypatch):
        """--user flag should work with --last N."""
        from skill_issues.sessions import store

        monkeypatch.setattr(store, "get_user_prefix", lambda: ("dp", True))

        all_sessions = store.load_sessions()
        filtered = store.filter_by_user(all_sessions)
        last_one = filtered[-1:]

        assert len(last_one) == 1
        assert last_one[0]["id"] == "dp-s002"
