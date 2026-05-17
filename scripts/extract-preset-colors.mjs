/**
 * Extract dominant colors from hair preset GLB files.
 * Usage: node scripts/extract-preset-colors.mjs
 *
 * Outputs color hex values for each preset's materials.
 * These values are used in src/lib/hair-matching/preset-metadata.ts
 */

import { NodeIO } from '@gltf-transform/core';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const HAIR_DIR = 'public/models/hair-library';

const PRESET_FILES = [
  { id: 'hair-01', front: 'N00_000_Hair_01_HAIR.glb', back: 'N00_000_00_HairBack_01_HAIR.glb' },
  { id: 'hair-02', front: 'N00_000_Hair_02_HAIR.glb', back: 'N00_000_00_HairBack_02_HAIR.glb' },
  { id: 'hair-03', front: 'N00_000_Hair_03_HAIR.glb', back: 'N00_000_00_HairBack_03_HAIR.glb' },
  { id: 'hair-04', front: 'N00_000_Hair_04_HAIR.glb', back: 'N00_000_00_HairBack_04_HAIR.glb' },
  { id: 'hair-05', front: 'N00_000_Hair_05_HAIR.glb', back: 'N00_000_00_HairBack_05_HAIR.glb' },
];

function rgbToHex(r, g, b) {
  const toHex = (v) => Math.round(v * 255).toString(16).padStart(2, '0');
  return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
}

async function extractColors() {
  const io = new NodeIO();

  for (const preset of PRESET_FILES) {
    const frontPath = resolve(HAIR_DIR, preset.front);

    try {
      const document = await io.read(frontPath);
      const root = document.getRoot();
      const materials = root.listMaterials();

      console.log(`\n--- ${preset.id} (${preset.front}) ---`);
      console.log(`Materials: ${materials.length}`);

      for (const mat of materials) {
        const name = mat.getName();
        const baseColor = mat.getBaseColorFactor(); // [r, g, b, a]
        if (baseColor) {
          const hex = rgbToHex(baseColor[0], baseColor[1], baseColor[2]);
          console.log(`  ${name}: ${hex} (rgba: ${baseColor.map(v => v.toFixed(3)).join(', ')})`);
        }
      }

      // Mesh statistics
      const meshes = root.listMeshes();
      let totalVertices = 0;
      for (const mesh of meshes) {
        for (const prim of mesh.listPrimitives()) {
          const pos = prim.getAttribute('POSITION');
          if (pos) totalVertices += pos.getCount();
        }
      }
      console.log(`  Total vertices: ${totalVertices}, Meshes: ${meshes.length}`);
    } catch (e) {
      console.error(`  Error reading ${frontPath}: ${e.message}`);
    }
  }
}

extractColors().catch(console.error);
