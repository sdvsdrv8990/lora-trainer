# Remotion Rendering Layer

> **Status: TypeScript layer not yet built.** Python bridge is complete.
> This file will be updated when `pipeline/remotion/` is built and verified locally.

## What It Is

[Remotion](https://remotion.dev) is a React + TypeScript framework that renders
video programmatically — each frame is a React component, audio sync is declarative,
and the output is a standard MP4. It replaces the Pillow/FFmpeg frame-stacking approach
with a fully event-driven, component-based renderer.

## Why It's in This Project

Remotion handles the part of the pipeline that produces per-scene MP4 files with:

- **Character animation** — Stickman components read lipsync JSON per frame
- **Text overlays** — FloatingText, SpeechBubble with spring animations
- **Synchronized audio** — `<Audio src=…/>` inside React, frame-perfect
- **Animated numbers** — counter effects (views, subscribers, etc.)

The Python/Pillow compositor (v1) can only produce static frames assembled by FFmpeg.
Remotion (v2) produces a native MP4 with motion, audio, and animation from a single render call.

## Where It Fits in the Workflow

Entry point B, Step 6 (v2 path):

```
pipeline_submit_scene_layouts → [scene_layout.json]
        ↓
pipeline_render_scene(scene_id, wait=true)
        ↓
src/remotion/renderer.py       ← calls ts-node render.ts via subprocess
        ↓
pipeline/remotion/render.ts    ← NOT YET BUILT
        ↓
renders/scenes/scene_NNN.mp4
```

The Python bridge (`renderer.py`, `render_jobs.py`) is complete and tested.
Only the TypeScript layer is missing.

## TypeScript Layer — What Needs Building

```
pipeline/remotion/
├── package.json
├── tsconfig.json
├── render.ts                  ← CLI entry: reads scene JSON, calls renderMedia()
└── src/
    ├── Root.tsx               ← registers <Composition id="Scene">
    ├── Scene.tsx              ← event-driven renderer
    ├── types.ts               ← SceneEvent and SceneLayout interfaces
    ├── components/
    │   ├── Stickman.tsx       ← character with lipsync mouth swap
    │   ├── FloatingText.tsx   ← animated text overlay
    │   ├── AnimatedNumber.tsx ← counter animation
    │   └── SpeechBubble.tsx   ← character speech bubble
    └── presets/
        ├── dramatic_popup.ts  ← spring() scale-in
        ├── shake.ts           ← camera shake
        └── slide_in.ts        ← slide from left/right
```

npm dependencies (under 300MB total):
```bash
npm install remotion @remotion/core @remotion/renderer ts-node typescript
```

Do NOT install: `@remotion/player`, `@remotion/lambda`, `framer-motion`, `gsap`.

## Scene Layout Schema

The TypeScript layer reads a `SceneLayout` JSON written by `pipeline_submit_scene_layouts`:

```typescript
interface SceneLayout {
  scene_id: number;
  chapter: string;
  audio_file: string;     // absolute path to .mp3
  duration: number;       // total seconds
  fps: number;            // default 30
  canvas: { width: number; height: number };
  events: SceneEvent[];
}

interface SceneEvent {
  time: number;           // seconds from scene start
  action: 'show' | 'hide' | 'change_state' | 'trigger_preset' | 'show_text' | 'show_number';
  target?: string;        // component id
  component?: string;     // Stickman | FloatingText | AnimatedNumber | SpeechBubble
  state?: Record<string, string>;
  position?: { x: number; y: number };
  preset?: string;
}
```

## Lipsync Integration

When a Stickman character speaks:
1. `pipeline_generate_lipsync(channel, scenario, scene_id)` → `md/lipsync_scene_NNN.json`
2. Scene layout event includes `"lipsync_file": "md/lipsync_scene_001.json"` in state
3. `Scene.tsx` reads the file, passes `lipCues[]` to `<Stickman/>`
4. `Stickman.tsx` picks correct mouth SVG per frame using `currentTime`

Mouth SVG assets: `pipeline/global_assets/characters/crowd/mouth/` (4 shapes: neutral, open, open_wide, closed)

## Implementation Checklist

> For the local developer. Update this file and remove the "Status: planned" line
> when the TypeScript layer is built and `pipeline_render_scene` produces a real MP4.

- [ ] `cd pipeline/remotion && npm install`
- [ ] Build all TypeScript files listed above
- [ ] `npx tsc --noEmit` passes
- [ ] `npx ts-node render.ts /tmp/test_scene.json /tmp/test.mp4` produces a valid MP4
- [ ] `pipeline_render_scene` MCP tool calls through end-to-end
- [ ] Create SVG character parts in `global_assets/characters/crowd/`
- [ ] Update this file: change status to "implemented"

## README Link

Add this row to the README documentation table once the TS layer is shipped:

```markdown
| [Remotion rendering](docs/pipeline/reference/REMOTION_RENDERING.md) | React/TS scene renderer, components, lipsync |
```
