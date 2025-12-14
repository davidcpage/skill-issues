# Decision 003: Design Doc Process and Protocol Fitness

**Status:** Accepted
**Date:** 2025-12-14
**Accepted:** 2025-12-14

## Context

We've been creating design docs in `.decisions/` for complex issues. This has worked well - the docs serve as first-class artifacts that capture reasoning, not just conclusions.

This raises a meta question: should we formalize the design doc process? And does **protocol fitness** apply here too - could aligning with well-known processes like PEPs or RFCs improve AI effectiveness?

## Protocol Fitness for Design Processes

PEPs (Python Enhancement Proposals) and RFCs (Request for Comments) are extensively represented in training data:

| Format | Domain | Key Characteristics |
|--------|--------|---------------------|
| PEP | Python | Numbered, status field, canonical sections, BDFL decides |
| RFC | Internet standards | Numbered, status track, formal structure, consensus process |
| ADR | Software architecture | Numbered, status, context/decision/consequences |
| IETF BCP | Best practices | Like RFC but for recommendations |

All share common patterns:
- **Numbered identifiers** (PEP-8, RFC-2119, ADR-001)
- **Explicit status** (Draft, Accepted, Final, Rejected, Superseded)
- **Canonical sections** (Abstract, Motivation, Specification, Rationale)
- **Immutable once accepted** (new doc supersedes, doesn't edit)
- **Discussion elsewhere** (mailing list, issues, etc.)

These patterns are deeply embedded in training data. An AI reading "Status: Draft" or "## Motivation" has strong priors about what to expect.

## Current Approach

Our `.decisions/` directory uses:
- Numbered files: `001-name.md`, `002-name.md`
- Informal status field
- Flexible sections (whatever fits the topic)
- Issues reference decisions; loose back-links
- Docs evolve during drafting

This is lightweight and working. The question is whether more structure adds value.

## Options

### Option A: Keep it loose (current)

**Pros:**
- Low overhead
- Flexibility for different types of decisions
- Working well so far

**Cons:**
- No protocol fitness benefits
- Inconsistent structure across docs
- Status field is informal

### Option B: Light PEP-style conventions

Adopt conventions without strict enforcement:

```markdown
# Decision NNN: Title

**Status:** Draft | Accepted | Superseded by NNN
**Date:** YYYY-MM-DD
**Related Issues:** #024, #025

## Summary
One paragraph overview.

## Motivation
Why is this needed?

## Design
The actual proposal/decision.

## Alternatives Considered
What else was evaluated?

## Open Questions
Unresolved issues (remove when accepting).
```

**Pros:**
- Protocol fitness: sections match PEP/RFC patterns
- Consistent structure aids navigation
- Status field becomes meaningful
- Still lightweight

**Cons:**
- Some overhead
- May feel bureaucratic for small decisions

### Option C: Full ADR (Architecture Decision Records) style

Use established ADR format:

```markdown
# ADR NNN: Title

**Status:** Proposed | Accepted | Deprecated | Superseded
**Date:** YYYY-MM-DD
**Deciders:** [list]

## Context
What is the issue?

## Decision
What was decided?

## Consequences
What are the results?
```

**Pros:**
- Well-documented format with tooling
- Very strong protocol fitness (ADRs are common in training data)
- Forces clear consequence thinking

**Cons:**
- More rigid than we may need
- "Deciders" field less relevant for solo/small team

## Relationship to Issues

Design docs and issues serve different purposes:

| Aspect | Issues | Design Docs |
|--------|--------|-------------|
| Purpose | Track work items | Record decisions and reasoning |
| Lifecycle | Open → Closed | Draft → Accepted → (Superseded) |
| Granularity | Individual tasks | Cross-cutting concerns |
| Mutability | Append-only events | Evolve during draft, stable after |

**Linking conventions:**
- Issues can reference decisions: "See .decisions/002-... for design"
- Decisions can list related issues: "Related Issues: #024, #025"
- Implementation issues should reference the decision they implement

This is one-way dependency like sessions→issues: decisions are the stable artifact, issues reference them.

## PEP Process as Reference

The PEP process has useful elements we could borrow:

1. **PEP types:** Standards Track, Informational, Process
   - We could have: Design (technical decisions), Process (workflow decisions), Informational (analysis/research)

2. **Status flow:** Draft → Accepted → Final (or Rejected/Withdrawn/Superseded)
   - Ours: Draft → Accepted → Superseded (simpler)

3. **Required sections:** Abstract, Motivation, Rationale, Specification
   - We could adopt: Summary, Motivation, Design, Alternatives

4. **Immutability:** Accepted PEPs don't change; new PEPs supersede
   - We could adopt: Draft docs evolve, Accepted docs are stable

## Recommendation

**Option B: Light PEP-style conventions**

Adopt these conventions without strict enforcement:

1. **Standard header:**
   ```markdown
   # Decision NNN: Title

   **Status:** Draft | Accepted | Superseded by NNN
   **Date:** YYYY-MM-DD
   **Related Issues:** (optional)
   ```

2. **Suggested sections** (use what fits):
   - Summary (one paragraph)
   - Motivation (why needed)
   - Design (the decision)
   - Alternatives Considered
   - Open Questions (remove when accepting)

3. **Status transitions:**
   - Draft: Under discussion, may change
   - Accepted: Decision made, stable
   - Superseded by NNN: Replaced by newer decision

4. **Linking:**
   - Issues reference decisions in descriptions
   - Decisions optionally list related issues

This gives protocol fitness benefits (AI recognizes PEP-like structure) while staying lightweight.

## Open Questions

~~1. Should we retroactively update existing decisions to match conventions?~~
   - No strict requirement; existing decisions work fine as-is

~~2. Do we need a "Rejected" status for decisions we explicitly decided against?~~
   - No; use Accepted with decision being "we won't do X because..."

~~3. Should there be a formal acceptance process, or is "author marks Accepted" sufficient?~~
   - Author marks Accepted is sufficient for this scale

## Implementation

Implemented as portable ADR skill: `.claude/skills/adr/SKILL.md`

Key decisions:
- Named "adr" for protocol fitness (well-established pattern)
- Skill documents methodology; CLAUDE.md provides repo-specific config
- First-use initialization prompts user to confirm location/format
- No tooling needed (just conventions in markdown)

## Related Issues

- #028: Research existing local-first issue trackers (may find design doc patterns)
- #029: Finalize design doc process conventions (closed by this acceptance)
