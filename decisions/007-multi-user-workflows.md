# ADR 007: Multi-User Workflows

**Status:** Accepted
**Date:** 2025-12-19 (updated 2025-12-20)

## Context

skill-issues was designed for single-user Claude Code sessions, with git providing implicit attribution through commit history. As adoption grows, small teams (~5 users) want to use these skills collaboratively on shared repositories.

The current design has several multi-user limitations:

1. **Session ownership** - Sessions have no user field; all sessions appear in one list with no filtering
2. **ID conflicts** - Sequential IDs (001, 002) conflict when users create issues/sessions concurrently offline
3. **ADR numbering** - Same conflict problem for numbered ADRs
4. **Configuration** - No mechanism to identify the current user

The goal is to support small team collaboration without introducing significant complexity, coordination servers, or breaking the local-first, git-native design principles.

## Decision

### User Identification via Git Config

User prefix is determined through a fallback chain:

1. **Environment variable**: `SKILL_ISSUES_PREFIX` (for CI/scripts)
2. **Git config**: `git config skill-issues.prefix` (explicit override)
3. **Derived**: First initial + last initial from `git config user.name` (e.g., "David Page" → "dp")
4. **Fallback**: "xx" if nothing else available

Configuration is set via standard git config:
```bash
# Global (one-time setup)
git config --global skill-issues.prefix "dp"

# Per-repo override (optional)
git config skill-issues.prefix "david"
```

No project-level config files are introduced. Git config already handles global vs local override and is already gitignored.

On first use with a derived prefix, display a hint:
```
Derived prefix "dp" from git config user.name "David Page"
To customize: git config --global skill-issues.prefix "yourprefix"
```

### Session Changes

**ID format change:** `dp-s001` → `dp-dp-s001`

Sessions gain a `user` field matching the prefix:
```json
{"id": "dp-dp-s001", "user": "dp", "date": "2025-12-19", "topic": "...", ...}
```

**Filtering behavior:**
- `sessions` - Shows only current user's sessions (default)
- `sessions --user all` - Shows all users' sessions
- `sessions --user xy` - Shows specific user's sessions
- `sessions board` - Tabs per user: current user first (selected by default), other users alphabetically, "All" tab last

The `--user` flag is orthogonal to query type, so it combines with other flags: `sessions --last 5 --user all`.

**ID generation:** `next_session_id()` generates IDs scoped to user prefix, e.g., if `dp-dp-s003` exists, next is `dp-dp-s004`.

**Pairing:** Sessions remain single-user. If two people pair, each creates their own session reflecting on the same work. Different perspectives are valuable, and this avoids complexity of multi-author filtering.

### Issue Changes

**ID format change:** `001` → `dp-001`

```json
{"ts": "...", "type": "created", "id": "dp-001", "title": "...", ...}
```

The hyphen separator improves readability and matches the session format (`dp-dp-s001`).

**No filtering by default** - Issues are shared work items, not personal. All users see all issues.

**ID generation:** `next_id()` generates IDs scoped to user prefix.

**Prefix constraints:** 2-4 characters, required (no blank prefix allowed).

### ADR Changes

**Draft naming convention:** New ADRs start as drafts with slug-only names:
```
.decisions/draft-multi-user-workflows.md
```

**Acceptance assigns number:** When transitioning to Accepted status:
```bash
adr accept draft-multi-user-workflows
# Renames to: 007-multi-user-workflows.md
```

The `adr accept` command:
1. Finds next available number
2. Renames file preserving the slug
3. Updates Status field from Draft to Accepted

**Reference resolution:** References use the slug (e.g., "see the multi-user-workflows ADR"). The slug is preserved through the draft→numbered transition, making references searchable. No automated reference rewriting is needed.

**Conflict handling:** If two users accept ADRs simultaneously, git merge conflict occurs. This is appropriate - accepting an ADR is a deliberate coordination point for small teams.

### Per-User Event Files

Rather than a shared `events.jsonl` that all users append to, each user writes to their own file:

```
.issues/
  events-dp.jsonl    # dp's events
  events-jb.jsonl    # jb's events
.sessions/
  events-dp.jsonl
  events-jb.jsonl
```

**Event routing:** Events go to the **actor's file**, not the entity owner's file:
- If `jb` adds a note to issue `dp-001`, that event goes in `events-jb.jsonl`
- When loading issues, aggregate events from all user files

