// PRD EditorStore 인터페이스 정의
// Sprint 1: morphTargets, boneScales, materials, versions, undo/redo

export interface MorphTargetMap {
  [name: string]: number; // -1.0 ~ 1.0
}

export interface BoneScaleMap {
  [boneName: string]: {
    x: number;
    y: number;
    z: number;
  };
}

export interface MaterialSlot {
  name: string;
  color?: string;
  metalness?: number;
  roughness?: number;
  opacity?: number;
  textureUrl?: string;
}

export interface MaterialMap {
  [slotName: string]: MaterialSlot;
}

export interface AvatarVersion {
  id: string;
  name: string;
  parameters: AvatarParameters;
  thumbnailDataUrl?: string;
  createdAt: string;
}

export interface AvatarParameters {
  morphTargets: MorphTargetMap;
  boneScales: BoneScaleMap;
  materials: MaterialMap;
}

export interface EditorState {
  // Avatar identification
  avatarId: string | null;
  templateId: string | null;

  // Editing parameters
  morphTargets: MorphTargetMap;
  boneScales: BoneScaleMap;
  materials: MaterialMap;

  // Version management
  versions: AvatarVersion[];

  // UI state
  isLoading: boolean;
  error: string | null;
}

export interface EditorActions {
  // Morph targets
  setMorphTarget: (name: string, value: number) => void;
  resetMorphTargets: () => void;

  // Bone scales
  setBoneScale: (boneName: string, axis: 'x' | 'y' | 'z', value: number) => void;
  resetBoneScales: () => void;

  // Materials
  setMaterial: (slotName: string, property: keyof MaterialSlot, value: string | number) => void;
  resetMaterials: () => void;

  // Versions
  saveVersion: (name?: string, thumbnailDataUrl?: string) => void;
  restoreVersion: (versionId: string) => void;
  deleteVersion: (versionId: string) => void;
  renameVersion: (versionId: string, name: string) => void;

  // Undo/Redo
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;

  // Reset all
  resetAll: () => void;

  // Utility
  setAvatarId: (id: string) => void;
  setTemplateId: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export type EditorStore = EditorState & EditorActions;
