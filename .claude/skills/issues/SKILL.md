---
name: issues
description: Local-first issue tracking with GitHub Issues semantics. Create, close, and query issues with dependencies. Use when managing project work items, tracking bugs/features/tasks, or reviewing what needs to be done.
---

# Issue Tracking Skill

A minimal, append-only event log for tracking issues. Designed for close human-AI collaboration.

**Portable:** This skill directory contains both documentation and tooling. Copy to any repo to use.

## Tools

- `issues.py` - Query and write tool for managing issues (auto-creates data file if missing)

## Data Location

Events are stored in `.issues/events.jsonl` (project root) - one JSON event per line, append-only. The directory and file are auto-created on first use.

## Quick Reference

```bash
# Reading
python3 issues.py              # Open issues (default)
python3 issues.py --open       # Open issues (explicit)
python3 issues.py --closed     # Closed issues
python3 issues.py --ready      # Open and not blocked
python3 issues.py --all        # All issues including closed
python3 issues.py ID           # Show single issue
python3 issues.py --show ID    # Show single issue (explicit)
python3 issues.py --diagram    # Mermaid dependency diagram
python3 issues.py --diagram ascii  # ASCII dependency diagram

# Writing
python3 issues.py --create "Title" [options]
python3 issues.py --close ID "Reason"
python3 issues.py --note ID "Content"
python3 issues.py --block ID "BLOCKER_IDS"
python3 issues.py --unblock ID "BLOCKER_IDS"
```

**Why append-only?**
- Writes are trivial (just append)
- Git diffs are always additions at the end
- Full history without digging through git commits
- No read-modify-write complexity

## Event Schema

Four event types:

```json
// created - sets initial fields
{"ts": "2025-12-13T14:00:00Z", "type": "created", "id": "014", "title": "Short title", "issue_type": "task", "priority": 2, "description": "Details", "blocked_by": ["013"], "labels": ["needs-review"]}

// updated - changes mutable fields (priority, blocked_by, labels)
{"ts": "2025-12-13T14:15:00Z", "type": "updated", "id": "014", "priority": 1, "reason": "Blocking other work, needs to be done first"}

// note - adds context during work (can have multiple per issue)
{"ts": "2025-12-13T14:30:00Z", "type": "note", "id": "014", "content": "Discovered that the API requires auth tokens, not session cookies. See src/api/widget.ts:45"}

// closed - terminal state
{"ts": "2025-12-13T15:00:00Z", "type": "closed", "id": "014", "reason": "Done - explanation"}
```

**Fields:**
- `ts`: ISO 8601 timestamp
- `type`: "created", "updated", "note", or "closed"
- `id`: Simple incrementing ID (string, e.g., "014")
- `title`: Short description (created only)
- `issue_type`: "bug", "feature", or "task" (created only)
- `priority`: 0=critical, 1=high, 2=medium (default), 3=low, 4=backlog (created or updated)
- `description`: Detailed context (created only, optional but recommended)
- `blocked_by`: Array of issue IDs (created or updated)
- `labels`: Array of custom tags for categorization (created or updated, optional). Examples: "needs-review", "breaking-change", "documentation"
- `content`: Free-form text for notes (note only)
- `reason`: Explanation for update or closure (updated or closed)

**Mutability:** Most fields are immutable after creation. Use `updated` events to change `priority`, `blocked_by`, or `labels`. Use `note` events to add context. If title/description are fundamentally wrong, close and recreate.

## Reading Issues

```bash
# Open issues (default)
python3 issues.py
python3 issues.py --open       # explicit form

# Closed issues
python3 issues.py --closed

# Ready issues (open and not blocked by other open issues)
python3 issues.py --ready

# All issues including closed
python3 issues.py --all

# Show single issue by ID
python3 issues.py 053          # shorthand
python3 issues.py --show 053   # explicit form
```

Output is JSON array sorted by priority, then ID (except single issue which returns object).

## Creating Issues

```bash
python3 issues.py --create "Title" [options]
```

**Options:**
- `-t, --type {bug,feature,task}` - Issue type (default: task)
- `-p, --priority {0,1,2,3,4}` - Priority 0=critical to 4=backlog (default: 2)
- `-d, --description TEXT` - Detailed description
- `-b, --blocked-by IDS` - Comma-separated blocking issue IDs
- `-l, --labels LABELS` - Comma-separated labels

**Examples:**
```bash
# Simple task
python3 issues.py --create "Fix login timeout"

# Bug with details
python3 issues.py --create "API returns 500 on empty input" \
  -t bug -p 1 -d "Discovered when testing edge cases"

# Feature blocked by other work
python3 issues.py --create "Add export to CSV" \
  -t feature -b 014,015 -l "needs-review"
```

