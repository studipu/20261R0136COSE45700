/**
 * Inspect a VRM file's mesh names, material names, and texture info
 * to debug hair detection issues.
 */
import * as fs from 'fs';

const filePath = process.argv[2] || 'public/models/5.vrm';
const buf = fs.readFileSync(filePath);

// Parse GLB header
const magic = buf.readUInt32LE(0);
const version = buf.readUInt32LE(4);
const totalLength = buf.readUInt32LE(8);

console.log(`=== GLB Header ===`);
console.log(`Magic: 0x${magic.toString(16)}, Version: ${version}, Size: ${(totalLength / 1024 / 1024).toFixed(1)}MB`);

// Parse JSON chunk
const jsonLength = buf.readUInt32LE(12);
const jsonStr = buf.subarray(20, 20 + jsonLength).toString('utf8');
const gltf = JSON.parse(jsonStr);

// VRM extension
const vrmExt = gltf.extensions?.VRM || gltf.extensions?.VRMC_vrm;
console.log(`\nVRM version: ${vrmExt ? 'VRM 0.x' : ''}`);
if (gltf.extensions?.VRMC_vrm) console.log('VRM version: 1.0');

// Nodes
console.log(`\n=== Nodes (${gltf.nodes?.length || 0}) ===`);
for (const [i, node] of (gltf.nodes || []).entries()) {
  if (node.mesh !== undefined || node.skin !== undefined) {
    console.log(`  Node[${i}] "${node.name || '?'}" mesh=${node.mesh ?? '-'} skin=${node.skin ?? '-'}`);
  }
}

// Meshes and primitives
console.log(`\n=== Meshes (${gltf.meshes?.length || 0}) ===`);
for (const [i, mesh] of (gltf.meshes || []).entries()) {
  const prims = mesh.primitives || [];
  let totalVerts = 0;
  const matIndices = [];
  for (const prim of prims) {
    if (prim.attributes?.POSITION !== undefined) {
      const acc = gltf.accessors[prim.attributes.POSITION];
      totalVerts += acc.count;
    }
    if (prim.material !== undefined) matIndices.push(prim.material);
  }
  const matNames = matIndices.map(mi => gltf.materials?.[mi]?.name || `mat_${mi}`);
  console.log(`  Mesh[${i}] "${mesh.name || '?'}" prims=${prims.length} verts=${totalVerts} materials=[${matNames.join(', ')}]`);
}

// Materials
console.log(`\n=== Materials (${gltf.materials?.length || 0}) ===`);
for (const [i, mat] of (gltf.materials || []).entries()) {
  const pbr = mat.pbrMetallicRoughness || {};
  const baseColor = pbr.baseColorFactor || [1, 1, 1, 1];
  const baseTexIdx = pbr.baseColorTexture?.index;

  // MToon extension
  const mtoon = mat.extensions?.VRM_materials_mtoon || mat.extensions?.VRMC_materials_mtoon;

  const colorHex = '#' + baseColor.slice(0, 3).map(c => Math.round(c * 255).toString(16).padStart(2, '0')).join('');

  let texInfo = baseTexIdx !== undefined ? `tex[${baseTexIdx}]` : 'no-tex';
  if (mtoon) {
    // MToon may have its own texture references
    const litTex = mtoon.mainTex?.index ?? mtoon.shadeMultiplyTexture?.index;
    if (litTex !== undefined) texInfo += ` mtoon-lit-tex[${litTex}]`;
  }

  console.log(`  Mat[${i}] "${mat.name || '?'}" color=${colorHex} ${texInfo} ${mtoon ? '[MToon]' : ''}`);
}

// Textures
console.log(`\n=== Textures (${gltf.textures?.length || 0}) ===`);
for (const [i, tex] of (gltf.textures || []).entries()) {
  const img = gltf.images?.[tex.source];
  const name = img?.name || img?.uri || `image_${tex.source}`;
  const mimeType = img?.mimeType || '?';
  let sizeInfo = '';
  if (img?.bufferView !== undefined) {
    const bv = gltf.bufferViews[img.bufferView];
    sizeInfo = `${(bv.byteLength / 1024).toFixed(0)}KB`;
  }
  console.log(`  Tex[${i}] source=${tex.source} "${name}" ${mimeType} ${sizeInfo}`);
}

// VRM meta / humanoid bones
if (vrmExt) {
  console.log(`\n=== VRM Meta ===`);
  console.log(`  Title: ${vrmExt.meta?.title || '?'}`);
  console.log(`  Author: ${vrmExt.meta?.author || '?'}`);

  if (vrmExt.humanoid?.humanBones) {
    console.log(`\n=== Humanoid Bones ===`);
    const bones = vrmExt.humanoid.humanBones;
    if (Array.isArray(bones)) {
      // VRM 0.x: array of { bone, node }
      for (const bone of bones) {
        const nodeName = gltf.nodes?.[bone.node]?.name || `node_${bone.node}`;
        if (['head', 'neck', 'hips', 'spine'].includes(bone.bone)) {
          console.log(`  ${bone.bone} → node[${bone.node}] "${nodeName}"`);
        }
      }
    } else {
      // VRM 1.0: object { head: { node: N }, ... }
      for (const [boneName, boneData] of Object.entries(bones)) {
        const nodeIdx = boneData?.node;
        const nodeName = gltf.nodes?.[nodeIdx]?.name || `node_${nodeIdx}`;
        if (['head', 'neck', 'hips', 'spine'].includes(boneName)) {
          console.log(`  ${boneName} → node[${nodeIdx}] "${nodeName}"`);
        }
      }
    }
  }
}

