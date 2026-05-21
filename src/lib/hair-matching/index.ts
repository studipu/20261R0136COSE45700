/**
 * Hair matching module - barrel export.
 */

export { hexToHsl, colorSimilarity } from './color-distance';
export type { HSL } from './color-distance';

export { PRESET_METADATA, getPresetMetadataById } from './preset-metadata';
export type { PresetMetadata } from './preset-metadata';

export { extractVRMHairFeatures, matchHairPresets, matchHairPresetsFromColor } from './matcher';
export type { VRMHairFeatures, HairMatchResult, HairRecommendation, MatchConfidence } from './matcher';

export { extractHairColorFromImage } from './image-analyzer';
export type { ImageHairColorResult } from './image-analyzer';

import type { VRM } from '@pixiv/three-vrm';
import type { DetectedMaterial } from '@/lib/vrm/materials';
import type { HairRecommendation } from './matcher';
import { extractVRMHairFeatures, matchHairPresets, matchHairPresetsFromColor } from './matcher';
import { extractHairColorFromImage } from './image-analyzer';

/**
 * Convenience function: extract features from VRM and match in one call.
 */
export function recommendHairPreset(
  vrm: VRM,
  materials: DetectedMaterial[]
): HairRecommendation | null {
  const features = extractVRMHairFeatures(vrm, materials);
  if (!features) return null;
  return matchHairPresets(features);
}

/**
 * Convenience function: extract hair color from an image and match in one call.
 */
export async function recommendHairPresetFromImage(
  file: File,
): Promise<HairRecommendation | null> {
  const result = await extractHairColorFromImage(file);
  if (!result) return null;
  return matchHairPresetsFromColor(result.dominantColor, result.hsl);
}
