import React from "react";
import { useCurrentFrame, useVideoConfig, Audio, AbsoluteFill } from "remotion";
import { ComponentState, SceneEvent, SceneLayout, SceneState } from "./types";
import { Background } from "./components/Background";
import { Stickman, StickmanProps } from "./components/Stickman";
import { FloatingText } from "./components/FloatingText";
import { AnimatedNumber } from "./components/AnimatedNumber";
import { SpeechBubble } from "./components/SpeechBubble";
import { dramaticPopup } from "./presets/dramatic_popup";
import { shake } from "./presets/shake";
import { slideIn } from "./presets/slide_in";

function buildStateAtTime(events: SceneEvent[], frame: number, fps: number): SceneState {
  const visible = new Map<string, ComponentState>();
  const activePresets = new Map<string, { preset: string; startFrame: number }>();

  for (const event of events) {
    const eventFrame = Math.floor(event.time * fps);
    if (eventFrame > frame) break;

    if (event.action === "show" && event.target && event.component) {
      visible.set(event.target, {
        target: event.target,
        component: event.component,
        state: event.state,
        position: event.position,
        value: event.value,
        style: event.style,
      });
    }
    if (event.action === "hide" && event.target) {
      visible.delete(event.target);
      activePresets.delete(event.target);
    }
    if (event.action === "change_state" && event.target) {
      const existing = visible.get(event.target);
      if (existing) {
        visible.set(event.target, { ...existing, state: { ...existing.state, ...event.state } });
      }
    }
    if (event.action === "trigger_preset" && event.target && event.preset) {
      activePresets.set(event.target, { preset: event.preset, startFrame: eventFrame });
    }
    if (event.action === "show_text" && event.target) {
      visible.set(event.target, {
        target: event.target,
        component: "floating_text",
        state: event.state,
        position: event.position,
        value: event.value,
        style: event.style,
        preset_start_frame: eventFrame,
      });
    }
    if (event.action === "show_number" && event.target) {
      visible.set(event.target, {
        target: event.target,
        component: "animated_number",
        position: event.position,
        value: event.value,
        preset_start_frame: eventFrame,
      });
    }
  }

  return { components: [...visible.values()], activePresets };
}

function applyPreset(
  presetName: string,
  frame: number,
  fps: number,
  startFrame: number
): React.CSSProperties {
  if (presetName === "dramatic_popup") {
    const { scale, opacity } = dramaticPopup(frame, fps, startFrame);
    return { transform: `scale(${scale})`, opacity };
  }
  if (presetName === "shake") {
    const { x, y } = shake(frame, startFrame);
    return { transform: `translate(${x}px, ${y}px)` };
  }
  if (presetName === "slide_in") {
    const { x, y, opacity } = slideIn(frame, fps, startFrame);
    return { transform: `translate(${x}px, ${y}px)`, opacity };
  }
  return {};
}

function renderComponent(
  cs: ComponentState,
  frame: number,
  fps: number,
  activePresets: Map<string, { preset: string; startFrame: number }>,
  canvas: { width: number; height: number }
): React.ReactNode {
  const presetInfo = activePresets.get(cs.target);
  const presetStyle = presetInfo
    ? applyPreset(presetInfo.preset, frame, fps, presetInfo.startFrame)
    : {};

  const pos = cs.position ?? { x: 0, y: 0 };
  const wrapStyle: React.CSSProperties = { position: "absolute", ...presetStyle };

  if (cs.component === "background") {
    return (
      <Background
        key={cs.target}
        color={(cs.state?.color) ?? "#FFFFFF"}
        imagePath={cs.state?.image_path}
        width={canvas.width}
        height={canvas.height}
      />
    );
  }
  if (cs.component === "stickman") {
    const p: Partial<StickmanProps> = {
      color: cs.state?.color ?? "#9E9E9E",
      emotion: (cs.state?.emotion ?? "neutral") as StickmanProps["emotion"],
      pose: (cs.state?.pose ?? "standing") as StickmanProps["pose"],
      text: cs.state?.text,
      position: pos,
      scale: cs.state?.scale ? parseFloat(cs.state.scale) : 1,
      flip_x: cs.state?.flip_x === "true",
    };
    return (
      <div key={cs.target} style={wrapStyle}>
        <Stickman {...(p as StickmanProps)} position={{ x: 0, y: 0 }} />
      </div>
    );
  }
  if (cs.component === "floating_text") {
    return (
      <FloatingText
        key={cs.target}
        text={String(cs.value ?? "")}
        style={(cs.style ?? "label") as "gut_punch" | "label" | "caption"}
        startFrame={cs.preset_start_frame ?? 0}
        position={pos}
      />
    );
  }
  if (cs.component === "animated_number") {
    return (
      <AnimatedNumber
        key={cs.target}
        value={Number(cs.value ?? 0)}
        prefix={cs.state?.prefix}
        suffix={cs.state?.suffix}
        startFrame={cs.preset_start_frame ?? 0}
        position={pos}
      />
    );
  }
  if (cs.component === "speech_bubble") {
    return (
      <div key={cs.target} style={{ position: "absolute", left: pos.x, top: pos.y, ...wrapStyle }}>
        <SpeechBubble
          text={String(cs.value ?? cs.state?.text ?? "")}
          style={(cs.state?.template ?? "oval_right") as "oval_right" | "oval_left" | "thought"}
        />
      </div>
    );
  }
  return null;
}

interface SceneProps {
  layout: SceneLayout;
}

export const Scene: React.FC<SceneProps> = ({ layout }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const sceneState = buildStateAtTime(layout.events, frame, fps);

  return (
    <AbsoluteFill style={{ background: "#FFFFFF" }}>
      <Audio src={layout.audio_file} />
      {sceneState.components.map((c) =>
        renderComponent(c, frame, fps, sceneState.activePresets, layout.canvas)
      )}
    </AbsoluteFill>
  );
};
