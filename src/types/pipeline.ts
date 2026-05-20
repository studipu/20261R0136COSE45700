/**
 * TypeScript types matching the face-feature pipeline JSON output.
 *
 * Python pipeline: face-feature/pipeline/pipeline.py  run_pipeline()
 * Avatar keys:     face-feature/pipeline/avatar_keys.py  compute_avatar_keys()
 */

/** 26-dimensional feature vector from FaceFeatureVector dataclass */
export interface FeatureVector {
  // Global proportions (9)
  eye_aspect_ratio: number;
  eye_distance_ratio: number;
  face_width_height_ratio: number;
  nose_height_ratio: number;
  nose_width_ratio: number;
  mouth_width_ratio: number;
  jaw_width_ratio: number;
  forehead_ratio: number;
  chin_ratio: number;
  // Eye shape detail (10)
  eye_width_ratio: number;
  eye_height_ratio: number;
  eye_rot: number;
  eye_front_height: number;
  eye_front_flat: number;
  eye_tail_height: number;
  eye_top_lid_flat: number;
  eye_lower_lid_flat: number;
  eye_top_lid_down: number;
  eye_lower_lid_up: number;
  // Brow (4)
  brow_dist_ratio: number;
  brow_height_ratio: number;
  brow_rot: number;
  brow_width_ratio: number;
  // Mouth detail (2)
  mouth_corner_ratio: number;
  mouth_height_ratio: number;
  // Nose detail (1)
  nose_under_nose_ratio: number;
}

/** 29 avatar morph-target keys (maps 1:1 to VRM shape keys) */
export type AvatarParameters = Record<string, number>;

/** 9 UI slider initial values from template_selector */
export interface SliderInit {
  eye_size: number;
  eye_distance: number;
  face_round: number;
  nose_height: number;
  nose_width: number;
  mouth_width: number;
  jaw_width: number;
  forehead_height: number;
  chin_length: number;
}

export type TemplateName = 'cute' | 'slim' | 'mature';

/** Full pipeline response (run_pipeline output) */
export interface PipelineResult {
  status: 'ok' | 'failed_stage4';
  glb_path?: string;
  renders?: Record<string, string>;
  feature_vector: FeatureVector | null;
  feature_source: 'original' | 'front_render' | null;
  feature_debug?: Record<string, unknown>;
  avatar_parameters: AvatarParameters | null;
  parameter_debug?: Record<string, unknown>;
  template: TemplateName | null;
  confidence: number | null;
  all_scores: Record<string, number> | null;
  slider_init: SliderInit | null;
  error?: string;
}
