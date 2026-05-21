import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import {
  VRMSpringBoneLoaderPlugin,
  VRMSpringBoneManager,
} from '@pixiv/three-vrm-springbone';
import * as THREE from 'three';

export interface HairLoadResult {
  scene: THREE.Group;
  springBoneManager: VRMSpringBoneManager | null;
}

let loaderInstance: GLTFLoader | null = null;

function getLoader(): GLTFLoader {
  if (!loaderInstance) {
    loaderInstance = new GLTFLoader();
    loaderInstance.register((parser) => new VRMSpringBoneLoaderPlugin(parser));
  }
  return loaderInstance;
}

export async function loadHairGLB(url: string): Promise<HairLoadResult> {
  const loader = getLoader();
  const gltf = await loader.loadAsync(url);
  const springBoneManager: VRMSpringBoneManager | null =
    gltf.userData?.vrmSpringBoneManager ?? null;

  return { scene: gltf.scene, springBoneManager };
}
