/**
 * VRM hair feature extraction and preset matching.
 *
 * Detection strategy:
 * 1. Name-based: identify hair materials/meshes by keyword matching
 * 2. Structural: fall back to head-bone position heuristic
 *
 * Color extraction:
 * - Samples base color texture (if present) and multiplies with material color
 * - Prevents white-color misdetection when textures carry the actual color
 */

import type { VRM } from '@pixiv/three-vrm';
import * as THREE from 'three';
import { MToonMaterial } from '@pixiv/three-vrm-materials-mtoon';
import type { DetectedMaterial } from '@/lib/vrm/materials';
import type { HSL } from './color-distance';
import { hexToHsl, colorSimilarity } from './color-distance';
import { PRESET_METADATA } from './preset-metadata';

// ---- Types ----

export interface VRMHairFeatures {
  dominantColor: string; // hex
  hsl: HSL;
  totalVertexCount: number;
  meshCount: number;
}

export interface HairMatchResult {
  presetId: string;
  score: number;        // 0~1 combined score
  colorScore: number;   // 0~1
  geometryScore: number; // 0~1
}

export type MatchConfidence = 'high' | 'medium' | 'low';

export interface HairRecommendation {
  bestMatch: HairMatchResult;
  allResults: HairMatchResult[];
  confidence: MatchConfidence;
  extractedColor: string; // hex color extracted from VRM
}

// ---- Hair regex ----

const HAIR_REGEX = /hair|bangs|ponytail|braid|wig|strand|fringe|tress|locks|mane|髪/i;

// Materials that are clearly NOT hair
const NON_HAIR_MAT = /skin|face|body|eye|iris|pupil|mouth|teeth|tongue|cloth|shirt|pant|dress|shoe|arm|leg|hand|foot|torso|neck|cornea|sclera|eyebrow|eyelash|eyelid|nail|brow/i;

// ---- Texture Sampling ----

// Cache to avoid sampling the same texture multiple times
const _texColorCache = new Map<string, THREE.Color | null>();

/**
 * Get the base color texture from a material.
 * Handles both MToonMaterial (uniform-based) and standard materials.
 */
function getBaseTexture(mat: THREE.Material): THREE.Texture | null {
  // MToonMaterial: use getter (proxies to uniforms.map.value)
  if (mat instanceof MToonMaterial) {
    // Try getter first
    const tex = mat.map;
    if (tex) return tex;
    // Fallback: access uniform directly
    return mat.uniforms?.map?.value ?? null;
  }

  // Standard / PBR materials
  const std = mat as THREE.MeshStandardMaterial;
  return std.map ?? null;
}

/**
 * Sample average color from a material's base texture.
 * Downscales to 32x32, averages non-transparent pixels.
 * Results are cached by texture UUID.
 */
function sampleTextureColor(mat: THREE.Material): THREE.Color | null {
  const texture = getBaseTexture(mat);
  if (!texture) {
    console.log(`[HairMatch] No texture on material "${mat.name}"`);
    return null;
  }

  // Cache check
  if (_texColorCache.has(texture.uuid)) {
    return _texColorCache.get(texture.uuid) ?? null;
  }

  const image = texture.image;
  if (!image) {
    console.log(`[HairMatch] Texture "${texture.name || texture.uuid}" has no image data`);
    _texColorCache.set(texture.uuid, null);
    return null;
  }

  // Guard: need a drawable image source with width/height
  const w = (image as { width?: number }).width ?? 0;
  if (w === 0) {
    console.log(`[HairMatch] Texture image has zero width`);
    _texColorCache.set(texture.uuid, null);
    return null;
  }

  try {
    const canvas = document.createElement('canvas');
    const size = 32;
    canvas.width = size;
    canvas.height = size;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      _texColorCache.set(texture.uuid, null);
      return null;
    }

    ctx.drawImage(image as CanvasImageSource, 0, 0, size, size);
    const data = ctx.getImageData(0, 0, size, size).data;

    let r = 0, g = 0, b = 0, count = 0;
    for (let i = 0; i < data.length; i += 4) {
      if (data[i + 3] < 128) continue; // skip transparent pixels
      r += data[i];
      g += data[i + 1];
      b += data[i + 2];
      count++;
    }

    if (count === 0) {
      console.log(`[HairMatch] Texture "${mat.name}" has no opaque pixels`);
      _texColorCache.set(texture.uuid, null);
      return null;
    }

    const result = new THREE.Color(r / count / 255, g / count / 255, b / count / 255);
    console.log(`[HairMatch] Texture sampled "${mat.name}": #${result.getHexString()} (${count} opaque px)`);
    _texColorCache.set(texture.uuid, result.clone());
    return result;
  } catch (e) {
    console.warn('[HairMatch] Texture sampling failed for', mat.name, e);
    _texColorCache.set(texture.uuid, null);
    return null;
  }
}

