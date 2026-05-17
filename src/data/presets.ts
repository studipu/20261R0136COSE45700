import type { PresetItem, QuickPreset } from '@/types/preset';

export const PRESET_ITEMS: PresetItem[] = [
  {
    id: 'hair-none',
    name: '없음',
    category: 'hair',
    thumbnailUrl: '',
  },
  {
    id: 'hair-01',
    name: '헤어 1',
    category: 'hair',
    thumbnailUrl: '/thumbnails/hair-01.png',
    meshUrl: '/models/hair-library/N00_000_Hair_01_HAIR.glb',
    hairBackUrl: '/models/hair-library/N00_000_00_HairBack_01_HAIR.glb',
  },
  {
    id: 'hair-02',
    name: '헤어 2',
    category: 'hair',
    thumbnailUrl: '/thumbnails/hair-02.png',
    meshUrl: '/models/hair-library/N00_000_Hair_02_HAIR.glb',
    hairBackUrl: '/models/hair-library/N00_000_00_HairBack_02_HAIR.glb',
  },
  {
    id: 'hair-03',
    name: '헤어 3',
    category: 'hair',
    thumbnailUrl: '/thumbnails/hair-03.png',
    meshUrl: '/models/hair-library/N00_000_Hair_03_HAIR.glb',
    hairBackUrl: '/models/hair-library/N00_000_00_HairBack_03_HAIR.glb',
  },
  {
    id: 'hair-04',
    name: '헤어 4',
    category: 'hair',
    thumbnailUrl: '/thumbnails/hair-04.png',
    meshUrl: '/models/hair-library/N00_000_Hair_04_HAIR.glb',
    hairBackUrl: '/models/hair-library/N00_000_00_HairBack_04_HAIR.glb',
  },
  {
    id: 'hair-05',
    name: '헤어 5',
    category: 'hair',
    thumbnailUrl: '/thumbnails/hair-05.png',
    meshUrl: '/models/hair-library/N00_000_Hair_05_HAIR.glb',
    hairBackUrl: '/models/hair-library/N00_000_00_HairBack_05_HAIR.glb',
  },
  {
    id: 'outfit-none',
    name: '없음',
    category: 'outfit',
    thumbnailUrl: '',
  },
  {
    id: 'outfit-01',
    name: '의상 1',
    category: 'outfit',
    thumbnailUrl: '/thumbnails/cloth-01.png',
    meshUrl: '/models/cloth_1.vrm',
  },
  {
    id: 'outfit-02',
    name: '의상 2',
    category: 'outfit',
    thumbnailUrl: '/thumbnails/cloth-02.png',
    meshUrl: '/models/cloth_2.vrm',
  },
  {
    id: 'outfit-03',
    name: '의상 3',
    category: 'outfit',
    thumbnailUrl: '/thumbnails/cloth-03.png',
    meshUrl: '/models/cloth_3.vrm',
  },
  {
    id: 'outfit-04',
    name: '의상 4',
    category: 'outfit',
    thumbnailUrl: '/thumbnails/cloth-04.png',
    meshUrl: '/models/cloth_4.vrm',
  },
  {
    id: 'outfit-05',
    name: '의상 5',
    category: 'outfit',
    thumbnailUrl: '/thumbnails/cloth-05.png',
    meshUrl: '/models/cloth_5.vrm',
  },
  {
    id: 'accessory-none',
    name: '없음',
    category: 'accessory',
    thumbnailUrl: '',
  },
  {
    id: 'accessory-glasses',
    name: '안경',
    category: 'accessory',
    thumbnailUrl: '',
  },
  {
    id: 'accessory-hat',
    name: '모자',
    category: 'accessory',
    thumbnailUrl: '',
  },
];

export const QUICK_PRESETS: QuickPreset[] = [
  {
    id: 'big-eyes-small-nose',
    name: '큰 눈 + 작은 코',
    description: '귀여운 인상의 큰 눈과 작은 코 조합',
    isBuiltIn: true,
    values: {
      morphTargets: {
        face_eye_size: 0.8,
        face_eye_height: 0.5,
        face_nose_height: 0.2,
        face_nose_width: 0.2,
        face_nose_length: 0.2,
      },
    },
  },
  {
    id: 'v-line-jaw',
    name: 'V라인 턱',
    description: '갸름한 V라인 턱선',
    isBuiltIn: true,
    values: {
      morphTargets: {
        face_jaw_width: 0.2,
        face_jaw_length: 0.6,
        face_chin_shape: 0.7,
        face_cheek_fullness: 0.3,
      },
    },
  },
  {
    id: 'soft-round-face',
    name: '부드러운 동그란 얼굴',
    description: '둥글고 부드러운 인상',
    isBuiltIn: true,
    values: {
      morphTargets: {
        face_jaw_width: 0.6,
        face_cheek_fullness: 0.7,
        face_chin_shape: 0.3,
        face_forehead_width: 0.6,
      },
    },
  },
  {
    id: 'sharp-features',
    name: '날카로운 이목구비',
    description: '또렷한 이목구비',
    isBuiltIn: true,
    values: {
      morphTargets: {
        face_eye_tilt: 0.6,
        face_nose_height: 0.7,
        face_nose_length: 0.5,
        face_jaw_width: 0.3,
        face_chin_shape: 0.6,
      },
    },
  },
];

export function getPresetsByCategory(category: PresetItem['category']): PresetItem[] {
  return PRESET_ITEMS.filter((p) => p.category === category);
}
