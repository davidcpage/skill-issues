"""skill-issues: Local-first issue tracking and session memory for Claude Code."""

import os
import subprocess

__version__ = "0.1.0"


class PrefixError(Exception):
    """Raised when user prefix is invalid."""

    pass


def _get_git_config(key: str) -> str | None:
    """Get a git config value, returning None if not set or git unavailable."""
    try:
        result = subprocess.run(
            ["git", "config", "--get", key],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def _derive_prefix_from_name(name: str) -> str | None:
    """Derive a 2-letter prefix from a full name (first + last initials).

    Examples:
        "David Page" -> "dp"
        "Alice" -> None (need at least 2 words)
        "Jean-Pierre Dupont" -> "jd"
    """
    parts = name.split()
    if len(parts) < 2:
        return None
    first_initial = parts[0][0].lower()
    last_initial = parts[-1][0].lower()
    return first_initial + last_initial


def _validate_prefix(prefix: str) -> str:
    """Validate and normalize a prefix.

    Args:
        prefix: The prefix to validate.

    Returns:
        The normalized (lowercase) prefix.

    Raises:
        PrefixError: If prefix is invalid.
    """
    if not prefix:
        raise PrefixError("Prefix cannot be empty")

    prefix = prefix.lower().strip()

    if not prefix:
        raise PrefixError("Prefix cannot be empty or whitespace only")

    if len(prefix) < 2:
        raise PrefixError(f"Prefix must be at least 2 characters, got '{prefix}'")

    if len(prefix) > 4:
        raise PrefixError(f"Prefix must be at most 4 characters, got '{prefix}'")

    if not prefix.isalnum():
        raise PrefixError(f"Prefix must be alphanumeric, got '{prefix}'")

    return prefix


def get_user_prefix() -> tuple[str, bool]:
    """Get the user prefix for issue/session IDs.

    Resolution order:
    1. SKILL_ISSUES_PREFIX environment variable
    2. git config skill-issues.prefix
    3. Derived from git config user.name (first + last initials)
    4. Fallback to "xx"

    Returns:
        A tuple of (prefix, was_derived) where was_derived is True if the
        prefix was derived from user.name rather than explicitly configured.

    Raises:
        PrefixError: If an explicitly configured prefix is invalid.
    """
    # 1. Environment variable (highest priority)
    env_prefix = os.environ.get("SKILL_ISSUES_PREFIX", "").strip()
    if env_prefix:
        return (_validate_prefix(env_prefix), False)

    # 2. Git config skill-issues.prefix
    git_prefix = _get_git_config("skill-issues.prefix")
    if git_prefix:
        return (_validate_prefix(git_prefix), False)

    # 3. Derive from git config user.name
    user_name = _get_git_config("user.name")
    if user_name:
        derived = _derive_prefix_from_name(user_name)
        if derived:
            return (derived, True)

    # 4. Fallback
    return ("xx", True)
