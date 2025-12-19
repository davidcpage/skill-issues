---
name: issues
description: Local-first issue tracking with GitHub Issues semantics. Create, close, and query issues with dependencies. Use when managing project work items, tracking bugs/features/tasks, or reviewing what needs to be done.
---

# Issue Tracking Skill

A minimal, append-only event log for tracking issues. Designed for close human-AI collaboration.

**Installation required:** Install the `skill-issues` package for CLI tools:
```bash
uv tool install skill-issues
```

## Data Location

Events are stored in `.issues/events.jsonl` (project root) - one JSON event per line, append-only. The directory and file are auto-created on first use.

## User Prefix

Issue IDs include a user prefix (e.g., `dp-001`) to enable conflict-free collaboration. The prefix is resolved in order:

1. `SKILL_ISSUES_PREFIX` environment variable
2. `git config skill-issues.prefix`
3. Derived from `git config user.name` (first + last initials)
4. Fallback: `xx`

**Configure once per machine:**
```bash
git config --global skill-issues.prefix "dp"
```

On first use with a derived prefix, you'll see a hint about configuration.

## Quick Reference

```bash
# Reading
issues                    # Open issues (default)
issues --open             # Open issues (explicit)
issues --closed           # Closed issues
issues --ready            # Open and not blocked
issues --all              # All issues including closed
issues ID                 # Show single issue
issues --show ID          # Show single issue (explicit)
issues --diagram          # Mermaid dependency diagram
issues --diagram ascii    # ASCII dependency diagram

# Writing
issues create "Title" [options]
issues close ID "Reason"
issues note ID "Content"
issues add-dep ID "DEP_IDS"
issues remove-dep ID "DEP_IDS"

# TUI
issues board              # Kanban board view
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
{"ts": "2025-12-13T14:00:00Z", "type": "created", "id": "dp-014", "title": "Short title", "issue_type": "task", "priority": 2, "description": "Details", "depends_on": ["dp-013"], "labels": ["needs-review"]}

// updated - changes mutable fields (priority, depends_on, labels)
{"ts": "2025-12-13T14:15:00Z", "type": "updated", "id": "dp-014", "priority": 1, "reason": "Blocking other work, needs to be done first"}

// note - adds context during work (can have multiple per issue)
{"ts": "2025-12-13T14:30:00Z", "type": "note", "id": "dp-014", "content": "Discovered that the API requires auth tokens, not session cookies. See src/api/widget.ts:45"}

// closed - terminal state
{"ts": "2025-12-13T15:00:00Z", "type": "closed", "id": "dp-014", "reason": "Done - explanation"}
```

**Fields:**
- `ts`: ISO 8601 timestamp
- `type`: "created", "updated", "note", or "closed"
- `id`: User-prefixed ID (string, e.g., "dp-014")
- `title`: Short description (created only)
- `issue_type`: "bug", "feature", or "task" (created only)
- `priority`: 0=critical, 1=high, 2=medium (default), 3=low, 4=backlog (created or updated)
- `description`: Detailed context (created only, optional but recommended)
- `depends_on`: Array of issue IDs this issue depends on (created or updated)
- `labels`: Array of custom tags for categorization (created or updated, optional). Examples: "needs-review", "breaking-change", "documentation"
- `content`: Free-form text for notes (note only)
- `reason`: Explanation for update or closure (updated or closed)

**Mutability:** Most fields are immutable after creation. Use `updated` events to change `priority`, `depends_on`, or `labels`. Use `note` events to add context. If title/description are fundamentally wrong, close and recreate.

## Reading Issues

```bash
# Open issues (default)
issues
issues --open       # explicit form

# Closed issues
issues --closed

# Ready issues (open and not blocked by other open issues)
issues --ready

# All issues including closed
issues --all

# Show single issue by ID
issues dp-053          # shorthand
issues --show dp-053   # explicit form
```

Output is JSON array sorted by priority, then ID (except single issue which returns object).

## Creating Issues

```bash
issues create "Title" [options]
```

**Options:**
- `-t, --type {bug,feature,task}` - Issue type (default: task)
- `-p, --priority {0,1,2,3,4}` - Priority 0=critical to 4=backlog (default: 2)
- `-d, --description TEXT` - Detailed description
- `-b, --depends-on IDS` - Comma-separated dependency issue IDs
- `-l, --labels LABELS` - Comma-separated labels

