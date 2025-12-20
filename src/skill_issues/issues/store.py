"""
Issues store layer - data operations for append-only issue tracking.

This module handles all data persistence and querying for issues.
It can be imported independently of the CLI.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from skill_issues import get_user_prefix

# Data directory lives in project root (current working directory)
PROJECT_ROOT = Path.cwd()
ISSUES_DIR = PROJECT_ROOT / ".issues"
LEGACY_EVENTS_FILE = ISSUES_DIR / "events.jsonl"


def get_user_events_file(prefix: str | None = None) -> Path:
    """Get the per-user events file path."""
    if prefix is None:
        prefix, _ = get_user_prefix()
    return ISSUES_DIR / f"events-{prefix}.jsonl"


def ensure_data_dir() -> None:
    """Create data directory if missing."""
    if not ISSUES_DIR.exists():
        ISSUES_DIR.mkdir(parents=True)


def ensure_user_events_file(prefix: str | None = None) -> Path:
    """Create user's events file if missing and return path."""
    ensure_data_dir()
    events_file = get_user_events_file(prefix)
    if not events_file.exists():
        events_file.touch()
    return events_file


def get_timestamp() -> str:
    """Return current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def append_event(event: dict[str, Any]) -> None:
    """Append a JSON event to the current user's events file."""
    events_file = ensure_user_events_file()
    # Ensure file ends with newline before appending
    content = events_file.read_text()
    needs_newline = content and not content.endswith("\n")
    with open(events_file, "a") as f:
        if needs_newline:
            f.write("\n")
        f.write(json.dumps(event, separators=(",", ":")) + "\n")
        f.flush()


def _load_events_from_file(filepath: Path) -> list[dict[str, Any]]:
    """Load events from a single JSONL file."""
    if not filepath.exists():
        return []
    events = []
    for line in filepath.read_text().splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def _load_all_events() -> list[dict[str, Any]]:
    """Load events from all user files and legacy file, sorted by timestamp."""
    ensure_data_dir()
    all_events: list[dict[str, Any]] = []

    # Load from per-user files (events-*.jsonl)
    for events_file in ISSUES_DIR.glob("events-*.jsonl"):
        all_events.extend(_load_events_from_file(events_file))

    # Load from legacy shared file (events.jsonl)
    all_events.extend(_load_events_from_file(LEGACY_EVENTS_FILE))

    # Sort by timestamp to ensure correct event ordering
    all_events.sort(key=lambda e: e.get("ts", ""))

    return all_events


