# Group 3 — Character Rig + Lipsync

## Status

| Component | Status | Location |
|---|---|---|
| Lipsync Python module | ✅ done | `src/audio/lipsync.py` |
| MCP tool: pipeline_generate_lipsync | ✅ done | `server.py` line 2331 |
| Stickman Remotion component | ❌ missing | `pipeline/remotion/src/components/Stickman.tsx` |
| SpeechBubble component | ❌ missing | `pipeline/remotion/src/components/SpeechBubble.tsx` |
| FloatingText component | ❌ missing | `pipeline/remotion/src/components/FloatingText.tsx` |
| Animation presets | ❌ missing | `pipeline/remotion/src/presets/` |
| SVG character parts | ❌ missing | `global_assets/characters/crowd/` |

## Layer Map (pipe-dev-guide)

```
Layer 0 — Entity: lipsync JSON (md/lipsync_scene_NNN.json)
Layer 1 — MCP tool: pipeline_generate_lipsync (done)
Layer 2 — Python module: src/audio/lipsync.py (done)
Layer 3 — TypeScript: Stickman.tsx reads lipsync JSON + applies mouth SVG (MISSING)
Layer 4 — Binary dep: rhubarb-lip-sync (install on local PC)
Layer 5 — Assets: global_assets/characters/crowd/ SVG parts (MISSING)
```

## Lipsync Python Layer (already done)

`src/audio/lipsync.py` responsibilities (one function):
- Find `rhubarb` binary in known locations
- Run: `rhubarb -f json <audio.mp3>`
- Map phoneme codes A–H/X to mouth shapes
- Write `md/lipsync_scene_NNN.json`

Output format:
```json
[
  {"start": 0.00, "end": 0.10, "value": "X", "mouth_shape": "neutral"},
  {"start": 0.10, "end": 0.22, "value": "A", "mouth_shape": "open_wide"},
  {"start": 0.22, "end": 0.35, "value": "B", "mouth_shape": "closed"},
  ...
]
```

Module boundary: `lipsync.py` only generates the JSON. Stickman.tsx reads it at render time.

## Rhubarb Installation (local PC)

```bash
# Download single binary — no runtime deps, MIT license
wget https://github.com/DanielSWolf/rhubarb-lip-sync/releases/download/v1.13.0/rhubarb-linux-x64.zip
unzip rhubarb-linux-x64.zip
sudo cp rhubarb /usr/local/bin/
chmod +x /usr/local/bin/rhubarb

# Verify
rhubarb --version
```

Verification of Python wrapper:
```bash
cd pipeline
venv/bin/python -c "
from pathlib import Path
from src.audio.lipsync import generate_lipsync, _find_rhubarb
print('rhubarb found at:', _find_rhubarb())
"
```

## SVG Character Structure to Create

```
global_assets/characters/crowd/
├── body/
│   ├── standing.svg
│   ├── pointing_right.svg
│   ├── pointing_left.svg
│   └── arms_raised.svg
├── eyes/
│   ├── neutral.svg
│   ├── happy.svg
│   ├── shocked.svg
│   ├── angry.svg
│   └── sad.svg
└── mouth/
    ├── neutral.svg     ← X (rest)
    ├── open.svg        ← C, D, G, H
    ├── open_wide.svg   ← A, E
    └── closed.svg      ← B, F
```

SVG design rules:
- Each file is ONE SVG part (no full character in a single file)
- All SVGs use `currentColor` for the character color — no hardcoded hex
- Stickman style: thin lines, simple geometry, 200×300px viewport
- Mouth SVGs: 60×40px viewport (composited on top of head)
- Color is applied via CSS `color` property on the wrapper `<div>`

## Stickman.tsx

```tsx
// pipeline/remotion/src/components/Stickman.tsx
import React from 'react';
import type { SceneEvent } from '../types';

interface LipCue {
  start: number;
  end: number;
  mouth_shape: 'neutral' | 'open' | 'open_wide' | 'closed';
}

interface StickmanProps {
  color: string;
  emotion: 'neutral' | 'happy' | 'sad' | 'shocked' | 'angry';
  pose: 'standing' | 'pointing_right' | 'pointing_left' | 'arms_raised';
  position: { x: number; y: number };
  scale?: number;
  lipCues?: LipCue[];        // loaded from lipsync JSON if character speaks
  currentTime?: number;      // seconds — used to pick correct mouth shape
}

export const Stickman: React.FC<StickmanProps> = ({
  color, emotion, pose, position, scale = 1, lipCues, currentTime = 0,
}) => {
  const assetsBase = process.env.GLOBAL_ASSETS_PATH ?? '/global_assets';
  const base = `${assetsBase}/characters/crowd`;

  // Pick current mouth shape from lip cues
  const currentCue = lipCues?.find(c => currentTime >= c.start && currentTime < c.end);
  const mouthShape = currentCue?.mouth_shape ?? 'neutral';

  return (
    <div style={{
      position: 'absolute',
      left: position.x,
      top: position.y,
      transform: `scale(${scale})`,
      color,                // CSS currentColor applied to SVGs
      width: 200,
      height: 300,
    }}>
      <img src={`${base}/body/${pose}.svg`} style={{ position: 'absolute', width: '100%' }} />
      <img src={`${base}/eyes/${emotion}.svg`} style={{ position: 'absolute', top: 60, left: 60 }} />
      <img src={`${base}/mouth/${mouthShape}.svg`} style={{ position: 'absolute', top: 140, left: 70 }} />
    </div>
  );
};
```

