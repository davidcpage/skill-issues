"""skill-issues: Local-first issue tracking and session memory for Claude Code."""

import os
import subprocess
import sys
from pathlib import Path

__version__ = "0.1.0"

# Override for project root (set via CLI --root or programmatically)
_project_root_override: Path | None = None


def set_project_root(path: Path | str | None) -> None:
    """Set an explicit project root override.

    This takes precedence over all other resolution methods.
    Call with None to clear the override.

    Args:
        path: Absolute path to use as project root, or None to clear.
    """
    global _project_root_override
    if path is None:
        _project_root_override = None
    else:
        _project_root_override = Path(path).resolve()


def find_project_root(data_dir_name: str = ".issues") -> Path:
    """Find the project root directory.

    Resolution order:
    1. Explicit override (set via set_project_root() or CLI --root)
    2. SKILL_ISSUES_ROOT environment variable
    3. Walk up from cwd looking for existing data directory (.issues or .sessions)
    4. Walk up from cwd looking for .git directory
    5. Fall back to current working directory

    Args:
        data_dir_name: The data directory to look for when walking up.
                      Defaults to ".issues" but can be ".sessions".

    Returns:
        Path to the project root directory.
    """
    # 1. Explicit override
    if _project_root_override is not None:
        return _project_root_override

    # 2. Environment variable
    env_root = os.environ.get("SKILL_ISSUES_ROOT", "").strip()
    if env_root:
        return Path(env_root).resolve()

    cwd = Path.cwd().resolve()

    # 3. Walk up looking for existing data directories
    # Check for both .issues and .sessions to find the nearest one
    current = cwd
    while True:
        if (current / ".issues").is_dir() or (current / ".sessions").is_dir():
            return current
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    # 4. Walk up looking for .git
    current = cwd
    while True:
        if (current / ".git").exists():
            return current
        parent = current.parent
        if parent == current:  # Reached filesystem root
            break
        current = parent

    # 5. Fall back to cwd
    return cwd


def get_project_root() -> Path:
    """Get the resolved project root.

    This is a convenience wrapper around find_project_root() that
    caches the result for the lifetime of the process.

    Returns:
        Path to the project root directory.
    """
    # Note: We don't cache because the override might change
    return find_project_root()


# File marker to track if we've shown the prefix hint in this project
def _get_hint_marker() -> Path:
    """Get the path to the prefix hint marker file."""
    return get_project_root() / ".sessions" / ".prefix-hint-shown"


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


def maybe_show_prefix_hint() -> None:
    """Show a one-time hint about derived prefix configuration.

    This displays on first use in a project when the prefix was derived
    from git config user.name rather than explicitly configured.

    The hint is non-blocking and only shown once per project.
    """
    hint_marker = _get_hint_marker()

    # Check if we've already shown the hint
    if hint_marker.exists():
        return

    prefix, was_derived = get_user_prefix()

    if not was_derived:
        return

    # Get the user.name for the message
    user_name = _get_git_config("user.name")

    # Create the marker file (and parent dir if needed)
    try:
        hint_marker.parent.mkdir(parents=True, exist_ok=True)
        hint_marker.touch()
    except OSError:
        # If we can't write the marker, still show the hint but it may repeat
        pass

    # Show the hint
    if user_name:
        print(
            f'Derived prefix "{prefix}" from git config user.name "{user_name}"',
            file=sys.stderr,
        )
    else:
        print(f'Using fallback prefix "{prefix}"', file=sys.stderr)

    print(
        'To customize: git config --global skill-issues.prefix "yourprefix"',
        file=sys.stderr,
    )
    print(file=sys.stderr)
