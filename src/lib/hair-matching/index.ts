/**
 * Hair matching module - barrel export.
 */

export { hexToHsl, colorSimilarity } from './color-distance';
export type { HSL } from './color-distance';

export { PRESET_METADATA, getPresetMetadataById } from './preset-metadata';
export type { PresetMetadata } from './preset-metadata';

export { extractVRMHairFeatures, matchHairPresets } from './matcher';
export type { VRMHairFeatures, HairMatchResult, HairRecommendation, MatchConfidence } from './matcher';

import type { VRM } from '@pixiv/three-vrm';
import type { DetectedMaterial } from '@/lib/vrm/materials';
import type { HairRecommendation } from './matcher';
import { extractVRMHairFeatures, matchHairPresets } from './matcher';

/**
 * Convenience function: extract features and match in one call.
 */
export function recommendHairPreset(
  vrm: VRM,
  materials: DetectedMaterial[]
): HairRecommendation | null {
  const features = extractVRMHairFeatures(vrm, materials);
  if (!features) return null;
  return matchHairPresets(features);
}
