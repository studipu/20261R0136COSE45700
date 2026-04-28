import type { MorphTargetMap, BoneScaleMap, MaterialMap } from './editor';

export type PresetCategory = 'hair' | 'outfit' | 'accessory';

export interface PresetItem {
  id: string;
  name: string;
  category: PresetCategory;
  thumbnailUrl: string;
  meshUrl?: string;
  blendShapeKey?: string;
}

export interface QuickPreset {
  id: string;
  name: string;
  description?: string;
  isBuiltIn: boolean;
  values: {
    morphTargets?: MorphTargetMap;
    boneScales?: BoneScaleMap;
    materials?: MaterialMap;
  };
}
