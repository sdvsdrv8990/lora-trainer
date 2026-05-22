export interface SceneEvent {
  time: number;
  action:
    | "show"
    | "hide"
    | "change_state"
    | "trigger_preset"
    | "show_text"
    | "show_number";
  target?: string;
  component?: string;
  state?: Record<string, string>;
  value?: string | number;
  preset?: string;
  position?: { x: number; y: number };
  style?: string;
}

export interface SceneLayout {
  scene_id: number;
  chapter: string;
  audio_file: string;
  duration: number;
  fps: number;
  canvas: { width: number; height: number };
  events: SceneEvent[];
}

export interface ComponentState {
  target: string;
  component: string;
  state?: Record<string, string>;
  position?: { x: number; y: number };
  value?: string | number;
  preset?: string;
  preset_start_frame?: number;
  style?: string;
}

export interface SceneState {
  components: ComponentState[];
  activePresets: Map<string, { preset: string; startFrame: number }>;
}
