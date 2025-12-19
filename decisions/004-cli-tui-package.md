# ADR 004: CLI and TUI Package

**Status:** Draft
**Date:** 2025-12-16

## Context

The skill-issues repo provides `issues.py` and `sessions.py` as standalone scripts designed primarily for AI invocation via Claude Code. They work but have limitations:

1. **Verbose invocation**: `python3 .claude/skills/issues/issues.py list --open`
2. **No human-friendly visualization**: Output is JSON, optimized for machine consumption
3. **Copy-based installation**: Users copy scripts to each project

Human users need efficient ways to gather context from past sessions and see project status at a glance. A multi-turn conversation with Claude to incrementally explore sessions is slow compared to a scrollable TUI view.

Inspiration: [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) provides a TUI for the beads issue tracker with split-view, kanban board, and vim-style navigation.

## Decision

**Package the skills as an installable Python package (`skill-issues`) with:**

1. **CLI entry points** as bare commands:
   - `issues` - issue tracking commands
   - `sessions` - session memory commands

2. **TUI subcommands** for human visualization:
   - `issues board` - kanban board view of issues
   - `sessions board` - scrollable session browser

3. **Install via uv tool**:
   ```bash
   uv tool install skill-issues
   ```

4. **Use Textual** for the TUI framework (Python, good widget library, stays in existing stack)

5. **Backwards compatible**: Raw scripts continue to work for copy-based installation

## Consequences

### Positive

- Clean CLI: `issues list --open` instead of verbose python path
- Human-friendly visualization without leaving terminal
- Single install, available across all projects
- Natural home for future enhancements (shell completion, etc.)
- Textual stays in Python ecosystem (no Go dependency)

### Negative

- Adds Textual as a dependency (~10MB)
- Users must install once (vs zero-install copy)
- Two invocation paths to document (installed CLI vs raw scripts)

### Neutral

- Claude Code permissions become cleaner: `Bash(issues:*)` vs long paths
- TUI is read-only initially; mutations still go through CLI commands

## Alternatives Considered

### A. Bubble Tea (Go)

**Rejected.** Would require adding Go to the project. Faster binary, but Textual is fast enough for this use case and keeps the stack homogeneous.

### B. Rich output only (no interactivity)

**Deferred.** Could add `--dashboard` flags for formatted output piped to `less -R`. Simpler, but loses navigation and filtering. May revisit as a lightweight alternative for environments where Textual is too heavy.

### C. Namespace command (`skill issues`, `skill sessions`)

**Rejected.** Adds unnecessary prefix. `issues` and `sessions` are unlikely to conflict with existing tools, and bare commands are more ergonomic.

## Implementation Plan

### Phase 1: Package Structure

1. Create `pyproject.toml` with:
   - Package metadata (name: `skill-issues`)
   - Entry points for `issues` and `sessions` commands
   - Textual dependency (optional extra initially, then required)

2. Create `src/skill_issues/` package structure:
   ```
   src/skill_issues/
   ├── __init__.py
   ├── issues/
   │   ├── __init__.py
   │   ├── cli.py          # argparse CLI (refactored from issues.py)
   │   ├── store.py        # data layer (load_issues, append_event, etc.)
   │   └── tui.py          # Textual app for kanban board
   ├── sessions/
   │   ├── __init__.py
   │   ├── cli.py          # argparse CLI (refactored from sessions.py)
   │   ├── store.py        # data layer
   │   └── tui.py          # Textual app for session viewer
   └── tui/
       ├── __init__.py
       └── widgets.py      # shared TUI components
   ```

3. Refactor existing scripts:
   - Extract data layer (store) from CLI logic
   - CLI imports store and provides argparse interface
   - TUI imports store and provides Textual interface

### Phase 2: Sessions TUI (`sessions board`)

Priority: Sessions viewer first (sharpest pain point for human context-gathering)

Features:
- Left panel: session list with date, topic, counts
- Right panel: expanded view of selected session (learnings, questions, actions)
- Vim navigation: `j/k` to move, `Enter` to expand, `q` to quit
- Search/filter: `/` to filter by topic

### Phase 3: Issues TUI (`issues board`)

Features:
- Kanban columns: Ready | In Progress | Blocked | Closed
- Issue cards showing ID, title, priority badge
- Expand to see description, notes, blockers
- Filter by priority, labels, type

### Phase 4: Polish and Documentation

- Shell completion scripts
- README with installation and usage
- Update CLAUDE.md with new invocation patterns
- Permissions examples for Claude Code

## Related Issues

- To be created for each implementation phase

## Open Questions

1. Should `issues board` show closed issues by default or require a flag?
2. Do we want a combined dashboard view, or just separate `sessions board` and `issues board`?
3. Should TUI support write operations (close issue, add note) or stay read-only?

## Lessons Learned

### uv tool install caching

When developing locally with `uv tool install .`, uv aggressively caches the built wheel. Using `--force` or even uninstall/reinstall may not pick up source changes. The reliable workaround:

```bash
uv tool uninstall skill-issues
uv cache clean
uv tool install .
```

This clears the cached wheel and forces a fresh build. Document this for contributors.

## References

- [beads_viewer](https://github.com/Dicklesworthstone/beads_viewer) - TUI inspiration
- [Textual](https://textual.textualize.io/) - Python TUI framework
- [skill-issues-tui.md](../research-notebook/dev/planning/features/skill-issues-tui.md) - initial concept doc
