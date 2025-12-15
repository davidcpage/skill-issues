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

## Using in Your Project

Copy the skills you want to your project:

```bash
# Copy all skills
cp -r .claude/skills/issues .claude/skills/sessions .claude/skills/adr /path/to/your/project/.claude/skills/

# Or just the ones you need
cp -r .claude/skills/issues /path/to/your/project/.claude/skills/
```

Data directories (`.issues/`, `.memory/`, `.decisions/`) are created automatically on first use.

### Permissions

Add to your project's `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(python3 .claude/skills/issues/issues.py:*)",
      "Bash(python3 .claude/skills/sessions/sessions.py:*)"
    ]
  }
}
```
