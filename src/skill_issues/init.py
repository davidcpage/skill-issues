"""Shared initialization logic for skill-issues.

Handles copying skill files and updating permissions for Claude Code projects.
"""

import json
import sys
from pathlib import Path
from typing import Any


SKILLS = ["issues", "sessions", "adr"]

PERMISSIONS = {
    "issues": "Bash(issues:*)",
    "sessions": "Bash(sessions:*)",
    # adr has no CLI, so no permission needed
}

# Find the repo root (for editable installs)
_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent.parent  # src/skill_issues -> src -> repo root


def get_skill_content(skill_name: str) -> str | None:
    """Get the SKILL.md content for a skill.

    First tries the repo's .claude/skills directory (editable install),
    then falls back to package data (wheel install).
    """
    # Try editable install location first
    repo_skill_file = _REPO_ROOT / ".claude" / "skills" / skill_name / "SKILL.md"
    if repo_skill_file.exists():
        return repo_skill_file.read_text()

    # Try package data location (wheel install)
    package_skill_file = _PACKAGE_DIR / "skills" / skill_name / "SKILL.md"
    if package_skill_file.exists():
        return package_skill_file.read_text()

    return None


def _is_editable_install() -> bool:
    """Check if running from an editable install (git clone)."""
    repo_skills = _REPO_ROOT / ".claude" / "skills"
    return repo_skills.exists() and repo_skills.is_dir()


def install_skill(project_dir: Path, skill_name: str, update: bool = False) -> str:
    """Install a skill to the project directory.

    Uses symlinks for editable installs (git clone), copies for wheel installs.
    Returns a status message.

    Args:
        project_dir: Path to the project directory.
        skill_name: Name of the skill to install.
        update: If True, overwrite existing SKILL.md files (does not affect symlinks).
    """
    target_dir = project_dir / ".claude" / "skills" / skill_name
    target_file = target_dir / "SKILL.md"

    # Check if already exists
    if target_dir.exists():
        if target_dir.is_symlink():
            return f"{skill_name}: already linked (symlinks auto-update)"

        if not update:
            return f"{skill_name}: already exists (use --update to overwrite SKILL.md)"

        # Update mode: overwrite the SKILL.md file
        content = get_skill_content(skill_name)
        if content is None:
            return f"{skill_name}: not found in package"
        target_file.write_text(content)
        return f"{skill_name}: updated SKILL.md"

    # For editable installs, use symlinks
    if _is_editable_install():
        source_dir = _REPO_ROOT / ".claude" / "skills" / skill_name
        if not source_dir.exists():
            return f"{skill_name}: not found in repo"

        # Create parent directory and symlink
        target_dir.parent.mkdir(parents=True, exist_ok=True)
        target_dir.symlink_to(source_dir)
        return f"{skill_name}: linked"

    # For wheel installs, copy the file
    content = get_skill_content(skill_name)
    if content is None:
        return f"{skill_name}: not found in package"

    # Create directory and write file
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file.write_text(content)
    return f"{skill_name}: installed"


def update_permissions(project_dir: Path, skill_names: list[str]) -> str:
    """Add permissions for skills to .claude/settings.json.

    Returns a status message.
    """
    settings_file = project_dir / ".claude" / "settings.json"

    # Determine which permissions to add
    perms_to_add = [PERMISSIONS[s] for s in skill_names if s in PERMISSIONS]
    if not perms_to_add:
        return "permissions: none needed"

    if settings_file.exists():
        try:
            settings: dict[str, Any] = json.loads(settings_file.read_text())
        except json.JSONDecodeError:
            return "permissions: settings.json exists but is invalid JSON"

        # Get existing permissions
        existing = settings.get("permissions", {}).get("allow", [])

        # Check which are already present
        new_perms = [p for p in perms_to_add if p not in existing]
        if not new_perms:
            return "permissions: already configured"

        # Add new permissions
        if "permissions" not in settings:
            settings["permissions"] = {}
        if "allow" not in settings["permissions"]:
            settings["permissions"]["allow"] = []
        settings["permissions"]["allow"].extend(new_perms)

        settings_file.write_text(json.dumps(settings, indent=2) + "\n")
        return f"permissions: added {', '.join(new_perms)}"
    else:
        # Create new settings file
        settings_file.parent.mkdir(parents=True, exist_ok=True)
        settings = {"permissions": {"allow": perms_to_add}}
        settings_file.write_text(json.dumps(settings, indent=2) + "\n")
        return f"permissions: created settings.json"


def init_skills(project_dir: Path, skill_names: list[str], update: bool = False) -> list[str]:
    """Initialize skills in a project directory.

    Args:
        project_dir: Path to the project directory.
        skill_names: List of skill names to install.
        update: If True, overwrite existing SKILL.md files.

    Returns:
        List of status messages.
    """
    messages = []

    # Install each skill
    for skill in skill_names:
        if skill not in SKILLS:
            messages.append(f"{skill}: unknown skill")
            continue
        messages.append(install_skill(project_dir, skill, update=update))

    # Update permissions
    messages.append(update_permissions(project_dir, skill_names))

    return messages


def run_init(skill_names: list[str], project_path: str | None = None, update: bool = False) -> int:
    """Run init from CLI.

    Args:
        skill_names: List of skill names to install.
        project_path: Path to project (default: current directory).
        update: If True, overwrite existing SKILL.md files.

    Returns:
        Exit code (0 for success).
    """
    project_dir = Path(project_path) if project_path else Path.cwd()

    if not project_dir.exists():
        print(f"Error: {project_dir} does not exist", file=sys.stderr)
        return 1

    project_dir = project_dir.resolve()
    if update:
        print(f"Updating SKILL.md files in: {project_dir}")
    else:
        print(f"Initializing in: {project_dir}")
    print()

    messages = init_skills(project_dir, skill_names, update=update)
    for msg in messages:
        print(f"  {msg}")

    print()
    print("Done.")
    return 0
