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
}

/**
 * Metadata for hair presets 01-05.
 * Colors are extracted from the GLB materials (MToon litFactor / baseColorFactor).
 * Geometry counts from mesh inspection.
 */
const RAW_METADATA: Omit<PresetMetadata, 'hsl'>[] = [
  {
    presetId: 'hair-01',
    dominantColor: '#2C222B', // dark brown/black
    vertexCount: 115406,
    meshCount: 92,
    backVertexCount: 62353,
    backMeshCount: 92,
  },
  {
    presetId: 'hair-02',
    dominantColor: '#71635A', // medium brown
    vertexCount: 105320,
    meshCount: 79,
    backVertexCount: 51847,
    backMeshCount: 79,
  },
  {
    presetId: 'hair-03',
    dominantColor: '#8D4A43', // auburn/reddish brown
    vertexCount: 110524,
    meshCount: 62,
    backVertexCount: 57051,
    backMeshCount: 62,
  },
  {
    presetId: 'hair-04',
    dominantColor: '#91672C', // golden brown
    vertexCount: 105892,
    meshCount: 40,
    backVertexCount: 52419,
    backMeshCount: 40,
  },
  {
    presetId: 'hair-05',
    dominantColor: '#090806', // black
    vertexCount: 98609,
    meshCount: 55,
    backVertexCount: 45136,
    backMeshCount: 55,
  },
];

export const PRESET_METADATA: PresetMetadata[] = RAW_METADATA.map((raw) => ({
  ...raw,
  hsl: hexToHsl(raw.dominantColor),
}));

export function getPresetMetadataById(presetId: string): PresetMetadata | undefined {
  return PRESET_METADATA.find((m) => m.presetId === presetId);
}
