---
id: code-design
name: code-design
description: Guide a technical design through its full lifecycle — explore the problem space, design the solution, and land the design artifacts (docs, ADRs, knowledge entries, INDEX cross-references) — without writing implementation code. Use when the user wants to design or redesign a system/feature/module, evaluate technical options and produce a decision, draft an RFC/design doc, or produce a review-ready architecture proposal. Do NOT use for pure brainstorming (use openspec-explore), for changes that need implementation tasks (use openspec-propose), or when the user is already implementing code.
---

# Code Design

A three-phase lifecycle for producing **decision-grade** design deliverables:
**Explore → Design → Land**. The skill stops at the implementation boundary.

## When to Use

- User wants to design a new system, feature, module, or service
- User wants to redesign or refactor an existing component (architecture-level)
- User wants to evaluate options and produce a decision (RFC, tech selection)
- User wants a review-ready design doc handed back to them
- "Should we do X or Y?" — needs structured trade-off analysis

## When NOT to Use

| Situation | Use instead |
|-----------|-------------|
| Pure brainstorming / open exploration | `openspec-explore` |
| Need formal change with implementation tasks | `openspec-propose` |
| Already implementing code | general tools |
| Bug investigation / debugging | general tools |

## The Lifecycle

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  1. EXPLORE │ ───▶ │  2. DESIGN  │ ───▶ │   3. LAND   │ ──▶ handoff
└─────────────┘      └─────────────┘      └─────────────┘
   no artifacts        design doc          written to repo
   yet (or just        + diagrams          + cross-refs
   problem             + trade-offs        updated
   statement)
```

### Phase 1 — Explore

Clarify the problem before designing solutions.

- Identify **stakeholders** and **success criteria**
- Map the **current state**: read code, read existing docs, identify patterns already in use
- Surface **constraints**: technical, business, time, team, compliance
- List **unknowns** and **risks** — explicit "we don't know X" is valuable

**Output** (conversation only, not yet committed): Problem statement + context map + open questions.

If the problem is unclear after exploration, surface 2–3 candidate framings and let the user pick.

### Phase 2 — Design

Generate the design. Always produce **at least two viable options** before recommending one.

- **Options**: 2–3 approaches with different trade-offs
- **Comparison table**: cost, risk, complexity, reversibility, time-to-implement
- **Recommended path**: pick one (or escalate to user) and justify
- **Design artifacts** (see `references/design-template.md`):
  - Architecture overview (ASCII or Mermaid)
  - Component responsibilities
  - Data flow (request/response, events, state)
  - Interface contracts (API shape, message schema, key types)
  - State management approach
  - Failure modes & mitigations
  - Migration / rollout plan (if changing existing systems)
  - Open questions carried forward

Use ASCII diagrams liberally. A good diagram replaces paragraphs.

### Phase 3 — Land

Deliver the design into the right places in the repo. This phase **writes files** but does **not** write implementation code.

Determine landing destinations based on what was designed:

| Design content | Land in |
|----------------|---------|
| Subsystem / domain-scoped design | `docs/design/<domain>/<topic>.md` (one folder per domain/subsystem) |
| Significant decision with rationale | Project's ADR convention (e.g. `docs/adr/YYYY-MM-DD-<slug>.md` or `knowledge/notes/decisions/`) |
| Concept / term / field definition | knowledge entry (`concept`) |
| Service / module responsibility | knowledge entry (`service`) |
| Cross-module dependency | knowledge entry (`relation`) |
| Gotcha / non-obvious behavior | knowledge entry (`pitfall`) |

`<domain>` follows the project's subsystem taxonomy. If the design is genuinely cross-cutting, use `docs/design/_cross/<topic>.md` or a `_shared/` folder; do **not** dump it at the `docs/design/` root.

After writing:

1. Update cross-references — `INDEX.md` / `README.md` / relevant table of contents
2. Verify links resolve (no broken anchors, no orphan files)
3. Produce a **handoff summary** for the user: what was written, where, and what is needed next (typically: an OpenSpec change proposal for implementation, or a review request)

## Guardrails

- **Never write implementation code** — explicit boundary; stop at handoff
- **Never create implementation tasks** (`tasks.md` with code steps) — that's `openspec-propose`'s job
- **Always produce visual artifacts** — diagrams, tables, comparisons
- **Always state trade-offs explicitly**, even for the chosen path
- **Always update cross-references** — orphaned designs rot fast
- **Always respect repo conventions** — kebab-case filenames, one H1 per file, fenced diagrams, table-based cross-refs
- **Always distinguish "decided" vs "open"** — bold-mark the recommendation, list open questions separately

## Quick Templates

### Trade-off table

```
| Option | Cost | Risk | Reversibility | Time | Complexity |
|--------|------|------|---------------|------|------------|
| A      | $$   | low  | high          | 2w   | low        |
| B      | $    | med  | low           | 1w   | high       |
| C      | $$$  | low  | mid           | 4w   | low        |
```

### Recommended path

```
**Recommendation: Option B**, because [primary reason].
Trade-offs accepted: [list].
Reversibility plan: [how to back out if wrong].
```

### Handoff summary

```
## Handoff

**Designed**: [one-line summary]
**Files written**:
- `path/to/file.md` — [purpose]
- `path/to/adr.md` — [decision]
**Cross-refs updated**: `INDEX.md`, [other]
**Next step** (implementation, not part of this skill):
- [ ] Open OpenSpec change via `openspec-propose`
- [ ] Schedule design review with [team]
**Open questions**: [list, or "none"]
```

## See Also

- `openspec-explore` — free-form thinking partner (no artifacts, no commitment)
- `openspec-propose` — formal change with implementation tasks (next step after code-design)
- `references/design-template.md` — full design-doc skeleton (optional scaffold)
