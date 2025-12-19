"""
Sessions store layer - data operations for session memory.

This module handles all data persistence and querying for sessions.
It can be imported independently of the CLI.
"""

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from skill_issues import get_user_prefix

# Data file lives in project root (current working directory)
PROJECT_ROOT = Path.cwd()
SESSIONS_DIR = PROJECT_ROOT / ".sessions"
SESSIONS_FILE = SESSIONS_DIR / "events.jsonl"

# Legacy paths for migration
LEGACY_DIR = PROJECT_ROOT / ".memory"
LEGACY_FILE = LEGACY_DIR / "sessions.jsonl"


def _migrate_if_needed() -> None:
    """Migrate from old .memory/sessions.jsonl to new .sessions/events.jsonl."""
    if LEGACY_FILE.exists() and not SESSIONS_FILE.exists():
        # Create new directory
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        # Move the file
        LEGACY_FILE.rename(SESSIONS_FILE)
        # Remove old directory if empty
        if LEGACY_DIR.exists() and not any(LEGACY_DIR.iterdir()):
            LEGACY_DIR.rmdir()
        print(f"Migrated {LEGACY_DIR}/ to {SESSIONS_DIR}/")


def ensure_data_file() -> None:
    """Create data directory and file if missing."""
    _migrate_if_needed()
    if not SESSIONS_DIR.exists():
        SESSIONS_DIR.mkdir(parents=True)
    if not SESSIONS_FILE.exists():
        SESSIONS_FILE.touch()


def load_sessions() -> list[dict[str, Any]]:
    """Read all sessions from JSONL file."""
    ensure_data_file()

    sessions = []
    for line in SESSIONS_FILE.read_text().splitlines():
        if not line.strip():
            continue
        sessions.append(json.loads(line))
    return sessions


def parse_session_id(session_id: str) -> tuple[str | None, int | None]:
    """Parse a session ID into (prefix, number).

    Handles both old format (s001) and new format (dp-s001).

    Returns:
        Tuple of (prefix, number). prefix is None for old-format IDs.
        Returns (None, None) if the ID doesn't match any known format.
    """
    # New format: prefix-sNNN (e.g., dp-s001)
    new_match = re.match(r"^([a-z0-9]{2,4})-s(\d+)$", session_id)
    if new_match:
        return (new_match.group(1), int(new_match.group(2)))

    # Old format: sNNN (e.g., s001)
    old_match = re.match(r"^s(\d+)$", session_id)
    if old_match:
        return (None, int(old_match.group(1)))

    return (None, None)


def next_session_id(sessions: list[dict[str, Any]], prefix: str | None = None) -> str:
    """Generate next session ID for the current user.

    Args:
        sessions: List of all sessions.
        prefix: User prefix to use. If None, uses get_user_prefix().

    Returns:
        Next session ID in format "prefix-sNNN" (e.g., "dp-s001").
    """
    if prefix is None:
        prefix, _ = get_user_prefix()

    # Find max number for this user's sessions
    max_num = 0
    for s in sessions:
        sid = s.get("id", "")
        parsed_prefix, num = parse_session_id(sid)
        if parsed_prefix == prefix and num is not None:
            max_num = max(max_num, num)

    return f"{prefix}-s{max_num + 1:03d}"


def append_session(session: dict[str, Any]) -> None:
    """Append a session to the JSONL file."""
    ensure_data_file()

    content = SESSIONS_FILE.read_text()
    if content and not content.endswith("\n"):
        content += "\n"

    line = json.dumps(session, separators=(",", ":"))
    SESSIONS_FILE.write_text(content + line + "\n")


def create_session(
    topic: str,
    learnings: list[str] | None = None,
    open_questions: list[str] | None = None,
    next_actions: list[str] | None = None,
    issues_worked: list[str] | None = None,
) -> dict[str, Any]:
    """Create a new session entry and return it."""
    sessions = load_sessions()
    prefix, _ = get_user_prefix()

    session = {
        "id": next_session_id(sessions, prefix),
        "user": prefix,
        "date": date.today().isoformat(),
        "topic": topic,
        "learnings": learnings or [],
        "open_questions": open_questions or [],
        "next_actions": next_actions or [],
        "issues_worked": issues_worked or [],
    }

    append_session(session)
    return session


def amend_session(
    session_id: str | None = None,
    learnings: list[str] | None = None,
    open_questions: list[str] | None = None,
    next_actions: list[str] | None = None,
    issues_worked: list[str] | None = None,
) -> dict[str, Any] | None:
    """Amend an existing session by appending to its arrays.

    Args:
        session_id: Session ID to amend, or None for the most recent session.
        learnings: Learnings to add.
        open_questions: Questions to add.
        next_actions: Actions to add.
        issues_worked: Issue IDs to add.

    Returns:
        The amended session, or None if no sessions exist or ID not found.
    """
    sessions = load_sessions()
    if not sessions:
        return None

    # Find the session to amend
    if session_id is None:
        target_idx = len(sessions) - 1
    else:
        target_idx = None
        for i, s in enumerate(sessions):
            if s.get("id") == session_id:
                target_idx = i
                break
        if target_idx is None:
            return None

    session = sessions[target_idx]

    # Append to array fields
    if learnings:
        session["learnings"] = session.get("learnings", []) + learnings
    if open_questions:
        session["open_questions"] = session.get("open_questions", []) + open_questions
    if next_actions:
        session["next_actions"] = session.get("next_actions", []) + next_actions
    if issues_worked:
        existing = session.get("issues_worked", [])
        # Avoid duplicates for issue IDs
        for issue_id in issues_worked:
            if issue_id not in existing:
                existing.append(issue_id)
        session["issues_worked"] = existing

    # Rewrite the file
    _rewrite_sessions(sessions)
    return session


