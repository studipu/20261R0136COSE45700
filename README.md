# UNFLATTEN — Animation Avatar Studio


**UNFLATTEN**은 애니메이션 스타일 레퍼런스 2D 이미지 한 장을 기반으로, 3D 아바타의 얼굴 파라미터, 텍스처, 헤어, 액세서리를 자동 구성하는 웹 기반 **3D 아바타 편집 시스템**입니다.

사용자는 2D 이미지를 업로드한 뒤 3D 아바타에 자동으로 적용된 얼굴 슬라이더, 텍스처, 헤어/액세서리 결과를 확인하고, 웹 에디터에서 직접 미세 조정할 수 있습니다.


```text
Reference Image
  → Face Key Extraction
  → Texture Correction
  → Hair / Accessory Matching
  → VRM Editor
```

---

## 개요

기존 VRM 3D 아바타 제작 과정은 비전문가에게 진입 장벽이 높습니다. 원하는 캐릭터와 비슷한 얼굴을 만들기 위해 여러 슬라이더를 직접 조절해야 하고, 텍스처를 수정하려면 그래픽 편집 도구 사용 경험이 필요합니다. 헤어, 액세서리, 재질, 표정, 모션도 각각 다른 방식으로 조정해야 하므로 하나의 아바타를 완성하기까지 많은 시행착오가 발생합니다.

UNFLATTEN은 이 과정을 다음과 같이 단순화합니다.

```text
이미지 한 장 업로드
  → 얼굴·텍스처·헤어 자동 분석
  → 기본 VRM 모델에 적용
  → 웹 에디터에서 미세 조정
  → 버전 저장
```

핵심 목표는 자동 분석 결과를 최종 결과로 고정하는 것이 아니라, 사용자가 이어서 편집 가능한 아바타 초안을 제공하는 것입니다.

---

## 주요 기능

### 얼굴 파라미터 추출

레퍼런스 2D 이미지에서 얼굴 랜드마크를 검출하고, 이를 VRM `morph target`에 적용할 수 있는 Avatar Key로 변환합니다.

* ADF 기반 28pt 얼굴 랜드마크 검출
* Kanosawa landmark fallback 지원
* OpenCV 기반 동공 보조 검출
* 얼굴 비율 기반 feature 계산
* 29개 Avatar Key 생성
* 에디터의 얼굴 슬라이더 초기값으로 적용

### 텍스처 보정

기본 VRM 텍스처의 UV 구조를 유지한 채, 레퍼런스 이미지의 특징을 반영하도록 텍스처를 보정합니다.

* Gemini 기반 시각 특징 분석
* OpenCV 기반 홍채 색상 및 안광 보정
* Face, Eyebrow, Eyeline, Pupil 등 주요 텍스처 슬롯 처리
* 보정된 텍스처를 VRM `material`에 적용

텍스처를 완전히 새로 생성하지 않고 동일 UV 기반으로 보정하기 때문에, 기존 모델의 음영과 질감을 유지하면서 레퍼런스의 특징을 반영할 수 있습니다.

### 헤어 매칭

레퍼런스 이미지의 색상과 스타일 정보를 기반으로 가장 유사한 헤어 프리셋을 선택합니다.

* 이미지 기반 헤어 색상 추출
* Gemini visual result 활용
* Lab ΔE 기반 색상 유사도 비교
* SpringBone이 포함된 GLB 헤어 프리셋 적용
* 커스텀 헤어 적용 시 기본 VRM 헤어 표시 여부 제어

### 액세서리 생성 및 부착

액세서리는 별도의 GLB asset으로 관리되며, VRM `anchor bone`을 기준으로 부착됩니다.

* 액세서리 GLB 업로드 지원
* VARCO image-to-3d 기반 액세서리 생성 흐름
* category 기반 slot 매핑
* offset, rotation, scale 조정
* 액세서리별 enable / disable 지원

### 웹 기반 VRM 에디터

브라우저에서 VRM 모델을 로드하고 실시간으로 편집합니다.

* Three.js 기반 3D viewer
* `@pixiv/three-vrm` 기반 VRM 로드 및 제어
* `morph target`, expression, material 조정
* MToon material 속성 조정
* 헤어, 의상, 액세서리 attachment 적용
* undo / redo
* 버전 저장 및 복원

---

## 동작 흐름

이미지가 업로드되면 시스템은 얼굴, 텍스처, 스타일 정보를 각각 분석한 뒤 하나의 에디터 상태로 합칩니다.

```text
2D 레퍼런스 이미지
  ├─ 얼굴 파라미터
  │   └─ landmarks → geometric features → Avatar Keys
  │
  ├─ 텍스처
  │   └─ Gemini + OpenCV → corrected texture slots
  │
  └─ 헤어 / 액세서리
      └─ preset matching or GLB attachment
        ↓
Zustand EditorStore
        ↓
Three.js + @pixiv/three-vrm
        ↓
편집 가능한 VRM 아바타
```

얼굴 키와 텍스처는 모두 2D 이미지 기반으로 처리합니다. 기본 아바타의 3D mesh를 새로 생성하지 않고, VRM 모델의 `morph target`, `material`, `attachment` 구조를 활용해 결과를 조립합니다.

