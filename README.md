# UNFLATTEN — Animation Avatar Studio

> 이미지 한 장을 분석해 기본 VRM 모델에 적용할 얼굴 슬라이더, 텍스처 보정, 헤어/액세서리 attachment를 자동 구성하는 웹 기반 3D 아바타 편집 시스템

UNFLATTEN은 애니메이션 스타일 레퍼런스 이미지 한 장을 입력받아, 사용자가 원하는 캐릭터와 닮은 3D VRM 아바타 초안을 빠르게 만들고 웹 에디터에서 미세 조정할 수 있도록 만든 프로젝트입니다.

핵심은 새로운 인체 3D mesh를 처음부터 생성하는 것이 아니라, **2D 이미지 분석 결과를 VRM runtime에서 즉시 적용 가능한 편집 상태로 변환**하는 것입니다. 얼굴 키와 텍스처는 2D 이미지 기반으로 추출·보정하고, 기본 VRM 모델에 morph target, material texture, hair/accessory attachment를 조립해 아바타를 완성합니다.

---

## Why

기존 VRM 아바타 제작 흐름에는 다음과 같은 진입 장벽이 있습니다.

- 얼굴을 닮게 만들기 위해 29개 이상의 슬라이더를 직접 조절해야 합니다.
- 텍스처 편집에는 Photoshop 같은 그래픽 도구 사용 경험이 필요합니다.
- 원하는 레퍼런스와 비슷한 결과를 얻기까지 반복적인 시행착오가 필요합니다.
- 비전문가가 하나의 아바타를 만들기까지 시간이 오래 걸립니다.

UNFLATTEN은 이 과정을 다음 흐름으로 단순화합니다.

```text
이미지 업로드 → 자동 분석·보정 → VRM 조립 → 미세 조정·저장
```

---

## Core Workflow

```text
2D Reference Image
  → 3 Parallel Pipelines
      ├─ Hair Matching
      │   ├─ client-side analysis
      │   ├─ Gemini visual result first
      │   ├─ top-region color extraction
      │   └─ Lab ΔE based preset matching
      │
      ├─ Face Keys
      │   ├─ ADF 28pt / Kanosawa fallback
      │   ├─ geometric ratio calculation
      │   ├─ HoughCircles pupil detection
      │   └─ 29 Avatar Key generation
      │
      └─ Texture
          ├─ Gemini visual feature extraction
          ├─ OpenCV pixel-level correction
          ├─ 7 texture slots
          └─ editable stamp candidates

  → EditorStore
  → Three.js + @pixiv/three-vrm Renderer
  → Fine-tuning / Version Save
```

얼굴 키와 텍스처는 모두 2D 이미지 기반으로 처리합니다. 3D 생성은 기본 아바타 생성 흐름이 아니라, 액세서리 GLB 생성 실험 경로에서만 사용합니다.

---

## Features

### Reference Image → 29 Avatar Keys

레퍼런스 이미지에서 얼굴 특징을 추출해 VRM morph target에 적용 가능한 Avatar Key로 변환합니다.

- ADF 기반 28pt 얼굴 랜드마크 검출
- 실패 시 Kanosawa landmark fallback 사용
- OpenCV HoughCircles 기반 동공 보조 검출
- 얼굴 크기 대비 기하 비율 계산
- 29개 Avatar Key 생성
  - 눈 14개
  - 눈썹 5개
  - 코 3개
  - 입 3개
  - 얼굴형 4개

### Texture Correction, Not Full Regeneration

텍스처 파이프라인은 완전히 새로운 UV 텍스처를 생성하는 방식이 아니라, 기본 VRM이 공유하는 동일 UV 구조를 유지한 채 마스터 텍스처의 일부를 보정하는 방식으로 설계했습니다.

이를 통해 기존 모델의 음영과 질감을 유지하면서 레퍼런스 이미지의 특징을 반영할 수 있고, VRM material slot에 안정적으로 적용할 수 있습니다.

처리 대상 텍스처는 다음과 같습니다.

