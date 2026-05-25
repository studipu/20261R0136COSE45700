# Virtual Avatar

애니메이션 스타일 레퍼런스 이미지로부터 VRM 아바타를 자동 생성하는 웹 애플리케이션.

- **얼굴 슬라이더 추출**: 레퍼런스 이미지 → ADF 28pt 랜드마크 → 29개 Avatar Keys → VRM morph target 자동 적용
- **텍스처 생성**: Gemini API 기반 얼굴 특징 분석 → 텍스처 자동 생성
- **헤어 매칭**: 이미지 색상/스타일 분석 → 프리셋 헤어 모델 자동 매칭

## 기술 스택

- **Frontend**: Next.js 16, React, Three.js (VRM 렌더링), Zustand
- **Backend**: Next.js API Routes → Python subprocess
- **AI/ML**: anime-face-detector (ADF), OpenCV, Google Gemini API

---

## 환경 설정

### 1. 저장소 클론 및 의존성 설치

```bash
git clone https://github.com/studipu/20261R0136COSE45700.git
cd 20261R0136COSE45700
git checkout face-feature
npm install
```

### 2. Git에 포함되지 않는 파일 복사

아래 파일들은 용량 문제로 Git에 포함되지 않습니다. 별도로 공유받아 프로젝트에 복사하세요.

| 파일 | 복사 위치 | 크기 | 필수 여부 |
|------|----------|------|----------|
| `checkpoint_landmark_191116.pth.tar` | `src/pipeline/kanosawa/` | 16MB | 필수 (텍스처 파이프라인) |
| `public/models/hair/` (5~9번 폴더) | `public/models/hair/` | 141MB | 선택 (추가 헤어 모델) |

> `public/models/hair-library/` (10개 GLB 파일)는 Git에 포함되어 있으므로 별도 복사 불필요.
> `experiments/` 폴더는 실험용이며 앱 실행에 불필요.

### 3. 환경 변수 설정 (`.env`)

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
GEMINI_API_KEY=<Google Gemini API 키>
PIPELINE_PYTHON=<Python venv 경로>
ADF_SERVER_URL=http://127.0.0.1:8000
```

| 변수 | 설명 |
|------|------|
| `GEMINI_API_KEY` | 텍스처 특징 추출에 사용하는 Google Gemini API 키 |
| `PIPELINE_PYTHON` | Python 가상환경의 python3 경로 (예: `~/.texture-pipeline-venv/bin/python3`) |
| `ADF_SERVER_URL` | anime-face-detector HTTP 서버 주소 (얼굴 슬라이더 추출용) |

### 4. Python 가상환경 설정

```bash
python3 -m venv ~/.texture-pipeline-venv
source ~/.texture-pipeline-venv/bin/activate
pip install -r TexturingPipeline/requirements.txt
```

설치 후 `.env`의 `PIPELINE_PYTHON`을 해당 venv 경로로 설정합니다.

```env
PIPELINE_PYTHON=/Users/<사용자명>/.texture-pipeline-venv/bin/python3
```

### 5. ADF 서버 실행 (얼굴 슬라이더 추출)

얼굴 슬라이더(face-keys) 추출을 위해 ADF 서버가 필요합니다.

**macOS (테스트용 mock 서버)**

anime-face-detector는 macOS에서 네이티브 실행이 불가하므로 mock 서버를 사용합니다.
모든 이미지에 동일한 고정 랜드마크를 반환합니다.

```bash
python face-feature/tools/mock_adf_server.py --port 8000
```

**Linux / WSL (실제 ADF 서버)**

정확한 얼굴 인식을 위해 Linux 환경에서 실제 ADF 서버를 실행합니다.

```bash
# anime-face-detector + mmcv + mmdet + mmpose 스택 설치 후
# ADF HTTP 서버 실행 (포트 8000)
```

---

## 실행

```bash
# 1. ADF 서버 실행 (별도 터미널)
python face-feature/tools/mock_adf_server.py --port 8000

# 2. 개발 서버 실행
npm run dev
```

http://localhost:3000 에서 확인할 수 있습니다.

---

## 프로젝트 구조

```
src/
├── app/
│   └── api/pipeline/
│       ├── face-keys/route.ts    # 얼굴 슬라이더 추출 API
│       └── texture/route.ts      # 텍스처 생성 API
├── components/
│   ├── editor/
│   │   ├── FaceFeatureApply.tsx   # 얼굴 슬라이더 UI
│   │   └── ReferenceModelUpload.tsx  # 레퍼런스 이미지 업로드
│   └── viewer/
│       └── VRMModel.tsx           # VRM 3D 모델 렌더링
├── lib/
│   ├── hair-matching/             # 헤어 매칭 로직
│   └── vrm/                      # VRM 유틸리티
├── pipeline/
│   ├── face/                      # 얼굴 슬라이더 Python 파이프라인
│   │   ├── run_extract.py         # CLI 진입점
│   │   ├── avatar_keys.py         # 28pt → 29 Avatar Keys
│   │   ├── feature_extractor.py   # 특징 벡터 추출
│   │   └── ...
│   └── kanosawa/                  # 랜드마크 검출 (PyTorch)
├── stores/
│   └── editorStore.ts             # 에디터 상태 관리 (Zustand)
└── types/
    ├── editor.ts
    └── pipeline.ts

face-feature/
└── tools/
    └── mock_adf_server.py         # macOS 테스트용 mock ADF 서버

TexturingPipeline/
├── requirements.txt               # Python 의존성 목록
└── src/                           # 텍스처 파이프라인 원본
```
