/**
 * VRM 파일에서 헤어를 머티리얼 기준으로 분리 추출하는 스크립트
 * SpringBone 물리 데이터도 함께 추출하여 GLB에 주입
 *
 * 출력:
 *   - N00_000_Hair_00_HAIR.glb      (앞머리/전체 헤어 스트랜드 + SpringBone)
 *   - N00_000_00_HairBack_00_HAIR.glb (뒷머리 + SpringBone)
 *
 * Usage: node scripts/extract-hair.mjs [input.vrm] [output-dir]
 */

import { NodeIO } from '@gltf-transform/core';
import * as fs from 'fs';
import * as path from 'path';

const inputPath = process.argv[2] || 'public/models/4.vrm';
const outputDir = process.argv[3] || path.join(path.dirname(inputPath), 'hair');

// ---------------------------------------------------------------------------
// GLB binary helpers
// ---------------------------------------------------------------------------

/** Read the JSON chunk from a GLB buffer (raw parse, preserves VRM extensions) */
function readGlbJson(glbBuffer) {
  const buf = Buffer.from(glbBuffer);
  // GLB header: magic(4) + version(4) + length(4) = 12 bytes
  // Chunk 0 header: chunkLength(4) + chunkType(4) = 8 bytes
  const jsonLen = buf.readUInt32LE(12);
  const jsonStr = buf.slice(20, 20 + jsonLen).toString('utf8').replace(/\0+$/, '');
  return JSON.parse(jsonStr);
}

/**
 * Replace the JSON chunk in a GLB buffer with new JSON data.
 * Preserves the binary chunk as-is.
 */
function replaceGlbJson(glbBuffer, newJson) {
  const buf = Buffer.from(glbBuffer);

  // Read original chunk layout
  const origJsonLen = buf.readUInt32LE(12);
  const binChunkStart = 20 + origJsonLen;

  // Encode new JSON, pad to 4-byte alignment with spaces (GLB spec)
  let jsonStr = JSON.stringify(newJson);
  while (jsonStr.length % 4 !== 0) jsonStr += ' ';
  const jsonBuf = Buffer.from(jsonStr, 'utf8');

  // Binary chunk (everything after the JSON chunk)
  const binChunk = buf.slice(binChunkStart);

  // New total length = 12 (header) + 8 (json chunk header) + jsonBuf.length + binChunk.length
  const totalLen = 12 + 8 + jsonBuf.length + binChunk.length;

  const out = Buffer.alloc(totalLen);
  // GLB header
  out.writeUInt32LE(0x46546C67, 0); // magic "glTF"
  out.writeUInt32LE(2, 4);           // version
  out.writeUInt32LE(totalLen, 8);    // total length
  // JSON chunk header
  out.writeUInt32LE(jsonBuf.length, 12); // chunk length
  out.writeUInt32LE(0x4E4F534A, 16);    // chunk type "JSON"
  // JSON data
  jsonBuf.copy(out, 20);
  // Binary chunk (header + data, copied as-is)
  binChunk.copy(out, 20 + jsonBuf.length);

  return out;
}

// ---------------------------------------------------------------------------
// SpringBone filtering
// ---------------------------------------------------------------------------

/** Build a name→index map for GLTF nodes */
function buildNodeNameMap(gltfJson) {
  const map = new Map();
  if (gltfJson.nodes) {
    gltfJson.nodes.forEach((node, idx) => {
      if (node.name) map.set(node.name, idx);
    });
  }
  return map;
}

/** Check if a node name (or its descendants) is hair-related */
function isHairRelated(name) {
  return /hair/i.test(name);
}

/**
 * Filter VRM 1.0 SpringBone data (VRMC_springBone extension).
 * Returns filtered extension object or null if nothing matches.
 */
