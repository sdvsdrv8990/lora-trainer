# Pipeline Constitution

> Governing document for the AI-controlled video production pipeline.
> Every future AI session working on this system treats the rules here as law.
> Created: 2026-05-23 — Prompt-00 of the 13-step quality ecosystem.

---

## Philosophy

This system is an AI-controlled video production pipeline: a Python MCP server that
Claude.ai web operates via 95 tool calls to produce complete video episodes — voiceover,
scene images, Remotion-rendered scene clips, and a DaVinci-ready FCPXML — from a plain
language script. It is **not** a generic media framework, a standalone editor, a
content-management platform, or an AI training system. Success looks like a complete
episode flowing from "user writes script" to "DaVinci-ready files on disk" with zero
manual intermediate steps. The end user's only job is to write the script; Claude handles
every production step by calling tools. Claude's role is **orchestrator, not executor**: it
reads tool responses, decides what to call next, and advances pipeline state — it never
runs Python, shell commands, or renders video itself.

### The Three Invariants

These principles may never be violated under any circumstances:

1. **The server must always respond.**
   No tool may raise an unhandled exception to Claude. Every code path ends in
   `{"ok": bool, ...}`. If the server crashes, Claude loses control of the pipeline.

2. **Claude is the only thing that advances pipeline state.**
   The app writes `step_status: in_progress` and `step_status: complete` on the
   *current* step, but it never increments `current_step`. Only `pipeline_set_state`
   called by Claude may advance the step counter. No module may advance state
   autonomously.

3. **Every module does exactly one thing.**
   Complexity is buried in single-purpose modules, not in tools or grab-bag files.
   No `utils.py`, no `helpers.py`. If a module does two things, split it. Tools
   in `server.py` only dispatch: validate input → call module → return JSON.

---

## Code Safety Policy

### Safe Move Protocol

When AI is considering moving, deleting, or restructuring code, these rules govern
every decision.

**RULE 1 — NEVER move code unless ALL of these are true:**
- (a) The code is provably unreachable from its current location OR creates a
      documented violation (wrong zone, wrong file, circular import).
- (b) The destination file and its tests are fully understood.
- (c) No tool response shape changes as a result of the move.
- (d) A static validator (`python -m py_compile`) can confirm correctness after
      the move.
- (e) The move can be done in ONE commit with ONE test verifying before/after
      behavior.

All five conditions must hold simultaneously. One missing condition = do not move.

**RULE 2 — NEVER delete code.**
Mark displaced code with `# MISPLACED: belongs in X` and leave it in place.
Deletion happens in a separate dedicated commit, only after the replacement is
verified working. Deleting and moving in the same commit is forbidden.

**RULE 3 — When missing entities are found:**
Do NOT move the code that uses them.
ADD the missing entity/function/file.
THEN verify the complete flow works end-to-end.
The fix target is the missing piece, not the consumer.

**RULE 4 — When code is in the wrong file but the system works:**
Leave it in place.
Create a file-specific skill documenting the violation.
Note the violation as MEDIUM severity in the audit.
Fix it only in a dedicated refactor session, never during feature work.
Working-but-misplaced is not an emergency.

**RULE 5 — When code has logic errors but is in the right file:**
Fix the error. Do not restructure the surrounding code.
A bug fix is a bug fix, not a refactor invitation.

**RULE 6 — When a binary or external dependency is missing:**
Do NOT remove the code that calls it.
Add a graceful check + clear human-readable error message.
Document the dependency in `PRODUCTION_PIPELINE.md`.
Missing binaries (rhubarb, ffmpeg, ts-node) must fail loudly, not silently.

---

## Skill Loading Policy

Every AI session working on this pipeline must load skills from this table before
writing a single line of code or documentation.

### Tier 1 — Load at every session start (no exceptions)

| Skill | Reason |
|---|---|
| `/pipe-dev-guide` | Project identity, module map, two-phase protocol, 95-tool list |
| `/pipe-policy-core` | This constitution in skill form — rules every session must follow |

### Tier 2 — Load when touching specific areas

| Trigger | Additional skill |
|---|---|
| Editing `pipeline/src/mcp/server.py` | `/pipe-mcp-tools` |
| Adding or modifying any Pydantic entity | `/pipe-entities` |
| Editing any file in `src/audio/` | `/pipe-file-audio-[filename]` (if exists) |
| Editing any file in `src/images/` | `/pipe-file-images-[filename]` (if exists) |
| Editing any adapter in `src/tts/adapters/` or `src/images/adapters/` | `/pipe-adapter-pattern` |
| Writing any test | `/pipe-test-patterns` |
| Changing OAuth, tunnel, or connector logic | `/pipe-claude-connector` |
| **Any code change whatsoever** | `/pipe-planning-gate` |