---

## 기술 구현

### Next.js API Routes와 Python 파이프라인 연동

Next.js API Route에서 업로드된 이미지를 임시 디렉터리에 저장한 뒤, Python 파이프라인을 subprocess로 실행합니다.

```text
Next.js API Route
  → 업로드 이미지 저장
  → Python script 실행
  → 결과 JSON 읽기
  → API 응답 반환
  → 에디터 상태에 적용
```

이를 통해 웹 애플리케이션 안에서 OpenCV, anime-face-detector, Gemini 기반 이미지 분석 파이프라인을 함께 사용할 수 있습니다.

### Face Key 정규화

랜드마크 좌표를 그대로 사용하는 대신, 얼굴 크기 대비 기하 비율을 계산하고 보정 과정을 거쳐 VRM에서 사용할 수 있는 값으로 변환합니다.

```text
ADF / Kanosawa landmarks
  → 기하 비율 계산
  → Calibration
  → Gamma correction
  → 29 Avatar Keys
```

이 과정은 이미지 크기나 얼굴 위치에 따른 흔들림을 줄이고, `morph target`에 적용 가능한 안정적인 값을 만들기 위한 구조입니다.

### 텍스처 파이프라인

텍스처 파이프라인은 Gemini와 OpenCV의 역할을 분리합니다.

| 도구     | 역할                                     |
| ------ | -------------------------------------- |
| Gemini | 피부톤, 볼터치, 점, 눈썹 색, 아이라인 타입 등 시각적 특징 판단 |
| OpenCV | 홍채 색상 샘플링, 안광 위치 감지, 픽셀 단위 보정          |

Gemini가 전체적인 시각 특징을 추출하고, OpenCV가 픽셀 단위 정확도가 필요한 영역을 보정합니다. 특히 홍채 색상이나 안광 위치처럼 정밀한 값이 필요한 부분은 랜드마크 좌표를 기준으로 직접 샘플링합니다.

### 편집 가능한 런타임 상태

자동 분석 결과는 최종 결과로 고정되지 않고, Zustand store에 편집 가능한 상태로 반영됩니다.

에디터는 다음 값을 실시간으로 VRM runtime에 적용합니다.

* `morph target`
* expression
* bone scale
* material color
* material texture
* MToon material property
* hair / outfit visibility
* accessory transform

---

## 기술 스택

| 영역                   | 기술                                                |
| -------------------- | ------------------------------------------------- |
| Frontend             | Next.js 16, React 19, TypeScript                  |
| 3D Viewer            | Three.js, React Three Fiber, `@pixiv/three-vrm`   |
| State Management     | Zustand                                           |
| Styling              | Tailwind CSS                                      |
| Backend Boundary     | Next.js API Routes                                |
| Pipeline Runtime     | Python subprocess                                 |
| AI / CV              | Gemini API, OpenCV, anime-face-detector, Kanosawa |
| 3D Assets            | VRM, GLB, MToon, SpringBone                       |
| Accessory Generation | VARCO image-to-3d API                             |

---

## 프로젝트 구조

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
│   └── viewer/
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

## 실행 방법

### 1. 저장소 클론

```bash
git clone https://github.com/studipu/261RCOSE45700.git
cd 261RCOSE45700
```

### 2. Node 의존성 설치

```bash
npm install
```

### 3. Python 가상환경 설정

```bash
python3 -m venv ~/.texture-pipeline-venv
source ~/.texture-pipeline-venv/bin/activate
pip install -r TexturingPipeline/requirements.txt
```

### 4. 환경 변수 설정

프로젝트 루트에 `.env` 파일을 생성합니다.

```env
GEMINI_API_KEY=<Google Gemini API Key>
PIPELINE_PYTHON=/absolute/path/to/python3
ADF_SERVER_URL=http://127.0.0.1:8000
VARCO_API_KEY=<Optional VARCO API Key>
```

| 변수                | 설명                                  |
| ----------------- | ----------------------------------- |
| `GEMINI_API_KEY`  | Gemini 기반 이미지 특징 분석에 사용             |
| `PIPELINE_PYTHON` | Python 파이프라인 실행에 사용할 interpreter 경로 |
| `ADF_SERVER_URL`  | ADF HTTP server 주소                  |
| `VARCO_API_KEY`   | 액세서리 image-to-3d 생성에 사용             |

### 5. ADF 서버 실행

macOS 개발 환경에서는 mock ADF 서버를 사용할 수 있습니다.

```bash
python face-feature/tools/mock_adf_server.py --port 8000
```

Linux / WSL 환경에서는 실제 anime-face-detector 기반 ADF 서버 실행을 권장합니다.

### 6. 개발 서버 실행

```bash
npm run dev
```

브라우저에서 다음 주소로 접속합니다.

```text
http://localhost:3000
```

---

## 참고 사항

일부 모델 파일이나 체크포인트는 용량 문제로 저장소에 포함되지 않을 수 있습니다. 전체 파이프라인 실행을 위해 필요한 파일은 지정된 경로에 복사해야 합니다.

```text
src/pipeline/kanosawa/checkpoint_landmark_191116.pth.tar
public/models/hair/
```
