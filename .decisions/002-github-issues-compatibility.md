# Decision 002: GitHub Issues Compatibility

**Status:** Accepted (on hold)
**Date:** 2025-12-14
**Updated:** 2025-12-14

**Hold rationale:** Full GitHub sync (Phases 2-4) adds complexity for marginal benefit. The ID mapping problem (local IDs ↔ GitHub numbers) is the main blocker. If GitHub visibility is needed, use GitHub as primary. Phase 1 schema additions (labels field) worth doing independently - see issue dp-032.

## Framing

The issues skill is essentially **"GitHub Issues but local"** - familiar semantics for developers who know GitHub Issues, but optimized for Claude Code workflows:

- **Local-first**: No network latency, works offline
- **Append-only**: Simpler conflict resolution, clean git diffs
- **AI-native**: Designed for Claude to read/write efficiently via tools

This framing guides compatibility: we should stay close to GitHub Issues semantics so the mental model transfers, and so sync tooling is straightforward when needed.

## Context

Some users will want to use GitHub Issues for issue tracking, especially for:
- Public/open-source projects where external contributors use GitHub
- Teams already invested in GitHub's ecosystem (Projects, Actions, etc.)
- Visibility to stakeholders who monitor GitHub but don't use Claude Code

Our issue tracking system should be compatible enough with GitHub Issues that we can later add tooling to export/import between them.

## Current State Comparison

### High Compatibility (direct mapping)

| Our Field | GitHub Field | Notes |
|-----------|--------------|-------|
| title | title | Direct |
| description | body | Direct |
| status (open/closed) | state | Direct |
| notes | comments | Both append-only |
| issue_type | labels | bug→"bug", feature→"feature", task→"task" |
| priority | labels | 0→"P0", 1→"P1", etc. |

### Gaps

| Our Field | GitHub | Bridging Strategy |
|-----------|--------|-------------------|
| id (string, e.g., "014") | number (int, e.g., 42) | Add optional `github_id` field |
| blocked_by | (none native) | Convention in body: "Blocked by #123" |
| closed reason (free text) | close_state_reason (enum) | Map to: completed, not_planned, duplicate |
| - | labels (custom) | Add optional `labels` array |
| - | assignees | Add optional `assignees` array (future) |
| - | milestone | Add optional `milestone` field (future) |

## Recommended Schema Additions

### Phase 1: Minimal compatibility

```json
{
  "github_id": 42,
  "labels": ["needs-review", "breaking-change"]
}
```

- `github_id`: Optional integer. Set when synced to/from GitHub.
- `labels`: Optional array. Custom labels beyond type/priority.

### Phase 2: Richer GitHub integration (future)

```json
{
  "assignees": ["username1", "username2"],
  "milestone": "v1.0",
  "github_url": "https://github.com/org/repo/issues/42"
}
```

## Sync Strategies

### Export to GitHub

```bash
# Create issue
gh issue create --title "..." --body "..." --label bug,P1

# Close issue
gh issue close 42 --reason completed --comment "Done - ..."

# Add comment (for notes)
gh issue comment 42 --body "..."
```

**Mapping closed reasons:**
- Our "Done - ..." → GitHub `completed`
- Our "Won't fix - ..." → GitHub `not_planned`
- Our "Duplicate of ..." → GitHub `duplicate`

### Import from GitHub

```bash
# List issues as JSON
gh issue list --json number,title,body,state,labels,comments

# Get single issue
gh issue view 42 --json number,title,body,state,labels,comments
```

**Mapping:**
- GitHub labels containing "bug"/"feature"/"task" → issue_type
- GitHub labels matching P0-P4 → priority
- GitHub comments → notes
- Other labels → labels array

### Bidirectional Sync (Complex)

Requires:
1. Tracking sync state (last sync timestamp per issue)
2. Conflict resolution (which side wins on concurrent edits?)
3. Mapping table (our id ↔ GitHub number)

**Recommendation:** Start with one-way export. Import and bidirectional sync are future work.

## blocked_by in GitHub

