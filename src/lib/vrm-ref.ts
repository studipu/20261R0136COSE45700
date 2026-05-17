import type { VRM } from '@pixiv/three-vrm';

let baseVrm: VRM | null = null;

export function setBaseVRM(vrm: VRM | null) {
  baseVrm = vrm;
}

export function getBaseVRM(): VRM | null {
  return baseVrm;
}