- Face
- Eyebrow
- Eyeline
- Pupil
- EyeWhite
- EyeHighlight / stamp candidates
- MouthInside

### Gemini + OpenCV Role Separation

텍스처 파이프라인에서는 Gemini와 OpenCV의 역할을 분리했습니다.

**Gemini — visual reasoning**

- 피부톤, 볼터치, 점
- 눈썹 색상
- 아이라인 타입
- 헤어 스타일 및 색상 힌트
- JSON 기반 특징 출력

**OpenCV — pixel-level correction**

- 홍채 색상 직접 샘플링
- 채도 기반 색상 필터링
- 안광 위치와 형태 검출
- 동공 및 홍채 세부 보정

정확한 픽셀 색상이 중요한 홍채 영역은 OpenCV가 랜드마크 좌표를 기준으로 직접 샘플링하고, 필요한 경우 Gemini 결과를 보정합니다.

### Hair Preset Matching

헤어는 새로 생성하기보다 프리셋 라이브러리에서 가장 유사한 모델을 선택해 장착합니다.

- 이미지 상단 영역 기반 대표 헤어 색상 추출
- Gemini visual result 우선 적용
- Lab ΔE 기반 색상 유사도 비교
- SpringBone 정보가 포함된 GLB 헤어 프리셋 적용
- 커스텀 헤어 적용 시 기본 VRM 헤어 visibility 제어

### Accessory Generation and Attachment

3D 생성은 액세서리 경로에서 사용합니다.

- VARCO image-to-3d API 기반 액세서리 GLB 생성
- 사용자의 직접 GLB 업로드 지원
- category → slot 매핑
- VRM anchor bone 기준 부착
- offset / rotation / scale 조정 UI 제공
- 액세서리별 enable / disable 및 교체 지원

### Web-based VRM Editor

브라우저에서 VRM 모델을 실시간으로 편집합니다.

- Three.js 기반 VRM 렌더링
- `@pixiv/three-vrm` 기반 VRM 로드 및 제어
- morph target / expression / bone scale 실시간 조정
- material color / texture 변경
- MToon material control
  - Shading Toony
  - Shading Shift
  - Rim Lighting Mix
- 헤어, 의상, 액세서리 attachment 적용
- undo / redo
- 최대 5개 버전 저장 및 복원
- 스크린샷 기반 버전 썸네일 저장
- 모션 재생 지원

---

## Architecture

```text
Browser
  └─ Next.js App Router
      ├─ Editor UI
      ├─ 3D VRM Viewer
      ├─ Zustand EditorStore
      └─ API Routes
          ├─ /api/pipeline/face-keys
          ├─ /api/pipeline/texture
          ├─ /api/pipeline/generate-3d
          └─ /api/accessory-generate
              └─ Python / External AI Pipeline
                  ├─ anime-face-detector
                  ├─ Kanosawa landmark fallback
                  ├─ OpenCV
                  ├─ Gemini API
                  ├─ VARCO / Meshy API
                  └─ PipelineResult JSON
```

프론트엔드와 백엔드는 하나의 Next.js 프로젝트 안에 있습니다. `src/app/api`가 백엔드 경계 역할을 하며, API Route는 업로드된 이미지를 임시 작업 디렉터리에 저장한 뒤 Python 스크립트를 subprocess로 실행합니다.

Python 파이프라인 결과는 JSON으로 반환되고, 프론트엔드는 이를 TypeScript 타입에 맞춰 Zustand store에 반영합니다.

---

## Main Pipelines

### Face Keys API

```text
POST /api/pipeline/face-keys

image
  → temporary input file
  → face-feature/run_extract.py
  → result.json
  → PipelineResult
```

역할:

- 얼굴 랜드마크 추출
- Avatar Key 계산
- template 분류
- slider 초기값 반환
- VRM morph target 적용용 parameter 반환

### Texture API

```text
POST /api/pipeline/texture

image
  → Kanosawa landmark extraction
  → Gemini + OpenCV feature extraction
  → texture correction
  → face-key extraction
  → hairstyle analysis
  → textures + features + hairMatch + faceKeys + proposedStamps
```

역할:

