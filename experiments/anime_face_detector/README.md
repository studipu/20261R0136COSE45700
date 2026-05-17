# Auto Face Shape Apply — PoC

> 입력 3D 에셋(VARCO GLB 등)의 얼굴 특징을 추출해 마스터 VRM의 블렌드쉐입 슬라이더에 자동 적용하는 end-to-end 파이프라인.
> 작성: 2026-05-09 · 상태: PoC 검증 완료

---

## 한 줄 요약

```
입력 GLB → 정면 렌더 → 24 landmark + 색상 segmentation → 25개 측정값
       → 마스터 baseline과 비교 → 단방향 매핑 → 8~12개 슬라이더 자동 적용
       → 변형된 마스터 모델 결과 PNG
```

8개 active 슬라이더가 자동 산출되었고 마스터 메시가 의미 있게 변형됨을 확인.

---

## 디렉토리 구조

```
experiments/anime_face_detector/
├── README.md                    # 이 파일
├── kanosawa_repo/               # CFA model + 우리 측정 모듈
│   ├── CFA.py                   # PyTorch landmark detection model
│   ├── checkpoint_landmark_191116.pth.tar  # 16.7MB 가중치
│   ├── lbpcascade_animeface.xml # anime 얼굴 detection
│   ├── extract_landmarks.py     # 24 landmark 추출 (cascade fallback 포함)
│   ├── measure_face.py          # landmark + HSV 색상 → 25 metrics
│   └── compute_sliders.py       # baseline ↔ user 비교 → sliders.json
├── scripts/                     # Production pipeline
│   ├── render_front.py          # Blender headless: GLB/VRM → 정면 PNG
│   ├── apply_sliders.py         # Blender headless: sliders 적용 + 렌더
│   ├── make_comparison.py       # 3-way 비교 이미지
│   └── run_pipeline.sh          # ★ Orchestrator
├── inputs/                      # 입력 (PNG, GLB 등)
└── outputs/                     # 모든 결과
```

---

## 빠른 사용법

### 단일 명령

```bash
cd experiments/anime_face_detector/scripts
./run_pipeline.sh \
    /path/to/input.glb \
    /path/to/master.vrm \
    /path/to/output_dir
```

### 출력 파일

| 파일 | 내용 |
|---|---|
| `input_front.png` | 입력 GLB 정면 렌더 (512×512) |
| `master_baseline.png` | 마스터 VRM 정면 렌더 (캐시) |
| `input_measure.json` | 입력 25개 측정값 |
| `master_measure.json` | 마스터 25개 측정값 |
| `sliders.json` | 산출된 슬라이더 값 (29개 키, 8~12개 active) |
| `master_result.png` | 슬라이더 적용 후 마스터 렌더 |
| `comparison.png` | 3-way 비교 (입력 / baseline / 적용 후) |

### Baseline 캐싱

같은 마스터 VRM을 반복 사용할 때 매번 baseline 측정을 다시 돌릴 필요 없음.
`run_pipeline.sh`가 `master_baseline.png` 존재하면 자동 skip.
강제 재생성: `REGEN_BASELINE=1 ./run_pipeline.sh ...`

---

## 의존성 (production 머신)

### 1. Blender 4.2+ 

```bash
# macOS
brew install --cask blender
# Linux
sudo apt install blender
```

