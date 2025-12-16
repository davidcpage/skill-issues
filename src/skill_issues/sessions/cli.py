"""CLI entry point for sessions command."""

import argparse
import json
import sys

from . import store


def main() -> int:
    """Entry point for the sessions command."""
    parser = argparse.ArgumentParser(
        description="Session memory tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sessions                         # Last session
  sessions view                    # Interactive TUI browser
  sessions --last 3                # Last 3 sessions
  sessions --open-questions        # All open questions
  sessions --create "feature-x" -l "Learned thing" -i "001,002"
"""
    )

    # Subcommand for TUI
    parser.add_argument("command", nargs="?", choices=["view"], help="Subcommand: view (interactive TUI)")

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

    # Handle view subcommand (TUI)
    if args.command == "view":
        from . import tui
        tui.run_app()
        return 0

    # Handle create command
    if args.create:
        issues_worked = args.issues.split(",") if args.issues else None
        session = store.create_session(
            topic=args.create,
            learnings=args.learning,
            open_questions=args.question,
            next_actions=args.action,
            issues_worked=issues_worked,
        )
        print(json.dumps(session, indent=2))
        return 0

    # Query commands
    sessions = store.load_sessions()

    if not sessions:
        print("[]")
        return 0

    # Handle markdown output (not JSON)
    if args.summary:
        print(store.generate_summary(sessions))
        return 0
    elif args.timeline:
        print(store.generate_timeline(sessions))
        return 0

    if args.all:
        output = sessions
    elif args.open_questions:
        output = store.aggregate_open_questions(sessions)
    elif args.next_actions:
        output = store.aggregate_next_actions(sessions)
    elif args.issue:
        output = store.filter_by_issue(sessions, args.issue)
    elif args.topic:
        output = store.filter_by_topic(sessions, args.topic)
    elif args.last:
        output = sessions[-args.last:]
    else:
        # Default: last session
        output = sessions[-1]

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
