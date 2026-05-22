import React from "react";
import { SpeechBubble } from "./SpeechBubble";

// Pre-computed CSS filters for the 7 locked channel colors.
// Generated via https://angel-rs.github.io/css-color-filter-generator/
const COLOR_FILTERS: Record<string, string> = {
  "#FFD700": "brightness(0) saturate(100%) invert(89%) sepia(45%) saturate(800%) hue-rotate(5deg)",
  "#2196F3": "brightness(0) saturate(100%) invert(42%) sepia(85%) saturate(600%) hue-rotate(185deg)",
  "#4CAF50": "brightness(0) saturate(100%) invert(52%) sepia(50%) saturate(500%) hue-rotate(85deg)",
  "#FF4444": "brightness(0) saturate(100%) invert(27%) sepia(90%) saturate(700%) hue-rotate(335deg)",
  "#9C27B0": "brightness(0) saturate(100%) invert(20%) sepia(80%) saturate(600%) hue-rotate(270deg)",
  "#FF9800": "brightness(0) saturate(100%) invert(65%) sepia(80%) saturate(700%) hue-rotate(5deg)",
  "#9E9E9E": "brightness(0) saturate(100%) invert(65%)",
};

export interface StickmanProps {
  color: string;
  emotion: "neutral" | "happy" | "sad" | "shocked" | "angry";
  pose: "standing" | "pointing_right" | "pointing_left" | "sitting" | "arms_raised";
  text?: string;
  position: { x: number; y: number };
  scale?: number;
  flip_x?: boolean;
}

const ASSETS_BASE = process.env.GLOBAL_ASSETS_PATH ?? "/home/admin/projects/lora-trainer/pipeline/global_assets";

export const Stickman: React.FC<StickmanProps> = ({
  color,
  emotion,
  pose,
  text,
  position,
  scale = 1,
  flip_x = false,
}) => {
  const filter = COLOR_FILTERS[color] ?? "";
  const base = `${ASSETS_BASE}/characters/crowd`;

  return (
    <div
      style={{
        position: "absolute",
        left: position.x,
        top: position.y,
        transform: `scale(${scale}) scaleX(${flip_x ? -1 : 1})`,
        transformOrigin: "top left",
        width: 200,
        height: 400,
      }}
    >
      <img
        src={`${base}/body/${pose}.svg`}
        style={{ position: "absolute", width: 200, height: 400, filter }}
      />
      <img
        src={`${base}/eyes/${emotion}.svg`}
        style={{ position: "absolute", width: 200, height: 400 }}
      />
      {text && (
        <div style={{ position: "absolute", top: -80, left: 0 }}>
          <SpeechBubble text={text} style={flip_x ? "oval_left" : "oval_right"} />
        </div>
      )}
    </div>
  );
};