[VRM Add-on for Blender](https://vrm-addon-for-blender.info/) 활성화 필요.

### 2. Python 패키지

```bash
pip install \
    torch==1.13.1 torchvision==0.14.1 \
    --index-url https://download.pytorch.org/whl/cpu

pip install "numpy<2" opencv-python Pillow
```

> **주의:** PyTorch 1.13 + numpy 1.x 조합이 kanosawa CFA 모델에 필요.
> PyTorch 2.x + numpy 2.x는 호환성 이슈 있음.

### 3. 모델 가중치 (자동 다운로드 안 됨, 한 번만)

```bash
cd experiments/anime_face_detector/kanosawa_repo
gdown "https://drive.google.com/uc?id=1NckKw7elDjQTllRxttO87WY7cnQwdMqz" \
      -O checkpoint_landmark_191116.pth.tar
wget https://raw.githubusercontent.com/nagadomi/lbpcascade_animeface/master/lbpcascade_animeface.xml
```

(이 파일들은 이미 디렉토리에 다운받혀 있음)

---

## 시스템 설계 — 4 단계

### Stage 1. 정면 렌더 (Blender headless)
- `render_front.py`: GLB/VRM → 정면 512×512 PNG
- 자동 추정: 얼굴 z = bbox top - height × 0.18
- 회색 배경 + soft light (burn-out 방지)

### Stage 2. 측정값 추출 (kanosawa + HSV)
- `extract_landmarks.py`: lbpcascade로 face bbox → CFA 24 landmark
  - cascade 실패 시 점진적 완화(sf=1.05→1.2) 후 center fallback
- `measure_face.py`: 25 metrics
  - **눈/눈썹 (10 + 5)**: landmark 거리·각도 정규화
  - **입 (3 metrics)**: HSV 색상 (H<15 ∪ H>165, S>60) segmentation
  - **얼굴 윤곽 (3)**: face_left/chin/right
- 모든 metric은 **face_width로 정규화** → 카메라 거리·해상도 무관

### Stage 3. 매핑 (단방향)
- `compute_sliders.py`: 29개 블렌드쉐입 키 정의
- 매핑 모드 2종:
  - **`ratio`**: `(user - baseline) / baseline` → 비율 변화
  - **`abs`**: `|user| - |baseline|` → 절대 변화 (각도, 회전)
- `max_change_ratio` 키별 튜닝 가능 (default 0.30)
- **단방향 (양의 방향만 변형)**: user ≤ baseline → 슬라이더 0

### Stage 4. 적용 + 렌더 (Blender headless)
- `apply_sliders.py`: VRM import → Face mesh shape_keys 설정 → 정면 렌더
- 누락 키는 안전하게 무시 + 경고

---

## 측정 가능 / 불가능 매트릭스

| 카테고리 | 키 | 자동 추출 |
|---|---|---|
| **Eye 자동 (5/14)** | Eye_Width, Eye_WidthV, Eye_Dist, Eye_Height, Eye_Rot | ✅ |
| Eye 미지원 (9/14) | Pupil*, Eye_FrontHeight, Eye_FrontFlat, Eye_TailHeight, Eye_TopLid*, Eye_LowerLid* | ❌ Phase 2 |
| **Brow 자동 (4/5)** | Brow_Width, Brow_Dist, Brow_Height, Brow_Rot | ✅ |
| Brow 미지원 (1/5) | Brow_WidthV (눈썹 두께) | ❌ |
| **Mouth 자동 (3/3)** | Mouth_Width, Mouth_Height, Mouth_Corner | ✅ (HSV 색상 사용) |
| **Nose 미지원 (3/3)** | Nose_Height, Nose_Width, Nose_UnderNose | ❌ 측면 렌더 필요 |
| **Face 미지원 (4/4)** | Face_JawLine, Cheek, Roundness, ChinWidth | ❌ 윤곽선 분석 필요 |

→ **자동 12개 키 / 미지원 17개 키** (29개 중)

---

## PoC 검증 결과

### 입력 vs 마스터 측정 비교 (예: VARCO anime girl)

| 측정 | Master | VARCO | 슬라이더 산출 |
|---|---|---|---|
| eye_width | 0.233 | 0.284 | Eye_Width = **0.731** |
| eye_widthV | 0.192 | 0.207 | Eye_WidthV = **0.256** |
| eye_rot_deg | 0° | −9.3° | Eye_Rot = **0.622** |
| brow_width | 0.236 | 0.263 | Brow_Width = **0.389** |
| brow_y_norm | 0.006 | 0.052 | Brow_Height = **1.000** |
| brow_rot_deg | −1.2° | −6.5° | Brow_Rot = **0.352** |
| lip_width_norm | 0.814 | 0.979 | Mouth_Width = **0.675** |
| mouth_y_norm | 0.747 | 0.875 | Mouth_Height = **0.858** |
| eye_dist | 0.415 | 0.310 | Eye_Dist = 0 (단방향) |

**8개 active sliders.** 베이스 메시에 적용 시 시각적으로 의미 있는 변형 확인 (눈 커짐, 눈꼬리·눈썹 변화).

---

## 트러블슈팅

| 증상 | 해결 |
|---|---|
| `Cascade 0 faces detected` | 카메라 너무 closeup → `--cam-dist 0.7`로 늘림. 또는 fallback bbox 자동 사용됨 |
| `Numpy is not available` | numpy 2.x 설치됨 → `pip install "numpy<2"` 다운그레이드 |
| `mmcv-full build failed` | 우리는 mmcv 안 씀 (kanosawa는 PyTorch only) |
| `import_scene.vrm not found` | Blender Add-on 메뉴에서 VRM Add-on 활성화 |
| 얼굴이 화면 밖에 잘림 | `--lens 35`로 줄이거나 `--cam-dist` 늘림 |
| 슬라이더 적용 후 변화 없음 | sliders.json 모두 0인지 확인. `max_change_ratio` 0.15로 줄여 효과 강화 |

---

## 다음 단계

| Phase | 작업 |
|---|---|
| **Phase 2-A** | Nose/Face 측정 추가 (측면 렌더 + 윤곽선 분석) |
| **Phase 2-B** | 양방향 매핑 — 마스터에 *_Minus blendshape 추가 (이현지님 작업) |
| **Phase 2-C** | Three.js 포팅 — `morphTargetInfluences`로 직접 적용 (백승우님) |
| **Phase 2-D** | Pupil 추출 (눈동자 영역 HSV로 segment) |
| **Phase 3** | anime-face-detector(28 landmark, 입꼬리 포함) Docker 환경에서 시도 → 정밀도 ↑ |
| **Phase 3** | 사용자 사진(2D) → 직접 적용 (3D 우회 가능) |

---

## 라이선스

- **kanosawa CFA model**: 별도 라이선스 명시 없음 — 본 PoC는 학술/연구용
- **lbpcascade_animeface**: MIT (nagadomi)
- **PyTorch / OpenCV / Blender**: BSD / Apache / GPL

production 사용 전 각 의존성의 SaaS 재배포 여부 확인 필요.

---

## 핵심 메시지

> **end-to-end 자동 적용이 PoC 단계에서 검증됨.** 입력 anime 캐릭터의 눈/눈썹/입 특징이 마스터 모델의 12개 블렌드쉐입에 자동 반영됨. 코·턱선 같은 7개는 추가 작업 필요하지만 인프라 자체는 완성.

> **재현성:** `run_pipeline.sh <input> <master> <output>` 한 줄로 끝.

> **확장성:** 새 입력 GLB가 들어와도 같은 명령으로 처리. 마스터 변경 시 `REGEN_BASELINE=1`로 baseline 재측정.
