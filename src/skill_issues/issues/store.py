"""
Issues store layer - data operations for append-only issue tracking.

This module handles all data persistence and querying for issues.
It can be imported independently of the CLI.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Data file lives in project root (current working directory)
PROJECT_ROOT = Path.cwd()
EVENTS_FILE = PROJECT_ROOT / ".issues/events.jsonl"


def ensure_data_file() -> None:
    """Create data directory and file if missing."""
    if not EVENTS_FILE.parent.exists():
        EVENTS_FILE.parent.mkdir(parents=True)
    if not EVENTS_FILE.exists():
        EVENTS_FILE.touch()


def get_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_event(event: dict[str, Any]) -> None:
    """Append a JSON event to the events file."""
    ensure_data_file()
    # Ensure file ends with newline before appending
    content = EVENTS_FILE.read_text()
    needs_newline = content and not content.endswith("\n")
    with open(EVENTS_FILE, "a") as f:
        if needs_newline:
            f.write("\n")
        f.write(json.dumps(event, separators=(",", ":")) + "\n")
        f.flush()


def load_issues() -> dict[str, dict[str, Any]]:
    """Read events and reconstruct current state of all issues."""
    ensure_data_file()
    issues: dict[str, dict[str, Any]] = {}

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
                update_record: dict[str, Any] = {"ts": event["ts"]}
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


def next_id(issues: dict[str, dict[str, Any]]) -> str:
    """Return next available issue ID (zero-padded 3 digits)."""
    if not issues:
        return "001"
    max_id = max(int(i) for i in issues.keys())
    return f"{max_id + 1:03d}"


# --- Filter functions ---

def filter_open(issues: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return only open issues."""
    return {k: v for k, v in issues.items() if v["status"] == "open"}


def filter_closed(issues: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return only closed issues."""
    return {k: v for k, v in issues.items() if v["status"] == "closed"}


def filter_ready(issues: dict[str, dict[str, Any]], all_issues: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
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


# --- Write operations ---

def create_issue(
    title: str,
    issue_type: str = "task",
    priority: int = 2,
    description: str = "",
    blocked_by: list[str] | None = None,
    labels: list[str] | None = None,
) -> str:
    """Create a new issue and return its ID."""
    issues = load_issues()
    new_id = next_id(issues)

    event: dict[str, Any] = {
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


def close_issue(issue_id: str, reason: str) -> None:
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


def add_note(issue_id: str, content: str) -> None:
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


def block_issue(issue_id: str, blocker_ids: list[str]) -> list[str]:
    """Add blockers to an issue. Returns list of added blocker IDs."""
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


def unblock_issue(issue_id: str, blocker_ids: list[str]) -> list[str]:
    """Remove blockers from an issue. Returns list of removed blocker IDs."""
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


# --- Diagram generation ---

def generate_mermaid_diagram(
    issues: dict[str, dict[str, Any]],
    all_issues: dict[str, dict[str, Any]],
    include_closed: bool = False,
) -> str:
    """Generate Mermaid flowchart showing issue dependencies."""
    # LR (left-right) produces vertically-scrollable diagrams
    lines = ["flowchart LR"]

    # Determine which issues to include
    if include_closed:
        display_issues = all_issues
    else:
        display_issues = {k: v for k, v in all_issues.items() if v["status"] == "open"}

    if not display_issues:
        return "flowchart LR\n    empty[No issues to display]"

    open_ids = set(k for k, v in all_issues.items() if v["status"] == "open")

    # Track which issues have dependencies
    has_incoming: set[str] = set()

    # Collect edges
    edges: list[tuple[str, str]] = []
    for issue_id, issue in display_issues.items():
        for blocker_id in issue.get("blocked_by", []):
            if blocker_id in display_issues:
                edges.append((blocker_id, issue_id))
                has_incoming.add(issue_id)

    # Generate node definitions with truncated titles
    for issue_id, issue in sorted(display_issues.items(), key=lambda x: x[0]):
        title = issue["title"]
        if len(title) > 30:
            title = title[:27] + "..."
        title = title.replace('"', "'").replace("[", "(").replace("]", ")")

        if issue["status"] == "closed":
            lines.append(f'    {issue_id}(["{issue_id}: {title}"])')
        else:
            lines.append(f'    {issue_id}["{issue_id}: {title}"]')

    # Generate edges
    for blocker_id, blocked_id in edges:
        lines.append(f"    {blocker_id} --> {blocked_id}")

    # Style nodes
    for issue_id, issue in display_issues.items():
        if issue["status"] == "closed":
            lines.append(f"    style {issue_id} fill:#90EE90")
        elif issue_id in has_incoming:
            lines.append(f"    style {issue_id} fill:#FFB6C1")
        else:
            lines.append(f"    style {issue_id} fill:#87CEEB")

    return "\n".join(lines)


def generate_ascii_diagram(
    issues: dict[str, dict[str, Any]],
    all_issues: dict[str, dict[str, Any]],
    include_closed: bool = False,
) -> str:
    """Generate ASCII diagram showing issue dependencies."""
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

    # Calculate depths
    depths: dict[str, int] = {}
    remaining = set(display_issues.keys())

    depth = 0
    max_iterations = len(remaining) + 1
    while remaining and max_iterations > 0:
        max_iterations -= 1
        at_this_depth: set[str] = set()
        for issue_id in remaining:
            blockers = set(display_issues[issue_id].get("blocked_by", []))
            blockers_in_display = blockers & set(display_issues.keys())
            blockers_remaining = blockers_in_display & remaining
            if not blockers_remaining:
                at_this_depth.add(issue_id)
                depths[issue_id] = depth
        remaining -= at_this_depth
        depth += 1

    # Handle cycles
    for issue_id in remaining:
        depths[issue_id] = depth

    # Group by depth
    by_depth: dict[int, list[str]] = {}
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

            if issue["status"] == "closed":
                marker = "{CLOSED}"
            elif set(issue.get("blocked_by", [])) & open_ids:
                marker = "(BLOCKED)"
            else:
                marker = "[READY]"

            lines.append(f"  {marker} {issue_id}: {title}")

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
