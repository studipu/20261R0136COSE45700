/**
 * Pre-computed metadata for each hair preset.
 * Colors extracted from GLB material baseColorFactor.
 * Geometry data from mesh analysis.
 */

import type { HSL } from './color-distance';
import { hexToHsl } from './color-distance';

export interface PresetMetadata {
  presetId: string;
  dominantColor: string; // hex
  hsl: HSL;
  vertexCount: number; // front hair
  meshCount: number;   // front hair
  backVertexCount: number;
  backMeshCount: number;
  /** Hairstyle keywords for Gemini-based matching */
  styleKeywords: string[];
  /** Hair length category */
  lengthCategory: string;
}

/**
 * Metadata for hair presets 01-05.
 * Colors are extracted from the GLB materials (MToon litFactor / baseColorFactor).
 * Geometry counts from mesh inspection.
 */
const RAW_METADATA: Omit<PresetMetadata, 'hsl'>[] = [
  {
    presetId: 'hair-01',
    dominantColor: '#785947', // medium brown (sampled from rendered thumbnail)
    vertexCount: 115406,
    meshCount: 92,
    backVertexCount: 62353,
    backMeshCount: 92,
    styleKeywords: ['long_straight', 'straight'],
    lengthCategory: 'long',
  },
  {
    presetId: 'hair-02',
    dominantColor: '#735544', // medium brown (sampled from rendered thumbnail)
    vertexCount: 105320,
    meshCount: 79,
    backVertexCount: 51847,
    backMeshCount: 79,
    styleKeywords: ['short_bob', 'bob'],
    lengthCategory: 'short',
  },
  {
    presetId: 'hair-03',
    dominantColor: '#705242', // medium brown (sampled from rendered thumbnail)
    vertexCount: 110524,
    meshCount: 62,
    backVertexCount: 57051,
    backMeshCount: 62,
    styleKeywords: ['ponytail'],
    lengthCategory: 'medium',
  },
  {
    presetId: 'hair-04',
    dominantColor: '#775846', // medium brown (sampled from rendered thumbnail)
    vertexCount: 105892,
    meshCount: 40,
    backVertexCount: 52419,
    backMeshCount: 40,
    styleKeywords: ['very_long_straight', 'long_straight', 'straight'],
    lengthCategory: 'very_long',
  },
  {
    presetId: 'hair-05',
    dominantColor: '#725443', // medium brown (sampled from rendered thumbnail)
    vertexCount: 98609,
    meshCount: 55,
    backVertexCount: 45136,
    backMeshCount: 55,
    styleKeywords: ['short_braid', 'braid'],
    lengthCategory: 'short',
  },
];

export const PRESET_METADATA: PresetMetadata[] = RAW_METADATA.map((raw) => ({
  ...raw,
  hsl: hexToHsl(raw.dominantColor),
}));

export function getPresetMetadataById(presetId: string): PresetMetadata | undefined {
  return PRESET_METADATA.find((m) => m.presetId === presetId);
}