def _rewrite_sessions(sessions: list[dict[str, Any]]) -> None:
    """Rewrite the entire sessions file."""
    ensure_data_file()
    lines = [json.dumps(s, separators=(",", ":")) for s in sessions]
    SESSIONS_FILE.write_text("\n".join(lines) + "\n" if lines else "")


# --- Filter functions ---

def filter_by_user(sessions: list[dict[str, Any]], user: str | None = None) -> list[dict[str, Any]]:
    """Return sessions for a specific user.

    Args:
        sessions: List of sessions to filter.
        user: User prefix to filter by. If None, uses current user from get_user_prefix().

    Returns:
        Sessions belonging to the specified user.
    """
    if user is None:
        user, _ = get_user_prefix()

    result = []
    for s in sessions:
        # Check explicit user field first
        if s.get("user") == user:
            result.append(s)
        # Fall back to parsing ID for legacy sessions
        elif "user" not in s:
            parsed_prefix, _ = parse_session_id(s.get("id", ""))
            if parsed_prefix == user:
                result.append(s)
    return result


def filter_by_issue(sessions: list[dict[str, Any]], issue_id: str) -> list[dict[str, Any]]:
    """Return sessions that worked on a specific issue."""
    return [s for s in sessions if issue_id in s.get("issues_worked", [])]


def filter_by_topic(sessions: list[dict[str, Any]], keyword: str) -> list[dict[str, Any]]:
    """Return sessions with topic containing keyword (case-insensitive)."""
    keyword = keyword.lower()
    return [s for s in sessions if keyword in s.get("topic", "").lower()]


# --- Aggregation functions ---

def aggregate_open_questions(sessions: list[dict[str, Any]]) -> list[str]:
    """Return unique open questions across all sessions."""
    questions = []
    seen: set[str] = set()
    for s in sessions:
        for q in s.get("open_questions", []):
            if q not in seen:
                questions.append(q)
                seen.add(q)
    return questions


def aggregate_next_actions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return all next actions across all sessions (most recent first)."""
    actions = []
    for s in reversed(sessions):
        for a in s.get("next_actions", []):
            actions.append({"session": s["id"], "date": s["date"], "action": a})
    return actions


# --- Markdown generation ---

def generate_timeline(sessions: list[dict[str, Any]]) -> str:
    """Generate markdown timeline of sessions."""
    if not sessions:
        return "No sessions recorded yet."

    lines = ["## Session Timeline", ""]

    by_date: dict[str, list[dict[str, Any]]] = {}
    for s in sessions:
        d = s.get("date", "unknown")
        by_date.setdefault(d, []).append(s)

    for d in sorted(by_date.keys(), reverse=True):
        lines.append(f"### {d}")
        lines.append("")

        for s in by_date[d]:
            sid = s.get("id", "?")
            topic = s.get("topic", "untitled")
            learnings = len(s.get("learnings", []))
            questions = len(s.get("open_questions", []))
            issues = s.get("issues_worked", [])

            stats = []
            if learnings:
                stats.append(f"{learnings} learning{'s' if learnings != 1 else ''}")
            if questions:
                stats.append(f"{questions} question{'s' if questions != 1 else ''}")
            if issues:
                stats.append(f"{len(issues)} issue{'s' if len(issues) != 1 else ''}")

            stat_str = f" ({', '.join(stats)})" if stats else ""
            lines.append(f"- **{sid}** {topic}{stat_str}")

        lines.append("")

    return "\n".join(lines)


def generate_summary(sessions: list[dict[str, Any]]) -> str:
    """Generate comprehensive markdown summary for documentation."""
    if not sessions:
        return "No sessions recorded yet."

    lines = ["## Project Session Summary", ""]

    dates = [s.get("date") for s in sessions if s.get("date")]
    all_learnings: list[str] = []
    all_questions: list[str] = []
    all_issues: set[str] = set()

    for s in sessions:
        all_learnings.extend(s.get("learnings", []))
        all_questions.extend(s.get("open_questions", []))
        all_issues.update(s.get("issues_worked", []))

    lines.append("### Overview")
    lines.append("")
    if dates:
        lines.append(f"- **Period:** {min(dates)} to {max(dates)}")
    lines.append(f"- **Sessions:** {len(sessions)}")
    lines.append(f"- **Total learnings:** {len(all_learnings)}")
    lines.append(f"- **Issues touched:** {len(all_issues)}")
    lines.append("")

    lines.append("### Timeline")
    lines.append("")

    by_date: dict[str, list[dict[str, Any]]] = {}
    for s in sessions:
        d = s.get("date", "unknown")
        by_date.setdefault(d, []).append(s)

    for d in sorted(by_date.keys()):
        topics = [s.get("topic", "?") for s in by_date[d]]
        count = len(topics)
        topic_preview = ", ".join(topics[:3])
        if len(topics) > 3:
            topic_preview += f" (+{len(topics)-3} more)"
        lines.append(f"- **{d}** ({count} session{'s' if count != 1 else ''}): {topic_preview}")

    lines.append("")

    lines.append("### Key Learnings")
    lines.append("")

    for s in sessions[-10:]:
        learnings = s.get("learnings", [])
        if learnings:
            topic = s.get("topic", "?")
            lines.append(f"- **{topic}:** {learnings[0]}")

    lines.append("")

    unique_questions: list[str] = []
    seen: set[str] = set()
    for s in sessions:
        for q in s.get("open_questions", []):
            if q not in seen:
                unique_questions.append(q)
                seen.add(q)

    if unique_questions:
        lines.append("### Open Questions")
        lines.append("")
        for q in unique_questions:
            lines.append(f"- {q}")
        lines.append("")

    return "\n".join(lines)
