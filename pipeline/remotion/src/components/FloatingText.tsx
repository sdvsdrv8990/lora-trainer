import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { interpolate } from "remotion";

interface FloatingTextProps {
  text: string;
  style?: "gut_punch" | "label" | "caption";
  startFrame: number;
  position: { x: number; y: number };
}

const STYLE_MAP = {
  gut_punch: { fontSize: 64, fontWeight: "900", color: "#FF2222", textShadow: "3px 3px 0 #000" },
  label:     { fontSize: 36, fontWeight: "bold", color: "#111111", textShadow: "none" },
  caption:   { fontSize: 28, fontWeight: "normal", color: "#333333", textShadow: "none" },
};

export const FloatingText: React.FC<FloatingTextProps> = ({
  text,
  style = "label",
  startFrame,
  position,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const elapsed = frame - startFrame;
  const opacity = interpolate(elapsed, [0, fps * 0.3], [0, 1], {
    extrapolateRight: "clamp",
    extrapolateLeft: "clamp",
  });

  const s = STYLE_MAP[style];

  return (
    <div
      style={{
        position: "absolute",
        left: position.x,
        top: position.y,
        opacity,
        fontFamily: "Arial, sans-serif",
        ...s,
      }}
    >
      {text}
    </div>
  );
};