// Check for hair-related keywords in ALL names
console.log(`\n=== Hair Keyword Search ===`);
const hairRegex = /hair|bangs|ponytail|braid|wig|strand|fringe|tress|locks|mane|髪/i;
const nonHairRegex = /skin|face|body|eye|iris|pupil|mouth|teeth|tongue|cloth|shirt|pant|dress|shoe|arm|leg|hand|foot|torso|neck|cornea|sclera/i;

console.log('Materials with hair keywords:');
for (const [i, mat] of (gltf.materials || []).entries()) {
  if (hairRegex.test(mat.name || '')) {
    console.log(`  Mat[${i}] "${mat.name}"`);
  }
}

console.log('Meshes with hair keywords:');
for (const [i, mesh] of (gltf.meshes || []).entries()) {
  if (hairRegex.test(mesh.name || '')) {
    console.log(`  Mesh[${i}] "${mesh.name}"`);
  }
}

console.log('Nodes with hair keywords:');
for (const [i, node] of (gltf.nodes || []).entries()) {
  if (hairRegex.test(node.name || '')) {
    console.log(`  Node[${i}] "${node.name}"`);
  }
}

// Show ALL material and mesh names for manual inspection
console.log(`\n=== All Material Names ===`);
for (const [i, mat] of (gltf.materials || []).entries()) {
  const pbr = mat.pbrMetallicRoughness || {};
  const baseColor = pbr.baseColorFactor || [1, 1, 1, 1];
  const colorHex = '#' + baseColor.slice(0, 3).map(c => Math.round(c * 255).toString(16).padStart(2, '0')).join('');
  console.log(`  [${i}] "${mat.name || '?'}" → ${colorHex}`);
}

console.log(`\n=== All Mesh Names ===`);
for (const [i, mesh] of (gltf.meshes || []).entries()) {
  console.log(`  [${i}] "${mesh.name || '?'}"`);
}

// Extract actual hair texture colors from binary data
console.log(`\n=== Hair Texture Color Sampling ===`);
const binOffset = 20 + jsonLength;
const binChunkLength = buf.readUInt32LE(binOffset);
const binData = buf.subarray(binOffset + 8, binOffset + 8 + binChunkLength);

// Find hair material texture indices
const hairMatIndices = [];
for (const [i, mat] of (gltf.materials || []).entries()) {
  if (hairRegex.test(mat.name || '')) {
    const pbr = mat.pbrMetallicRoughness || {};
    const texIdx = pbr.baseColorTexture?.index;
    if (texIdx !== undefined) {
      hairMatIndices.push({ matIdx: i, matName: mat.name, texIdx });
    }
  }
}

for (const { matName, texIdx } of hairMatIndices) {
  const tex = gltf.textures[texIdx];
  const img = gltf.images[tex.source];
  if (img?.bufferView === undefined) {
    console.log(`  "${matName}" → external image, skip`);
    continue;
  }
  const bv = gltf.bufferViews[img.bufferView];
  const imgBytes = binData.subarray(bv.byteOffset || 0, (bv.byteOffset || 0) + bv.byteLength);

  // Decode PNG header to get dimensions
  // PNG signature: 137 80 78 71 13 10 26 10
  if (imgBytes[0] === 137 && imgBytes[1] === 80) {
    const w = imgBytes.readUInt32BE(16);
    const h = imgBytes.readUInt32BE(20);
    console.log(`  "${matName}" → tex[${texIdx}] PNG ${w}x${h} (${(bv.byteLength/1024).toFixed(0)}KB)`);
    console.log(`    Base color in GLTF: #ffffff (all white → color comes from texture)`);
    console.log(`    → Texture sampling required for actual color`);
  } else {
    console.log(`  "${matName}" → tex[${texIdx}] non-PNG format`);
  }
}

console.log(`\n=== DIAGNOSIS ===`);
const allWhite = (gltf.materials || []).every(m => {
  const c = m.pbrMetallicRoughness?.baseColorFactor || [1,1,1,1];
  return c[0] > 0.99 && c[1] > 0.99 && c[2] > 0.99;
});
if (allWhite) {
  console.log(`  ALL ${gltf.materials.length} materials have baseColorFactor=#ffffff`);
  console.log(`  → Hair color is ENTIRELY in textures, not in material base color`);
  console.log(`  → Without texture sampling, extracted color = #ffffff (wrong)`);
  console.log(`  → The texture sampling fix in matcher.ts should resolve this`);
}
