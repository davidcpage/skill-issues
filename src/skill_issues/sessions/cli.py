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
  sessions board                   # Interactive TUI browser
  sessions --last 3                # Last 3 sessions
  sessions --open-questions        # All open questions
  sessions --create "feature-x" -l "Learned thing" -i "001,002"
  sessions --amend -l "Another learning"      # Amend last session
  sessions --amend s041 -l "Learning"         # Amend specific session
"""
    )

    # Subcommands
    parser.add_argument("command", nargs="?", choices=["board", "init"], help="Subcommand: board (TUI), init (setup skill)")
    parser.add_argument("init_path", nargs="?", help="Project path for init (default: current directory)")

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

    # Amend command
    query.add_argument("--amend", nargs="?", const=True, metavar="ID",
                       help="Amend a session (last session if no ID given)")

    # Options for --create and --amend
    parser.add_argument("-l", "--learning", action="append", metavar="TEXT",
                        help="Add a learning (can be repeated)")
    parser.add_argument("-q", "--question", action="append", metavar="TEXT",
                        help="Add an open question (can be repeated)")
    parser.add_argument("-a", "--action", action="append", metavar="TEXT",
                        help="Add a next action (can be repeated)")
    parser.add_argument("-i", "--issues", metavar="IDS",
                        help="Comma-separated list of issue IDs worked on")

    args = parser.parse_args()

    # Handle board subcommand (TUI)
    if args.command == "board":
        from . import tui
        tui.run_app()
        return 0

    # Handle init subcommand
    if args.command == "init":
        from .. import init as init_module
        return init_module.run_init(["sessions"], args.init_path)

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

    # Handle amend command
    if args.amend:
        # Check if anything to amend
        if not any([args.learning, args.question, args.action, args.issues]):
            print("Error: --amend requires at least one of -l, -q, -a, or -i", file=sys.stderr)
            return 1

        # args.amend is True (no ID) or a string (session ID)
        session_id = None if args.amend is True else args.amend
        issues_worked = args.issues.split(",") if args.issues else None

        session = store.amend_session(
            session_id=session_id,
            learnings=args.learning,
            open_questions=args.question,
            next_actions=args.action,
            issues_worked=issues_worked,
        )

        if session is None:
            if session_id:
                print(f"Error: Session '{session_id}' not found", file=sys.stderr)
            else:
                print("Error: No sessions exist yet. Use --create first.", file=sys.stderr)
            return 1

        # Build summary of what was added
        added = []
        if args.learning:
            n = len(args.learning)
            added.append(f"{n} learning{'s' if n != 1 else ''}")
        if args.question:
            n = len(args.question)
            added.append(f"{n} question{'s' if n != 1 else ''}")
        if args.action:
            n = len(args.action)
            added.append(f"{n} action{'s' if n != 1 else ''}")
        if args.issues:
            n = len(issues_worked)
            added.append(f"{n} issue{'s' if n != 1 else ''}")

        print(f"Amended session {session['id']}: added {', '.join(added)}")
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
