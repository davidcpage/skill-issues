# Decision 001: Keep Sessions and Issues Separate

**Date:** 2025-12-13
**Status:** Decided
**Issue:** 016

## Context

We have two tracking systems:
- **Sessions** (`.memory/sessions.jsonl`) - capture learnings, context, open questions, next actions from each conversation
- **Issues** (`.issues/events.jsonl`) - track concrete work items with priorities, dependencies, notes

Question: Are we overcomplicating by having both? Should they merge?

## Data

At time of decision:
- 7 sessions capturing learnings, questions, next actions
- 17 issues (3 open, 14 closed) tracking work items

## Analysis

### What Each System Captures

| Dimension | Sessions | Issues |
|-----------|----------|--------|
| **Scope** | Time-bounded (one conversation) | Work-bounded (may span sessions) |
| **Focus** | What we learned (meta) | What we need to do (concrete) |
| **Key fields** | learnings, open_questions, next_actions | title, priority, blocked_by, notes |
| **Query patterns** | "Where were we?", "What did we learn about X?" | "What's ready?", "What's blocking Y?" |

### The Orthogonality Insight

These track **orthogonal dimensions**:
- A session may touch multiple issues
- An issue may span multiple sessions

Example from our data:
```
Session dp-s006 ──┬── Issue dp-005 (closed in dp-s006)
               ├── Issue dp-014 (created in dp-s006, still open)
               ├── Issue dp-015 (created in dp-s006, still open)
               └── Issue dp-016 (created in dp-s006, still open)

Issue dp-017 was created and closed entirely within dp-s007
```

### Arguments for Keeping Separate

1. **Different lifecycles** - sessions end when conversation ends; issues end when work completes
2. **Learnings don't fit in issues** - "beads uses hash IDs to prevent merge conflicts" isn't actionable work
3. **Open questions aren't always issues** - "Would structured note types add value?" is exploratory, not committed work
4. **Query needs differ** - "load context" wants last session; "what's ready" wants unblocked issues

### Arguments for Merging

1. **next_actions overlap** - session next_actions often become issues
2. **Two systems to maintain** - cognitive overhead
3. **Linking creates coupling** - already have `issues_worked` and `session` field

### What Would Merging Look Like?

**Option A: Issues absorb sessions**
- Add `learning` event type to issues
- Add `question` event type (open questions as special issue type)
- Problem: Lose the "session as unit" concept; learnings become awkward entries

**Option B: Sessions absorb issues**
- Issues become entries in a session log
- Problem: Lose cross-session issue continuity; doesn't work for multi-session issues

**Option C: Unified event log**
- Single events.jsonl with session_start, session_end, issue_created, note, learning, question, etc.
- Problem: Complex schema, serves neither purpose optimally

## Decision

**Keep sessions and issues separate.**

The current linking mechanism (`issues_worked` in sessions, `session` field in issues) is the right design - it connects two orthogonal tracking systems without conflating them.

The overlap where `next_actions` sometimes become issues is actually healthy: sessions capture the thought, issues formalize the commitment. Not everything in `next_actions` needs to become an issue.

## Consequences

1. Continue maintaining both `.memory/` and `.issues/` systems
2. Use bidirectional linking when relevant (not mandatory)
3. Deprioritize issue dp-014 (session tooling) and 015 (field granularity) unless real pain emerges
4. Accept minor cognitive overhead as cost of cleaner separation of concerns

---

## Evolution: One-Way Dependency (Issue dp-018)

**Date:** 2025-12-13
**Issue:** 018

### New Insight

The original decision allowed bidirectional linking (`issues_worked` in sessions, `session` field in issues). A sharing model analysis reveals this is problematic:

| | Issues | Sessions |
|---|--------|----------|
| **Scope** | Multi-user, shared via git | Single-user, personal |
| **Sync** | Collaborative | Local only |

If I create issue dp-017 with `session: "dp-s008"` and you sync via git, that reference is meaningless to you - you don't have my session dp-s008.

### Refined Decision

**One-way dependency: sessions → issues only**

- Sessions MAY reference issues via `issues_worked`
- Issues MUST NOT reference sessions

This keeps issues as clean, portable, shareable units while sessions remain personal annotations layered on top.

### Querying Still Works

"Show all sessions that worked on issue dp-017":
```bash
jq -s '.[] | select(.issues_worked | contains(["017"]))' .memory/sessions.jsonl
```

### Skill Architecture Implication

This suggests a clean skill separation:

| Skill | Aware of | Responsibility |
|-------|----------|----------------|
| `issues` | Nothing | CRUD issues, query, dependencies - self-contained |
| `sessions` | `issues` | CRUD sessions, link to issues, query history |

The dependency flows one direction, matching the data model.

### Updated Consequences

1. Remove `session` field from issue event schema
2. Keep `issues_worked` in session schema
3. Issues skill is standalone; sessions skill imports from issues
4. Existing `session` fields in events.jsonl can remain (historical) but new events should omit them
