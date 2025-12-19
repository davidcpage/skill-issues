---
name: sessions
description: Session memory for tracking learnings, open questions, and next actions across conversations. Use when starting a session, capturing insights, or reviewing what was learned previously.
---

# Sessions Skill

Personal session memory for AI agent conversations. Captures learnings, open questions, and next actions across sessions.

**Installation required:** Install the `skill-issues` package for CLI tools:
```bash
uv tool install skill-issues
```

**Dependency:** This skill optionally references the [issues skill](../issues/SKILL.md) via the `issues_worked` field. The dependency is one-way: sessions can reference issues, but issues never reference sessions.

## Data Location

Sessions are stored in `.sessions/events.jsonl` (project root) - one JSON object per line, append-only.

## User Prefix

Session IDs include a user prefix (e.g., `dp-s001`) to enable multi-user collaboration. The prefix is resolved in order:

1. `SKILL_ISSUES_PREFIX` environment variable
2. `git config skill-issues.prefix`
3. Derived from `git config user.name` (first + last initials)
4. Fallback: `xx`

**Configure once per machine:**
```bash
git config --global skill-issues.prefix "dp"
```

On first use with a derived prefix, you'll see a hint about configuration.

**Note:** Sessions are filtered by user by default. Use `--user all` to see all users' sessions.

## Quick Reference

```bash
# Reading (filtered to current user by default)
sessions                  # Last session (current user)
sessions --last 3         # Last N sessions (current user)
sessions --last 5 --user all  # Last 5 from all users
sessions --user xy        # Last session from user 'xy'
sessions --all            # All sessions (current user)
sessions --open-questions # All open questions across sessions
sessions --next-actions   # All next actions (with session attribution)
sessions --topic beads    # Search by topic
sessions --issue dp-014   # Sessions that worked on a specific issue
sessions --summary        # Markdown summary for documentation
sessions --timeline       # Markdown timeline of sessions

# Writing
sessions --create "topic" [options]

# TUI
sessions board            # Interactive session browser (with user tabs)
```

## Schema

```json
{
  "id": "dp-s001",
  "user": "dp",
  "date": "2025-12-13",
  "topic": "feature-implementation",
  "learnings": [
    "Key insight from this session",
    "Another thing we discovered"
  ],
  "open_questions": [
    "Unresolved question to explore later"
  ],
  "next_actions": [
    "Concrete follow-up task"
  ],
  "issues_worked": ["dp-014", "dp-015"]
}
```

**Fields:**
- `id`: User-prefixed session ID (e.g., "dp-s001", "jb-s001")
- `user`: User prefix (matches prefix in ID)
- `date`: ISO date (YYYY-MM-DD)
- `topic`: Primary topic or theme of the session
- `learnings`: Key insights - meta-knowledge, not actionable work
- `open_questions`: Unresolved questions to explore (may or may not become issues)
- `next_actions`: Concrete follow-ups (may or may not become issues)
- `issues_worked`: Array of issue IDs created, closed, or worked on (optional, references issues skill)

## Reading Sessions

```bash
# Last session (current user only - most common for session startup)
sessions

# Last N sessions (current user)
sessions --last 3

# Cross-user queries with --user flag
sessions --user all         # Last session from any user
sessions --last 5 --user all  # Last 5 from all users
sessions --user xy          # Last session from user 'xy'

# All sessions (current user)
sessions --all

# All open questions across sessions
sessions --open-questions

# All next actions (with session attribution)
sessions --next-actions

# Search by topic
sessions --topic beads

# Find sessions that worked on a specific issue
sessions --issue dp-014

# Generate markdown summary for documentation
sessions --summary

# Generate markdown timeline of sessions
sessions --timeline

# Show help
sessions --help
```

## Interactive TUI

Browse sessions interactively with a split-view interface:

```bash
sessions board
```

**Features:**
- User tabs at top: current user first, other users alphabetically, "All" tab last
- Left panel: session list with date, topic, and counts
- Right panel: expanded session details (learnings, questions, actions)
- Vim navigation: `j`/`k` (up/down), `g`/`G` (top/bottom), `h`/`l` (prev/next tab)
- Search: `/` to filter by topic, `Escape` to clear
- Quit: `q`

## Documentation Output

Generate formatted markdown for READMEs and documentation:

```bash
# Full summary with overview, timeline, key learnings, and open questions
sessions --summary

# Timeline grouped by date with session stats
sessions --timeline
```

**Summary includes:**
- Overview stats (date range, session count, learnings, issues)
- Compact timeline by date
- Key learnings (first learning from recent sessions)
- Deduplicated open questions

**Timeline includes:**
- Sessions grouped by date (most recent first)
- Per-session stats (learnings, questions, issues worked)

## Creating Sessions

```bash
# Basic session with topic only
sessions --create "topic-slug"

# Full session with all fields
sessions --create "feature-implementation" \
  -l "First learning" \
  -l "Second learning" \
  -q "Open question to explore" \
  -a "Next action item" \
  -i "001,002,003"
```

**Options:**
- `-l, --learning TEXT` - Add a learning (repeatable)
- `-q, --question TEXT` - Add an open question (repeatable)
- `-a, --action TEXT` - Add a next action (repeatable)
- `-i, --issues IDS` - Comma-separated issue IDs worked on

The command auto-generates the session ID and sets today's date.

## Workflow

### Session Start

User triggers with phrases like "load context", "what's the status", "last session", "where were we".

```bash
sessions
```

Review learnings, open questions, and next actions from last session.

### During Session

- Track which issues you create, close, or work on
- Note learnings as they emerge
- Capture open questions that arise

### Session End

Append a session entry capturing:
1. **Learnings** - insights that aren't actionable work items
2. **Open questions** - things to explore (not all become issues)
3. **Next actions** - concrete follow-ups (some may become issues)
4. **Issues worked** - link to issues skill for traceability

## Relationship to Issues

| Aspect | Sessions | Issues |
|--------|----------|--------|
| **Scope** | Time-bounded (one conversation) | Work-bounded (may span sessions) |
| **Focus** | What we learned (meta) | What we need to do (concrete) |
| **Sharing** | User-scoped by default, git-synced | Collaborative, git-synced |
| **References** | Can reference issues | Cannot reference sessions |

**Key insight:** Not everything in `open_questions` or `next_actions` needs to become an issue. Sessions capture the thought; issues formalize the commitment.

## Principles

- **Append-only**: Never modify existing sessions
- **User-scoped by default**: Sessions filter to current user; use `--user all` for collaboration
- **One-way dependency**: Sessions reference issues, not vice versa
