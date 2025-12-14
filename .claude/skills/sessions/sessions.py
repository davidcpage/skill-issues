#!/usr/bin/env python3
"""
Session memory tool with query and create commands.

Query:
    python3 sessions.py              # Last session (default)
    python3 sessions.py --last 3     # Last N sessions
    python3 sessions.py --all        # All sessions
    python3 sessions.py --issue 014  # Sessions that worked on issue
    python3 sessions.py --topic auth # Sessions matching topic
    python3 sessions.py --open-questions  # Aggregate open questions
    python3 sessions.py --next-actions    # Aggregate next actions

Create:
    python3 sessions.py --create "topic-slug" -l "learning1" -l "learning2"
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path

# Data file lives in project root, not with the skill
# Resolve project root from script location (.claude/skills/sessions/ -> 3 levels up)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SESSIONS_FILE = PROJECT_ROOT / ".memory/sessions.jsonl"


def ensure_data_file():
    """Create data directory and file if missing."""
    if not SESSIONS_FILE.parent.exists():
        SESSIONS_FILE.parent.mkdir(parents=True)
    if not SESSIONS_FILE.exists():
        SESSIONS_FILE.touch()


def load_sessions():
    """Read all sessions from JSONL file."""
    ensure_data_file()

    sessions = []
    for line in SESSIONS_FILE.read_text().splitlines():
        if not line.strip():
            continue
        sessions.append(json.loads(line))
    return sessions


def next_session_id(sessions):
    """Generate next session ID from existing sessions."""
    if not sessions:
        return "s001"

    # Extract numeric parts and find max
    max_num = 0
    for s in sessions:
        sid = s.get("id", "")
        if sid.startswith("s") and sid[1:].isdigit():
            max_num = max(max_num, int(sid[1:]))

    return f"s{max_num + 1:03d}"


def append_session(session):
    """Append a session to the JSONL file."""
    ensure_data_file()

    content = SESSIONS_FILE.read_text()
    # Ensure file ends with newline before appending
    if content and not content.endswith("\n"):
        content += "\n"

    # Compact JSON to save tokens
    line = json.dumps(session, separators=(",", ":"))
    SESSIONS_FILE.write_text(content + line + "\n")


def create_session(args):
    """Create a new session entry."""
    sessions = load_sessions()

    session = {
        "id": next_session_id(sessions),
        "date": date.today().isoformat(),
        "topic": args.create,
        "learnings": args.learning or [],
        "open_questions": args.question or [],
        "next_actions": args.action or [],
        "issues_worked": args.issues.split(",") if args.issues else []
    }

    append_session(session)
    print(json.dumps(session, indent=2))


def filter_by_issue(sessions, issue_id):
    """Return sessions that worked on a specific issue."""
    return [s for s in sessions if issue_id in s.get("issues_worked", [])]


def filter_by_topic(sessions, keyword):
    """Return sessions with topic containing keyword (case-insensitive)."""
    keyword = keyword.lower()
    return [s for s in sessions if keyword in s.get("topic", "").lower()]


def aggregate_open_questions(sessions):
    """Return unique open questions across all sessions."""
    questions = []
    seen = set()
    for s in sessions:
        for q in s.get("open_questions", []):
            if q not in seen:
                questions.append(q)
                seen.add(q)
    return questions


def aggregate_next_actions(sessions):
    """Return all next actions across all sessions (most recent first)."""
    actions = []
    for s in reversed(sessions):
        for a in s.get("next_actions", []):
            actions.append({"session": s["id"], "date": s["date"], "action": a})
    return actions


def generate_timeline(sessions):
    """Generate markdown timeline of sessions."""
    if not sessions:
        return "No sessions recorded yet."

    lines = ["## Session Timeline", ""]

    # Group sessions by date
    by_date = {}
    for s in sessions:
        date = s.get("date", "unknown")
        by_date.setdefault(date, []).append(s)

    for date in sorted(by_date.keys(), reverse=True):
        lines.append(f"### {date}")
        lines.append("")

        for s in by_date[date]:
            sid = s.get("id", "?")
            topic = s.get("topic", "untitled")
            learnings = len(s.get("learnings", []))
            questions = len(s.get("open_questions", []))
            issues = s.get("issues_worked", [])

            # Format: **s001** topic-name (3 learnings, 2 issues)
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


def generate_summary(sessions):
    """Generate comprehensive markdown summary for documentation."""
    if not sessions:
        return "No sessions recorded yet."

    lines = ["## Project Session Summary", ""]

    # Overview stats
    dates = [s.get("date") for s in sessions if s.get("date")]
    all_learnings = []
    all_questions = []
    all_issues = set()

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

    # Timeline (compact)
    lines.append("### Timeline")
    lines.append("")

    by_date = {}
    for s in sessions:
        date = s.get("date", "unknown")
        by_date.setdefault(date, []).append(s)

    for date in sorted(by_date.keys()):
        topics = [s.get("topic", "?") for s in by_date[date]]
        count = len(topics)
        topic_preview = ", ".join(topics[:3])
        if len(topics) > 3:
            topic_preview += f" (+{len(topics)-3} more)"
        lines.append(f"- **{date}** ({count} session{'s' if count != 1 else ''}): {topic_preview}")

    lines.append("")

    # Key learnings (sample from each session)
    lines.append("### Key Learnings")
    lines.append("")

    # Get first learning from each session as highlights
    for s in sessions[-10:]:  # Last 10 sessions
        learnings = s.get("learnings", [])
        if learnings:
            topic = s.get("topic", "?")
            # First learning as highlight
            lines.append(f"- **{topic}:** {learnings[0]}")

    lines.append("")

    # Open questions (deduplicated)
    unique_questions = []
    seen = set()
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


def main():
    parser = argparse.ArgumentParser(
        description="Session memory tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 sessions.py                    # Last session
  python3 sessions.py --last 3           # Last 3 sessions
  python3 sessions.py --open-questions   # All open questions
  python3 sessions.py --create "feature-x" -l "Learned thing" -i "001,002"
"""
    )

    # Query options (mutually exclusive group)
    query = parser.add_mutually_exclusive_group()
    query.add_argument("--all", action="store_true", help="Show all sessions")
    query.add_argument("--last", type=int, metavar="N", help="Show last N sessions")
    query.add_argument("--issue", metavar="ID", help="Sessions that worked on issue ID")
    query.add_argument("--topic", metavar="KEYWORD", help="Sessions with topic containing keyword")
    query.add_argument("--open-questions", action="store_true", help="Aggregate all open questions")
    query.add_argument("--next-actions", action="store_true", help="Aggregate all next actions")
    query.add_argument("--summary", action="store_true", help="Generate markdown summary for documentation")
    query.add_argument("--timeline", action="store_true", help="Generate markdown timeline of sessions")

    # Create command
    query.add_argument("--create", metavar="TOPIC", help="Create a new session with given topic")

    # Create options (only used with --create)
    parser.add_argument("-l", "--learning", action="append", metavar="TEXT",
                        help="Add a learning (can be repeated)")
    parser.add_argument("-q", "--question", action="append", metavar="TEXT",
                        help="Add an open question (can be repeated)")
    parser.add_argument("-a", "--action", action="append", metavar="TEXT",
                        help="Add a next action (can be repeated)")
    parser.add_argument("-i", "--issues", metavar="IDS",
                        help="Comma-separated list of issue IDs worked on")

    args = parser.parse_args()

    # Handle create command
    if args.create:
        create_session(args)
        return

    # Query commands
    sessions = load_sessions()

    if not sessions:
        print("[]")
        return

    # Handle markdown output (not JSON)
    if args.summary:
        print(generate_summary(sessions))
        return
    elif args.timeline:
        print(generate_timeline(sessions))
        return

    if args.all:
        output = sessions
    elif args.open_questions:
        output = aggregate_open_questions(sessions)
    elif args.next_actions:
        output = aggregate_next_actions(sessions)
    elif args.issue:
        output = filter_by_issue(sessions, args.issue)
    elif args.topic:
        output = filter_by_topic(sessions, args.topic)
    elif args.last:
        output = sessions[-args.last:]
    else:
        # Default: last session
        output = sessions[-1]

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
