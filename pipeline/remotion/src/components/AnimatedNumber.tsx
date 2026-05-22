import React from "react";
import { useCurrentFrame, useVideoConfig } from "remotion";
import { interpolate, spring } from "remotion";

interface AnimatedNumberProps {
  value: number;
  prefix?: string;
  suffix?: string;
  startFrame: number;
  position: { x: number; y: number };
  decimals?: number;
}

export const AnimatedNumber: React.FC<AnimatedNumberProps> = ({
  value,
  prefix = "",
  suffix = "",
  startFrame,
  position,
  decimals = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 14, stiffness: 120, mass: 0.7 },
  });

  const displayed = interpolate(progress, [0, 1], [0, value]);

  return (
    <div
      style={{
        position: "absolute",
        left: position.x,
        top: position.y,
        fontSize: 72,
        fontWeight: "900",
        fontFamily: "Arial, sans-serif",
        color: "#111111",
      }}
    >
      {prefix}{displayed.toFixed(decimals)}{suffix}
    </div>
  );
};
