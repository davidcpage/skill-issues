# ADR 008: Folder Structure for Skills Data

**Status:** Accepted
**Date:** 2025-12-19

## Context

skill-issues provides three skills with different storage needs:

| Skill | Current Location | Content Type |
|-------|-----------------|--------------|
| ADRs | `.decisions/` | Markdown documentation |
| Issues | `.issues/events.jsonl` | Append-only event log |
| Sessions | `.memory/sessions.jsonl` | Append-only event log |

The current structure has several problems:

1. **ADRs hidden inappropriately** - Architecture Decision Records are documentation meant to be read by developers, reviewed in PRs, and referenced during design discussions. Hiding them in a dot-folder is counterintuitive and reduces discoverability.

2. **Inconsistent naming** - `.memory/` is abstract and unclear; `.sessions/` would be more obvious.

3. **Inconsistent internal files** - Issues uses `events.jsonl`, sessions uses `sessions.jsonl`.

## Decision

### ADRs: Move to Visible `decisions/` Folder

ADRs move from `.decisions/` to `decisions/` at the project root.

```
decisions/
  001-sessions-vs-issues.md
  002-github-issues-compatibility.md
  ...
```

Rationale:
- ADRs are documentation, not data - they should be visible
- Root-level `decisions/` is clear and unlikely to clash with existing project folders
- Doesn't assume the project has a `docs/` folder with a particular structure
- Matches common conventions (adr-tools uses `doc/adr/`, many use `docs/decisions/`)

### Issues and Sessions: Keep Hidden, Standardize Naming

Issues and sessions remain in hidden folders because:
- They're append-only event logs (data stores), not human-readable documentation
- Users interact via CLI/TUI, not by reading files directly
- Similar to `.git/` - important infrastructure but not meant for browsing

Naming changes for consistency:
- `.memory/` renamed to `.sessions/`
- `sessions.jsonl` renamed to `events.jsonl` (matches issues)

New structure:
```
.issues/
  events.jsonl
.sessions/           # renamed from .memory
  events.jsonl       # renamed from sessions.jsonl
```

### Migration Strategy

Given only ~3 repositories and ~2 users currently:

1. **CLI auto-migration** - On first access, if old location exists and new doesn't:
   - Move/rename the folder/file automatically
   - Print a one-time message: "Migrated .memory/ to .sessions/"

2. **Backward compatibility period** - For one release cycle:
   - Check both old and new locations when reading
   - Write only to new location
   - After migration, old location won't exist

3. **SKILL.md updates** - Update all SKILL.md files to reference new locations

4. **init command updates** - `issues init` and `sessions init` create new folder structure

## Consequences

### Positive

- **ADRs discoverable** - Developers can browse decisions in file tree without knowing to look in hidden folder
- **Clear separation** - Documentation (visible) vs data stores (hidden)
- **Consistent naming** - `.sessions/` is obvious, `events.jsonl` used everywhere
- **Low migration cost** - Auto-migration with few existing repos

### Negative

- **Breaking change** - Existing repos need migration (mitigated by auto-migration)
- **Git history** - Moving `.decisions/` to `decisions/` may complicate git blame (use `git log --follow`)

### Neutral

- **Three separate folders** - Could consolidate into one `.skill-issues/` folder, but separate folders allow independent skill installation

## Alternatives Considered

### Single `.dev/` or `dev/` folder for everything
```
dev/
  adr/
  issues.jsonl
  sessions.jsonl
```
Rejected: Couples the three skills together. They're designed to be independently installable. Also `dev/` could clash with development tooling folders.

### Keep ADRs hidden, just fix naming
Rejected: ADRs really are documentation and benefit from visibility. The naming inconsistency is minor compared to the discoverability issue.

### `docs/adr/` instead of `decisions/`
Rejected: Many projects have `docs/` with their own structure. Root-level `decisions/` is cleaner and makes no assumptions.

### `.adr/` (hidden but standardized)
Rejected: Doesn't solve the core problem - ADRs should be visible.

## Related Issues

- dp-092: Implement folder structure changes from ADR 008
