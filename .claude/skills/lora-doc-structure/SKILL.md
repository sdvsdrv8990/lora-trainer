---
name: lora-doc-structure
description: "Documentation structure rules for lora-trainer. Defines what goes in docs/project/ vs docs/development/, how to update memory.md and architecture.md, and the writing style for all project docs."
---

# lora-doc-structure — Documentation Structure Rules

## Directory Layout

```
docs/
├── project/                ← STABLE: decisions that survive sessions
│   ├── memory.md           ← Stable project decisions (source of truth)
│   ├── architecture.md     ← Module boundary map and data flow
│   └── README.md           ← User-facing overview of docs
└── development/            ← VOLATILE: in-progress notes, research, bugs
    ├── README.md           ← Index of development docs
    ├── hot-test-bugs.md    ← Active known bugs in tests or dev
    └── <feature>.md        ← Per-feature research or design notes
```

---

## docs/project/memory.md — The Truth File

This file answers: **What decisions are stable and must not be reversed without a documented reason?**

### When to Update

Update `memory.md` when:
- A library, flag, or version is chosen and locked (e.g., `AdamW` not `AdamW8bit`)
- A constraint is discovered (e.g., RDNA2 requires `HSA_OVERRIDE_GFX_VERSION=10.3.0`)
- A design principle is established (e.g., "no subprocess calls outside trainer.py")
- A user-facing promise is made (e.g., "the happy path is `python train.py --images ./images`")

### When NOT to Update

Do not add to `memory.md`:
- Temporary decisions or experiments
- Implementation details that may change
- Bug descriptions (those go in `docs/development/hot-test-bugs.md`)
- In-progress research

### Format

```markdown
## <Category>

- Decision: [what was decided]
  - Reason: [why — constraint, test result, user requirement]
  - Effective since: [date or phase]
```

---

## docs/project/architecture.md — The Boundary Map

This file answers: **Which file owns which concern?**

### Required Sections

1. **Module Map** — table of `Concern → File`
2. **Data Flow** — how a training run moves through the modules (CLI → validate → dataset → train → output)
3. **Forbidden Cross-Dependencies** — which files must NOT import from which

### When to Update

Update `architecture.md` when:
- A new file is added to `src/`
- A concern is moved from one file to another
- A forbidden dependency is discovered and documented
- The data flow changes

---

## docs/development/ — Per-Feature Working Notes

Create a new file here when:
- Researching a new feature or library
- Investigating a persistent bug
- Designing a non-obvious implementation

**Naming:** `docs/development/<topic>.md`

**Lifecycle:** Delete or archive when the feature ships and findings are merged into `memory.md` or `architecture.md`.

**Never** leave development docs as the only record of a stable decision. Promote to `docs/project/memory.md`.

---

## Writing Style Rules

1. **No generic headers.** Use "AdamW on AMD" not "Optimizer Notes".
2. **Every decision has a reason.** Don't write "Use AdamW." Write "Use AdamW — AdamW8bit is unstable on ROCm."
3. **No padded prose.** Use tables and bullet lists over paragraphs.
4. **Audience is future-AI, not end-user.** Docs here guide AI working on the codebase, not users running train.py.
5. **Dates matter.** When documenting a decision tied to a library version, record the version and date.

---

## Documentation Completion Checklist

After any code change:

```
□ memory.md updated if a stable decision was made
□ architecture.md updated if a module was added, moved, or removed
□ development/<feature>.md created for non-trivial research (and later cleaned up)
□ No stable decision lives only in a development/ file
□ No doc references a library version without stating what version
```