GitHub has no native dependency tracking. Options:

1. **Body convention**: Include "Blocked by #123, #456" line in issue body
2. **Label**: Add "blocked" label when blocked_by is non-empty
3. **Task list**: Use `- [ ] Depends on #123` in body (renders as checklist)
4. **GitHub Projects**: Use project board dependencies (complex, requires Projects v2)

**Recommendation:** Use body convention + "blocked" label. Simple, visible, parseable.

```markdown
## Dependencies
Blocked by: #123, #456
```

## Implementation Phases

### Phase 1: Schema preparation
- Add optional `github_id` and `labels` fields to schema
- Update issues.py to handle new fields
- No sync tooling yet

### Phase 2: One-way export
- `issues.py --export-github` outputs `gh` commands
- Or: Python script that calls `gh` CLI directly
- Manual trigger, not automatic

### Phase 3: Import (future)
- `issues.py --import-github` reads from `gh issue list`
- Creates local issues for GitHub issues not yet tracked

### Phase 4: Bidirectional sync (future)
- Requires sync state tracking
- Conflict resolution strategy
- Probably needs a daemon or hook

## AI Agent Familiarity

A non-obvious advantage of GitHub Issues compatibility: **LLMs have extensive training data on GitHub Issues**.

This means AI agents already "know" how to:
- Write clear issue titles and descriptions
- Use labels, milestones, and references appropriately
- Follow conventions like "Fixes #123", task lists (`- [ ]`), @mentions
- Structure comments for clarity
- Close issues with meaningful summaries

By aligning with GitHub Issues semantics, we leverage this statistical prior. The AI doesn't need to learn a new format - it's working in a deeply familiar domain. This is a form of **protocol fitness**: the format is optimized not just for human familiarity but for AI effectiveness.

## Decisions

### D1: Schema extensions (deferred)

**Decision:** Document the compatibility mapping but defer implementation. Add `github_id` and `labels` fields when first needed.

**Rationale:** YAGNI. The schema additions are low-cost when needed, but adding them now creates fields that may never be used. The compatibility analysis ensures we won't paint ourselves into a corner.

### D2: blocked_by as structural field (accepted)

**Decision:** Keep `blocked_by` as a first-class structured field, not a body convention.

**Context:** GitHub Issues lacks native dependency tracking - users write "Blocked by #123" in issue bodies by convention. We considered dropping `blocked_by` to maximize GitHub alignment and protocol fitness.

**Rationale:**
1. **Tooling value:** `--ready` filtering requires structural data. Parsing body text is fragile and requires more context for Claude to reason about.
2. **Concept is universal:** "Blocked by" semantics appear extensively in training data across JIRA, Azure DevOps, and even GitHub body conventions. The concept has strong protocol fitness even if GitHub lacks the field.
3. **Clean mapping:** Export renders as body convention (`Blocked by: #123, #456`), import parses it back. The mapping is straightforward.
4. **Deliberate extension:** This is where "GitHub Issues but better for AI" provides value. We're not inventing new semantics, just making existing conventions structural.

**Trade-off acknowledged:** We're not 1:1 with GitHub. But the tooling benefit justifies the small schema divergence.

### D3: Task list integration (rejected)

**Decision:** Skip task list integration. Task lists (`- [ ] item`) are just markdown in descriptions, with no special tooling.

**Context:** GitHub task lists render as interactive checkboxes with completion tracking. Issue dp-026 proposed similar integration for protocol fitness benefits.

**Rationale:**
1. **Avoids two mechanisms for the same thing:** Both `blocked_by` and task lists can express "do A before B". Having both creates confusion about when to use which.
2. **Task lists are a UI feature:** The value is interactive checkboxes in GitHub's web interface. In our text-based append-only system, we'd need machinery to track checkbox state across events.
3. **blocked_by already serves the need:** Dependency-aware filtering via `--ready` handles the core use case. Task lists would add complexity for marginal benefit.
4. **Markdown still works:** Users can write `- [ ] step` in descriptions for informal breakdowns. We just don't track or render it specially.

