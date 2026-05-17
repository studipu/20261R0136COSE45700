import { NodeIO } from '@gltf-transform/core';
import * as fs from 'fs';
import * as path from 'path';

const outputDir = 'public/models/cloth-library';
fs.mkdirSync(outputDir, { recursive: true });

const indices = process.argv.slice(2);
if (indices.length === 0) {
  console.log('Usage: node scripts/extract-cloth.mjs 2 3 4 5');
  process.exit(1);
}

for (const i of indices) {
  const inputPath = `public/models/cloth_${i}.vrm`;
  if (!fs.existsSync(inputPath)) {
    console.log(`Skipping ${inputPath} (not found)`);
    continue;
  }

  console.log(`\n=== ${inputPath} ===`);
  const io = new NodeIO();
  const buf = fs.readFileSync(inputPath);
  const doc = await io.readBinary(new Uint8Array(buf));
  const root = doc.getRoot();

  const clothMatNames = root.listMaterials()
    .map(m => m.getName())
    .filter(n => n.includes('CLOTH'));

  console.log(`의상 머티리얼 ${clothMatNames.length}개:`);
  clothMatNames.forEach(n => console.log(`  - ${n}`));

  for (const node of root.listNodes()) {
    const mesh = node.getMesh();
    if (!mesh) continue;

    const prims = mesh.listPrimitives();
    const toRemove = [];

    for (const prim of prims) {
      const mat = prim.getMaterial();
      const matName = mat ? mat.getName() : '';
      if (!clothMatNames.includes(matName)) {
        toRemove.push(prim);
      }
    }

    if (toRemove.length === prims.length) {
      node.setMesh(null);
    } else {
      for (const prim of toRemove) {
        mesh.removePrimitive(prim);
      }
    }
  }

  const paddedIndex = i.toString().padStart(2, '0');
  const outputPath = path.join(outputDir, `cloth_${paddedIndex}.glb`);
  const outputBuffer = await io.writeBinary(doc);
  fs.writeFileSync(outputPath, Buffer.from(outputBuffer));

  const sizeKB = (fs.statSync(outputPath).size / 1024).toFixed(1);
  console.log(`-> ${outputPath} (${sizeKB} KB)`);
}

console.log('\n완료!');