- Gemini 기반 정성 특징 추출
- OpenCV 기반 픽셀 보정
- 텍스처 보정 및 data URL 반환
- face key 병렬 추출
- 헤어 매칭 결과 반환
- texture stamp 후보 반환

### Accessory Generate API

```text
POST /api/accessory-generate

image or glb
  → image: VARCO image-to-3d submit / poll / download
  → glb: direct upload
  → local generated GLB URL
  → accessory instance
```

역할:

- 이미지 기반 액세서리 GLB 생성
- 직접 업로드된 GLB 저장
- 에디터에서 장착 가능한 asset URL 반환

### Generate 3D API

`/api/pipeline/generate-3d`는 전체 3D 생성 실험을 위한 API입니다. 현재 주 사용 흐름에서는 얼굴 키·텍스처가 2D 이미지 기반으로 처리되며, 3D 생성은 액세서리 생성 경로에 집중되어 있습니다.

---

## Technical Highlights

### 1. Next.js ↔ Python Pipeline Integration

Next.js API Route에서 Python 스크립트를 subprocess로 실행합니다.

구현 시 고려한 부분:

- 업로드 파일을 OS temp directory에 저장
- Python interpreter를 `PIPELINE_PYTHON` 환경변수로 분리
- route별 timeout 설정
- 결과 JSON 존재 여부 검증
- 실패 시 error response 반환
- debug output 저장
- 작업 종료 후 temp directory 정리

### 2. Face Key Normalization

얼굴 슬라이더 값은 랜드마크 좌표를 그대로 사용하지 않고 다음 단계를 거쳐 VRM morph target에 적용 가능한 값으로 변환합니다.

```text
Landmark Detection
  → Calibration
  → Gamma Correction
  → 29 Avatar Keys
```

- **Landmark Detection**: ADF 28pt를 기본으로 사용하고, 실패 시 Kanosawa fallback을 사용합니다.
- **Calibration**: 기준 이미지에서 각 key별 P5–P95 범위를 계산해 min/max 정규화 범위로 사용합니다.
- **Gamma Correction**: key별 민감도 차이를 줄이기 위해 감마 보정 곡선을 적용합니다.

### 3. Python ↔ TypeScript Data Contract

Python 파이프라인 결과를 프론트엔드에서 안정적으로 다루기 위해 `PipelineResult`, `TextureResult`, `FeatureVector` 타입을 정의했습니다.

```ts
export interface PipelineResult {
  status: 'ok' | 'failed_stage4';
  glb_path?: string;
  renders?: Record<string, string>;
  feature_vector: FeatureVector | null;
  feature_source: 'original' | 'front_render' | null;
  feature_debug?: Record<string, unknown>;
  avatar_parameters: Record<string, number> | null;
  parameter_debug?: Record<string, unknown>;
  template: 'cute' | 'slim' | 'mature' | null;
  confidence: number | null;
  all_scores: Record<string, number> | null;
  slider_init: SliderInit | null;
  error?: string;
}
```

이 구조 덕분에 Python 파이프라인이 변경되어도 프론트엔드 적용 지점을 명확히 추적할 수 있습니다.

### 4. VRM Runtime Application

VRM 모델은 단순히 렌더링되는 것이 아니라, 에디터 상태에 따라 실시간으로 변형됩니다.

적용 대상:

- VRM expression
- raw morph target influence
- humanoid bone scale
- material color
- material shading property
- material texture
- hair / outfit visibility
- accessory transform

VRM Expression API로 관리되는 값과 raw morph target을 구분해 적용하고, material 변경은 이전 상태와 비교해 불필요한 반복 적용을 줄였습니다.

### 5. Zustand-based Editor State

에디터의 모든 편집 상태는 Zustand store에서 관리합니다.

주요 상태:

- `morphTargets`
- `boneScales`
- `materials`
- `hairFrontUrl` / `hairBackUrl`
- `outfitUrl`
- `accessoryInstances`
- `versions`
- `proposedStamps`
- `selectedAnimationIndex`