**Semantic distinction (for guidance):** If a sub-item deserves its own title/priority/description, make it a separate issue with `blocked_by`. If it's just a step within one unit of work, write it as markdown in the description.

## Protocol Fitness: Deeper Questions

The "AI Agent Familiarity" section above hints at something potentially more powerful. This section explores whether **protocol fitness** - designing tools around patterns LLMs already know from training - should be a primary design driver.

### Q1: How powerful is the protocol fitness effect?

Beads works surprisingly well with AI agents despite issue tracking seeming like a complex skill. The hypothesis: **issue tracker patterns may actually be more familiar to LLMs than TodoWrite, not less**.

TodoWrite is a simplified abstraction with fewer fields and less structure. Issue trackers like GitHub Issues appear millions of times in training data with consistent patterns:
- Field semantics (title, description, status, priority, labels)
- Workflow patterns (open → in progress → closed)
- Reference syntax (`#123`, `Fixes #123`)
- Relationship types (blocks, parent/child through task lists)

If this hypothesis is correct, issue tracking may genuinely be *easier* for Claude than todo lists because the patterns are more consistent in training data. TodoWrite's simplicity may actually *reduce* effectiveness by providing weaker priors.

### Q2: What aspects of protocol fitness matter?

Structural patterns likely matter more than exact field names, but there's probably benefit to alignment:
- `status` / `labels` / `assignee` are stable across trackers
- GitHub task list syntax (`- [ ] item`) is highly recognizable
- CLI verbs like `create`, `close`, `list` match common patterns
- Issue reference syntax (`#123`) transfers well

**Question:** Would exact GitHub Issues field naming (vs close approximations) measurably help Claude Code? The benefit is probabilistic - closer matches should activate stronger priors.

### Q3: Is GitHub Issues the right model?

GitHub Issues is almost certainly dominant in public training data:
- Massive volume of public repositories
- Tight integration with PRs/commits means issues appear in many contexts
- Issue references visible even when just reading code

JIRA is common in enterprise but less in *public* data. However, the Epic → Story → Task hierarchy is culturally widespread and discussed extensively, so those patterns are well-known even if raw JIRA content is less common.

**Trade-off:** GitHub Issues alignment enables import/export (offline/file-based version that syncs). JIRA's hierarchy model may better fit complex workflows. These aren't mutually exclusive - we could support GitHub-style flat issues with JIRA-style parent/child relationships.

### Q4: Do our relation type preferences reflect training data priors?

Current design favors `blocking` and `parent/child` over `relates-to` and `discovered-from`. This may be protocol fitness at work:

| Relation | Training Data Representation | Prior Strength |
|----------|------------------------------|----------------|
| blocking | Explicit in many trackers, implicit in dependency discussions | Strong |
| parent/child | GitHub task lists, JIRA epics/subtasks, nested issues | Strong |
| relates-to | Exists but conventions vary widely | Weak |
| discovered-from | Unusual - maybe "duplicate of" in bug trackers | Very weak |

Designing around relations with strong priors may yield better AI performance.

### Q5: Does branching workflow matter for protocol fitness?

GitHub Issues heavily involves PR → Issue links and commit references in comments. A workflow pattern common in training data:

1. Create branch for issue
2. Make commits referencing issue (`Fixes #123`)
3. Open PR linking to issue
4. Merge closes issue automatically

**Question:** Would a branch-per-issue workflow improve AI effectiveness by aligning with this pattern?

**Pragmatic view:** Probably not worth the overhead for simple issues. But for complex issues (those with children or blocking others), branching provides:
- Reviewable diffs that can be referenced in issue comments
- Ability to discuss specific commits (`see abc123 for the approach`)
- Rollback capability
- Parallel work without blocking main

**Tentative convention:** Yolo on main for simple/leaf issues. Branch for issues with children or that block other issues.

### GitHub Task List Syntax

A specific syntactic element worth highlighting. In GitHub Issues, this markdown in descriptions/comments:

```markdown
## Tasks
- [ ] Implement user authentication
- [ ] Add password validation
- [x] Create login form (completed)
- [ ] Fix bug #123
```

Renders as interactive checkboxes. GitHub:
- Tracks completion percentage ("2 of 4 tasks complete")
- Shows progress bars on issue lists
- Can auto-close referenced issues when checked

This is extremely common in training data. Integrating this syntax could provide strong protocol fitness benefits.

## Research Findings (2025-12-14)

This section documents findings from issues 024 (GitHub Issues audit) and 028 (local-first tracker research).

### Local-First Issue Trackers Surveyed

| Tool | Storage Approach | Human-Readable? | Git Integration | Key Insight |
|------|------------------|-----------------|-----------------|-------------|
| **[git-bug](https://github.com/git-bug/git-bug)** | Git objects in `refs/git-bug/` namespace | No (binary blobs) | Native - uses git internals | Sophisticated: operations-based model, logical clocks for ordering, GraphQL API, bridges to GitHub/GitLab |
| **[Bugs Everywhere](https://bugs-everywhere.readthedocs.io/)** | `.be/` directory with UUID subdirs, JSON `values` files | Moderate (UUIDs hard to read) | VCS-agnostic (git/hg/bzr/darcs) | Mature, but complex directory structure |
| **[ditz](https://github.com/jashmenn/ditz)** | `issues/` directory, line-based human-editable format | Yes | Manual (commit with code) | Release-based grouping, plugin system, generates HTML status pages |
| **[TicGit](https://github.com/jeffWelling/ticgit)** | Separate `ticgit` git branch | No (separate branch) | Stores in git, syncs via push/pull | 4 fixed states, no extensibility - "granddaddy" of branch-based trackers |
| **[Poor Man's Issue Tracker](https://github.com/driusan/PoormanIssueTracker)** | Plain filesystem: `issues/` + subdirs | Excellent | Manual (commit with code) | Directory name = title, Status/Priority/Description as plain files, `blockedby/` subdir |
| **[Fossil](https://fossil-scm.org/)** | SQLite database (not in source tree) | No | Built-in (not git) | Deliberately rejected file-in-tree approach - tickets are mutable, need web access |

**Key patterns observed:**
- git-bug's operations model is conceptually similar to our append-only events
- Poor Man's `blockedby/` subdirectory validates structural dependency tracking
- Fossil's rejection of file-in-tree is a deliberate choice for different use case (web UI, mutable state)

### Existing Claude Code Skills for Issue Tracking

| Skill | Approach | Integration |
|-------|----------|-------------|
| **[SpecWeave GitHub Issue Tracker](https://claude-plugins.dev/skills/@anton-abyzov/specweave/github-issue-tracker)** | Syncs with GitHub Issues | Checklists, comments, labels via GitHub API |
| **[Agile Workflow Skills](https://github.com/levnikolaevich/claude-code-skills)** | Syncs with Linear | Epics → Stories → Tasks hierarchy, kanban in markdown |
| **Built-in TodoWrite** | In-memory during session | Ephemeral, no persistence |

**Finding:** No existing Claude Code skill uses a local-first, file-based, append-only approach like ours. All mature solutions integrate with external platforms (GitHub, Linear). This confirms we're filling a gap.

### GitHub Issues Field Audit

| GitHub Field | Our Field | Mapping Quality | Notes |
|--------------|-----------|-----------------|-------|
| `title` | `title` | ✅ Direct | |
| `body` | `description` | ✅ Direct | |
| `state` | `status` | ✅ Direct | We use `status` (more common across trackers) |
| `state_reason` | `reason` (free text) | ⚠️ Partial | GitHub: enum (completed/not_planned/duplicate). Ours: free text. Can map. |
| `labels` | `issue_type` + `priority` | ⚠️ Partial | We encode type/priority structurally; GitHub uses labels |
| `labels` (custom) | ❌ Missing | Gap | Add optional `labels` array (Phase 1) |
| `assignees` | ❌ Missing | Gap | Not needed for single-user; add if/when needed |
| `milestone` | ❌ Missing | Gap | Could map to release/version concept |
| `number` | `id` | ⚠️ Different type | GitHub: int. Ours: string. Add `github_id` for sync |
| ❌ N/A | `blocked_by` | **Extension** | We have this; GitHub doesn't (body convention only) |
| `comments` | `notes` | ✅ Direct | Both append-only |
| `created_at` | `ts` on created event | ✅ Direct | |
| `updated_at` | `ts` on latest event | ✅ Derivable | |
| `closed_at` | `ts` on closed event | ✅ Direct | |

### Comparison with beads

| Feature | beads | Our Skill | Notes |
|---------|-------|-----------|-------|
| Storage | SQLite + JSONL | JSONL only | We skip the cache layer (appropriate for <1000 issues) |
| JSONL format | Mutable entity-per-line | Append-only events | Different philosophy - ours has cleaner git diffs |
| Dependencies | 4 types (blocks, parent-child, related, discovered-from) | 1 type (blocked_by) | Simpler; blocks is the essential one |
| Hash IDs | Yes (bd-a1b2) | No (sequential "014") | Beads handles concurrent agents; we're single-agent |
| Field: `Status` | ✅ | ✅ | Same name (not GitHub's `state`) |
| Field: `Labels` | ✅ Optional array | ❌ Not yet | Gap to address |
| Daemon | Yes | No | We're simpler |

**Key pattern borrowed from beads:** The `blocked_by` → `--ready` pattern for agent orientation.

### JSONL vs Poor Man's for Agent Navigability

| Dimension | Poor Man's | JSONL Append-Only | Winner for Agents |
|-----------|------------|-------------------|-------------------|
| **File reads per issue** | 3-4 (Status, Priority, Description, blockedby/) | 1 (single file) | **JSONL** |
| **Parse complexity** | Directory names, file conventions, symlink handling | Native JSON | **JSONL** |
| **All context together** | No - scattered across files | Yes - one line | **JSONL** |
| **Timestamps** | Need git blame | Inline in events | **JSONL** |
| **History** | Git log | Events in file | **JSONL** |
| **Git diffs** | File additions/changes | Line additions only | **JSONL** (append-only) |
| **Title constraints** | Filesystem chars, dash conventions | Arbitrary strings | **JSONL** |
| **Human browsable** | Excellent (ls, cat) | Good (cat, jq) | Poor Man's |

**Verdict:** Poor Man's optimizes for humans navigating with basic shell tools. JSONL optimizes for programmatic access. Since our primary user is an LLM agent, JSONL is the right choice.

### Field Naming: `status` vs `state`

| System | Field Name |
|--------|------------|
| GitHub Issues | `state` |
| beads | `Status` |
| JIRA | `status` |
| Linear | `state` |
| Our skill | `status` |

**Decision:** Keep `status`. It's more common overall and more natural language ("What's the status?" vs "What's the state?"). The fact that we independently chose `status` (matching beads and JIRA) suggests it has stronger overall protocol fitness.

### Labels Field Purpose

We've made `issue_type` and `priority` structural fields (typed, validated, queryable). The `labels` field serves as an escape hatch for arbitrary categorization:
- `needs-review`, `breaking-change`, `good-first-issue`, `documentation`
- Custom workflow states beyond open/closed
- Team-specific categorization

GitHub uses labels for everything including type/priority (as conventions). We separate concerns: structural fields for core semantics, labels for custom categorization.

## Open Questions

1. Should blocked_by sync use body convention, labels, or both?
2. For bidirectional sync, should local or GitHub be source of truth?
3. Should we support multiple remotes (GitHub + GitLab)?
4. ~~How can we measure the protocol fitness effect empirically?~~ (Addressed: observe agent effectiveness with familiar patterns)
5. ~~Should we adopt exact GitHub Issues field naming?~~ (Decided: keep `status`, it has broader fitness)
6. Should parent/child support JIRA-style hierarchies or GitHub-style task lists?
7. What's the right threshold for "branch for this issue"?