/**
 * Get the effective visible color of a material.
 * Combines base color with texture color (base * texture, as the GPU shader does).
 */
function getEffectiveColor(mat: THREE.Material): THREE.Color {
  let baseColor: THREE.Color;
  if (mat instanceof MToonMaterial) {
    baseColor = mat.color?.clone() ?? new THREE.Color(0xffffff);
  } else {
    const std = mat as THREE.MeshStandardMaterial;
    baseColor = std.color?.clone() ?? new THREE.Color(0xffffff);
  }

  const texColor = sampleTextureColor(mat);
  if (texColor) {
    // GPU multiplies base color by texture color
    const effective = new THREE.Color(
      baseColor.r * texColor.r,
      baseColor.g * texColor.g,
      baseColor.b * texColor.b
    );
    console.log(`[HairMatch] Effective color for "${mat.name}": base=#${baseColor.getHexString()} * tex=#${texColor.getHexString()} = #${effective.getHexString()}`);
    return effective;
  }

  console.log(`[HairMatch] Using base color only for "${mat.name}": #${baseColor.getHexString()}`);
  return baseColor;
}

// ---- Structural Detection ----

/**
 * Detect potential hair materials by vertex position relative to the head bone.
 * Used as fallback when name-based detection finds nothing.
 *
 * Strategy: sample vertices of each mesh; if >40% are above the head bone
 * and the material name doesn't match known non-hair patterns, classify as hair.
 */
function detectHairByPosition(vrm: VRM): Set<string> {
  const hairMatNames = new Set<string>();

  const headBone =
    vrm.humanoid?.getNormalizedBoneNode('head') ??
    vrm.humanoid?.getRawBoneNode('head');
  if (!headBone) {
    console.log('[HairMatch] No head bone found for structural detection');
    return hairMatNames;
  }

  vrm.scene.updateWorldMatrix(true, true);

  const headPos = new THREE.Vector3();
  headBone.getWorldPosition(headPos);
  console.log(`[HairMatch] Head bone world Y: ${headPos.y.toFixed(3)}`);

  const tempVec = new THREE.Vector3();

  vrm.scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (!mesh.isMesh || !mesh.geometry) return;

    const posAttr = mesh.geometry.attributes?.position;
    if (!posAttr || posAttr.count === 0) return;

    // Sample up to 200 vertices evenly across the mesh
    const sampleCount = Math.min(posAttr.count, 200);
    const step = Math.max(1, Math.floor(posAttr.count / sampleCount));
    let aboveHead = 0;
    let total = 0;

    for (let i = 0; i < posAttr.count; i += step) {
      tempVec.fromBufferAttribute(posAttr, i);
      mesh.localToWorld(tempVec);
      if (tempVec.y > headPos.y) {
        aboveHead++;
      }
      total++;
    }

    const ratio = total > 0 ? aboveHead / total : 0;

    // >40% above head → likely hair
    if (ratio > 0.4) {
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const mat of mats) {
        if (mat?.name && !NON_HAIR_MAT.test(mat.name)) {
          hairMatNames.add(mat.name);
          console.log(
            `[HairMatch] Structural hit: "${mat.name}" on "${mesh.name}" ` +
            `(${(ratio * 100).toFixed(0)}% above head, ${posAttr.count} verts)`
          );
        }
      }
    }
  });

  if (hairMatNames.size === 0) {
    console.log('[HairMatch] Structural detection found no hair candidates');
  }

  return hairMatNames;
}

// ---- Feature Extraction ----

/**
 * Extract hair features from a loaded VRM model.
 *
 * 1. Try name-based hair material detection
 * 2. Fall back to structural (head-bone) detection
 * 3. Extract color via texture sampling + base color
 */
