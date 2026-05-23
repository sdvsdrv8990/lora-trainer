# Group 1 — Remotion Rendering Layer

## Status

| Component | Status | Location |
|---|---|---|
| Python bridge: job queue | ✅ done | `src/remotion/render_jobs.py` |
| Python bridge: subprocess call | ✅ done | `src/remotion/renderer.py` |
| MCP tools: 8 tools | ✅ done | `server.py` lines 2081–2280 |
| TypeScript: render.ts | ❌ missing | `pipeline/remotion/render.ts` |
| TypeScript: Scene.tsx | ❌ missing | `pipeline/remotion/src/Scene.tsx` |
| TypeScript: components | ❌ missing | `pipeline/remotion/src/components/` |
| TypeScript: presets | ❌ missing | `pipeline/remotion/src/presets/` |
| Pipeline preview (PNG) | ⚠️ stub | `renderer.py:36` — raises NotImplementedError |

## Layer Map (pipe-dev-guide)

```
Layer 0 — Entity: SceneLayout + SceneEvent (TypeScript types in render.ts)
Layer 1 — MCP tools: 8 tools in server.py (done)
Layer 2 — Python module: src/remotion/ (done)
Layer 3 — TypeScript: pipeline/remotion/ (MISSING — must build)
Layer 4 — External dep: @remotion/renderer (npm install)
```

## What the Python Bridge Does

`render_jobs.py`:
- Manages a `threading.Event` cancel token per workspace
- Runs `_render_worker()` in background thread (or synchronously if `wait=true`)
- Writes `md/remotion_status.json` after every scene attempt
- Calls `renderer.render_scene(scene_dict, output_path)` per scene

`renderer.py`:
- Calls `ts-node render.ts <scene_json> <output.mp4>` via `subprocess.run`
- `ts-node` binary expected at `pipeline/remotion/node_modules/.bin/ts-node`
- Timeout: 300 seconds per scene

## What Still Needs to Be Built

### Directory structure to create

```
pipeline/remotion/
├── package.json
├── tsconfig.json
├── render.ts                    ← CLI entry: reads scene JSON, calls renderMedia()
└── src/
    ├── Root.tsx                 ← registers <Composition id="Scene">
    ├── Scene.tsx                ← event-driven renderer, reads SceneLayout
    ├── types.ts                 ← SceneEvent and SceneLayout interfaces
    ├── components/
    │   ├── Stickman.tsx         ← character (see 04_CHARACTER_LIPSYNC.md)
    │   ├── FloatingText.tsx     ← text bubble appearing on screen
    │   ├── AnimatedNumber.tsx   ← counter animation (e.g. "1,543,000 views")
    │   └── SpeechBubble.tsx     ← speech bubble for characters
    └── presets/
        ├── dramatic_popup.ts    ← spring() scale-in
        ├── slide_in.ts          ← slide from left/right
        └── shake.ts             ← camera shake effect
```

### npm install (minimal — under 300MB)

```bash
cd pipeline/remotion
npm init -y
npm install remotion @remotion/core @remotion/renderer ts-node typescript
```

**Do NOT install:** @remotion/player, @remotion/lambda, framer-motion, gsap, anime.js

### render.ts (CLI entry point)

```typescript
// pipeline/remotion/render.ts
import { renderMedia, selectComposition } from '@remotion/renderer';
import * as fs from 'fs';
import * as path from 'path';

async function main() {
  const [,, sceneJsonPath, outputPath] = process.argv;
  if (!sceneJsonPath || !outputPath) {
    console.error('Usage: ts-node render.ts <scene.json> <output.mp4>');
    process.exit(1);
  }

  const layout = JSON.parse(fs.readFileSync(sceneJsonPath, 'utf8'));

  const composition = await selectComposition({
    serveUrl: path.join(__dirname, './'),
    id: 'Scene',
    inputProps: { layout },
  });

  await renderMedia({
    composition,
    serveUrl: path.join(__dirname, './'),
    codec: 'h264',
    outputLocation: outputPath,
    inputProps: { layout },
    concurrency: 1,
    timeoutInMilliseconds: 240000,
    verbose: false,
  });

  console.log('render complete:', outputPath);
}

main().catch(err => {
  console.error(err);
  process.exit(1);
});
```

### types.ts (entity schema — must match Python scene_layout.json)

```typescript
// pipeline/remotion/src/types.ts
export interface SceneEvent {
  time: number;           // seconds from scene start
  action: 'show' | 'hide' | 'change_state' | 'trigger_preset' | 'show_text' | 'show_number';
  target?: string;        // component id
  component?: string;     // which component type to show
  state?: Record<string, string>;
  value?: string | number;
  preset?: string;
  position?: { x: number; y: number };
  style?: string;
}

export interface SceneLayout {
  scene_id: number;
  chapter: string;
  audio_file: string;     // absolute path to .mp3
  duration: number;       // total seconds
  fps: number;            // default 30
  canvas: { width: number; height: number };
  events: SceneEvent[];
}
```

