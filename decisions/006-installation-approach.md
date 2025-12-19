# Decision 006: Installation Approach

**Status:** Accepted
**Date:** 2025-12-16

## Context

The skill-issues package needs an installation workflow that:
1. Installs CLI tools (`issues`, `sessions`, `adr`)
2. Registers skills with Claude Code (copies SKILL.md to project's `.claude/skills/`)
3. Sets up permissions in `.claude/settings.json`
4. Works for both development (git clone) and future PyPI distribution

The initial approach used a shell script (`init.sh`) but this:
- Required users to know where they cloned the repo
- Was separate from the CLI tools
- Didn't support per-skill installation

## Decision

**Implement `init` as a CLI subcommand with symlinks for editable installs:**

```bash
# Install all skills
issues init --all /path/to/project

# Install individual skills
issues init /path/to/project
sessions init /path/to/project
adr init /path/to/project
```

**Behavior:**
- For editable installs (git clone): Create symlinks to repo's `.claude/skills/`
- For wheel installs (PyPI): Copy SKILL.md files from package data
- Merge permissions into existing `.claude/settings.json`
- Idempotent (safe to run multiple times)

## Rationale

### Symlinks for editable installs

When installed via `uv tool install -e .`, symlinks mean:
- `git pull` updates CLI code, SKILL.md files, and everything else
- No need to re-run init after updates
- Matches developer expectations from npm link, pip install -e

### Copy for wheel installs

PyPI wheels don't have access to the repo, so copying is the only option. This is acceptable because:
- SKILL.md files rarely change (instructions for Claude, not code)
- Users can re-run `issues init --all` after `uv tool upgrade` if needed
- Most users will use the git clone workflow anyway

### Per-skill init commands

Each CLI owns its skill's installation:
- `issues init` installs issues skill + `Bash(issues:*)` permission
- `sessions init` installs sessions skill + `Bash(sessions:*)` permission
- `adr init` installs adr skill (no permission needed, no CLI)

This allows users to pick and choose. The `--all` flag on `issues init` is a convenience for installing everything.

### Detection logic

```python
def _is_editable_install() -> bool:
    """Check if running from an editable install (git clone)."""
    repo_skills = _REPO_ROOT / ".claude" / "skills"
    return repo_skills.exists() and repo_skills.is_dir()
```

If the repo's `.claude/skills/` directory exists relative to the package, we're in an editable install and use symlinks.

## Consequences

### Positive

- Single workflow: clone, install, init
- `git pull` updates everything for editable installs
- Per-skill installation for users who want just one skill
- Clean path to PyPI distribution

### Negative

- PyPI users need to re-run init after upgrades to get updated SKILL.md files
- Symlinks may confuse users unfamiliar with them

### Neutral

- `init.sh` removed (functionality moved to CLI)
- Three CLI entry points instead of two (`adr` added)

## Quick Start (README)

```bash
git clone https://github.com/davidcpage/skill-issues.git
cd skill-issues
uv tool install -e .
issues init --all /path/to/your/project
```

## Alternatives Considered

### A. Keep init.sh

**Rejected.** Shell script is separate from CLI, harder to discover, doesn't support per-skill installation.

### B. Always copy, never symlink

**Rejected.** Breaks the "git pull updates everything" workflow that developers expect from editable installs.

### C. Always symlink, even for PyPI

**Not possible.** PyPI wheels don't include the repo structure, only package data.

### D. Require manual skill registration

**Rejected.** Too much friction. The init command automates what was previously 5+ manual steps.

## Related

- ADR 004: CLI and TUI Package
- Issue dp-076: Add init subcommand to issues CLI
- Issue dp-077: Add init subcommand to sessions CLI
- Issue dp-078: Add minimal adr CLI with init subcommand
