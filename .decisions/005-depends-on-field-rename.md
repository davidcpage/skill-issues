# Decision 005: Rename blocked_by to depends_on

**Status:** Accepted
**Date:** 2025-12-16

## Context

The issues skill uses a `blocked_by` field to express dependencies between issues. When issue A has `blocked_by: ["B", "C"]`, it means A cannot be worked on until B and C are resolved.

However, the field name `blocked_by` is semantically awkward:
- "Issue A is blocked by B" makes sense when B is open
- "Issue A is blocked by B" reads strangely when B is closed - it implies active blocking
- A closed dependency is still a dependency, it's just satisfied

## Decision

Rename `blocked_by` to `depends_on` across the codebase.

## Rationale

1. **Semantic accuracy**: `depends_on` describes the relationship, not the current state. A closed dependency is still a dependency - it's just satisfied.

2. **Consistency with conventions**: Package managers (npm, pip, cargo) and build systems (make, bazel) use "depends on" terminology. This aligns with developer mental models.

3. **Separation of concerns**: The field describes the *relationship*. The *status* (blocked vs ready) is a derived property based on whether dependencies are satisfied.

4. **Better UI language**: "Depends on: 064" reads correctly regardless of whether 064 is open or closed. The TUI can still show "blocked" status for issues with unsatisfied dependencies.

## Alternatives Considered

| Option | Pros | Cons |
|--------|------|------|
| `blocked_by` (current) | Immediately actionable language | Semantically wrong when blocker is closed |
| `depends_on` | Accurate, matches conventions | Slightly less urgent feel |
| `requires` | Clear | Perhaps too strong |
| `after` | Simple | Too vague |

## Migration Strategy

### Phase 1: Backwards-compatible read (this PR)

The code will:
- **Read**: Accept both `blocked_by` and `depends_on` in events
- **Write**: Always write `depends_on` for new events
- **Display**: Show as "Depends on" in TUI/CLI output

This allows old data to continue working without migration.

### Phase 2: Data migration (optional, future)

A migration script could rewrite `events.jsonl` to use `depends_on`, but this is optional since Phase 1 provides full compatibility.

## Changes Required

### Code changes
- `store.py`: Read both field names, write `depends_on`
- `cli.py`: Rename `--blocked-by` flag to `--depends-on` (keep `-b` alias)
- `tui.py`: Update display text
- `SKILL.md`: Update documentation

### CLI interface changes

| Before | After |
|--------|-------|
| `--blocked-by 001,002` | `--depends-on 001,002` |
| `-b 001,002` | `-b 001,002` (unchanged) |
| `--block ID DEPS` | `--add-dep ID DEPS` |
| `--unblock ID DEPS` | `--remove-dep ID DEPS` |

## Impact

- **Breaking**: CLI flag names change (but short flags preserved)
- **Non-breaking**: Old event data continues to work
- **Documentation**: SKILL.md needs update

## References

- Issue dp-073: Rename blocked_by field to depends_on
- ADR 002: Documents `blocked_by` as structural field (D2)
