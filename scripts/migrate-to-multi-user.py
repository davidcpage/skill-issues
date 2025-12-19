#!/usr/bin/env python3
from __future__ import annotations

"""
Migrate skill-issues data to multi-user ID format.

Compatible with Python 3.8+.

This script converts old-format IDs to new prefixed format:
- Sessions: s001 -> dp-s001 (adds user field)
- Issues: 001 -> dp-001 (updates depends_on refs)

Usage:
    # Single user (all data attributed to one prefix)
    python migrate-to-multi-user.py --prefix dp

    # Dry run (preview changes without writing)
    python migrate-to-multi-user.py --prefix dp --dry-run

    # Multi-user with git blame attribution
    python migrate-to-multi-user.py --multi-user --author-map authors.json

    # Generate author map from git blame (review and edit before using)
    python migrate-to-multi-user.py --generate-author-map > authors.json

Requirements:
    - Python 3.10+
    - Run from project root (where .issues/ and .memory/ directories are)
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def get_git_blame_authors(filepath: Path) -> dict[int, str]:
    """Get author for each line using git blame.

    Returns dict mapping line number (1-indexed) to author name.
    """
    if not filepath.exists():
        return {}

    try:
        result = subprocess.run(
            ["git", "blame", "--line-porcelain", str(filepath)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            print(f"Warning: git blame failed for {filepath}", file=sys.stderr)
            return {}

        authors = {}
        current_line = 0
        for line in result.stdout.splitlines():
            if line.startswith("author "):
                author = line[7:]  # Remove "author " prefix
                authors[current_line] = author
            elif not line.startswith("\t") and not line.startswith(" ") and " " in line:
                # Line like "abc123 1 1 1" - commit hash and line numbers
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    current_line = int(parts[1])

        return authors
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {}


def derive_prefix_from_name(name: str) -> str:
    """Derive 2-letter prefix from full name."""
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).lower()
    elif len(parts) == 1 and len(parts[0]) >= 2:
        return parts[0][:2].lower()
    return "xx"


def generate_author_map(sessions_file: Path, events_file: Path) -> dict:
    """Generate author map from git blame for review."""
    author_map = {
        "authors": {},  # "Author Name" -> "prefix"
        "sessions": {},  # line number -> prefix (override)
        "issues": {},    # line number -> prefix (override)
    }

    # Collect unique authors
    unique_authors = set()

    if sessions_file.exists():
        for line_num, author in get_git_blame_authors(sessions_file).items():
            unique_authors.add(author)

    if events_file.exists():
        for line_num, author in get_git_blame_authors(events_file).items():
            unique_authors.add(author)

    # Generate suggested prefixes
    for author in sorted(unique_authors):
        prefix = derive_prefix_from_name(author)
        author_map["authors"][author] = prefix

    return author_map


def migrate_session_id(old_id: str, prefix: str) -> str | None:
    """Convert old session ID to new format."""
    match = re.match(r"^s(\d+)$", old_id)
    if match:
        return f"{prefix}-s{match.group(1)}"
    return None


def migrate_issue_id(old_id: str, prefix: str) -> str | None:
    """Convert old issue ID to new format."""
    match = re.match(r"^(\d+)$", old_id)
    if match:
        return f"{prefix}-{match.group(1)}"
    return None


def is_old_session_id(session_id: str) -> bool:
    """Check if session ID is in old format."""
    return bool(re.match(r"^s\d+$", session_id))


def is_old_issue_id(issue_id: str) -> bool:
    """Check if issue ID is in old format."""
    return bool(re.match(r"^\d+$", issue_id))


class Migrator:
    def __init__(
        self,
        prefix: str | None = None,
        author_map: dict | None = None,
        dry_run: bool = False,
    ):
        self.prefix = prefix
        self.author_map = author_map or {}
        self.dry_run = dry_run
        self.stats = {"sessions": 0, "events": 0, "issues_worked": 0}

        # Build ID mapping as we go (for updating references)
        self.session_id_map: dict[str, str] = {}  # old -> new
        self.issue_id_map: dict[str, str] = {}    # old -> new

    def get_prefix_for_author(self, author: str) -> str:
        """Get prefix for an author name."""
        if self.prefix:
            return self.prefix
        return self.author_map.get("authors", {}).get(author, "xx")

    def get_prefix_for_session_line(self, line_num: int, default_author: str) -> str:
        """Get prefix for a session line (with override support)."""
        override = self.author_map.get("sessions", {}).get(str(line_num))
        if override:
            return override
        return self.get_prefix_for_author(default_author)

    def get_prefix_for_issue_line(self, line_num: int, default_author: str) -> str:
        """Get prefix for an issue line (with override support)."""
        override = self.author_map.get("issues", {}).get(str(line_num))
        if override:
            return override
        return self.get_prefix_for_author(default_author)

    def migrate_sessions(self, sessions_file: Path) -> list[dict]:
        """Migrate sessions to new format."""
        if not sessions_file.exists():
            print(f"Sessions file not found: {sessions_file}")
            return []

        content = sessions_file.read_text()
        sessions = [json.loads(line) for line in content.splitlines() if line.strip()]

        # Get git blame authors if doing multi-user
        blame_authors = {}
        if not self.prefix:
            blame_authors = get_git_blame_authors(sessions_file)

        migrated = []
        for i, session in enumerate(sessions, 1):
            old_id = session.get("id", "")

            if is_old_session_id(old_id):
                author = blame_authors.get(i, "Unknown")
                prefix = self.get_prefix_for_session_line(i, author)

                new_id = migrate_session_id(old_id, prefix)
                if new_id:
                    self.session_id_map[old_id] = new_id
                    session["id"] = new_id
                    session["user"] = prefix
                    self.stats["sessions"] += 1
                    print(f"  Session {old_id} -> {new_id} (author: {author})")

            # Update issues_worked references
            if "issues_worked" in session:
                new_issues = []
                for issue_id in session["issues_worked"]:
                    if issue_id in self.issue_id_map:
                        new_issues.append(self.issue_id_map[issue_id])
                        self.stats["issues_worked"] += 1
                    elif is_old_issue_id(issue_id):
                        # Will be mapped later, use placeholder
                        new_issues.append(f"__PENDING__{issue_id}")
                    else:
                        new_issues.append(issue_id)
                session["issues_worked"] = new_issues

            migrated.append(session)

        return migrated

    def migrate_events(self, events_file: Path) -> list[dict]:
        """Migrate issue events to new format."""
        if not events_file.exists():
            print(f"Events file not found: {events_file}")
            return []

        content = events_file.read_text()
        events = [json.loads(line) for line in content.splitlines() if line.strip()]

        # Get git blame authors if doing multi-user
        blame_authors = {}
        if not self.prefix:
            blame_authors = get_git_blame_authors(events_file)

        # First pass: build issue ID map from 'created' events
        for i, event in enumerate(events, 1):
            if event.get("type") == "created":
                old_id = event.get("id", "")
                if is_old_issue_id(old_id):
                    author = blame_authors.get(i, "Unknown")
                    prefix = self.get_prefix_for_issue_line(i, author)
                    new_id = migrate_issue_id(old_id, prefix)
                    if new_id:
                        self.issue_id_map[old_id] = new_id

        # Second pass: migrate all events
        migrated = []
        for i, event in enumerate(events, 1):
            old_id = event.get("id", "")

            # Migrate main ID
            if old_id in self.issue_id_map:
                event["id"] = self.issue_id_map[old_id]
                self.stats["events"] += 1

            # Migrate depends_on references
            if "depends_on" in event:
                event["depends_on"] = [
                    self.issue_id_map.get(d, d) for d in event["depends_on"]
                ]

            # Migrate session references
            if "session" in event:
                old_session = event["session"]
                if old_session in self.session_id_map:
                    event["session"] = self.session_id_map[old_session]
                elif is_old_session_id(old_session):
                    # Try to migrate inline
                    prefix = self.prefix or "xx"
                    new_session = migrate_session_id(old_session, prefix)
                    if new_session:
                        event["session"] = new_session

            migrated.append(event)

        return migrated

    def finalize_sessions(self, sessions: list[dict]) -> list[dict]:
        """Replace pending issue ID placeholders with actual mapped IDs."""
        for session in sessions:
            if "issues_worked" in session:
                session["issues_worked"] = [
                    self.issue_id_map.get(iid.replace("__PENDING__", ""), iid)
                    if iid.startswith("__PENDING__") else iid
                    for iid in session["issues_worked"]
                ]
        return sessions

    def run(self, project_root: Path):
        """Run the migration."""
        sessions_file = project_root / ".memory/sessions.jsonl"
        events_file = project_root / ".issues/events.jsonl"

        print(f"Migrating in: {project_root}")
        print(f"Mode: {'single-user' if self.prefix else 'multi-user'}")
        if self.prefix:
            print(f"Prefix: {self.prefix}")
        print()

        # Migrate issues first (to build ID map)
        print("Migrating issues...")
        events = self.migrate_events(events_file)

        # Then migrate sessions (uses issue ID map)
        print("\nMigrating sessions...")
        sessions = self.migrate_sessions(sessions_file)
        sessions = self.finalize_sessions(sessions)

        print(f"\nStats:")
        print(f"  Sessions migrated: {self.stats['sessions']}")
        print(f"  Events migrated: {self.stats['events']}")
        print(f"  Issue refs updated: {self.stats['issues_worked']}")

        if self.dry_run:
            print("\n[DRY RUN] No files written")
            return

        # Write files
        if events:
            lines = [json.dumps(e, separators=(",", ":")) for e in events]
            events_file.write_text("\n".join(lines) + "\n")
            print(f"\nWrote: {events_file}")

        if sessions:
            lines = [json.dumps(s, separators=(",", ":")) for s in sessions]
            sessions_file.write_text("\n".join(lines) + "\n")
            print(f"Wrote: {sessions_file}")

        print("\nMigration complete!")
        print("\nNext steps:")
        print("  1. Review changes: git diff")
        print("  2. Update ADR references manually if needed")
        print("  3. Commit: git add -A && git commit -m 'Migrate to multi-user ID format'")


def main():
    parser = argparse.ArgumentParser(
        description="Migrate skill-issues data to multi-user ID format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single user migration
  python migrate-to-multi-user.py --prefix dp

  # Preview changes first
  python migrate-to-multi-user.py --prefix dp --dry-run

  # Multi-user: generate author map for review
  python migrate-to-multi-user.py --generate-author-map > authors.json
  # Edit authors.json to set correct prefixes, then:
  python migrate-to-multi-user.py --author-map authors.json
        """,
    )

    parser.add_argument(
        "--prefix",
        help="User prefix for single-user migration (e.g., 'dp', 'alice')",
    )
    parser.add_argument(
        "--author-map",
        type=Path,
        help="JSON file mapping authors to prefixes (for multi-user)",
    )
    parser.add_argument(
        "--generate-author-map",
        action="store_true",
        help="Generate author map from git blame (outputs JSON to stdout)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files",
    )
    parser.add_argument(
        "--project-root",
        type=Path,
        default=Path.cwd(),
        help="Project root directory (default: current directory)",
    )

    args = parser.parse_args()

    if args.generate_author_map:
        sessions_file = args.project_root / ".memory/sessions.jsonl"
        events_file = args.project_root / ".issues/events.jsonl"
        author_map = generate_author_map(sessions_file, events_file)
        print(json.dumps(author_map, indent=2))
        return

    if not args.prefix and not args.author_map:
        parser.error("Either --prefix or --author-map is required")

    author_map = None
    if args.author_map:
        if not args.author_map.exists():
            parser.error(f"Author map file not found: {args.author_map}")
        author_map = json.loads(args.author_map.read_text())

    migrator = Migrator(
        prefix=args.prefix,
        author_map=author_map,
        dry_run=args.dry_run,
    )
    migrator.run(args.project_root)


if __name__ == "__main__":
    main()