function filterSpringBoneV1(springBoneExt, gltfJson) {
  const nodeNames = gltfJson.nodes?.map((n) => n.name || '') || [];
  const origColliders = springBoneExt.colliders || [];
  const origColliderGroups = springBoneExt.colliderGroups || [];
  const origSprings = springBoneExt.springs || [];

  // Filter springs: keep if any joint node is hair-related
  const keptSprings = [];
  const usedColliderGroupIndices = new Set();

  for (const spring of origSprings) {
    const joints = spring.joints || [];
    const hasHairJoint = joints.some((j) => {
      const nodeName = nodeNames[j.node] || '';
      return isHairRelated(nodeName);
    });
    // Also check spring name/comment
    const nameMatch = spring.name ? isHairRelated(spring.name) : false;

    if (hasHairJoint || nameMatch) {
      keptSprings.push(spring);
      // Track collider group references
      if (spring.colliderGroups) {
        for (const idx of spring.colliderGroups) {
          usedColliderGroupIndices.add(idx);
        }
      }
    }
  }

  if (keptSprings.length === 0) return null;

  // Remap collider groups: keep only referenced ones
  const oldToNewCG = new Map();
  const keptColliderGroups = [];
  const usedColliderIndices = new Set();

  for (const oldIdx of [...usedColliderGroupIndices].sort((a, b) => a - b)) {
    const cg = origColliderGroups[oldIdx];
    if (!cg) continue;
    oldToNewCG.set(oldIdx, keptColliderGroups.length);
    keptColliderGroups.push(cg);
    if (cg.colliders) {
      for (const ci of cg.colliders) usedColliderIndices.add(ci);
    }
  }

  // Remap colliders: keep only referenced ones
  const oldToNewCollider = new Map();
  const keptColliders = [];
  for (const oldIdx of [...usedColliderIndices].sort((a, b) => a - b)) {
    const c = origColliders[oldIdx];
    if (!c) continue;
    oldToNewCollider.set(oldIdx, keptColliders.length);
    keptColliders.push(c);
  }

  // Update indices in collider groups
  for (const cg of keptColliderGroups) {
    if (cg.colliders) {
      cg.colliders = cg.colliders
        .filter((ci) => oldToNewCollider.has(ci))
        .map((ci) => oldToNewCollider.get(ci));
    }
  }

  // Update colliderGroup indices in springs
  for (const spring of keptSprings) {
    if (spring.colliderGroups) {
      spring.colliderGroups = spring.colliderGroups
        .filter((idx) => oldToNewCG.has(idx))
        .map((idx) => oldToNewCG.get(idx));
    }
  }

  return {
    ...(springBoneExt.specVersion ? { specVersion: springBoneExt.specVersion } : {}),
    colliders: keptColliders.length > 0 ? keptColliders : undefined,
    colliderGroups: keptColliderGroups.length > 0 ? keptColliderGroups : undefined,
    springs: keptSprings,
  };
}

/**
 * Filter VRM 0.x SpringBone data (VRM.secondaryAnimation).
 * Returns filtered secondaryAnimation object or null if nothing matches.
 */
function filterSpringBoneV0(secondaryAnim, gltfJson) {
  const nodeNames = gltfJson.nodes?.map((n) => n.name || '') || [];
  const origBoneGroups = secondaryAnim.boneGroups || [];
  const origColliderGroups = secondaryAnim.colliderGroups || [];

  // Filter bone groups: keep if comment or bone names are hair-related
  const keptBoneGroups = [];
  const usedColliderGroupIndices = new Set();

  for (const bg of origBoneGroups) {
    const commentMatch = bg.comment ? isHairRelated(bg.comment) : false;
    const boneMatch = (bg.bones || []).some((boneIdx) => {
      return isHairRelated(nodeNames[boneIdx] || '');
    });

    if (commentMatch || boneMatch) {
      keptBoneGroups.push(bg);
      if (bg.colliderGroups) {
        for (const idx of bg.colliderGroups) {
          usedColliderGroupIndices.add(idx);
        }
      }
    }
  }

  if (keptBoneGroups.length === 0) return null;

  // Remap collider groups
  const oldToNewCG = new Map();
  const keptColliderGroups = [];

  for (const oldIdx of [...usedColliderGroupIndices].sort((a, b) => a - b)) {
    const cg = origColliderGroups[oldIdx];
    if (!cg) continue;
    oldToNewCG.set(oldIdx, keptColliderGroups.length);
    keptColliderGroups.push(cg);
  }

  // Update colliderGroup indices in bone groups
  for (const bg of keptBoneGroups) {
    if (bg.colliderGroups) {
      bg.colliderGroups = bg.colliderGroups
        .filter((idx) => oldToNewCG.has(idx))
        .map((idx) => oldToNewCG.get(idx));
    }
  }

  return {
    boneGroups: keptBoneGroups,
    colliderGroups: keptColliderGroups.length > 0 ? keptColliderGroups : undefined,
  };
}

/**
 * Extract and filter SpringBone data from the original VRM JSON.
 * Returns { extensionKey, extensionData } or null.
 */
function extractSpringBone(origJson) {
  // VRM 1.0
  if (origJson.extensions?.VRMC_springBone) {
    const filtered = filterSpringBoneV1(origJson.extensions.VRMC_springBone, origJson);
    if (filtered) {
      console.log(
        `   🦴 SpringBone (v1): ${filtered.springs.length} spring(s), ` +
        `${(filtered.colliders || []).length} collider(s)`
      );
      return { extensionKey: 'VRMC_springBone', extensionData: filtered };
    }
  }

  // VRM 0.x
  if (origJson.extensions?.VRM?.secondaryAnimation) {
    const filtered = filterSpringBoneV0(origJson.extensions.VRM.secondaryAnimation, origJson);
    if (filtered) {
      console.log(
        `   🦴 SpringBone (v0): ${filtered.boneGroups.length} bone group(s), ` +
        `${(filtered.colliderGroups || []).length} collider group(s)`
      );
      return { extensionKey: 'VRM_secondaryAnimation', extensionData: filtered, isV0: true, origVrmExt: origJson.extensions.VRM };
    }
  }

  return null;
}

