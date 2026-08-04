---
id: code-implement
name: code-implement
description: Drive a feature from problem statement through OpenSpec's full pipeline (explore → propose → apply → archive) with explicit user confirmation gates before each phase. Use when the user wants to implement a feature end-to-end, walk the full OpenSpec workflow, pick up a code-design handoff and ship it, or continue an existing change through to archive. Confirmation is mandatory between phases — the user can approve, revise, skip, or abort at every gate. Do NOT use for pure design work without implementation intent (use code-design), for thinking-only sessions (use openspec-explore directly), or for a single ad-hoc OpenSpec command.
---

# Code Implement

A gated pipeline that walks OpenSpec from problem statement to archived change. Each phase **stops and waits** for explicit user confirmation before proceeding.

## Position in the Workflow

```
   ┌────────────┐         ┌─────────────┐        ┌─────────────┐
   │ code-design│ ──────▶ │code-implement│ ──────▶ │  change     │
   │  (handoff) │         │ (this skill) │        │  archived   │
   └────────────┘         └──────┬──────┘        └─────────────┘
                                 │
                                 │ drives
                                 ▼
              ┌──────────────────────────────────┐
              │  OpenSpec pipeline              │
              │  explore → propose →            │
              │  apply → archive                │
              │  (each: ⚠ CONFIRM gate)        │
              └──────────────────────────────────┘
```

`code-implement` is downstream of `code-design`. If a handoff exists, this skill picks it up; otherwise it can start from a fresh problem statement.

## The Pipeline

```
   ⚠ Gate 1       ⚠ Gate 2       ⚠ Gate 3        ⚠ Gate 4
   Confirm        Confirm        Confirm         Confirm
   framing        exploration    proposal/       archive
                                 specs ready     sync choice
     │              │              │               │
     ▼              ▼              ▼               ▼
┌────────┐    ┌────────┐    ┌────────┐      ┌────────┐
│explore │───▶│propose │───▶│  apply │─────▶│archive │
└────────┘    └────────┘    └────────┘      └────────┘
  free-form     creates       implements      finalizes
  thinking      proposal/     tasks           change
                design/
                tasks
```

### Gate 1 — Confirm Framing

Before invoking `openspec-explore`:

- Restate the problem in one paragraph
- Identify the change name (kebab-case, derived from problem)
- List any handoff from `code-design` (if present, surface it)
- **Ask user to confirm scope and change name**. Options: proceed · revise scope · abort

Only after confirmation: hand off to `openspec-explore`.

### Gate 2 — Confirm Exploration

After `openspec-explore` has crystallized thinking:

- Summarize what was learned (problem, constraints, options considered)
- Surface any open questions that should be resolved before formalizing
- **Ask user to confirm readiness to formalize**. Options: ready to propose · resolve open questions first · keep exploring · abort

Only after confirmation: hand off to `openspec-propose`.

### Gate 3 — Confirm Proposal Review

After `openspec-propose` has created `proposal.md`, `design.md`, `tasks.md`:

- Show artifact paths and `openspec validate` output
- Estimate task count and rough scope
- **Ask user to confirm review path**:
  - "Proceed to apply" — implement now
  - "Pause for review" — stop here so user/team can review artifacts before code lands
  - "Revise proposal" — go back and update artifacts
  - "Abort" — close change without applying
- If user wants to apply: hand off to `openspec-apply-change`

### Gate 4 — Confirm Archive

After `openspec-apply-change` reports all tasks complete:

- Show final task list (all `- [x]`)
- Identify delta specs that need syncing
- **Ask user to confirm archive path**:
  - "Sync + archive" — run `openspec-sync-specs` then `openspec-archive-change`
  - "Archive without sync" — skip sync if user has handled it externally
  - "Pause for review" — stop before archive, leave change active
  - "Abort" — leave change active, no archive

Only after confirmation: hand off to `openspec-archive-change`.

## Confirmation Pattern

Every gate follows this exact pattern:

1. **Restate** — recap what just happened and what's next
2. **Surface** — list options with trade-offs in a table
3. **Wait** — stop, do NOT proceed, do NOT auto-advance
4. **Honor** — act only on explicit user choice (one of the options, or "abort"/"revise" override)

```
## Gate N: <phase name>

**Just completed**: [summary]
**About to do**: [next phase in one line]

| Option | What happens | Trade-off |
|--------|--------------|-----------|
| proceed | [next phase runs] | commits to implementation |
| pause | stop here, change stays in current state | review time, no momentum |
| revise | go back and update [which artifact] | extra iteration |
| abort | close without [next step] | loses partial work |

**Awaiting confirmation.**
```

## Stop Conditions

End the pipeline immediately if any of the following:

- User says "abort", "stop", "cancel", "退出", "取消" → confirm abort, then close
- `openspec validate` fails → don't proceed to apply, surface errors
- `openspec-apply-change` reports a blocker → don't auto-resume
- A gate's option chosen is "pause" or "abort" → stop, don't auto-continue on next turn
- OpenSpec CLI missing → report, suggest `openspec` install

## Pre-Conditions

Before starting Gate 1, verify:

- Working directory contains an OpenSpec project (or a registered store)
- `openspec` CLI is installed and reachable
- User has provided (or you have surfaced) a problem statement / handoff

If any of these is missing, ask before starting.

## Differences from Related Skills

| Skill | Scope | Confirmation gates |
|-------|-------|--------------------|
| `code-design` | Design lifecycle; no implementation | none (designer stays in design) |
| `openspec-explore` | Single phase: think freely | none |
| `openspec-propose` | Single phase: create change artifacts | none (creates artifacts, hands off) |
| `openspec-apply-change` | Single phase: implement tasks | none (drives task list) |
| `openspec-archive-change` | Single phase: archive change | one confirmation (sync choice) |
| **`code-implement`** | **Full pipeline across all 4 phases** | **four mandatory gates** |

## Quick Templates

### Pipeline status

```
## Pipeline: <change-name>

| Phase | Status | Gate |
|-------|--------|------|
| explore | ✓ done | Gate 1 ✓ approved |
| propose | ✓ done | Gate 2 ✓ approved |
| apply   | ⏳ in progress (4/7 tasks) | Gate 3 ✓ approved |
| archive | ⏸ pending | Gate 4 — awaiting confirmation |

**Next**: <phase name> requires confirmation to proceed.
```

### Resume from a checkpoint

If user says "继续" / "resume" / "next" mid-pipeline:

1. Check current state: `openspec status --change "<name>"`
2. Identify which gate is next
3. Restate that gate and wait

## See Also

- `code-design` — upstream; produces the handoff this skill consumes
- `openspec-explore` / `openspec-propose` / `openspec-apply-change` / `openspec-archive-change` — the underlying phase skills this orchestrator delegates to