## How Lipsync Connects to Stickman in Scene Events

When a character should speak, the scene layout includes a lipsync reference:

```json
{
  "time": 1.2,
  "action": "show",
  "target": "worker_A",
  "component": "Stickman",
  "state": {
    "color": "#FFD700",
    "emotion": "neutral",
    "pose": "standing",
    "lipsync_file": "md/lipsync_scene_001.json"
  },
  "position": {"x": 400, "y": 200}
}
```

`Scene.tsx` loads the lipsync JSON and passes it to Stickman:

```tsx
// Scene.tsx — inside renderComponent()
if (event.component === 'Stickman' && event.state?.lipsync_file) {
  const lipCues = loadLipsyncData(event.state.lipsync_file);  // fs.readFileSync at render time
  return <Stickman {...props} lipCues={lipCues} currentTime={currentTime} />;
}
```

## Animation Presets

```typescript
// pipeline/remotion/src/presets/dramatic_popup.ts
import { spring, interpolate } from 'remotion';

export function dramaticPopup(frame: number, fps: number, startFrame: number) {
  const f = frame - startFrame;
  const progress = spring({ frame: f, fps, config: { damping: 8, stiffness: 200, mass: 0.8 } });
  return {
    scale: interpolate(progress, [0, 1], [0, 1]),
    opacity: interpolate(Math.min(f, 10), [0, 10], [0, 1]),
  };
}

// pipeline/remotion/src/presets/shake.ts
export function shake(frame: number, startFrame: number, intensity = 8) {
  const e = frame - startFrame;
  if (e < 0 || e > 15) return { x: 0, y: 0 };
  const decay = Math.max(0, 1 - e / 15);
  return {
    x: Math.sin(e * 1.5) * intensity * decay,
    y: Math.cos(e * 2.1) * intensity * 0.5 * decay,
  };
}

// pipeline/remotion/src/presets/slide_in.ts
import { interpolate, spring } from 'remotion';

export function slideIn(frame: number, fps: number, startFrame: number, from: 'left' | 'right' = 'left') {
  const f = frame - startFrame;
  const progress = spring({ frame: f, fps, config: { damping: 12, stiffness: 150 } });
  const x = interpolate(progress, [0, 1], [from === 'left' ? -300 : 300, 0]);
  const opacity = interpolate(progress, [0, 0.4], [0, 1]);
  return { x, opacity };
}
```

**Rule:** Use ONLY `spring()` and `interpolate()` from `remotion`. No external animation libraries.

## FloatingText.tsx

```tsx
// pipeline/remotion/src/components/FloatingText.tsx
import React from 'react';
import { useCurrentFrame, useVideoConfig, interpolate, spring } from 'remotion';

interface FloatingTextProps {
  text: string;
  style: 'gut_punch' | 'label' | 'caption';
  position: { x: number; y: number };
  startFrame: number;
}

const STYLES = {
  gut_punch: { fontSize: 72, fontWeight: 900, color: '#FF4444', textShadow: '3px 3px 0 #000' },
  label:     { fontSize: 32, fontWeight: 600, color: '#333', background: 'rgba(255,255,255,0.9)', padding: '8px 16px', borderRadius: 8 },
  caption:   { fontSize: 24, fontWeight: 400, color: '#555', background: 'rgba(255,255,255,0.7)', padding: '4px 10px', borderRadius: 4 },
};

export const FloatingText: React.FC<FloatingTextProps> = ({ text, style, position, startFrame }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const elapsed = frame - startFrame;
  const progress = spring({ frame: elapsed, fps, config: { damping: 10, stiffness: 180 } });
  const opacity = interpolate(Math.min(elapsed, 8), [0, 8], [0, 1]);

  return (
    <div style={{
      position: 'absolute',
      left: position.x,
      top: position.y,
      transform: `scale(${progress})`,
      opacity,
      ...STYLES[style],
    }}>
      {text}
    </div>
  );
};
```

## Phase 4 Checklist

- [ ] Create SVG character parts in `global_assets/characters/crowd/` (body × 4, eyes × 5, mouth × 4)
- [ ] Build `pipeline/remotion/src/components/Stickman.tsx`
- [ ] Build `pipeline/remotion/src/components/FloatingText.tsx`
- [ ] Build `pipeline/remotion/src/components/SpeechBubble.tsx`
- [ ] Build `pipeline/remotion/src/presets/dramatic_popup.ts`, `shake.ts`, `slide_in.ts`
- [ ] Install rhubarb on local PC and verify: `rhubarb --version`
- [ ] Test: `pipeline_generate_lipsync(channel, scenario, scene_id=1)` → `md/lipsync_scene_001.json` exists
- [ ] Test: render a scene with Stickman + lipsync events → mouth moves with audio
- [ ] TypeScript check: `npx tsc --noEmit` passes

## resolve-mcp Overlap Assessment for Group 3

resolve-mcp has Fusion tools (8 tools) that can technically do animation.
**We do NOT use them for character animation.**

Reasons:
- Fusion is for compositing finished video, not generating character animation from events
- Our character animation is generated at render time by Remotion, not post-processed in Resolve
- Fusion workflow requires manual node graph construction — cannot be described in our SceneEvent JSON
- Lipsync is applied at the Remotion level (mouth SVG swapping per frame) — Fusion cannot access our rhubarb JSON

**Verdict: Group 3 has zero overlap with resolve-mcp. Build it entirely ourselves.**