### Scene.tsx (core renderer)

```tsx
// pipeline/remotion/src/Scene.tsx
import React from 'react';
import { useCurrentFrame, useVideoConfig, Audio, AbsoluteFill } from 'remotion';
import type { SceneLayout, SceneEvent } from './types';

function buildStateAtTime(events: SceneEvent[], time: number) {
  const visible = new Map<string, SceneEvent & { id: string }>();
  for (const ev of events) {
    if (ev.time > time) break;
    if (ev.action === 'show' && ev.target) visible.set(ev.target, { ...ev, id: ev.target });
    if (ev.action === 'hide' && ev.target) visible.delete(ev.target);
    if (ev.action === 'change_state' && ev.target) {
      const cur = visible.get(ev.target);
      if (cur) visible.set(ev.target, { ...cur, state: { ...cur.state, ...ev.state } });
    }
  }
  return [...visible.values()];
}

export const Scene: React.FC<{ layout: SceneLayout }> = ({ layout }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;
  const components = buildStateAtTime(layout.events, currentTime);

  return (
    <AbsoluteFill style={{ background: 'white' }}>
      <Audio src={layout.audio_file} />
      {components.map(c => <RenderComponent key={c.id} event={c} frame={frame} fps={fps} />)}
    </AbsoluteFill>
  );
};
```

### Root.tsx (composition registration)

```tsx
// pipeline/remotion/src/Root.tsx
import React from 'react';
import { Composition } from 'remotion';
import { Scene } from './Scene';
import type { SceneLayout } from './types';

const defaultLayout: SceneLayout = {
  scene_id: 0, chapter: '', audio_file: '', duration: 5,
  fps: 30, canvas: { width: 1920, height: 1080 }, events: [],
};

export const Root: React.FC = () => (
  <Composition
    id="Scene"
    component={Scene}
    durationInFrames={150}
    fps={30}
    width={1920}
    height={1080}
    defaultProps={{ layout: defaultLayout }}
    calculateMetadata={({ props }) => ({
      durationInFrames: Math.ceil(props.layout.duration * props.layout.fps),
      fps: props.layout.fps,
      width: props.layout.canvas.width,
      height: props.layout.canvas.height,
    })}
  />
);
```

## MCP Tools — Current Implementation

All 8 tools are in `server.py`. Each delegates to `remotion_jobs` or `layout_store`.

| Tool | Delegates to | Status |
|---|---|---|
| `pipeline_render_scene` | `remotion_jobs.start(ws, [scene], wait)` | ✅ implemented |
| `pipeline_render_all_scenes` | `remotion_jobs.start(ws, scenes, wait)` | ✅ implemented |
| `pipeline_get_remotion_status` | `remotion_jobs.read_status(ws)` | ✅ implemented |
| `pipeline_stop_render` | `remotion_jobs.stop(ws)` | ✅ implemented |
| `pipeline_update_scene_event` | `layout_store.update_scene_event(...)` | ✅ implemented |
| `pipeline_move_event` | `layout_store.move_event(...)` | ✅ implemented |
| `pipeline_preview_scene_event` | renderer.py stub | ⚠️ returns path only, no actual render |
| `pipeline_list_scene_events` | `layout_store.load_layout_raw(ws)` | ✅ implemented |

## pipeline_preview_scene_event — Fix Plan

Current behavior: returns `preview_path` string but does NOT render the PNG.

Fix options:
1. **Option A**: Call Remotion `renderStill` CLI: `npx remotion still Scene --frame=<N> output.png`
2. **Option B**: Call FFmpeg to extract a frame from an already-rendered scene mp4

Option B is simpler and has zero extra deps:
```python
def render_scene_preview(scene_id, time, workspace):
    mp4 = workspace / f"renders/scenes/scene_{scene_id:03d}.mp4"
    if not mp4.exists():
        raise FileNotFoundError("Scene not rendered yet. Run pipeline_render_scene first.")
    out = workspace / f"renders/previews/scene_{scene_id:03d}_t{time:.1f}.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-ss", str(time), "-i", str(mp4),
        "-frames:v", "1", str(out), "-y"
    ], check=True, capture_output=True)
    return out
```

**Implement in Phase 2 (local PC).**

## Phase 1 Verification (local PC)

```bash
cd pipeline/remotion
npm install
npx tsc --noEmit      # TypeScript check — must pass

# Minimal test: render 1 scene with fake layout
echo '{
  "scene_id": 1, "chapter": "Test", "audio_file": "/dev/null",
  "duration": 3, "fps": 30, "canvas": {"width": 1280, "height": 720},
  "events": []
}' > /tmp/test_scene.json
npx ts-node render.ts /tmp/test_scene.json /tmp/test_output.mp4

# Verify output
ffprobe /tmp/test_output.mp4 | grep Duration
```

**Expected:** mp4 file, ~3 seconds, 1280×720.
