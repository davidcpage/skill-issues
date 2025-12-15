#!/usr/bin/env python3
"""
Append-only issue tracker tool.

Reads events.jsonl, reconstructs issue state, outputs filtered JSON.
Also supports writing events via --create, --close, --note, --block, and --unblock commands.

Usage:
    python3 .claude/skills/issues/issues.py              # Open issues (default)
    python3 .claude/skills/issues/issues.py --all        # All issues
    python3 .claude/skills/issues/issues.py --ready      # Open and not blocked
    python3 .claude/skills/issues/issues.py --show ID    # Show single issue details
    python3 .claude/skills/issues/issues.py --create "Title" [options]
    python3 .claude/skills/issues/issues.py --close ID "Reason"
    python3 .claude/skills/issues/issues.py --note ID "Content"
    python3 .claude/skills/issues/issues.py --block ID "BLOCKER_IDS"
    python3 .claude/skills/issues/issues.py --unblock ID "BLOCKER_IDS"
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Data file lives in project root, not with the skill
# Resolve project root from script location (.claude/skills/issues/ -> 3 levels up)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
EVENTS_FILE = PROJECT_ROOT / ".issues/events.jsonl"


def ensure_data_file():
    """Create data directory and file if missing."""
    if not EVENTS_FILE.parent.exists():
        EVENTS_FILE.parent.mkdir(parents=True)
    if not EVENTS_FILE.exists():
        EVENTS_FILE.touch()


def load_issues():
    """Read events and reconstruct current state of all issues."""
    ensure_data_file()
    issues = {}

    for line in EVENTS_FILE.read_text().splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        issue_id = event["id"]
        event_type = event["type"]

        if event_type == "created":
            issues[issue_id] = {
                "id": issue_id,
                "title": event["title"],
                "type": event.get("issue_type", "task"),
                "priority": event.get("priority", 2),
                "description": event.get("description", ""),
                "blocked_by": event.get("blocked_by", []),
                "labels": event.get("labels", []),
                "created": event["ts"],
                "status": "open",
                "notes": [],
                "updates": [],
            }
        elif event_type == "updated":
            if issue_id in issues:
                # Track the update in history
                update_record = {"ts": event["ts"]}
                if "reason" in event:
                    update_record["reason"] = event["reason"]
                # Apply mutable field changes
                for field in ["priority", "blocked_by", "labels"]:
                    if field in event:
                        update_record[field] = {"from": issues[issue_id].get(field), "to": event[field]}
                        issues[issue_id][field] = event[field]
                issues[issue_id]["updates"].append(update_record)
        elif event_type == "note":
            if issue_id in issues:
                issues[issue_id]["notes"].append({
                    "ts": event["ts"],
                    "content": event.get("content", ""),
                })
        elif event_type == "closed":
            if issue_id in issues:
                issues[issue_id]["status"] = "closed"
                issues[issue_id]["closed_reason"] = event.get("reason", "")
                issues[issue_id]["closed_at"] = event["ts"]

    return issues


def filter_open(issues):
    """Return only open issues."""
    return {k: v for k, v in issues.items() if v["status"] == "open"}


def filter_ready(issues, all_issues):
    """Return open issues not blocked by other open issues."""
    open_ids = set(filter_open(all_issues).keys())
    ready = {}
    for k, v in issues.items():
        if v["status"] != "open":
            continue
        blockers = set(v.get("blocked_by", []))
        open_blockers = blockers & open_ids
        if not open_blockers:
            ready[k] = v
    return ready


def get_timestamp():
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def next_id(issues):
    """Return next available issue ID (zero-padded 3 digits)."""
    if not issues:
        return "001"
    max_id = max(int(i) for i in issues.keys())
    return f"{max_id + 1:03d}"


def append_event(event):
    """Append a JSON event to the events file."""
    ensure_data_file()
    # Ensure file ends with newline before appending
    content = EVENTS_FILE.read_text()
    needs_newline = content and not content.endswith("\n")
    with open(EVENTS_FILE, "a") as f:
        if needs_newline:
            f.write("\n")
        f.write(json.dumps(event, separators=(",", ":")) + "\n")


def create_issue(title, issue_type="task", priority=2, description="", blocked_by=None, labels=None):
    """Create a new issue and return its ID."""
    issues = load_issues()
    new_id = next_id(issues)

    event = {
        "ts": get_timestamp(),
        "type": "created",
        "id": new_id,
        "title": title,
        "issue_type": issue_type,
        "priority": priority,
    }

    if description:
        event["description"] = description
    if blocked_by:
        event["blocked_by"] = blocked_by
    if labels:
        event["labels"] = labels

    append_event(event)
    return new_id


def close_issue(issue_id, reason):
    """Close an issue with a reason."""
    issues = load_issues()

    if issue_id not in issues:
        raise ValueError(f"Issue {issue_id} not found")
    if issues[issue_id]["status"] == "closed":
        raise ValueError(f"Issue {issue_id} is already closed")

    event = {
        "ts": get_timestamp(),
        "type": "closed",
        "id": issue_id,
        "reason": reason,
    }

    append_event(event)


def add_note(issue_id, content):
    """Add a note to an issue."""
    issues = load_issues()

    if issue_id not in issues:
        raise ValueError(f"Issue {issue_id} not found")

    event = {
        "ts": get_timestamp(),
        "type": "note",
        "id": issue_id,
        "content": content,
    }

    append_event(event)


def block_issue(issue_id, blocker_ids):
    """Add blockers to an issue."""
    issues = load_issues()

    if issue_id not in issues:
        raise ValueError(f"Issue {issue_id} not found")
    if issues[issue_id]["status"] == "closed":
        raise ValueError(f"Issue {issue_id} is already closed")

    # Validate blocker IDs exist
    for bid in blocker_ids:
        if bid not in issues:
            raise ValueError(f"Blocker issue {bid} not found")

    current_blockers = set(issues[issue_id].get("blocked_by", []))
    new_blockers = set(blocker_ids)
    added = new_blockers - current_blockers

    if not added:
        raise ValueError(f"Issue {issue_id} is already blocked by {blocker_ids}")

    updated_blockers = sorted(current_blockers | new_blockers)

    event = {
        "ts": get_timestamp(),
        "type": "updated",
        "id": issue_id,
        "blocked_by": updated_blockers,
        "reason": f"Added blockers: {', '.join(sorted(added))}",
    }

    append_event(event)
    return sorted(added)


def unblock_issue(issue_id, blocker_ids):
    """Remove blockers from an issue."""
    issues = load_issues()

    if issue_id not in issues:
        raise ValueError(f"Issue {issue_id} not found")
    if issues[issue_id]["status"] == "closed":
        raise ValueError(f"Issue {issue_id} is already closed")

    current_blockers = set(issues[issue_id].get("blocked_by", []))
    to_remove = set(blocker_ids)
    removed = to_remove & current_blockers

    if not removed:
        raise ValueError(f"Issue {issue_id} is not blocked by any of {blocker_ids}")

    updated_blockers = sorted(current_blockers - to_remove)

    event = {
        "ts": get_timestamp(),
        "type": "updated",
        "id": issue_id,
        "blocked_by": updated_blockers,
        "reason": f"Removed blockers: {', '.join(sorted(removed))}",
    }

    append_event(event)
    return sorted(removed)


def parse_list_arg(value):
    """Parse comma-separated list argument."""
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


def generate_mermaid_diagram(issues, all_issues, include_closed=False):
    """Generate Mermaid flowchart showing issue dependencies."""
    # LR (left-right) produces vertically-scrollable diagrams, better than
    # TD which creates very wide diagrams with many independent nodes
    lines = ["flowchart LR"]

    # Determine which issues to include
    if include_closed:
        display_issues = all_issues
    else:
        display_issues = {k: v for k, v in all_issues.items() if v["status"] == "open"}

    if not display_issues:
        return "flowchart LR\n    empty[No issues to display]"

    open_ids = set(k for k, v in all_issues.items() if v["status"] == "open")

    # Track which issues have dependencies (for layout)
    has_incoming = set()
    has_outgoing = set()

    # Collect edges
    edges = []
    for issue_id, issue in display_issues.items():
        for blocker_id in issue.get("blocked_by", []):
            # Only show edge if blocker is in display set
            if blocker_id in display_issues:
                edges.append((blocker_id, issue_id))
                has_incoming.add(issue_id)
                has_outgoing.add(blocker_id)

    # Generate node definitions with truncated titles
    for issue_id, issue in sorted(display_issues.items(), key=lambda x: x[0]):
        title = issue["title"]
        # Truncate long titles
        if len(title) > 30:
            title = title[:27] + "..."
        # Escape special Mermaid characters
        title = title.replace('"', "'").replace("[", "(").replace("]", ")")

        # Node shape based on status
        if issue["status"] == "closed":
            # Closed: stadium shape (rounded)
            lines.append(f'    {issue_id}(["{issue_id}: {title}"])')
        else:
            # Open: rectangle
            lines.append(f'    {issue_id}["{issue_id}: {title}"]')

    # Generate edges (blocker --> blocked)
    for blocker_id, blocked_id in edges:
        lines.append(f"    {blocker_id} --> {blocked_id}")

    # Style nodes
    for issue_id, issue in display_issues.items():
        if issue["status"] == "closed":
            lines.append(f"    style {issue_id} fill:#90EE90")  # Light green for closed
        elif issue_id in has_incoming:
            # Blocked by something
            lines.append(f"    style {issue_id} fill:#FFB6C1")  # Light pink for blocked
        else:
            # Ready (open, not blocked)
            lines.append(f"    style {issue_id} fill:#87CEEB")  # Light blue for ready

    return "\n".join(lines)


def generate_ascii_diagram(issues, all_issues, include_closed=False):
    """Generate ASCII diagram showing issue dependencies."""
    # Determine which issues to include
    if include_closed:
        display_issues = all_issues
    else:
        display_issues = {k: v for k, v in all_issues.items() if v["status"] == "open"}

    if not display_issues:
        return "No issues to display"

    open_ids = set(k for k, v in all_issues.items() if v["status"] == "open")

    lines = []
    lines.append("Issue Dependency Diagram")
    lines.append("=" * 50)
    lines.append("")
    lines.append("Legend: [READY] (BLOCKED) {CLOSED}")
    lines.append("")

    # Group issues by their dependency depth
    # Issues with no blockers are at depth 0
    depths = {}
    remaining = set(display_issues.keys())

    # Calculate depths
    depth = 0
    max_iterations = len(remaining) + 1
    while remaining and max_iterations > 0:
        max_iterations -= 1
        at_this_depth = set()
        for issue_id in remaining:
            blockers = set(display_issues[issue_id].get("blocked_by", []))
            blockers_in_display = blockers & set(display_issues.keys())
            blockers_remaining = blockers_in_display & remaining
            if not blockers_remaining:
                at_this_depth.add(issue_id)
                depths[issue_id] = depth
        remaining -= at_this_depth
        depth += 1

    # Handle cycles (remaining issues)
    for issue_id in remaining:
        depths[issue_id] = depth

    # Group by depth
    by_depth = {}
    for issue_id, d in depths.items():
        by_depth.setdefault(d, []).append(issue_id)

    # Output by depth level
    for d in sorted(by_depth.keys()):
        if d == 0:
            lines.append("Root issues (no blockers):")
        else:
            lines.append(f"Depth {d}:")

        for issue_id in sorted(by_depth[d]):
            issue = display_issues[issue_id]
            title = issue["title"]
            if len(title) > 40:
                title = title[:37] + "..."

            # Format based on status
            if issue["status"] == "closed":
                marker = "{CLOSED}"
            elif set(issue.get("blocked_by", [])) & open_ids:
                marker = "(BLOCKED)"
            else:
                marker = "[READY]"

            lines.append(f"  {marker} {issue_id}: {title}")

            # Show what blocks this issue
            blockers = issue.get("blocked_by", [])
            if blockers:
                blocker_strs = []
                for b in blockers:
                    if b in display_issues:
                        status = "open" if all_issues[b]["status"] == "open" else "closed"
                        blocker_strs.append(f"{b}({status})")
                    else:
                        blocker_strs.append(f"{b}(not shown)")
                if blocker_strs:
                    lines.append(f"           └── blocked by: {', '.join(blocker_strs)}")

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Append-only issue tracker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Query flags (mutually exclusive with write commands)
    query_group = parser.add_mutually_exclusive_group()
    query_group.add_argument("--all", action="store_true", help="Show all issues including closed")
    query_group.add_argument("--ready", action="store_true", help="Show open issues not blocked")
    query_group.add_argument("--show", metavar="ID", help="Show details of a single issue")
    query_group.add_argument("--diagram", nargs="?", const="mermaid", choices=["mermaid", "ascii"],
                             metavar="FORMAT", help="Generate dependency diagram (mermaid or ascii, default: mermaid)")

    # Write commands
    parser.add_argument("--create", metavar="TITLE", help="Create a new issue with the given title")
    parser.add_argument("--close", nargs=2, metavar=("ID", "REASON"), help="Close an issue")
    parser.add_argument("--note", nargs=2, metavar=("ID", "CONTENT"), help="Add a note to an issue")
    parser.add_argument("--block", nargs=2, metavar=("ID", "BLOCKER_IDS"), help="Add blockers to an issue (comma-separated IDs)")
    parser.add_argument("--unblock", nargs=2, metavar=("ID", "BLOCKER_IDS"), help="Remove blockers from an issue (comma-separated IDs)")

    # Diagram options
    parser.add_argument("--include-closed", action="store_true",
                        help="Include closed issues in diagram (only used with --diagram)")

    # Create options
    parser.add_argument("--type", "-t", choices=["bug", "feature", "task"], default="task",
                        help="Issue type (default: task)")
    parser.add_argument("--priority", "-p", type=int, choices=[0, 1, 2, 3, 4], default=2,
                        help="Priority 0=critical to 4=backlog (default: 2)")
    parser.add_argument("--description", "-d", default="", help="Issue description")
    parser.add_argument("--blocked-by", "-b", default="", help="Comma-separated list of blocking issue IDs")
    parser.add_argument("--labels", "-l", default="", help="Comma-separated list of labels")

    args = parser.parse_args()

    # Handle write commands
    if args.create:
        blocked_by = parse_list_arg(args.blocked_by)
        labels = parse_list_arg(args.labels)
        new_id = create_issue(
            title=args.create,
            issue_type=args.type,
            priority=args.priority,
            description=args.description,
            blocked_by=blocked_by,
            labels=labels,
        )
        print(json.dumps({"created": new_id}))
        return

    if args.close:
        issue_id, reason = args.close
        try:
            close_issue(issue_id, reason)
            print(json.dumps({"closed": issue_id}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        return

    if args.note:
        issue_id, content = args.note
        try:
            add_note(issue_id, content)
            print(json.dumps({"noted": issue_id}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        return

    if args.block:
        issue_id, blocker_ids_str = args.block
        blocker_ids = parse_list_arg(blocker_ids_str)
        if not blocker_ids:
            print(json.dumps({"error": "No blocker IDs provided"}), file=sys.stderr)
            sys.exit(1)
        try:
            added = block_issue(issue_id, blocker_ids)
            print(json.dumps({"blocked": issue_id, "added": added}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        return

    if args.unblock:
        issue_id, blocker_ids_str = args.unblock
        blocker_ids = parse_list_arg(blocker_ids_str)
        if not blocker_ids:
            print(json.dumps({"error": "No blocker IDs provided"}), file=sys.stderr)
            sys.exit(1)
        try:
            removed = unblock_issue(issue_id, blocker_ids)
            print(json.dumps({"unblocked": issue_id, "removed": removed}))
        except ValueError as e:
            print(json.dumps({"error": str(e)}), file=sys.stderr)
            sys.exit(1)
        return

    # Handle query commands
    all_issues = load_issues()

    # Handle --show single issue
    if args.show:
        issue_id = args.show
        if issue_id not in all_issues:
            print(json.dumps({"error": f"Issue {issue_id} not found"}), file=sys.stderr)
            sys.exit(1)
        print(json.dumps(all_issues[issue_id], indent=2))
        return

    # Handle diagram output
    if args.diagram:
        include_closed = getattr(args, 'include_closed', False)
        if args.diagram == "ascii":
            print(generate_ascii_diagram(all_issues, all_issues, include_closed=include_closed))
        else:
            print(generate_mermaid_diagram(all_issues, all_issues, include_closed=include_closed))
        return

    if args.all:
        output = all_issues
    elif args.ready:
        output = filter_ready(all_issues, all_issues)
    else:
        output = filter_open(all_issues)

    # Sort by priority, then by id
    sorted_issues = sorted(output.values(), key=lambda x: (x.get("priority", 2), x["id"]))

    print(json.dumps(sorted_issues, indent=2))


if __name__ == "__main__":
    main()
