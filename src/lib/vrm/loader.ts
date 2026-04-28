import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { VRMLoaderPlugin, VRM } from '@pixiv/three-vrm';
import { MToonMaterial, MToonMaterialOutlineWidthMode } from '@pixiv/three-vrm-materials-mtoon';

let loaderInstance: GLTFLoader | null = null;

function getLoader(): GLTFLoader {
  if (!loaderInstance) {
    loaderInstance = new GLTFLoader();
    loaderInstance.register((parser) => new VRMLoaderPlugin(parser));
  }
  return loaderInstance;
}

/**
 * Fix MToon material outlines that render internal mesh boundaries
 * as visible lines across the face.
 */
function fixMToonOutlines(vrm: VRM): void {
  vrm.scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (!mesh.isMesh) return;

    const materials = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const mat of materials) {
      if (mat instanceof MToonMaterial) {
        // Disable outline rendering to prevent internal boundary lines
        mat.outlineWidthMode = MToonMaterialOutlineWidthMode.None;
        mat.outlineWidthFactor = 0;
        mat.needsUpdate = true;
      }
    }
  });
}

export async function loadVRM(url: string): Promise<VRM> {
  const loader = getLoader();

  const gltf = await loader.loadAsync(url);
  const vrm = gltf.userData.vrm as VRM;

  if (!vrm) {
    throw new Error('Failed to load VRM from file');
  }

  // VRM models face +Z by default, rotate to face camera (-Z)
  vrm.scene.rotation.y = Math.PI;

  // Fix MToon outline artifacts on face mesh boundaries
  fixMToonOutlines(vrm);

  // Debug: log morph targets found
  vrm.scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (mesh.isMesh && mesh.morphTargetDictionary) {
      const keys = Object.keys(mesh.morphTargetDictionary);
      const customKeys = keys.filter(k => k.startsWith('face_') || k.startsWith('body_'));
      if (customKeys.length > 0) {
        console.log(`[VRM] Custom morph targets on "${mesh.name}":`, customKeys);
      }
    }
  });

  return vrm;
}

export function getExpressionNames(vrm: VRM): string[] {
  const names: string[] = [];
  const manager = vrm.expressionManager;
  if (!manager) return names;

  for (const expression of manager.expressions) {
    names.push(expression.expressionName);
  }
  return names;
}

export function getMorphTargetNames(vrm: VRM): string[] {
  const names = new Set<string>();

  // Collect expression names to exclude from raw morph target list
  const expressionNames = new Set(getExpressionNames(vrm));

  vrm.scene.traverse((object) => {
    const mesh = object as THREE.Mesh;
    if (mesh.isMesh && mesh.morphTargetDictionary) {
      for (const name of Object.keys(mesh.morphTargetDictionary)) {
        // Exclude names already managed by VRM Expression API
        if (!expressionNames.has(name)) {
          names.add(name);
        }
      }
    }
  });

  return Array.from(names);
}

// Re-export for convenience
import * as THREE from 'three';
export { VRM };
