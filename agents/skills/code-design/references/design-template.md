# Design Doc Template

A scaffold for Phase 2 — Design artifacts. Copy and trim to fit the actual problem; not every section is mandatory.

---

# <Title>

> One-paragraph elevator pitch: what we're building, why, and the chosen path in one breath.

## Context

- **Problem**: [the gap we're closing]
- **Stakeholders**: [who cares, who blocks, who benefits]
- **Success criteria**: [how we know it worked]
- **Constraints**: [technical, business, time, team, compliance]
- **Out of scope**: [what this design deliberately does NOT address]

## Current State

Brief description of the existing system/subsystem this design touches. Link to relevant docs, ADRs, code paths. Identify the patterns already in use that this design must fit with.

## Options Considered

| Option | Cost | Risk | Reversibility | Time | Complexity |
|--------|------|------|---------------|------|------------|
| A      |      |      |               |      |            |
| B      |      |      |               |      |            |
| C      |      |      |               |      |            |

Brief description of each option (1–3 lines each).

## Recommended Approach

**Recommendation: Option X**, because [primary reason].

Trade-offs accepted:
- [trade-off 1]
- [trade-off 2]

Reversibility plan: [how to back out if wrong].

## Architecture

```
┌──────────────────────────────────────────────┐
│     ASCII or Mermaid diagram of the system   │
└──────────────────────────────────────────────┘
```

- **Component A**: [responsibility]
- **Component B**: [responsibility]
- **Data flow**: [request path / event path / state propagation]

## Interfaces

### API / message contracts

```
<Type or schema sketch>
```

### Key types

```pseudo
struct Foo { ... }
```

## State Management

- Where state lives: [DB / cache / in-memory / external]
- State transitions: [state machine if relevant]
- Consistency model: [strong / eventual / read-your-writes]

## Failure Modes

| Failure | Likelihood | Impact | Mitigation |
|---------|------------|--------|------------|
| [scenario] | low/med/high | [blast radius] | [handling] |

## Rollout / Migration

If this changes an existing system:
- Phase 1: [shadow / dark launch / feature flag]
- Phase 2: [gradual rollout]
- Phase 3: [full migration + cleanup]

## Open Questions

- [ ] [things still unresolved]
- [ ] [spikes to run]

## Cross-References

- **Landing destinations**: [list which repo paths this design maps to]
  - Primary: `docs/design/<domain>/<topic>.md` (domain = owning subsystem)
  - Decision (if any): follow project's ADR convention (e.g. `docs/adr/YYYY-MM-DD-<slug>.md`)
  - Knowledge entries: [concept / service / relation / pitfall] as applicable
- **Related designs**: [links to siblings]
- **Downstream**: [what implementation work this unblocks]
