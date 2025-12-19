---
name: adr
description: Architecture Decision Records for documenting significant technical decisions with context and trade-offs. Use when making architectural choices, recording design rationale, or reviewing past decisions.
---

# ADR Skill (Architecture Decision Records)

Lightweight decision records for capturing significant technical decisions with their context and reasoning.

**Portable:** Copy this skill directory to any repo. Configure location and format in CLAUDE.md.

## First-Time Setup

**On first use in a repo, confirm with the user:**

1. **Storage location** - Default: `.decisions/`
   - Alternatives: `docs/adr/`, `docs/decisions/`, `dev/decisions/`

2. **File naming** - Default: `NNN-short-name.md` (e.g., `001-auth-approach.md`)

3. **Additional frontmatter** - Some repos require specific frontmatter (tags, authors, etc.)

Once confirmed, document the choices in CLAUDE.md under a "Design Decisions" or "ADRs" section.

## When to Create an ADR

Create a decision record when:

- **Multiple valid approaches** exist with meaningful trade-offs
- **Cross-cutting concerns** affect multiple parts of the codebase
- **The decision needs future reference** (why did we choose X?)
- **Stakeholder alignment** is needed before implementation

Don't create ADRs for:
- Obvious implementation choices
- Decisions that won't matter in a month
- Pure style/formatting preferences

**Rule of thumb:** If you'd want to explain "why we did it this way" to a future contributor, write an ADR.

## Lifecycle

```
Draft → Accepted → [Superseded by NNN]
```

- **Draft:** Under discussion, content may change
- **Accepted:** Decision made, document is stable (don't edit substance)
- **Superseded:** Replaced by a newer ADR (link to it)

No "Rejected" status - if you decide against something, either don't write an ADR or mark it Accepted with the decision being "we won't do X because..."

## Recommended Structure

```markdown
# ADR NNN: Title

**Status:** Draft | Accepted | Superseded by NNN
**Date:** YYYY-MM-DD

## Context

What situation or problem prompted this decision? Include relevant constraints.

## Decision

What was decided? Be specific and concrete.

## Consequences

What are the implications? Include both positive and negative.

## Alternatives Considered

What other options were evaluated? Why were they rejected?
```

### Optional Sections

- **Related Issues:** Links to issues that prompted or implement this ADR
- **Open Questions:** Unresolved issues (remove before accepting)
- **References:** Links to external resources, prior art, research

## Relationship to Issues

ADRs and issues serve different purposes:

| Aspect | Issues | ADRs |
|--------|--------|------|
| Purpose | Track work items | Record decisions and reasoning |
| Lifecycle | Open → Closed | Draft → Accepted |
| Granularity | Individual tasks | Cross-cutting concerns |
| Mutability | Append-only events | Evolve during draft, stable after |

**Linking pattern:**
- Issues reference ADRs: "Implements ADR-002" or "See `.decisions/002-...` for design"
- ADRs optionally list related issues

## Creating an ADR

**Using the CLI (recommended):**
```bash
adr create auth-approach     # Creates draft-auth-approach.md
# Edit the file...
adr accept auth-approach     # Renames to NNN-auth-approach.md, updates status
```

**Manual process:**
1. Create file as `draft-slug-name.md` (no number yet)
2. Use Status: Draft
3. Reference from related issues
4. Discuss/iterate while Draft
5. When ready: `adr accept slug-name` assigns next number and updates status
6. Implement via issues

**CLI Commands:**
- `adr` - List all ADRs (accepted and drafts)
- `adr create <slug>` - Create a new draft ADR
- `adr accept <slug>` - Accept a draft, assign number, update status

## Protocol Fitness Note

This format draws from established patterns (PEPs, RFCs, ADRs) that appear extensively in LLM training data. The Status field, numbered identifiers, and section names (Context, Decision, Consequences) activate strong priors for how decision documents work.
