import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import * as THREE from 'three';

let loaderInstance: GLTFLoader | null = null;

function getLoader(): GLTFLoader {
  if (!loaderInstance) {
    loaderInstance = new GLTFLoader();
  }
  return loaderInstance;
}

const cache = new Map<string, THREE.Group>();

export async function loadGLB(url: string): Promise<THREE.Group> {
  const cached = cache.get(url);
  if (cached) {
    return cached.clone();
  }

  const loader = getLoader();
  const gltf = await loader.loadAsync(url);
  cache.set(url, gltf.scene);
  return gltf.scene.clone();
}

export function clearGLBCache(): void {
  cache.clear();
}
