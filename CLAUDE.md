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
- `issues create "Title"` / `issues close ID "Reason"` - Manage issues
- `issues note ID "Content"` - Add notes to issues
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

Use `issues init` to set up skills in any project:

```bash
# In the target project directory
issues init --all           # Install all skills (issues, sessions, adr)
issues init                  # Install just issues skill
sessions init                # Install just sessions skill
```

This copies SKILL.md files and configures permissions in `.claude/settings.json`.

### Updating Skills

When skill-issues is updated, refresh SKILL.md files in your projects:

```bash
# First update the CLI tool
uv tool install --upgrade skill-issues

# Then update SKILL.md files in your project
issues init --all --update
```

The `--update` flag overwrites existing SKILL.md files with the latest versions. It only affects documentation - your data (`.issues/`, `.memory/`, `.decisions/`) is never modified.

Data directories are created automatically on first use.

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
