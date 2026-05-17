/**
 * VRM 파일에서 헤어를 머티리얼 기준으로 분리 추출하는 스크립트
 *
 * 출력:
 *   - N00_000_Hair_00_HAIR.glb      (앞머리/전체 헤어 스트랜드)
 *   - N00_000_00_HairBack_00_HAIR.glb (뒷머리)
 *
 * Usage: node scripts/extract-hair.mjs [input.vrm] [output-dir]
 */

import { NodeIO } from '@gltf-transform/core';
import * as fs from 'fs';
import * as path from 'path';

const inputPath = process.argv[2] || 'public/models/4.vrm';
const outputDir = process.argv[3] || path.join(path.dirname(inputPath), 'hair');

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

  fs.mkdirSync(outputDir, { recursive: true });

  // 각 헤어 머티리얼별로 GLB 추출
  for (const hairMat of hairMaterials) {
    const matName = hairMat.getName();
    await extractByMaterial(io, glbBuffer, outputDir, matName);
  }

  console.log('\n✅ 추출 완료!');
}

/**
 * 특정 머티리얼을 사용하는 primitive만 포함하는 GLB를 생성
 */
async function extractByMaterial(io, glbBuffer, outputDir, targetMatName) {
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
  const outputBuffer = await io.writeBinary(doc);
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
