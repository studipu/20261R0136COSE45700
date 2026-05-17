/**
 * hair 하위 디렉토리의 GLB 파일들을 하나의 디렉토리로 합치기
 * Hair와 HairBack을 각각 독립적으로 넘버링
 *
 * 출력 예:
 *   N00_000_Hair_01_HAIR.glb      (from 5.vrm)
 *   N00_000_Hair_02_HAIR.glb      (from 6.vrm)
 *   ...
 *   N00_000_00_HairBack_01_HAIR.glb (from 5.vrm)
 *   N00_000_00_HairBack_02_HAIR.glb (from 6.vrm)
 *   ...
 */
import * as fs from 'fs';
import * as path from 'path';

const hairDir = 'public/models/hair';
const outputDir = 'public/models/hair-library';

fs.mkdirSync(outputDir, { recursive: true });

const dirs = fs.readdirSync(hairDir)
  .filter(d => fs.statSync(path.join(hairDir, d)).isDirectory())
  .sort((a, b) => Number(a) - Number(b));

// Hair와 HairBack 파일을 분리 수집
const hairFiles = [];
const hairBackFiles = [];

for (const dir of dirs) {
  const files = fs.readdirSync(path.join(hairDir, dir)).filter(f => f.endsWith('.glb'));
  for (const file of files) {
    const srcPath = path.join(hairDir, dir, file);
    if (file.includes('HairBack')) {
      hairBackFiles.push({ dir, file, srcPath });
    } else {
      hairFiles.push({ dir, file, srcPath });
    }
  }
}

console.log('=== 파일 병합 ===\n');
console.log('--- Hair (앞머리) ---');
hairFiles.forEach((item, i) => {
  const num = String(i + 1).padStart(2, '0');
  const newName = `N00_000_Hair_${num}_HAIR.glb`;
  const dstPath = path.join(outputDir, newName);
  fs.copyFileSync(item.srcPath, dstPath);
  console.log(`  ${item.dir}/${item.file} → ${newName}`);
});

console.log('\n--- HairBack (뒷머리) ---');
hairBackFiles.forEach((item, i) => {
  const num = String(i + 1).padStart(2, '0');
  const newName = `N00_000_00_HairBack_${num}_HAIR.glb`;
  const dstPath = path.join(outputDir, newName);
  fs.copyFileSync(item.srcPath, dstPath);
  console.log(`  ${item.dir}/${item.file} → ${newName}`);
});

console.log(`\n✅ 완료: ${outputDir}/`);
console.log(`   Hair: ${hairFiles.length}개 (01~${String(hairFiles.length).padStart(2, '0')})`);
console.log(`   HairBack: ${hairBackFiles.length}개 (01~${String(hairBackFiles.length).padStart(2, '0')})`);