def load_issues() -> dict[str, dict[str, Any]]:
    """Read events and reconstruct current state of all issues."""
    issues: dict[str, dict[str, Any]] = {}

    for event in _load_all_events():
        issue_id = event["id"]
        event_type = event["type"]

        if event_type == "created":
            # Support both old "blocked_by" and new "depends_on" field names
            depends_on = event.get("depends_on", event.get("blocked_by", []))
            issues[issue_id] = {
                "id": issue_id,
                "title": event["title"],
                "type": event.get("issue_type", "task"),
                "priority": event.get("priority", 2),
                "description": event.get("description", ""),
                "depends_on": depends_on,
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
                for field in ["priority", "labels"]:
                    if field in event:
                        update_record[field] = {"from": issues[issue_id].get(field), "to": event[field]}
                        issues[issue_id][field] = event[field]
                # Handle depends_on (support old "blocked_by" name for backwards compatibility)
                dep_value = event.get("depends_on", event.get("blocked_by"))
                if dep_value is not None:
                    update_record["depends_on"] = {"from": issues[issue_id].get("depends_on"), "to": dep_value}
                    issues[issue_id]["depends_on"] = dep_value
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


def parse_issue_id(issue_id: str) -> tuple[str | None, int | None]:
    """Parse an issue ID into (prefix, number).

    Handles both old format (001) and new format (dp-001).

    Returns:
        Tuple of (prefix, number). prefix is None for old-format IDs.
        Returns (None, None) if the ID doesn't match any known format.
    """
    # New format: prefix-NNN (e.g., dp-001)
    new_match = re.match(r"^([a-z0-9]{2,4})-(\d+)$", issue_id)
    if new_match:
        return (new_match.group(1), int(new_match.group(2)))

    # Old format: NNN (e.g., 001, 088)
    old_match = re.match(r"^(\d+)$", issue_id)
    if old_match:
        return (None, int(old_match.group(1)))

    return (None, None)


def next_id(issues: dict[str, dict[str, Any]], prefix: str | None = None) -> str:
    """Return next available issue ID for the current user.

    Args:
        issues: Dict of all issues.
        prefix: User prefix to use. If None, uses get_user_prefix().

    Returns:
        Next issue ID in format "prefix-NNN" (e.g., "dp-001").
    """
    if prefix is None:
        prefix, _ = get_user_prefix()

    # Find max number for this user's issues
    max_num = 0
    for issue_id in issues.keys():
        parsed_prefix, num = parse_issue_id(issue_id)
        if parsed_prefix == prefix and num is not None:
            max_num = max(max_num, num)

    return f"{prefix}-{max_num + 1:03d}"


# --- Filter functions ---

def filter_open(issues: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return only open issues."""
    return {k: v for k, v in issues.items() if v["status"] == "open"}


def filter_closed(issues: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return only closed issues."""
    return {k: v for k, v in issues.items() if v["status"] == "closed"}


def filter_ready(issues: dict[str, dict[str, Any]], all_issues: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return open issues with no unsatisfied dependencies."""
    open_ids = set(filter_open(all_issues).keys())
    ready = {}
    for k, v in issues.items():
        if v["status"] != "open":
            continue
        deps = set(v.get("depends_on", []))
        unsatisfied_deps = deps & open_ids
        if not unsatisfied_deps:
            ready[k] = v
    return ready


# --- Write operations ---

def create_issue(
    title: str,
    issue_type: str = "task",
    priority: int = 2,
    description: str = "",
    depends_on: list[str] | None = None,
    labels: list[str] | None = None,
) -> str:
    """Create a new issue and return its ID."""
    issues = load_issues()
    prefix, _ = get_user_prefix()
    new_id = next_id(issues, prefix)

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
    if depends_on:
        event["depends_on"] = depends_on
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


def add_dependency(issue_id: str, dep_ids: list[str]) -> list[str]:
    """Add dependencies to an issue. Returns list of added dependency IDs."""
    issues = load_issues()

    if issue_id not in issues:
        raise ValueError(f"Issue {issue_id} not found")
    if issues[issue_id]["status"] == "closed":
        raise ValueError(f"Issue {issue_id} is already closed")

    # Validate dependency IDs exist
    for dep_id in dep_ids:
        if dep_id not in issues:
            raise ValueError(f"Dependency issue {dep_id} not found")

    current_deps = set(issues[issue_id].get("depends_on", []))
    new_deps = set(dep_ids)
    added = new_deps - current_deps

    if not added:
        raise ValueError(f"Issue {issue_id} already depends on {dep_ids}")

    updated_deps = sorted(current_deps | new_deps)

    event = {
        "ts": get_timestamp(),
        "type": "updated",
        "id": issue_id,
        "depends_on": updated_deps,
        "reason": f"Added dependencies: {', '.join(sorted(added))}",
    }

    append_event(event)
    return sorted(added)


def remove_dependency(issue_id: str, dep_ids: list[str]) -> list[str]:
    """Remove dependencies from an issue. Returns list of removed dependency IDs."""
    issues = load_issues()

    if issue_id not in issues:
        raise ValueError(f"Issue {issue_id} not found")
    if issues[issue_id]["status"] == "closed":
        raise ValueError(f"Issue {issue_id} is already closed")

    current_deps = set(issues[issue_id].get("depends_on", []))
    to_remove = set(dep_ids)
    removed = to_remove & current_deps

    if not removed:
        raise ValueError(f"Issue {issue_id} does not depend on any of {dep_ids}")

    updated_deps = sorted(current_deps - to_remove)

    event = {
        "ts": get_timestamp(),
        "type": "updated",
        "id": issue_id,
        "depends_on": updated_deps,
        "reason": f"Removed dependencies: {', '.join(sorted(removed))}",
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
        for dep_id in issue.get("depends_on", []):
            if dep_id in display_issues:
                edges.append((dep_id, issue_id))
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
    for dep_id, dependent_id in edges:
        lines.append(f"    {dep_id} --> {dependent_id}")

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
            deps = set(display_issues[issue_id].get("depends_on", []))
            deps_in_display = deps & set(display_issues.keys())
            deps_remaining = deps_in_display & remaining
            if not deps_remaining:
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
            lines.append("Root issues (no dependencies):")
        else:
            lines.append(f"Depth {d}:")

        for issue_id in sorted(by_depth[d]):
            issue = display_issues[issue_id]
            title = issue["title"]
            if len(title) > 40:
                title = title[:37] + "..."

            if issue["status"] == "closed":
                marker = "{CLOSED}"
            elif set(issue.get("depends_on", [])) & open_ids:
                marker = "(BLOCKED)"
            else:
                marker = "[READY]"

            lines.append(f"  {marker} {issue_id}: {title}")

            deps = issue.get("depends_on", [])
            if deps:
                dep_strs = []
                for d in deps:
                    if d in display_issues:
                        status = "open" if all_issues[d]["status"] == "open" else "closed"
                        dep_strs.append(f"{d}({status})")
                    else:
                        dep_strs.append(f"{d}(not shown)")
                if dep_strs:
                    lines.append(f"           └── depends on: {', '.join(dep_strs)}")

        lines.append("")

    return "\n".join(lines)
