# Migrating to Multi-User ID Format

This guide explains how to migrate existing skill-issues data from old format (`s001`, `001`) to new multi-user format (`dp-s001`, `dp-001`).

## Quick Start: Single User

If you're the only contributor to the repo:

```bash
cd /path/to/your/project

# Preview changes first
python /path/to/skill-issues/scripts/migrate-to-multi-user.py --prefix YOUR_PREFIX --dry-run

# Run the migration
python /path/to/skill-issues/scripts/migrate-to-multi-user.py --prefix YOUR_PREFIX

# Review and commit
git diff
git add -A && git commit -m "Migrate to multi-user ID format"
```

Replace `YOUR_PREFIX` with your 2-4 character prefix (e.g., `dp`, `alice`, `jb`).

## Multi-User Migration

For repos with multiple contributors, you'll want to attribute sessions and issues to the correct users.

### Step 1: Generate Author Map

```bash
cd /path/to/your/project
python /path/to/skill-issues/scripts/migrate-to-multi-user.py --generate-author-map > authors.json
```

This uses `git blame` to identify who committed each line and generates a JSON file like:

```json
{
  "authors": {
    "Alice Smith": "as",
    "Bob Jones": "bj"
  },
  "sessions": {},
  "issues": {}
}
```

### Step 2: Review and Edit the Author Map

Edit `authors.json` to:

1. **Fix prefixes** - The script derives prefixes from names (first+last initials). Adjust if needed:
   ```json
   "authors": {
     "Alice Smith": "alice",
     "Bob Jones": "bob"
   }
   ```

2. **Handle line-level overrides** (optional) - If specific lines were committed by one person but belong to another:
   ```json
   "sessions": {
     "15": "bob"    // Line 15 should use bob's prefix even though alice committed it
   },
   "issues": {
     "42": "alice"  // Line 42 override
   }
   ```

### Step 3: Run the Migration

```bash
# Preview first
python /path/to/skill-issues/scripts/migrate-to-multi-user.py --author-map authors.json --dry-run

# Run it
python /path/to/skill-issues/scripts/migrate-to-multi-user.py --author-map authors.json
```

### Step 4: Update ADR References (Manual)

The script updates `.issues/events.jsonl` and `.memory/sessions.jsonl`, but ADR files in `.decisions/` need manual updates if they reference issue numbers.

Search for old-format references:
```bash
grep -E "\b0[0-9]{2}\b" .decisions/*.md
```

Common patterns to update:
- `Issue 042` → `Issue dp-042`
- `#042` → `#dp-042`
- `- 042:` → `- dp-042:`
- `s015` → `dp-s015`

### Step 5: Commit

```bash
git add -A
git commit -m "Migrate to multi-user ID format"
```

## What Gets Migrated

| File | Changes |
|------|---------|
| `.issues/events.jsonl` | Issue IDs, `depends_on` arrays, `session` refs |
| `.memory/sessions.jsonl` | Session IDs, adds `user` field, `issues_worked` arrays |

## Prefix Requirements

- **Length**: 2-4 characters
- **Characters**: Alphanumeric only (a-z, 0-9)
- **Case**: Will be normalized to lowercase

## Troubleshooting

### "git blame failed"
The script uses git blame for multi-user attribution. If the files aren't tracked by git, use single-user mode with `--prefix`.

### Mixed old/new format after migration
The script only migrates old-format IDs. If you already have some new-format IDs, they're preserved.

### Need to re-run migration
The script is idempotent for already-migrated IDs - it only converts old format to new format.

## Example Output

```
Migrating in: /path/to/project
Mode: single-user
Prefix: dp

Migrating issues...
  Issue 001 -> dp-001 (author: David Page)
  Issue 002 -> dp-002 (author: David Page)
  ...

Migrating sessions...
  Session s001 -> dp-s001 (author: David Page)
  Session s002 -> dp-s002 (author: David Page)
  ...

Stats:
  Sessions migrated: 50
  Events migrated: 187
  Issue refs updated: 85

Wrote: .issues/events.jsonl
Wrote: .memory/sessions.jsonl

Migration complete!
```
