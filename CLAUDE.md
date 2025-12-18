# CLAUDE.md

Instructions for Claude Code when working with this repository.

## Skills Included

This repo provides three Claude Code skills designed around **protocol fitness** - formats that LLMs know well from training data.

- **issues** - Local-first issue tracking with GitHub Issues semantics
- **sessions** - Capture learnings, open questions, and next actions across sessions
- **adr** - Architecture Decision Records using familiar RFC/PEP patterns

Each skill is self-documenting via its `SKILL.md` file. Invoke them naturally by describing what you want to do.

## Example Data

This repo includes real data from building these skills:
- `.issues/events.jsonl` - Issues tracking the project
- `.memory/sessions.jsonl` - Sessions of learnings
- `.decisions/` - Design decisions made along the way

## Installation

Install the `skill-issues` package to get the CLI tools:

```bash
uv tool install skill-issues
```

This provides global `issues` and `sessions` commands that work in any project directory.

### Features

**Issues CLI:**
- `issues --open` / `issues --ready` / `issues --closed` - Query issues
- `issues --create "Title"` / `issues --close ID "Reason"` - Manage issues
- `issues --diagram` - Visualize dependencies
- `issues board` - Interactive Kanban TUI

**Sessions CLI:**
- `sessions` - Show last session
- `sessions --last 3` / `sessions --topic keyword` - Query sessions
- `sessions --create "topic"` - Create session
- `sessions board` - Interactive TUI browser

### Permissions

Add to your project's `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(issues:*)",
      "Bash(sessions:*)"
    ]
  }
}
```

### Using Skills in Other Projects

Copy the skill directories to register the skills with Claude Code:

```bash
# Copy skill definitions (SKILL.md files only)
cp -r .claude/skills/issues .claude/skills/sessions .claude/skills/adr /path/to/your/project/.claude/skills/
```

The CLI tools are installed globally via `uv tool install`, so they work in any project once installed.

Data directories (`.issues/`, `.memory/`, `.decisions/`) are created automatically on first use.

## Development Notes

### Testing imports

Use `uv run python` to test Python imports during development:

```bash
uv run python -c "from skill_issues.issues import tui; print('OK')"
```

### Reinstalling after changes

When developing locally, `uv tool install` caches built packages. If changes aren't reflected after reinstall:

```bash
uv tool uninstall skill-issues
uv cache clean
uv tool install .
```
