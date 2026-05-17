/**
 * hair 디렉토리 내 GLB 파일들의 메시 정보를 분석하여 중복 여부를 확인
 */
import * as fs from 'fs';
import * as path from 'path';
import * as crypto from 'crypto';

const hairDir = 'public/models/hair';
const dirs = fs.readdirSync(hairDir).filter(d => fs.statSync(path.join(hairDir, d)).isDirectory()).sort();

// 각 파일의 메시 geometry 해시를 수집
const fileInfos = [];

for (const dir of dirs) {
  const files = fs.readdirSync(path.join(hairDir, dir)).filter(f => f.endsWith('.glb'));
  for (const file of files) {
    const filePath = path.join(hairDir, dir, file);
    const buf = fs.readFileSync(filePath);
    const jsonLength = buf.readUInt32LE(12);
    const jsonChunkType = buf.readUInt32LE(16);
    const jsonStr = buf.slice(20, 20 + jsonLength).toString('utf8');
    const gltf = JSON.parse(jsonStr);

    // binary chunk
    const binOffset = 20 + jsonLength;
    const binLength = buf.readUInt32LE(binOffset);
    const binData = buf.slice(binOffset + 8, binOffset + 8 + binLength);

    const meshes = gltf.meshes || [];
    let vertexCount = 0;
    let primCount = 0;

    // 각 primitive의 POSITION 데이터를 해시
    const positionHashes = [];

    for (const mesh of meshes) {
      for (const prim of mesh.primitives) {
        primCount++;
        if (prim.attributes && prim.attributes.POSITION !== undefined) {
          const acc = gltf.accessors[prim.attributes.POSITION];
          vertexCount += acc.count;

          // accessor에서 실제 바이너��� 데이터 추출하여 해시
          const bufferView = gltf.bufferViews[acc.bufferView];
          const offset = (bufferView.byteOffset || 0) + (acc.byteOffset || 0);
          const componentSize = 4; // FLOAT
          const componentCount = 3; // VEC3
          const byteLength = acc.count * componentSize * componentCount;
          const posData = binData.slice(offset, offset + byteLength);
          const hash = crypto.createHash('md5').update(posData).digest('hex');
          positionHashes.push(hash);
        }
      }
    }

    // 파일 전체 geometry 해시 (모든 position 해시를 합산)
    const geometryHash = crypto.createHash('md5').update(positionHashes.sort().join(',')).digest('hex');

    fileInfos.push({
      dir,
      file,
      filePath,
      meshCount: meshes.length,
      primCount,
      vertexCount,
      geometryHash,
      size: buf.length,
    });

    console.log(`${dir}/${file}: prims=${primCount} vertices=${vertexCount} hash=${geometryHash.slice(0, 8)}`);
  }
}

// 중복 분석
console.log('\n=== 중복 분석 ===');
const hashGroups = {};
for (const info of fileInfos) {
  const key = info.file + ':' + info.geometryHash;
  if (!hashGroups[key]) hashGroups[key] = [];
  hashGroups[key].push(info);
}

const uniqueFiles = [];
const duplicates = [];

for (const [key, group] of Object.entries(hashGroups)) {
  uniqueFiles.push(group[0]);
  if (group.length > 1) {
    console.log(`\n중복 발견 (${group[0].file}, hash=${group[0].geometryHash.slice(0, 8)}):`);
    for (const g of group) {
      console.log(`  - ${g.dir}/${g.file}`);
    }
    for (let i = 1; i < group.length; i++) {
      duplicates.push(group[i]);
    }
  }
}

console.log(`\n총 파일: ${fileInfos.length}`);
console.log(`고유 메시: ${uniqueFiles.length}`);
console.log(`중복 파일: ${duplicates.length}`);

// 결과를 JSON으로 저장 (다음 스크립트에서 사용)
const result = { uniqueFiles, duplicates, hashGroups };
fs.writeFileSync('scripts/hair-analysis.json', JSON.stringify(result, null, 2));
console.log('\n분석 결과 저장: scripts/hair-analysis.json');
