import { interpolate, spring } from "remotion";

export function slideIn(
  frame: number,
  fps: number,
  startFrame: number,
  direction: "left" | "right" | "up" | "down" = "left",
  distance = 200
): { x: number; y: number; opacity: number } {
  const progress = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 12, stiffness: 150, mass: 0.6 },
  });
  const offset = interpolate(progress, [0, 1], [distance, 0]);
  const opacity = interpolate(progress, [0, 0.4], [0, 1], { extrapolateRight: "clamp" });
  return {
    x: direction === "left" ? -offset : direction === "right" ? offset : 0,
    y: direction === "up" ? -offset : direction === "down" ? offset : 0,
    opacity,
  };
}