**Benefits:**
- **Zero merge conflicts** - Each user only appends to their own file
- **Simpler git workflow** - No conflict resolution overhead
- **Trivial per-user queries** - `cat .issues/events-dp.jsonl` without parsing
- **Clear separation of actor vs entity** - Issue creator (in ID) and event actor (in file) are distinct concepts

**Reading:** Aggregate all `events-*.jsonl` files, sort by timestamp. The `*` glob naturally discovers all users.

**Legacy compatibility:** Also read from `events.jsonl` (shared legacy file) if present, using the `user` field for filtering.

### Migration Strategy

Existing repositories have unnumbered sessions (`dp-s001`) and issues (`001`). Given there are only ~3 existing projects:

- **Manual migration** is acceptable
- Add user prefix to existing IDs in the JSONL files
- Add `user` field to existing sessions
- Legacy `events.jsonl` files continue to work (read path checks both)

No automated migration tooling is planned unless adoption grows significantly.

## Consequences

### Positive

- **Zero coordination** - Users can create issues/sessions offline without conflicts
- **Zero merge conflicts** - Per-user files mean no JSONL append conflicts
- **Clear ownership** - Prefix immediately shows who created an item
- **Actor vs entity separation** - Event files track who did the action, IDs track who created the entity
- **No new config files** - Uses existing git config infrastructure
- **Minimal friction** - Works out of the box with derived prefix
- **Git-native** - All data still merges cleanly through git

### Negative

- **Longer IDs** - `dp-001` vs `001`, `dp-dp-s001` vs `dp-s001` (minor, ~3-5 chars)
- **Loses global ordering** - Can't tell at a glance that `jb-003` came after `dp-002` (use timestamps for ordering)
- **Migration needed** - Existing repos need manual ID updates
- **Prefix coordination** - Team members need unique prefixes (but 2-letter initials rarely collide for ~5 people)

### Neutral

- Sessions filtered by default may surprise users expecting to see teammate's sessions (mitigated by `--user all` flag and clear messaging)

## Alternatives Considered

### Central ID coordination server
Rejected: Violates local-first principle, adds infrastructure dependency.

### User ID ranges (Alice: 100-199, Bob: 200-299)
Rejected: Arbitrary limits, ugly, doesn't scale.

### UUID-based IDs with computed short refs
Rejected: Loses the nice short `001` identifiers, refs become unstable after merges.

### Project-level config file for prefix
Rejected: Adds friction - where does it live? When initialized? How documented? Git config already solves this.

### Multi-author sessions
Rejected: Adds complexity for rare use case. Each person can create their own session about paired work.

### Automated reference rewriting for ADRs
Rejected: High complexity, low frequency need. Slug preservation + search is sufficient.

## Related Issues

- dp-080: Add get_user_prefix() utility function (foundation)
- dp-081: Update session ID format to include user prefix
- dp-082: Add --all flag for cross-user session viewing
- dp-083: Add user filtering to sessions board TUI
- dp-084: Update issue ID format to include user prefix
- dp-085: Add draft ADR naming convention
- dp-086: Add adr accept command
- dp-087: Update SKILL.md files for multi-user workflows
- dp-088: Add first-run prefix derivation hint

## Resolved Questions

1. **Prefix length:** Constrained to 2-4 characters. Provides predictable ID lengths for UI layout while allowing flexibility beyond just initials.

2. **Issue display:** Issues show creator in the ID format `dp-083` (with hyphen for readability). Issue cards and CLI output use this format consistently. All issues remain visible to all users (no filtering).

3. **Sessions board UI:** Tabs per user, ordered with current user first (selected by default), then other users alphabetically, then "All" tab last.

4. **Blank prefix:** Not allowed. Prefix is required (2-4 chars). This ensures consistent ID formats everywhere and avoids parsing ambiguity between legacy `001` and new `dp001` formats. Existing repos migrate manually (only ~3 repos, simple JSONL edits).

5. **Sessions user filtering API:** Use `--user PREFIX` flag rather than repurposing `--all`. Query type (which sessions: `--all`, `--last N`, `--issue ID`, `--topic X`) and user scope (`--user`) are orthogonal dimensions. The `--user` flag mirrors GitHub CLI patterns (e.g., `gh pr list --author`), making it discoverable for both human users and Claude agents familiar with gh conventions.