**Examples:**
```bash
# Simple task
issues create "Fix login timeout"

# Bug with details
issues create "API returns 500 on empty input" \
  -t bug -p 1 -d "Discovered when testing edge cases"

# Feature blocked by other work
issues create "Add export to CSV" \
  -t feature -b dp-014,dp-015 -l "needs-review"
```

Returns `{"created": "dp-036"}` with the new issue ID.

## Adding Notes

```bash
issues note ID "Content"
```

**Example:**
```bash
issues note dp-015 "User clarified: they want CSV format, not JSON"
```

**When to add notes:**
- User provides context or clarification
- You discover something during implementation
- A decision is made that affects the approach
- You hit a blocker or find a workaround

Notes appear in the issue's `notes` array when reading issues.

## Updating Dependencies

Add or remove dependencies from existing issues:

```bash
# Add dependencies (comma-separated IDs)
issues add-dep dp-014 "dp-012,dp-013"

# Remove dependencies
issues remove-dep dp-014 "dp-012"
```

Returns `{"issue": "dp-014", "added_deps": ["dp-012", "dp-013"]}` or `{"issue": "dp-014", "removed_deps": ["dp-012"]}`.

**Error handling:** Returns error JSON to stderr if issue doesn't exist, is already closed, or dependency IDs are invalid.

## Other Updates

For other mutable fields (`priority`, `labels`), use the Edit tool to append an updated event to `.issues/events.jsonl`:

```json
{"ts": "2025-12-13T14:15:00Z", "type": "updated", "id": "dp-014", "priority": 1, "reason": "Blocking other work, needs to be done first"}
```

**Mutable fields:**
- `priority` - reprioritize as understanding evolves
- `depends_on` - add or change dependencies (prefer `--add-dep`/`--remove-dep` commands)
- `labels` - add or change custom tags

**Always include `reason`** to explain why the change was made. Updates appear in the issue's `updates` array with before/after values for traceability.

## Closing Issues

```bash
issues close ID "Reason"
```

**Example:**
```bash
issues close dp-015 "Done - implemented CSV export with unicode support"
```

Returns `{"closed": "dp-015"}` on success.

**Error handling:** Returns error JSON to stderr if issue doesn't exist or is already closed.

## Workflow

1. **Session start**: Check ready work
   ```bash
   issues --ready
   ```

2. **Pick work**: Choose from ready issues based on priority

3. **During work**:
   - Add note events for discoveries, decisions, user clarifications
   - Create new issues with `depends_on` if you find dependent work
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
issues --diagram

# ASCII format - for terminal/plain text
issues --diagram ascii

# Include closed issues to see full project history
issues --diagram --include-closed
```

**Mermaid output** renders in GitHub markdown:
- Uses left-right layout for vertical scrolling (better than wide horizontal diagrams)
- Rectangle nodes = open issues
- Stadium (rounded) nodes = closed issues
- Arrows show dependency relationships (dependency → dependent)
- Colors: blue = ready, pink = blocked, green = closed

**ASCII output** shows:
- Issues grouped by dependency depth (root issues first)
- `[READY]` = open, unblocked
- `(BLOCKED)` = open, waiting on other open issues
- `{CLOSED}` = completed
- Indented lines show what blocks each issue

## Interactive Board TUI

Browse issues interactively with a Kanban board interface:

```bash
issues board
```

**Columns:**
- **Ready**: Open issues with no open blockers
- **Blocked**: Open issues waiting on other open issues
- **Closed**: Completed issues

**Features:**
- Issue cards show priority badge, type icon, ID, and title
- Right panel shows full issue details (description, labels, dependencies, notes)
- Issues sorted by priority within each column

**Vim Navigation:**
- `h`/`l` - Move between columns
- `j`/`k` - Move between issues in current column
- `g`/`G` - Jump to top/bottom of column
- `r` - Refresh issues from disk
- `q` - Quit

## Dependency Reasoning

For small issue counts (<50), pass the output to Claude who can:
- Identify blocking relationships
- Find transitive dependencies (A blocks B blocks C)
- Suggest what to work on next based on the graph

The `--ready` flag handles simple dependency checking (issues with direct dependencies on other open issues).

## Principles

- **Append-only**: Never modify existing events
- **Immutable fields**: Close and recreate if wrong
- **Git-friendly**: Diffs are always additions
- **Claude does reasoning**: Tool just filters, Claude interprets
- **Proactive logging**: Create issues for bugs/problems when you encounter them, not later
