import type { MorphTargetMap, BoneScaleMap, MaterialMap } from './editor';

export interface TemplateMetadata {
  id: string;
  name: string;
  description: string;
  thumbnailUrl: string;
  vrmUrl: string;
  defaultValues?: {
    morphTargets?: MorphTargetMap;
    boneScales?: BoneScaleMap;
    materials?: MaterialMap;
  };
  tags?: string[];
}