### Tier 3 — Load for specific workflow areas

| Trigger | Additional skill |
|---|---|
| Creating content for a specific audience niche | `/pipe-niche-[niche-name]` |
| Working on Remotion TypeScript layer | `/pipe-arch-remotion` |
| Working on DaVinci FCPXML or resolve-mcp | `/pipe-arch-davinci` |
| Working on character SVGs or lipsync | `/pipe-arch-character` |

### File-without-skill rule

If you are about to touch a file and no Tier 2 or Tier 3 skill exists for it:
1. Check `pipeline/audit/` for any existing audit results mentioning that file.
2. If the file has known violations, do NOT proceed without a plan.
3. Create the file skill first, then proceed.

---

## Audit Policy

### Severity Definitions

**CRITICAL — fix immediately; blocks all other work:**
- Server crashes or loses state on any code path
- Tool returns non-JSON or raises an unhandled exception to Claude
- Data is silently corrupted (wrong values written, fields lost without error)
- Blocking bug that prevents a pipeline step from completing (e.g. relative paths
  in FCPXML, missing required entity field)

**HIGH — fix in next dedicated session; do not mix with feature work:**
- Tool returns a response that is missing required fields
- Wrong file path causes a silent empty result with no error
- Missing binary causes a cryptic traceback instead of a clear message
- Circular import that could cause import-time failure
- State gate not enforced (step allowed to run without prior step being complete)

**MEDIUM — schedule for refactor session; document in file skill:**
- Code in the wrong file (misplaced, but the system works)
- Module boundary violation (imports from wrong layer, but no crash)
- Missing module-level docstring
- Magic string buried in a function (should be a named constant)
- Tool business logic inside `server.py` (should be delegated to a module)

**LOW — note and move on; no action required:**
- Unused import
- Function slightly over 40 lines
- Missing parameter description on a rarely-used tool
- Minor style inconsistency

### Policy for Acting on Audit Results

| Severity | Action |
|---|---|
| CRITICAL | Fix in the same session it is found. Do not commit unrelated work first. |
| HIGH | Write exact remediation steps to `pipeline/audit/REMEDIATION_PLAN.md`. Fix in a dedicated session. |
| MEDIUM | Create file skill documenting the violation. Note in `pipeline/audit/AUDIT_REPORT.md`. |
| LOW | List in `pipeline/audit/AUDIT_REPORT.md`. No action required. |

### Mixing rule

Never fix CRITICAL and HIGH findings in the same commit. A CRITICAL fix must be
atomic and reviewable on its own. HIGH fixes should be batched only within the
same dedicated remediation session, not mixed with feature work.

---

## Niche Adaptation Policy

This pipeline is designed to produce video content in any audience niche. The
adaptation model separates what changes per niche from what never changes.

### What Changes Per Niche

| Layer | What adapts |
|---|---|
| `channel_config.json` | Tone, style, vocabulary, target audience, call-to-action phrasing |
| Script structure | Hook types, pacing rhythm, proof structure, CTA style |
| Visual style | Character color palette, animation energy level, text treatment |
| Competitor intelligence | Which channels to study, which metrics matter in this niche |
| Registry templates | What metadata columns to track (niche-specific KPIs) |

### What Never Changes

Regardless of niche, these stay constant:

- Pipeline steps (always 0 → 6 in order)
- Tool names and their response shapes
- File and directory structure for a scenario workspace
- Module boundaries and layer map
- The Three Invariants from Philosophy

### Niche Skill Structure

One skill file per niche (e.g. `/pipe-niche-productivity`, `/pipe-niche-finance`).
Each niche skill must contain:

| Section | Content |
|---|---|
| Target audience | Psychology, pain points, trust signals for this niche |
| Hook formulas | 3–5 opening patterns that work in this niche |
| Script pattern | Problem → solution → proof → CTA, adapted for this niche |
| Visual energy | Calm / medium / high-energy and why |
| Competitor channels | Specific channels to track in `pipeline_add_competitor_channel` |
| Registry columns | Which extra metadata columns to add per video in this niche |

### Adaptation boundary

When Claude creates a new channel for a niche:
1. Load the niche skill.
2. Run `pipeline_save_channel_config` with niche-specific values.
3. Run `pipeline_create_channel_skills` to generate 5 skill `.md` files from the config.
4. Do NOT change any tool, module, or entity. Niche adaptation is pure config.