undo/redo는 현재 편집 상태의 snapshot을 저장하는 방식으로 구현했습니다. 버전 저장 시 morph, bone, material, accessory 상태를 함께 보존합니다.

### 6. Accessory Instance Model

액세서리를 단일 URL이 아니라 독립적인 instance로 관리합니다.

```ts
interface AccessoryInstance {
  instanceId: string;
  presetId: string;
  category: AccessoryCategory;
  enabled: boolean;
  adjustment: {
    scaleMultiplier: [number, number, number];
    rotationDelta: [number, number, number];
    offsetDelta: [number, number, number];
  };
}
```

이 구조는 다음 확장을 가능하게 합니다.

- 여러 액세서리 동시 적용
- 카테고리별 교체
- 액세서리별 위치 보정
- 사용자 업로드 프리셋 적용
- 추천 결과와 실제 적용 상태 분리

---

## Tech Stack

### Frontend

| Tech | Usage |
|---|---|
| Next.js 16 | App Router, API Routes |
| React 19 | UI components |
| TypeScript | 타입 안정성 |
| Three.js | 3D 렌더링 |
| React Three Fiber | React 기반 Three.js 구성 |
| Drei | 3D viewer 유틸리티 |
| @pixiv/three-vrm | VRM 로드 및 제어 |
| Zustand | 에디터 상태 관리 |
| Tailwind CSS | UI 스타일링 |

### Backend / AI / CV

| Tech | Usage |
|---|---|
| Next.js API Routes | Python 파이프라인 호출 |
| Python | 이미지 분석 및 파이프라인 처리 |
| OpenCV | 이미지 처리, 색상/동공/안광 분석 |
| anime-face-detector | 애니메이션 얼굴 랜드마크 검출 |
| Kanosawa CFA | landmark fallback |
| Gemini API | 시각 특징 분석 |
| VARCO / Meshy API | 2D 이미지 기반 3D 생성 실험 |

### 3D / Runtime

| Tech | Usage |
|---|---|
| VRM | 아바타 모델 포맷 |
| MToon | 애니메이션 스타일 material |
| SpringBone | 헤어 물리 정보 |
| GLB | 헤어 / 액세서리 asset |

---

## Project Structure

```text
src/
├── app/
│   ├── api/
│   │   ├── pipeline/
│   │   │   ├── face-keys/
│   │   │   ├── texture/
│   │   │   └── generate-3d/
│   │   └── accessory-generate/
│   └── dev/
│       └── viewer/
├── components/
│   ├── editor/
│   │   ├── ReferenceModelUpload.tsx
│   │   ├── MorphTargetSlider.tsx
│   │   ├── MaterialEditor.tsx
│   │   ├── TextureStampEditor.tsx
│   │   ├── AccessoryUpload.tsx
│   │   ├── AccessoryFitPanel.tsx
│   │   └── VersionPanel.tsx
│   └── viewer/
│       ├── ThreeJSViewer.tsx
│       ├── VRMModel.tsx
│       ├── HairAttachment.tsx
│       └── AccessoryRenderScene.tsx
├── hooks/
├── lib/
│   ├── api/
│   ├── vrm/
│   ├── hair-matching/
│   └── accessory-attachment/
├── stores/
│   └── editorStore.ts
├── types/
│   ├── editor.ts
│   ├── pipeline.ts
│   └── accessory.ts
└── pipeline/

face-feature/
├── pipeline/
├── tools/
└── main.py

TexturingPipeline/
├── requirements.txt
└── src/
```

---

## Getting Started

### 1. Clone

```bash
git clone https://github.com/studipu/261RCOSE45700.git
cd 261RCOSE45700
```

### 2. Install Node dependencies

```bash
npm install
```

### 3. Set up Python environment

```bash
python3 -m venv ~/.texture-pipeline-venv
source ~/.texture-pipeline-venv/bin/activate
pip install -r TexturingPipeline/requirements.txt
```

