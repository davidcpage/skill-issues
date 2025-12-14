# skill-issues

Lightweight, local-first skills for Claude Code.

## What's Inside

Three tools designed for AI coding agents, stored as simple files in your repo:

| Skill | What it does |
|-------|--------------|
| **issues** | Local issue tracking inspired by GitHub Issues. A more granular companion for tracking work during development sessions. |
| **sessions** | Session memory that persists learnings, open questions, and next actions across conversations. Fully inspectable and user-managed. |
| **adr** | Architecture Decision Records using RFC/PEP-style format. |

All data lives in your repo as append-only JSONL files - no external services, no daemons, easy to read and edit directly.

## Quick Start

### Option 1: Copy skills to your project

```bash
# Clone this repo
git clone https://github.com/YOUR_USERNAME/skill-issues.git

# Copy skills to your project
cp -r skill-issues/.claude/skills/issues /path/to/your/project/.claude/skills/
cp -r skill-issues/.claude/skills/sessions /path/to/your/project/.claude/skills/
cp -r skill-issues/.claude/skills/adr /path/to/your/project/.claude/skills/
```

### Option 2: Use as template

Fork this repo and use it as a starting point. The example data shows the skills in action.

## Usage

### Issues

```bash
# View ready (unblocked) issues
python3 .claude/skills/issues/issues.py --ready

# Create an issue
python3 .claude/skills/issues/issues.py --create "Add dark mode" \
  --type feature --priority 2 --description "User requested dark theme"

# Close an issue
python3 .claude/skills/issues/issues.py --close 001 "Implemented in commit abc123"

# Add a note
python3 .claude/skills/issues/issues.py --note 001 "Blocked on design review"

# View dependency diagram
python3 .claude/skills/issues/issues.py --diagram
```

### Sessions

```bash
# View last session
python3 .claude/skills/sessions/sessions.py

# View all open questions
python3 .claude/skills/sessions/sessions.py --open-questions

# Create a session summary
python3 .claude/skills/sessions/sessions.py --create "auth-refactor" \
  -l "JWT tokens work better than sessions for our API" \
  -l "Need to handle token refresh on 401" \
  -q "Should we use refresh tokens or short-lived access tokens?" \
  -a "Implement token refresh logic" \
  -i "012,015"
```

### ADRs

Create markdown files in `.decisions/` following the template in `.claude/skills/adr/SKILL.md`.

```
.decisions/
├── 001-database-choice.md
├── 002-api-versioning.md
└── 003-auth-strategy.md
```

## Dogfooding

This repo was built using its own skills. The `.issues/` and `.memory/` directories contain the actual issues and session logs from development:

- **46 issues** tracked from initial prototype to publishable skills
- **22 sessions** capturing learnings about append-only logs, skill design, and more
- **3 ADRs** documenting key design decisions

Explore them to see the skills in real use.

## Philosophy

1. **Local-first** - No external services, just files in your repo
2. **Git-friendly** - Append-only JSONL means clean diffs and easy merges
3. **AI-native** - Optimized for Claude Code, not human CLI ergonomics
4. **Lightweight** - No daemons, databases, or complex setup

## Background: Why This Works

This project was inspired by [beads](https://github.com/steveyegge/beads) by Steve Yegge - a sophisticated agent memory system with git-backed JSONL, SQLite caching, and daemon architecture. These skills are a simplified take on similar ideas.

While exploring why Claude Code can work fluently with tools like beads or these skills with no special training, Claude Opus 4.5 introduced the term **protocol fitness** to describe the phenomenon. AI agents have seen millions of issue trackers, RFCs, and changelog formats in training data. This means they already understand the workflows - how to triage issues, track blockers, close with a reason, link related work.

The [development logs](docs/development-history.md) capture more discussion of this idea.

## Contributing

Issues and PRs welcome.

## License

MIT
