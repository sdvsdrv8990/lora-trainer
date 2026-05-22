import { interpolate, spring } from "remotion";

export function dramaticPopup(
  frame: number,
  fps: number,
  startFrame: number
): { scale: number; opacity: number } {
  const progress = spring({
    frame: frame - startFrame,
    fps,
    config: { damping: 8, stiffness: 200, mass: 0.8 },
  });
  return {
    scale: interpolate(progress, [0, 1], [0, 1]),
    opacity: interpolate(progress, [0, 0.3], [0, 1], { extrapolateRight: "clamp" }),
  };
}
