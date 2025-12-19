"""Tests for get_user_prefix() and related utilities."""

import os
import subprocess
from unittest.mock import patch

import pytest

from skill_issues import (
    PrefixError,
    _derive_prefix_from_name,
    _validate_prefix,
    get_user_prefix,
)


class TestDerivePrefix:
    """Tests for _derive_prefix_from_name()."""

    def test_two_word_name(self):
        assert _derive_prefix_from_name("David Page") == "dp"

    def test_three_word_name(self):
        assert _derive_prefix_from_name("Mary Jane Watson") == "mw"

    def test_hyphenated_first_name(self):
        assert _derive_prefix_from_name("Jean-Pierre Dupont") == "jd"

    def test_single_word_name(self):
        assert _derive_prefix_from_name("Alice") is None

    def test_empty_string(self):
        assert _derive_prefix_from_name("") is None

    def test_lowercase_input(self):
        assert _derive_prefix_from_name("david page") == "dp"

    def test_mixed_case(self):
        assert _derive_prefix_from_name("DAVID PAGE") == "dp"


class TestValidatePrefix:
    """Tests for _validate_prefix()."""

    def test_valid_two_char(self):
        assert _validate_prefix("dp") == "dp"

    def test_valid_three_char(self):
        assert _validate_prefix("abc") == "abc"

    def test_valid_four_char(self):
        assert _validate_prefix("abcd") == "abcd"

    def test_normalizes_to_lowercase(self):
        assert _validate_prefix("DP") == "dp"

    def test_strips_whitespace(self):
        assert _validate_prefix("  dp  ") == "dp"

    def test_alphanumeric_allowed(self):
        assert _validate_prefix("dp1") == "dp1"

    def test_empty_raises(self):
        with pytest.raises(PrefixError, match="cannot be empty"):
            _validate_prefix("")

    def test_whitespace_only_raises(self):
        with pytest.raises(PrefixError, match="cannot be empty"):
            _validate_prefix("   ")

    def test_too_short_raises(self):
        with pytest.raises(PrefixError, match="at least 2"):
            _validate_prefix("a")

    def test_too_long_raises(self):
        with pytest.raises(PrefixError, match="at most 4"):
            _validate_prefix("abcde")

    def test_non_alphanumeric_raises(self):
        with pytest.raises(PrefixError, match="alphanumeric"):
            _validate_prefix("d-p")


class TestGetUserPrefix:
    """Tests for get_user_prefix()."""

    def test_env_var_takes_priority(self):
        with patch.dict(os.environ, {"SKILL_ISSUES_PREFIX": "env"}):
            with patch("skill_issues._get_git_config", return_value="git"):
                prefix, derived = get_user_prefix()
                assert prefix == "env"
                assert derived is False

    def test_git_config_prefix_second(self):
        with patch.dict(os.environ, {"SKILL_ISSUES_PREFIX": ""}):
            with patch("skill_issues._get_git_config") as mock:
                mock.side_effect = lambda k: "git" if k == "skill-issues.prefix" else None
                prefix, derived = get_user_prefix()
                assert prefix == "git"
                assert derived is False

    def test_derived_from_user_name(self):
        with patch.dict(os.environ, {"SKILL_ISSUES_PREFIX": ""}):
            with patch("skill_issues._get_git_config") as mock:
                mock.side_effect = lambda k: "David Page" if k == "user.name" else None
                prefix, derived = get_user_prefix()
                assert prefix == "dp"
                assert derived is True

    def test_fallback_to_xx(self):
        with patch.dict(os.environ, {"SKILL_ISSUES_PREFIX": ""}):
            with patch("skill_issues._get_git_config", return_value=None):
                prefix, derived = get_user_prefix()
                assert prefix == "xx"
                assert derived is True

    def test_single_name_falls_through_to_fallback(self):
        with patch.dict(os.environ, {"SKILL_ISSUES_PREFIX": ""}):
            with patch("skill_issues._get_git_config") as mock:
                mock.side_effect = lambda k: "Alice" if k == "user.name" else None
                prefix, derived = get_user_prefix()
                assert prefix == "xx"
                assert derived is True

    def test_invalid_env_prefix_raises(self):
        with patch.dict(os.environ, {"SKILL_ISSUES_PREFIX": "toolong"}):
            with pytest.raises(PrefixError, match="at most 4"):
                get_user_prefix()

    def test_invalid_git_prefix_raises(self):
        with patch.dict(os.environ, {"SKILL_ISSUES_PREFIX": ""}):
            with patch("skill_issues._get_git_config") as mock:
                mock.side_effect = lambda k: "x" if k == "skill-issues.prefix" else None
                with pytest.raises(PrefixError, match="at least 2"):
                    get_user_prefix()
