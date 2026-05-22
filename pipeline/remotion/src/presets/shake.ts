export function shake(
  frame: number,
  startFrame: number,
  intensity = 8
): { x: number; y: number } {
  const elapsed = frame - startFrame;
  if (elapsed < 0 || elapsed > 15) return { x: 0, y: 0 };
  const decay = Math.max(0, 1 - elapsed / 15);
  return {
    x: Math.sin(elapsed * 1.5) * intensity * decay,
    y: Math.cos(elapsed * 2.1) * intensity * 0.5 * decay,
  };
}
