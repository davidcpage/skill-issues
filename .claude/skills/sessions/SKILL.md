# Sessions Skill

Personal session memory for AI agent conversations. Captures learnings, open questions, and next actions across sessions.

**Portable:** This skill directory can be copied to any repo. Data lives in `.memory/sessions.jsonl` (project root).

## Permissions

Add to `.claude/settings.json`:
```json
{"permissions": {"allow": ["Bash(python3 .claude/skills/sessions/sessions.py:*)"]}}
```

**Dependency:** This skill references the [issues skill](../issues/SKILL.md) via the `issues_worked` field. Issues do not reference sessions (one-way dependency). See `.decisions/001-sessions-vs-issues.md` for rationale.

## Tools

- `sessions.py` - Query and create tool for sessions (auto-creates data file if missing)

## Data Location

Sessions are stored in `.memory/sessions.jsonl` (project root) - one JSON object per line, append-only.

**Note:** Sessions are personal (single-user). Unlike issues, they are not designed for multi-user sync via git.

## Read vs Write Strategy

| Operation | Method | Notes |
|-----------|--------|-------|
| All reads | `sessions.py` | Auto-initializes, outputs JSON |
| Create | `sessions.py --create` | Auto-generates ID and date |

## Schema

```json
{
  "id": "s001",
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
  "issues_worked": ["014", "015"]
}
```

**Fields:**
- `id`: Unique session ID (e.g., "s001", "s002")
- `date`: ISO date (YYYY-MM-DD)
- `topic`: Primary topic or theme of the session
- `learnings`: Key insights - meta-knowledge, not actionable work
- `open_questions`: Unresolved questions to explore (may or may not become issues)
- `next_actions`: Concrete follow-ups (may or may not become issues)
- `issues_worked`: Array of issue IDs created, closed, or worked on (optional, references issues skill)

## Reading Sessions

```bash
# Last session (default - most common for session startup)
python3 .claude/skills/sessions/sessions.py

# Last N sessions
python3 .claude/skills/sessions/sessions.py --last 3

# All sessions
python3 .claude/skills/sessions/sessions.py --all

# All open questions across sessions
python3 .claude/skills/sessions/sessions.py --open-questions

# All next actions (with session attribution)
python3 .claude/skills/sessions/sessions.py --next-actions

# Search by topic
python3 .claude/skills/sessions/sessions.py --topic beads

# Find sessions that worked on a specific issue
python3 .claude/skills/sessions/sessions.py --issue 014

# Generate markdown summary for documentation
python3 .claude/skills/sessions/sessions.py --summary

# Generate markdown timeline of sessions
python3 .claude/skills/sessions/sessions.py --timeline

# Show help
python3 .claude/skills/sessions/sessions.py --help
```

**Note:** `--recent` is accepted as an alias for `--last`. Unknown flags produce a warning.

## Documentation Output

Generate formatted markdown for READMEs and documentation:

```bash
# Full summary with overview, timeline, key learnings, and open questions
python3 .claude/skills/sessions/sessions.py --summary

# Timeline grouped by date with session stats
python3 .claude/skills/sessions/sessions.py --timeline
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
python3 .claude/skills/sessions/sessions.py --create "topic-slug"

# Full session with all fields
python3 .claude/skills/sessions/sessions.py --create "feature-implementation" \
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
python3 .claude/skills/sessions/sessions.py
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
| **Sharing** | Personal, local | Collaborative, git-synced |
| **References** | Can reference issues | Cannot reference sessions |

**Key insight:** Not everything in `open_questions` or `next_actions` needs to become an issue. Sessions capture the thought; issues formalize the commitment.

## Principles

- **Append-only**: Never modify existing sessions
- **Personal**: Not designed for multi-user sync
- **One-way dependency**: Sessions reference issues, not vice versa
- **Lightweight**: Single Python script, no external dependencies