Returns `{"created": "036"}` with the new issue ID.

## Adding Notes

```bash
python3 issues.py --note ID "Content"
```

**Example:**
```bash
python3 issues.py --note 015 "User clarified: they want CSV format, not JSON"
```

**When to add notes:**
- User provides context or clarification
- You discover something during implementation
- A decision is made that affects the approach
- You hit a blocker or find a workaround

Notes appear in the issue's `notes` array when reading issues.

## Updating Dependencies

Add or remove blockers from existing issues:

```bash
# Add blockers (comma-separated IDs)
python3 issues.py --block 014 "012,013"

# Remove blockers
python3 issues.py --unblock 014 "012"
```

Returns `{"blocked": "014", "added": ["012", "013"]}` or `{"unblocked": "014", "removed": ["012"]}`.

**Error handling:** Returns error JSON to stderr if issue doesn't exist, is already closed, or blocker IDs are invalid.

## Other Updates

For other mutable fields (`priority`, `labels`), use the Edit tool to append an updated event to `.issues/events.jsonl`:

```json
{"ts": "2025-12-13T14:15:00Z", "type": "updated", "id": "014", "priority": 1, "reason": "Blocking other work, needs to be done first"}
```

**Mutable fields:**
- `priority` - reprioritize as understanding evolves
- `blocked_by` - add or change dependencies (prefer `--block`/`--unblock` commands)
- `labels` - add or change custom tags

**Always include `reason`** to explain why the change was made. Updates appear in the issue's `updates` array with before/after values for traceability.

## Closing Issues

```bash
python3 issues.py --close ID "Reason"
```

**Example:**
```bash
python3 issues.py --close 015 "Done - implemented CSV export with unicode support"
```

Returns `{"closed": "015"}` on success.

**Error handling:** Returns error JSON to stderr if issue doesn't exist or is already closed.

## Workflow

1. **Session start**: Check ready work
   ```bash
   python3 issues.py --ready
   ```

2. **Pick work**: Choose from ready issues based on priority

3. **During work**:
   - Add note events for discoveries, decisions, user clarifications
   - Create new issues with `blocked_by` if you find dependent work
   - **Proactively log bugs and issues you encounter** (see below)

4. **Complete**: Append a closed event with clear reason

5. **Session end**: Review open issues, ensure events are appended

## Proactive Issue Logging

**Important:** When you encounter problems during a session, create issues immediately rather than waiting to be asked. This includes:

- **Bugs in tools/skills** - If a command doesn't work as expected, log it
- **Usability issues** - Confusing interfaces, missing help text, unintuitive flags
- **Missing features** - Functionality you expected but wasn't there
- **Documentation gaps** - Instructions that are unclear or missing
- **Ideas for improvement** - Better approaches discovered while working

This is a key purpose of the issue tracker: capturing problems and improvements as they're discovered, when context is fresh. Don't assume someone else will remember to log it later.

## Dependency Diagrams

Generate visual diagrams showing issue relationships:

```bash
# Mermaid format (default) - for GitHub READMEs
python3 issues.py --diagram

# ASCII format - for terminal/plain text
python3 issues.py --diagram ascii

# Include closed issues to see full project history
python3 issues.py --diagram --include-closed
```

**Mermaid output** renders in GitHub markdown:
- Uses left-right layout for vertical scrolling (better than wide horizontal diagrams)
- Rectangle nodes = open issues
- Stadium (rounded) nodes = closed issues
- Arrows show blocked-by relationships (blocker → blocked)
- Colors: blue = ready, pink = blocked, green = closed

**ASCII output** shows:
- Issues grouped by dependency depth (root issues first)
- `[READY]` = open, unblocked
- `(BLOCKED)` = open, waiting on other open issues
- `{CLOSED}` = completed
- Indented lines show what blocks each issue

## Dependency Reasoning

For small issue counts (<50), pass the output to Claude who can:
- Identify blocking relationships
- Find transitive dependencies (A blocks B blocks C)
- Suggest what to work on next based on the graph

The `--ready` flag handles simple blocking (direct dependencies on open issues).

## Principles

- **Append-only**: Never modify existing events
- **Immutable fields**: Close and recreate if wrong
- **Simple tools**: Python for reads, Edit for writes
- **Git-friendly**: Diffs are always additions
- **Claude does reasoning**: Tool just filters, Claude interprets
- **Proactive logging**: Create issues for bugs/problems when you encounter them, not later
