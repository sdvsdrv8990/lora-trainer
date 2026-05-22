import React from "react";
import { Composition } from "remotion";
import { Scene } from "./Scene";
import { SceneLayout } from "./types";

const DEFAULT_LAYOUT: SceneLayout = {
  scene_id: 1,
  chapter: "Preview",
  audio_file: "",
  duration: 5,
  fps: 30,
  canvas: { width: 1920, height: 1080 },
  events: [],
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Scene"
      component={Scene}
      durationInFrames={DEFAULT_LAYOUT.fps * DEFAULT_LAYOUT.duration}
      fps={DEFAULT_LAYOUT.fps}
      width={DEFAULT_LAYOUT.canvas.width}
      height={DEFAULT_LAYOUT.canvas.height}
      defaultProps={{ layout: DEFAULT_LAYOUT }}
      calculateMetadata={async ({ props }: { props: { layout: SceneLayout } }) => {
        const layout = props.layout as SceneLayout;
        return {
          durationInFrames: Math.max(1, Math.ceil(layout.duration * layout.fps)),
          fps: layout.fps,
          width: layout.canvas.width,
          height: layout.canvas.height,
        };
      }}
    />
  );
};
