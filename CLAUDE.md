# CLAUDE.md

Instructions for Claude Code when working with this repository.

## Skills Included

This repo provides three Claude Code skills designed around **protocol fitness** - formats that LLMs know well from training data.

### Issues Skill
Local-first issue tracking with GitHub Issues semantics.

```bash
python3 .claude/skills/issues/issues.py --ready                    # Unblocked issues
python3 .claude/skills/issues/issues.py --create "Title" -d "Desc" # Create issue
python3 .claude/skills/issues/issues.py --close ID "Reason"        # Close issue
python3 .claude/skills/issues/issues.py --note ID "Note text"      # Add note
python3 .claude/skills/issues/issues.py --diagram                  # Dependency graph
```

### Sessions Skill
Capture learnings, open questions, and next actions across sessions.

```bash
python3 .claude/skills/sessions/sessions.py                        # Last session
python3 .claude/skills/sessions/sessions.py --open-questions       # All open questions
python3 .claude/skills/sessions/sessions.py --create "topic" \
  -l "Learning" -q "Question" -a "Action"                          # Create session
```

### ADR Skill
Architecture Decision Records using familiar RFC/PEP patterns.

See `.claude/skills/adr/SKILL.md` for conventions. ADRs go in `.decisions/`.

## Example Data

This repo includes real data from building these skills:
- `.issues/events.jsonl` - 45 issues tracking the project
- `.memory/sessions.jsonl` - 20 sessions of learnings
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
