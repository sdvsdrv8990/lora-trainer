# pipe-policy-core

> Load this skill at the start of EVERY pipeline session, immediately after
> `/pipe-dev-guide`. These are the standing laws — not suggestions.
> Source of truth: `pipeline/audit/CONSTITUTION.md`.

---

## The Three Invariants

These may never be violated:

1. **Server must always respond.**
   Every tool ends in `{"ok": bool, ...}`. No unhandled exception reaches Claude.
   If the server crashes, Claude loses the pipeline.

2. **Claude is the only thing that advances pipeline state.**
   The app sets `step_status: in_progress` and `step_status: complete` on the
   *current* step only. Only `pipeline_set_state` (called by Claude) may increment
   `current_step`. No module does this autonomously.

3. **Every module does exactly one thing.**
   No `utils.py`, no `helpers.py`. `server.py` only dispatches. Business logic lives
   in single-purpose modules under `src/`. Complexity hides in modules, not in tools.

---

## Safe Move Protocol

Before moving, deleting, or restructuring any code, verify ALL rules that apply.

### RULE 1 — Moving code

Never move code unless ALL five are true simultaneously:
- (a) Code is provably unreachable from its current location OR documents a violation
      (wrong zone, wrong file, circular import).
- (b) Destination file and its tests are fully understood.
- (c) No tool response shape changes as a result.
- (d) `python -m py_compile` passes after the move.
- (e) Done in ONE commit with ONE test verifying before/after.

**One false condition = do not move.**

### RULE 2 — Deleting code

Never delete code in the same commit as a move.
Mark with `# MISPLACED: belongs in X` and leave it.
Delete in a separate commit, only after replacement is verified working.

### RULE 3 — Missing entities

Do NOT move the code that uses a missing entity.
ADD the missing entity/function/file.
THEN verify the complete flow.

### RULE 4 — Misplaced but working code

Leave it in place.
Create a file skill documenting the violation.
Record as MEDIUM severity in `pipeline/audit/AUDIT_REPORT.md`.
Fix only in a dedicated refactor session, never during feature work.

### RULE 5 — Logic error in correct file

Fix the error. Do not restructure around it.

### RULE 6 — Missing external binary/dependency

Do NOT remove the calling code.
Add a graceful check + clear human-readable error.
Document the dependency in `PRODUCTION_PIPELINE.md`.

---

## Skill Loading Tiers

### Tier 1 — Every session, no exceptions

| Skill | Why |
|---|---|
| `/pipe-dev-guide` | Project identity, module map, two-phase protocol |
| `/pipe-policy-core` | This file — standing laws |

### Tier 2 — Load when touching specific areas

| Trigger | Skill |
|---|---|
| Editing `server.py` | `/pipe-mcp-tools` |
| Any Pydantic entity | `/pipe-entities` |
| Files in `src/audio/` | `/pipe-file-audio-[filename]` if exists |
| Files in `src/images/` | `/pipe-file-images-[filename]` if exists |
| Any adapter in `adapters/` | `/pipe-adapter-pattern` |
| Writing any test | `/pipe-test-patterns` |
| OAuth, tunnel, connector | `/pipe-claude-connector` |
| **Any code change** | `/pipe-planning-gate` |

### Tier 3 — Load for specific workflow areas

| Trigger | Skill |
|---|---|
| Niche-specific content | `/pipe-niche-[niche-name]` |
| Remotion TypeScript layer | `/pipe-arch-remotion` |
| DaVinci / FCPXML / resolve-mcp | `/pipe-arch-davinci` |
| Character SVGs or lipsync | `/pipe-arch-character` |

### File-without-skill rule

Touching a file with no matching Tier 2/3 skill?
1. Check `pipeline/audit/` for existing findings about that file.
2. If violations found: do NOT proceed without a plan.
3. Create the file skill first, then proceed.

---

## Audit Severity Definitions

| Severity | Definition | Action |
|---|---|---|
| **CRITICAL** | Server crash, unhandled exception to Claude, silent data corruption, blocking pipeline bug | Fix in same session. Do not commit other work first. |
| **HIGH** | Wrong response shape, silent empty result from bad path, cryptic missing-binary error, circular import, state gate bypass | Write steps to `REMEDIATION_PLAN.md`. Fix in dedicated session. |
| **MEDIUM** | Code in wrong file (works), wrong-layer import (no crash), missing docstring, magic string, business logic in `server.py` | Create file skill. Note in `AUDIT_REPORT.md`. |
| **LOW** | Unused import, function >40 lines, missing param description | List in `AUDIT_REPORT.md`. No action. |

**Mixing rule:** Never fix CRITICAL and HIGH in the same commit. CRITICAL fixes must
be atomic. HIGH fixes may batch within a single dedicated remediation session only.

---

## Niche Adaptation Boundaries

### What changes per niche (config only)

- `channel_config.json` — tone, style, vocabulary, audience, CTA
- Script structure — hook formulas, pacing, proof pattern
- Visual style — character colors, animation energy
- Competitor channel list — which channels to study
- Registry columns — niche-specific metadata KPIs

### What never changes

- Pipeline steps 0–6 and their order
- Tool names and response shapes
- Scenario workspace file/directory structure
- Module boundaries and layer map
- The Three Invariants

### Niche adaptation rule

Creating a channel for a new niche:
1. Load `/pipe-niche-[niche-name]`.
2. Run `pipeline_save_channel_config` with niche values.
3. Run `pipeline_create_channel_skills` to generate 5 skill `.md` files.
4. Do NOT change tools, modules, or entities. Adaptation is config only.

---

## Known CRITICAL Issues (as of 2026-05-23)

| File | Issue | Status |
|---|---|---|
| `src/davinci/exporter.py:52` | Relative `file://` paths in FCPXML break DaVinci import | Fixed in commit e522444 — verify on local PC |
| `src/remotion/renderer.py:36` | `render_scene_preview` raises `NotImplementedError` | Known stub — implement via FFmpeg frame extract in Phase 2 |

## Known Missing Components (as of 2026-05-23)

| Component | Location | Needed For |
|---|---|---|
| Remotion TypeScript layer | `pipeline/remotion/` | `pipeline_render_scene` to produce real MP4 |
| Stickman.tsx | `pipeline/remotion/src/components/` | Character animation |
| FloatingText.tsx | `pipeline/remotion/src/components/` | Text overlays |
| SpeechBubble.tsx | `pipeline/remotion/src/components/` | Dialog bubbles |
| Animation presets | `pipeline/remotion/src/presets/` | `dramatic_popup`, `shake`, `slide_in` |
| SVG character parts | `global_assets/characters/crowd/` | Stickman body/eyes/mouth |

See `docs/pipeline/integration/` for implementation specs on all of the above.