### 4. Configure environment variables

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
GEMINI_API_KEY=<Google Gemini API Key>
PIPELINE_PYTHON=/absolute/path/to/python3
ADF_SERVER_URL=http://127.0.0.1:8000
VARCO_API_KEY=<Optional VARCO API Key>
DATABASE_URL=<Optional PostgreSQL URL>
```

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Gemini 기반 시각 특징 추출에 사용 |
| `PIPELINE_PYTHON` | Python pipeline 실행에 사용할 interpreter 경로 |
| `ADF_SERVER_URL` | ADF HTTP server 주소 |
| `VARCO_API_KEY` | 액세서리 image-to-3d 생성에 사용 |
| `DATABASE_URL` | 향후 운영 저장소 연동용 PostgreSQL URL |

### 5. Run ADF server

macOS 개발 환경에서는 mock ADF 서버를 사용할 수 있습니다.

```bash
python face-feature/tools/mock_adf_server.py --port 8000
```

Linux / WSL 환경에서는 실제 anime-face-detector 기반 ADF 서버 실행을 권장합니다.

### 6. Run development server

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

---

## Environment Notes

일부 파일은 용량 또는 실행 환경 문제로 Git에 포함되지 않을 수 있습니다.

| File / Directory | Target Path | Required |
|---|---|---|
| `checkpoint_landmark_191116.pth.tar` | `src/pipeline/kanosawa/` | 텍스처 / fallback 파이프라인에 필요 |
| `public/models/hair/` 추가 모델 | `public/models/hair/` | 추가 헤어 프리셋 사용 시 필요 |

추가 참고:

- `public/models/hair-library/`의 기본 GLB 파일은 저장소에 포함되어 있습니다.
- `experiments/`는 실험용이며 기본 앱 실행에는 필수는 아닙니다.
- Gemini와 VARCO 기능은 유효한 API key가 필요합니다.
- 실제 anime-face-detector 실행은 Linux / WSL 환경을 권장합니다.

---

## Current Limitations

- **Pupil detection instability**  
  애니메이션 스타일 눈에서는 HoughCircles 기반 반지름 추정이 불안정할 수 있습니다.

- **Limited eyelid measurement**  
  `TopLidDown`, `LowerLidUp` 계열 값은 현재 안정적으로 측정하기 어려워 기본값에 가깝게 처리됩니다.

- **Calibration dataset size**  
  현재 calibration 기준 이미지 수가 제한적이므로, 더 다양한 캐릭터 스타일을 반영하려면 데이터셋 확장이 필요합니다.

- **Persistence layer**  
  현재 개발 흐름은 localStorage와 파일 기반 처리 중심이며, RDS 연동은 향후 개선 과제입니다.

- **Long-running pipeline jobs**  
  Python 파이프라인과 외부 AI API 호출은 실행 시간이 길어질 수 있으므로, 사용량이 늘면 background job queue 구조가 필요합니다.

---

## Roadmap

### Short-term

- calibration 이미지 확대
- 동공 검출 안정화
- Avatar Key 정규화 범위 개선
- texture stamp editor 개선

### Mid-term

- Gemini 분석 정확도 개선
- 헤어 / 액세서리 프리셋 확대
- 액세서리 추천 로직 고도화
- background task UX 개선

### Long-term

- RDS 기반 사용자별 avatar/version 저장
- 클라우드 배포 구조 안정화
- 실시간 preview 개선
- VRM export 기능 연결
- 자동 학습 기반 추천 품질 개선

---

## What I Learned

- Next.js API Route와 Python subprocess를 연결해 웹 앱 안에서 AI/CV 파이프라인을 운영하는 방법
- Python output과 TypeScript frontend 사이의 JSON contract를 설계하는 방법
- 이미지 분석 결과를 VRM morph target, material texture, attachment 상태로 변환하는 방법
- Three.js와 `@pixiv/three-vrm`을 사용해 VRM runtime을 실시간 제어하는 방법
- 복잡한 에디터 상태를 Zustand로 관리하고 undo/redo, version 저장까지 확장하는 방법
- 외부 AI API와 장시간 파이프라인 작업을 다룰 때 timeout, fallback, debug output, cleanup을 설계하는 방법

---

## Repository

```text
https://github.com/studipu/261RCOSE45700
```
