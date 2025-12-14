# Concepts

Terms and concepts developed or refined during this project.

---

## Protocol Fitness

**Definition:** The degree to which a format, convention, or interface aligns with patterns that LLMs have encountered extensively in their training data, leading to better AI performance when working with that format.

**Core insight:** LLMs have strong statistical priors from training data. Formats that appear millions of times (GitHub Issues, PEPs, RFCs, JSON, markdown) activate these priors, enabling more accurate and effective AI behavior. Novel or idiosyncratic formats lack these priors, requiring the model to reason from scratch.

**Etymology:**
- **Protocol** - suggests standardized formats and conventions (as in network protocols, PEPs, RFCs)
- **Fitness** - evolutionary connotation; how well-adapted something is to its environment

**Practical implications:**

1. **Prefer familiar formats** - GitHub Issues semantics may work better than a novel issue tracker format because LLMs have trained on millions of GitHub issues

2. **Use recognizable field names** - `status`, `title`, `description` activate stronger priors than `state_flag`, `heading`, `details`

3. **Follow established conventions** - Markdown, JSON, numbered lists, and section headers (## Context, ## Decision) are deeply embedded in training data

4. **Leverage domain patterns** - If building a decision record system, align with PEP/RFC/ADR patterns that LLMs know well

**Example:**
```
Low protocol fitness:
{"task_flag": "pending", "task_text": "Fix bug", "urgency_level": 2}

High protocol fitness:
{"status": "open", "title": "Fix bug", "priority": 2}
```

Both convey the same information, but the second activates priors from millions of issue trackers, todo apps, and project management tools in training data.

**Related concepts:**
- In-distribution vs out-of-distribution (ML terminology)
- Training data priors / statistical priors
- Prompt engineering (related but focused on instruction phrasing)

**First documented:** 2025-12-14, during development of issue tracking and ADR skills for Claude Code workflows.

**Status:** Coined term - not found in existing literature as of 2025-12-14.