export function extractVRMHairFeatures(
  vrm: VRM,
  detectedMaterials: DetectedMaterial[]
): VRMHairFeatures | null {
  // Clear texture cache for each new VRM analysis
  _texColorCache.clear();

  console.log(`[HairMatch] Analyzing VRM with ${detectedMaterials.length} materials`);
  console.log(`[HairMatch] Categories:`, detectedMaterials.map((m) => `${m.slotName}→${m.category}`).join(', '));

  let hairMaterials = detectedMaterials.filter((m) => m.category === 'hair');

  // Structural fallback when name-based detection fails
  let structuralNames: Set<string> | null = null;
  if (hairMaterials.length === 0) {
    console.log('[HairMatch] No hair materials by name, trying structural detection...');
    structuralNames = detectHairByPosition(vrm);
    if (structuralNames.size > 0) {
      hairMaterials = detectedMaterials.filter((m) => structuralNames!.has(m.slotName));
      console.log(`[HairMatch] Structural detection yielded ${hairMaterials.length} materials`);
    }
  }

  if (hairMaterials.length === 0) {
    console.log('[HairMatch] No hair materials detected (name or structural)');
    return null;
  }

  // Build the set of material names to look for in the scene
  const hairMatNames = new Set(hairMaterials.map((m) => m.slotName));
  if (structuralNames) {
    for (const name of structuralNames) hairMatNames.add(name);
  }

  // Collect hair mesh data with texture-aware color extraction
  const hairMeshData: { color: THREE.Color; vertexCount: number }[] = [];
  let totalVertexCount = 0;
  let meshCount = 0;

  vrm.scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (!mesh.isMesh) return;

    const meshName = mesh.name || '';
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];

    for (const mat of mats) {
      if (!mat) continue;

      const isHairMat =
        hairMatNames.has(mat.name) ||
        HAIR_REGEX.test(mat.name) ||
        HAIR_REGEX.test(meshName);
      if (!isHairMat) continue;

      const geometry = mesh.geometry;
      if (!geometry) continue;

      const vCount = geometry.attributes?.position?.count ?? 0;
      if (vCount === 0) continue;

      // Texture-aware color extraction
      const color = getEffectiveColor(mat);

      hairMeshData.push({ color, vertexCount: vCount });
      totalVertexCount += vCount;
      meshCount++;
    }
  });

  if (meshCount === 0 || totalVertexCount === 0) {
    // Fallback: use detected material color
    const fallbackColor = hairMaterials[0].color;
    console.log('[HairMatch] No hair meshes in scene, using detected material color:', fallbackColor);
    return {
      dominantColor: fallbackColor,
      hsl: hexToHsl(fallbackColor),
      totalVertexCount: 0,
      meshCount: 0,
    };
  }

  // Vertex-weighted average color
  const avgR = hairMeshData.reduce((sum, d) => sum + d.color.r * d.vertexCount, 0) / totalVertexCount;
  const avgG = hairMeshData.reduce((sum, d) => sum + d.color.g * d.vertexCount, 0) / totalVertexCount;
  const avgB = hairMeshData.reduce((sum, d) => sum + d.color.b * d.vertexCount, 0) / totalVertexCount;

  const avgColor = new THREE.Color(avgR, avgG, avgB);
  const hex = '#' + avgColor.getHexString();

  console.log(`[HairMatch] Extracted hair color: ${hex} (${meshCount} meshes, ${totalVertexCount} vertices)`);

  return {
    dominantColor: hex,
    hsl: hexToHsl(hex),
    totalVertexCount,
    meshCount,
  };
}

// ---- Matching ----

/**
 * Gaussian decay for geometry similarity.
 * Returns 1 when values are equal, decays toward 0 as difference grows.
 */
function gaussianSimilarity(a: number, b: number, sigma: number): number {
  const diff = a - b;
  return Math.exp(-(diff * diff) / (2 * sigma * sigma));
}

/**
 * Match extracted VRM hair features against all presets.
 *
 * Scoring strategy:
 * - Color (50%): HSL perceptual similarity
 * - Mesh count (50%): strand count as proxy for style complexity
 *   Tight sigma ensures different strand counts produce different results.
 *   (Preset bounding boxes are identical, so mesh count is the only
 *    geometric discriminator between the 5 presets.)
 */
export function matchHairPresets(features: VRMHairFeatures): HairRecommendation {
  const COLOR_WEIGHT = 0.50;
  const GEOMETRY_WEIGHT = 0.50;

  // Tight sigma for mesh count — preset range is 40-92, so sigma=15
  // ensures meaningful discrimination across that range.
  const MESH_SIGMA = 15;

  const results: HairMatchResult[] = PRESET_METADATA.map((preset) => {
    // Color similarity
    const cScore = colorSimilarity(features.hsl, preset.hsl);

    // Geometry similarity: mesh count (strand count) is the primary discriminator.
    // Vertex count is ignored — different VRM sources have wildly different
    // vertex densities per strand, making absolute count comparison meaningless.
    let gScore = 0.5; // neutral default when no geometry data
    if (features.meshCount > 0) {
      gScore = gaussianSimilarity(features.meshCount, preset.meshCount, MESH_SIGMA);
    }

    const score = COLOR_WEIGHT * cScore + GEOMETRY_WEIGHT * gScore;

    return {
      presetId: preset.presetId,
      score,
      colorScore: cScore,
      geometryScore: gScore,
    };
  });

  // Sort descending by score
  results.sort((a, b) => b.score - a.score);

  const bestScore = results[0].score;
  let confidence: MatchConfidence;
  if (bestScore > 0.7) confidence = 'high';
  else if (bestScore > 0.4) confidence = 'medium';
  else confidence = 'low';

  console.log(`[HairMatch] Best match: ${results[0].presetId} (score: ${bestScore.toFixed(3)}, confidence: ${confidence})`);
  console.log('[HairMatch] All scores:', results.map((r) => `${r.presetId}=${r.score.toFixed(3)}`).join(', '));

  return {
    bestMatch: results[0],
    allResults: results,
    confidence,
    extractedColor: features.dominantColor,
  };
}
