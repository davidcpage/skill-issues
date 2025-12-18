"""CLI entry point for issues command."""

import argparse
import json
import sys

from . import store


def parse_list_arg(value: str) -> list[str] | None:
    """Parse comma-separated list argument."""
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def looks_like_issue_id(arg: str) -> bool:
    """Check if an argument looks like an issue ID (3-digit number)."""
    return arg.isdigit() and len(arg) == 3


def main() -> int:
    """Entry point for the issues command."""
    # Check if first positional argument looks like an issue ID
    # If so, don't add subparsers to avoid conflict
    has_issue_id_arg = False
    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            continue
        # First positional argument found
        if looks_like_issue_id(arg):
            has_issue_id_arg = True
        break

    parser = argparse.ArgumentParser(
        description="Append-only issue tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Only add subcommands if we're not handling issue IDs
    if not has_issue_id_arg:
        subparsers = parser.add_subparsers(dest="subcommand")
        subparsers.add_parser("board", help="Open interactive Kanban board TUI")

        init_parser = subparsers.add_parser("init", help="Initialize skills in a project")
        init_parser.add_argument("path", nargs="?", help="Project path (default: current directory)")
        init_parser.add_argument("--all", "-a", action="store_true", help="Install all skills (issues, sessions, adr)")
        init_parser.add_argument("--update", "-u", action="store_true", help="Overwrite existing SKILL.md files")

        # Write subcommands (aliases for --create, --close, --note, etc.)
        create_parser = subparsers.add_parser("create", help="Create a new issue")
        create_parser.add_argument("title", help="Issue title")
        create_parser.add_argument("--type", "-t", choices=["bug", "feature", "task"], default="task",
                                   help="Issue type (default: task)")
        create_parser.add_argument("--priority", "-p", type=int, choices=[0, 1, 2, 3, 4], default=2,
                                   help="Priority 0=critical to 4=backlog (default: 2)")
        create_parser.add_argument("--description", "-d", default="", help="Issue description")
        create_parser.add_argument("--depends-on", "-b", default="", help="Comma-separated dependency IDs")
        create_parser.add_argument("--labels", "-l", default="", help="Comma-separated labels")

        close_parser = subparsers.add_parser("close", help="Close an issue")
        close_parser.add_argument("id", help="Issue ID to close")
        close_parser.add_argument("reason", help="Reason for closing")

        note_parser = subparsers.add_parser("note", help="Add a note to an issue")
        note_parser.add_argument("id", help="Issue ID")
        note_parser.add_argument("content", help="Note content")

        add_dep_parser = subparsers.add_parser("add-dep", help="Add dependencies to an issue")
        add_dep_parser.add_argument("id", help="Issue ID")
        add_dep_parser.add_argument("dep_ids", help="Comma-separated dependency IDs to add")

        remove_dep_parser = subparsers.add_parser("remove-dep", help="Remove dependencies from an issue")
        remove_dep_parser.add_argument("id", help="Issue ID")
        remove_dep_parser.add_argument("dep_ids", help="Comma-separated dependency IDs to remove")

    # Positional argument for issue ID(s) (implicit --show)
    parser.add_argument("issue_ids", nargs="*", metavar="ID", help="Issue ID(s) to show (shorthand for --show)")

    # Query flags (mutually exclusive with write commands)
    query_group = parser.add_mutually_exclusive_group()
    query_group.add_argument("--all", action="store_true", help="Show all issues including closed")
    query_group.add_argument("--open", action="store_true", help="Show all open issues (default)")
    query_group.add_argument("--closed", action="store_true", help="Show closed issues")
    query_group.add_argument("--ready", action="store_true", help="Show open issues not blocked")
    query_group.add_argument("--show", metavar="ID", help="Show details of a single issue")
    query_group.add_argument("--diagram", nargs="?", const="mermaid", choices=["mermaid", "ascii"],
                             metavar="FORMAT", help="Generate dependency diagram (mermaid or ascii, default: mermaid)")

    # Write commands
    parser.add_argument("--create", metavar="TITLE", help="Create a new issue with the given title")
    parser.add_argument("--close", nargs=2, metavar=("ID", "REASON"), help="Close an issue")
    parser.add_argument("--note", nargs=2, metavar=("ID", "CONTENT"), help="Add a note to an issue")
    parser.add_argument("--add-dep", nargs=2, metavar=("ID", "DEP_IDS"), help="Add dependencies to an issue (comma-separated IDs)")
    parser.add_argument("--remove-dep", nargs=2, metavar=("ID", "DEP_IDS"), help="Remove dependencies from an issue (comma-separated IDs)")

    # Diagram options
    parser.add_argument("--include-closed", action="store_true",
                        help="Include closed issues in diagram (only used with --diagram)")

    # Create options
    parser.add_argument("--type", "-t", choices=["bug", "feature", "task"], default="task",
                        help="Issue type (default: task)")
    parser.add_argument("--priority", "-p", type=int, choices=[0, 1, 2, 3, 4], default=2,
                        help="Priority 0=critical to 4=backlog (default: 2)")
    parser.add_argument("--description", "-d", default="", help="Issue description")
    parser.add_argument("--depends-on", "-b", default="", help="Comma-separated list of dependency issue IDs")
    parser.add_argument("--labels", "-l", default="", help="Comma-separated list of labels")

    args = parser.parse_args()

    # Handle subcommands
    subcommand = getattr(args, "subcommand", None)
    if subcommand == "board":
        from . import tui
        tui.run_app()
        return 0

    if subcommand == "init":
        from .. import init as init_module
        if getattr(args, "all", False):
            skills = ["issues", "sessions", "adr"]
        else:
            skills = ["issues"]
        return init_module.run_init(
            skills,
            getattr(args, "path", None),
            update=getattr(args, "update", False),
        )

    if subcommand == "create":
        depends_on = parse_list_arg(getattr(args, "depends_on", ""))
        labels = parse_list_arg(getattr(args, "labels", ""))
        try:
            new_id = store.create_issue(
                title=args.title,
                issue_type=getattr(args, "type", "task"),
                priority=getattr(args, "priority", 2),
                description=getattr(args, "description", ""),
                depends_on=depends_on,
                labels=labels,
            )
            print(json.dumps({"created": new_id}))
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    if subcommand == "close":
        try:
            store.close_issue(args.id, args.reason)
            print(json.dumps({"closed": args.id}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    if subcommand == "note":
        try:
            store.add_note(args.id, args.content)
            print(json.dumps({"noted": args.id}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    if subcommand == "add-dep":
        dep_ids = parse_list_arg(args.dep_ids)
        if not dep_ids:
            print(json.dumps({"error": "No dependency IDs provided"}), file=sys.stderr)
            return 1
        try:
            added = store.add_dependency(args.id, dep_ids)
            print(json.dumps({"issue": args.id, "added_deps": added}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    if subcommand == "remove-dep":
        dep_ids = parse_list_arg(args.dep_ids)
        if not dep_ids:
            print(json.dumps({"error": "No dependency IDs provided"}), file=sys.stderr)
            return 1
        try:
            removed = store.remove_dependency(args.id, dep_ids)
            print(json.dumps({"issue": args.id, "removed_deps": removed}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    # Handle write commands (flag syntax - kept for backward compatibility)
    if args.create:
        depends_on = parse_list_arg(args.depends_on)
        labels = parse_list_arg(args.labels)
        try:
            new_id = store.create_issue(
                title=args.create,
                issue_type=args.type,
                priority=args.priority,
                description=args.description,
                depends_on=depends_on,
                labels=labels,
            )
            print(json.dumps({"created": new_id}))
        except Exception as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    if args.close:
        issue_id, reason = args.close
        try:
            store.close_issue(issue_id, reason)
            print(json.dumps({"closed": issue_id}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    if args.note:
        issue_id, content = args.note
        try:
            store.add_note(issue_id, content)
            print(json.dumps({"noted": issue_id}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    if args.add_dep:
        issue_id, dep_ids_str = args.add_dep
        dep_ids = parse_list_arg(dep_ids_str)
        if not dep_ids:
            print(json.dumps({"error": "No dependency IDs provided"}), file=sys.stderr)
            return 1
        try:
            added = store.add_dependency(issue_id, dep_ids)
            print(json.dumps({"issue": issue_id, "added_deps": added}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    if args.remove_dep:
        issue_id, dep_ids_str = args.remove_dep
        dep_ids = parse_list_arg(dep_ids_str)
        if not dep_ids:
            print(json.dumps({"error": "No dependency IDs provided"}), file=sys.stderr)
            return 1
        try:
            removed = store.remove_dependency(issue_id, dep_ids)
            print(json.dumps({"issue": issue_id, "removed_deps": removed}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            return 1
        return 0

    # Handle query commands
    all_issues = store.load_issues()

    # Handle --show (single issue)
    if args.show:
        if args.show not in all_issues:
            print(json.dumps({"error": f"Issue {args.show} not found"}), file=sys.stderr)
            return 1
        print(json.dumps(all_issues[args.show], indent=2))
        return 0

    # Handle positional issue IDs (one or more)
    if args.issue_ids:
        # Check all IDs exist first
        missing = [id for id in args.issue_ids if id not in all_issues]
        if missing:
            print(json.dumps({"error": f"Issue(s) not found: {', '.join(missing)}"}), file=sys.stderr)
            return 1
        # Single ID: return object (backward compatible)
        if len(args.issue_ids) == 1:
            print(json.dumps(all_issues[args.issue_ids[0]], indent=2))
        else:
            # Multiple IDs: return array
            results = [all_issues[id] for id in args.issue_ids]
            print(json.dumps(results, indent=2))
        return 0

    # Handle diagram output
    if args.diagram:
        include_closed = getattr(args, 'include_closed', False)
        if args.diagram == "ascii":
            print(store.generate_ascii_diagram(all_issues, all_issues, include_closed=include_closed))
        else:
            print(store.generate_mermaid_diagram(all_issues, all_issues, include_closed=include_closed))
        return 0

    if args.all:
        output = all_issues
    elif args.closed:
        output = store.filter_closed(all_issues)
    elif args.ready:
        output = store.filter_ready(all_issues, all_issues)
    else:
        # Default (no flags or --open): show open issues
        output = store.filter_open(all_issues)

    # Sort by priority, then by id
    sorted_issues = sorted(output.values(), key=lambda x: (x.get("priority", 2), x["id"]))

    print(json.dumps(sorted_issues, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