/**
 * Inject SpringBone extension into a GLB's JSON chunk.
 */
function injectSpringBone(glbBuffer, springBoneResult) {
  if (!springBoneResult) return glbBuffer;

  const json = readGlbJson(glbBuffer);

  if (!json.extensions) json.extensions = {};
  if (!json.extensionsUsed) json.extensionsUsed = [];

  if (springBoneResult.isV0) {
    // VRM 0.x: store under extensions.VRM.secondaryAnimation
    if (!json.extensions.VRM) json.extensions.VRM = {};
    json.extensions.VRM.secondaryAnimation = springBoneResult.extensionData;
    if (!json.extensionsUsed.includes('VRM')) {
      json.extensionsUsed.push('VRM');
    }
  } else {
    // VRM 1.0: store under extensions.VRMC_springBone
    json.extensions[springBoneResult.extensionKey] = springBoneResult.extensionData;
    if (!json.extensionsUsed.includes(springBoneResult.extensionKey)) {
      json.extensionsUsed.push(springBoneResult.extensionKey);
    }
  }

  return replaceGlbJson(glbBuffer, json);
}

// ---------------------------------------------------------------------------
// Main extraction
// ---------------------------------------------------------------------------

async function extractHairByMaterial() {
  const io = new NodeIO();
  const glbBuffer = fs.readFileSync(inputPath);
  const document = await io.readBinary(new Uint8Array(glbBuffer));
  const root = document.getRoot();

  // 헤어 관련 머티리얼 탐색
  const allMaterials = root.listMaterials();
  const hairMaterials = allMaterials.filter((m) =>
    m.getName().toUpperCase().includes('HAIR'),
  );

  if (hairMaterials.length === 0) {
    console.error('❌ 헤어 관련 머티리얼을 찾을 수 없습니다.');
    process.exit(1);
  }

  console.log(`📂 Input: ${inputPath}`);
  console.log(`📁 Output: ${outputDir}`);
  console.log(`\n🎨 헤어 머티리얼 ${hairMaterials.length}개 발견:`);
  hairMaterials.forEach((m) => console.log(`   - ${m.getName()}`));

  // Extract SpringBone from original VRM
  const origJson = readGlbJson(glbBuffer);
  const springBoneResult = extractSpringBone(origJson);
  if (!springBoneResult) {
    console.log('   ⚠️  SpringBone 데이터 없음 (물리 시뮬레이션 미포함)');
  }

  fs.mkdirSync(outputDir, { recursive: true });

  // 각 헤어 머티리얼별로 GLB 추출
  for (const hairMat of hairMaterials) {
    const matName = hairMat.getName();
    await extractByMaterial(io, glbBuffer, outputDir, matName, springBoneResult);
  }

  console.log('\n✅ 추출 완료!');
}

/**
 * 특정 머티리얼을 사용하는 primitive만 포함하는 GLB를 생성
 */
async function extractByMaterial(io, glbBuffer, outputDir, targetMatName, springBoneResult) {
  const doc = await io.readBinary(new Uint8Array(glbBuffer));
  const root = doc.getRoot();
  const allNodes = root.listNodes();

  let keptPrimitives = 0;

  for (const node of allNodes) {
    const mesh = node.getMesh();
    if (!mesh) continue;

    const primitives = mesh.listPrimitives();
    const matchingPrims = [];
    const nonMatchingPrims = [];

    for (const prim of primitives) {
      const mat = prim.getMaterial();
      if (mat && mat.getName() === targetMatName) {
        matchingPrims.push(prim);
      } else {
        nonMatchingPrims.push(prim);
      }
    }

    if (matchingPrims.length === 0) {
      // 이 메시에는 대상 머티리얼이 없음 → 메시 제거
      node.setMesh(null);
    } else {
      // 대상이 아닌 primitive 제거
      for (const prim of nonMatchingPrims) {
        mesh.removePrimitive(prim);
      }
      keptPrimitives += matchingPrims.length;
    }
  }

  if (keptPrimitives === 0) {
    console.log(`   ⚠️  ${targetMatName}: primitive 없음, 스킵`);
    return;
  }

  const outputPath = path.join(outputDir, `${targetMatName}.glb`);
  let outputBuffer = await io.writeBinary(doc);

  // Inject SpringBone extension into the output GLB
  outputBuffer = injectSpringBone(Buffer.from(outputBuffer), springBoneResult);

  fs.writeFileSync(outputPath, Buffer.from(outputBuffer));

  const sizeKB = (fs.statSync(outputPath).size / 1024).toFixed(1);
  console.log(
    `\n   ✅ ${targetMatName}.glb (${sizeKB} KB, ${keptPrimitives} primitives)`,
  );
}

extractHairByMaterial().catch((err) => {
  console.error('Error:', err);
  process.exit(1);
});
