---
name: pipe-test-patterns
description: Load before writing any test for the pipeline app. Defines the test taxonomy, what to test per layer, mocking rules, and the test scenario ID system.
---

# pipe-test-patterns

## Test Taxonomy

```
tests/
├── unit/              ← per-module, no real engines, no real files
│   ├── entities/      ← Pydantic validation tests
│   ├── project/       ← manager + state logic
│   ├── scenario/      ← builder output format
│   ├── tts/           ← engine factory + adapter interface
│   ├── audio/         ← analyzer output format (real FFmpeg OK)
│   ├── images/        ← engine factory + batch logic
│   ├── assembly/      ← FFmpeg command builder (dry-run)
│   ├── davinci/       ← exporter logic (real Resolve NOT required)
│   └── mcp/           ← tool response shapes
└── integration/       ← end-to-end with real engines and real files
    ├── tts/           ← generate real audio and confirm file exists
    ├── audio/         ← confirm timing_report.json with real audio
    ├── images/        ← generate real image and confirm file exists
    └── pipeline/      ← full step sequences with a 2-scene scenario
```

## What to Test Per Layer

**Entities (`tests/unit/entities/`):**
- Valid payload parses without error.
- Missing required field raises `ValidationError`.
- Wrong type raises `ValidationError`.
- Field names match JSON contract.

**Project manager (`tests/unit/project/`):**
- Case 1 (both exist): no directories created, workspace path returned.
- Case 2 (sub-project missing): sub-project directory created, workspace returned.
- Case 3 (neither exists): full tree created.
- Case 4 (missing data): raises `MissingProjectDataError`.

**State manager (`tests/unit/project/`):**
- `set_in_progress` writes correct `state.json`.
- `set_complete` writes correct `state.json`.
- `load` with missing file raises `StateNotFoundError`.
- `load` with corrupted JSON raises `StateCorruptError`.

**MCP tools (`tests/unit/mcp/`):**
- Every tool returns `{"ok": bool}` in all code paths.
- Tool that fails returns `{"ok": false, "error": str}`.
- Tool never raises an exception to the caller.
- Generated input schemas have descriptions for every parameter.
- Public-facing numeric values may be accepted as strings when Claude.ai compatibility matters.

**MCP connector integration (`tests/integration/pipeline/` or dry-run evidence):**
- OAuth protected resource metadata is available at `/.well-known/oauth-protected-resource/mcp`.
- OAuth authorization metadata is available at `/.well-known/oauth-authorization-server`.
- JSON-RPC `initialize` over `POST /mcp` succeeds.
- Official MCP SDK `tools/list` returns the expected tool count.
- A bare `GET /mcp` is not treated as a valid health check.

**Adapter interface (`tests/unit/tts/`, `tests/unit/images/`):**
- Factory returns the correct adapter for each `engine` config value.
- Factory raises `ValueError` for unknown engine name.
- Adapter implements all abstract methods (structural test).

**FFmpeg assembly (`tests/unit/assembly/`):**
- Command builder produces correct FFmpeg flags for a 2-scene timing report (no real FFmpeg needed — assert command string).
- Dry-run mode (no actual render) confirms command shape.

## Mocking Rules

- Mock at the adapter boundary: mock `KokoroAdapter.generate`, not `ffmpeg.input`.
- Use `tmp_path` (pytest fixture) for all temporary file I/O — never a hardcoded path.
- Do not mock `state.json` — use `tmp_path` with a real file.
- Integration tests use real engines. Unit tests use mocks and fakes. Do not mix.

## MCP Manual Verification

When an automated integration test is not practical, paste the exact command output
into the completion evidence. Minimum acceptable evidence for MCP connector work:

```text
/.well-known/oauth-protected-resource/mcp -> 200
/.well-known/oauth-authorization-server -> 200
initialize -> 200
tools/list -> count 12
```

If Claude.ai UI still says `This connector has no tools available` but the SDK
returns tools:

- Check server log for `Processing request of type ListToolsRequest`.
- Re-add the custom integration to clear cached metadata.
- Simplify tool schemas before changing OAuth again.
- Keep `channel`, `scenario`, path-like parameters, and status values as strings unless there is a strong reason not to.

## Test ID System

Every test has a `SCN-P-NNN` ID in the docstring.

```python
def test_case_2_creates_subproject(tmp_path):
    """SCN-P-001: Project exists, sub-project missing — sub-project is created."""
    ...
```

Format: `SCN-P-` prefix (pipeline), three-digit number.
Track all IDs in `tests/scenarios/PIPELINE_MATRIX.md`.

## Scenario Matrix Entry Format

```markdown
| SCN-P-001 | project/manager | Case 2: sub-project created | unit | pass |
```

Columns: ID, module, description, test type (unit/integration), status (pass/fail/pending).

## Gate

Before calling any pipeline step complete, at least one of the following must be true:
- Unit tests pass for all modules touched.
- Integration test passes for the step's happy path.
- Dry-run evidence provided with explicit reason why full test was not possible.

For MCP protocol or Claude.ai connector changes, this general gate is not enough:
the SDK `initialize -> tools/list` check is mandatory unless the server cannot be
started in the current environment, and that blocker must be stated explicitly.
