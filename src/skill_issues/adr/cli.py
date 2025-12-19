"""CLI entry point for adr command."""

import argparse
import re
import sys
from datetime import date
from pathlib import Path


def get_decisions_dir() -> Path:
    """Get the decisions directory path."""
    return Path.cwd() / "decisions"


def _migrate_if_needed() -> None:
    """Migrate from old .decisions/ to new decisions/ folder."""
    legacy_dir = Path.cwd() / ".decisions"
    new_dir = Path.cwd() / "decisions"

    if legacy_dir.exists() and not new_dir.exists():
        legacy_dir.rename(new_dir)
        print(f"Migrated {legacy_dir}/ to {new_dir}/")


def find_next_number(decisions_dir: Path) -> int:
    """Find the next available ADR number."""
    if not decisions_dir.exists():
        return 1

    max_num = 0
    for f in decisions_dir.glob("*.md"):
        match = re.match(r"^(\d+)-", f.name)
        if match:
            num = int(match.group(1))
            max_num = max(max_num, num)

    return max_num + 1


def create_draft(slug: str) -> int:
    """Create a new draft ADR."""
    decisions_dir = get_decisions_dir()
    decisions_dir.mkdir(parents=True, exist_ok=True)

    # Normalize slug (lowercase, hyphens)
    slug = slug.lower().replace(" ", "-").replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")

    if not slug:
        print("Error: Invalid slug - must contain alphanumeric characters", file=sys.stderr)
        return 1

    draft_file = decisions_dir / f"draft-{slug}.md"

    if draft_file.exists():
        print(f"Error: {draft_file.name} already exists", file=sys.stderr)
        return 1

    # Check if a numbered version already exists
    for f in decisions_dir.glob(f"*-{slug}.md"):
        if re.match(r"^\d+-", f.name):
            print(f"Error: {f.name} already exists with this slug", file=sys.stderr)
            return 1

    # Create template
    title = slug.replace("-", " ").title()
    today = date.today().isoformat()

    content = f"""# ADR: {title}

**Status:** Draft
**Date:** {today}

## Context

What situation or problem prompted this decision? Include relevant constraints.

## Decision

What was decided? Be specific and concrete.

## Consequences

### Positive

-

### Negative

-

## Alternatives Considered

What other options were evaluated? Why were they rejected?
"""

    draft_file.write_text(content)
    print(f"Created: {draft_file.name}")
    print(f"  Edit the file, then run: adr accept {slug}")
    return 0


def accept_draft(slug: str) -> int:
    """Accept a draft ADR, assigning it a number."""
    decisions_dir = get_decisions_dir()

    if not decisions_dir.exists():
        print(f"Error: {decisions_dir} does not exist", file=sys.stderr)
        return 1

    # Find the draft file
    draft_file = decisions_dir / f"draft-{slug}.md"
    if not draft_file.exists():
        # Try with the full filename
        draft_file = decisions_dir / f"{slug}.md" if not slug.startswith("draft-") else decisions_dir / slug
        if slug.startswith("draft-"):
            draft_file = decisions_dir / f"{slug}.md"
        if not draft_file.exists():
            print(f"Error: draft-{slug}.md not found in {decisions_dir}", file=sys.stderr)
            return 1

    # Read and update content
    content = draft_file.read_text()

    # Verify it's a draft
    if "**Status:** Draft" not in content:
        print(f"Error: {draft_file.name} is not in Draft status", file=sys.stderr)
        return 1

    # Get next number
    next_num = find_next_number(decisions_dir)
    num_str = f"{next_num:03d}"

    # Update status
    content = content.replace("**Status:** Draft", "**Status:** Accepted")

    # Update title if it starts with "# ADR:"
    content = re.sub(
        r"^# ADR: ",
        f"# ADR {num_str}: ",
        content,
        count=1,
        flags=re.MULTILINE
    )

    # Determine new filename
    new_file = decisions_dir / f"{num_str}-{slug}.md"

    if new_file.exists():
        print(f"Error: {new_file.name} already exists", file=sys.stderr)
        return 1

    # Write updated content and rename
    new_file.write_text(content)
    draft_file.unlink()

    print(f"Accepted: {draft_file.name} → {new_file.name}")
    return 0


def list_adrs() -> int:
    """List all ADRs."""
    decisions_dir = get_decisions_dir()

    if not decisions_dir.exists():
        print("No decisions/ directory found")
        return 0

    drafts = []
    accepted = []

    for f in sorted(decisions_dir.glob("*.md")):
        if f.name.startswith("draft-"):
            drafts.append(f.name)
        elif re.match(r"^\d+-", f.name):
            accepted.append(f.name)

    if accepted:
        print("Accepted:")
        for name in accepted:
            print(f"  {name}")

    if drafts:
        if accepted:
            print()
        print("Drafts:")
        for name in drafts:
            print(f"  {name}")

    if not drafts and not accepted:
        print("No ADRs found")

    return 0


def main() -> int:
    """Entry point for the adr command."""
    _migrate_if_needed()

    parser = argparse.ArgumentParser(
        description="Architecture Decision Records skill",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  adr                        # List all ADRs
  adr create auth-approach   # Create draft-auth-approach.md
  adr accept auth-approach   # Accept draft, rename to NNN-auth-approach.md
  adr init                   # Initialize adr skill in current directory
"""
    )

    # Subcommands
    subparsers = parser.add_subparsers(dest="subcommand")

    init_parser = subparsers.add_parser("init", help="Initialize adr skill in a project")
    init_parser.add_argument("path", nargs="?", help="Project path (default: current directory)")

    create_parser = subparsers.add_parser("create", help="Create a new draft ADR")
    create_parser.add_argument("slug", help="Short name for the ADR (e.g., 'auth-approach')")

    accept_parser = subparsers.add_parser("accept", help="Accept a draft ADR, assigning it a number")
    accept_parser.add_argument("slug", help="Slug of the draft to accept (without 'draft-' prefix)")

    args = parser.parse_args()

    if args.subcommand == "init":
        from .. import init as init_module
        return init_module.run_init(["adr"], getattr(args, "path", None))

    if args.subcommand == "create":
        return create_draft(args.slug)

    if args.subcommand == "accept":
        return accept_draft(args.slug)

    # No subcommand - list ADRs
    return list_adrs()


if __name__ == "__main__":
    sys.exit(main())
