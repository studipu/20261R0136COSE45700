# Virtual Avatar Pipeline — 기술 문서

> 작성일: 2026-05-18  
> 대상: 팀원 전체 (프론트엔드 포함)  
> 브랜치: `update/feature-extractor` (Soob00/20261R0136COSE45700)

---

## 1. 전체 파이프라인 개요

입력 이미지 한 장에서 VRM 아바타 슬라이더 파라미터 29개를 자동 추출하는 시스템.

```
[입력 이미지]
     │
     ▼
Stage 2 ─── 2D → 3D 변환 (VARCO / Meshy API)
     │         → avatar.glb
     ▼
Stage 3 ─── GLB 멀티뷰 렌더링 (pyrender)
     │         → front.png / left.png / right.png / quarter.png
     │         → front_depth.npy / left_depth.npy / right_depth.npy
     ▼
Stage 4 ─── 얼굴 특징 추출
     │         → ADF 28pt 랜드마크 검출
     │         → OpenCV 눈동자(홍채) 검출
     │         → depth map 기반 코 돌출도 / 광대 계산
     │         → Avatar Key 29개 계산
     ▼
Stage 5 ─── 템플릿 선택 (코사인 유사도)
     │         → cute / slim / mature 중 1개
     ▼
Stage 6 ─── 슬라이더 초기값 매핑
               → slider_init 9개 (UI용)

[출력: pipeline_result.json]
```

---

## 2. 사용 모델 및 라이브러리

| 역할 | 모델 / 라이브러리 | 실행 환경 |
|------|------------------|-----------|
| 2D → 3D 변환 | VARCO Art API 또는 Meshy API | HTTP (외부 서비스) |
| 3D 렌더링 | pyrender + trimesh | Windows: pyglet 백엔드 / Linux: EGL 백엔드 (`PYOPENGL_PLATFORM=egl`) |
| 얼굴 랜드마크 | hysts/anime-face-detector (ADF) | WSL Ubuntu subprocess 또는 HTTP 서버 |
| 눈동자 검출 | OpenCV HoughCircles + contour fallback | 로컬 Python |
| 템플릿 선택 | 코사인 유사도 (numpy) | 로컬 Python |

### ADF (anime-face-detector) 실행 방식

ADF는 Windows에서 직접 실행이 불가해 두 가지 방식 지원:

```
방식 1 (기본): WSL Ubuntu subprocess
  → WSL 안에 miniconda 환경 'anime-detector' 설치 필요
  → adf_client.py가 persistent subprocess로 실행 유지

방식 2: HTTP 서버
  → 환경 변수 ADF_SERVER_URL 설정 시 자동 전환
  → 별도 서버에서 anime_bbox.py --server 실행 필요
```

환경 변수:
```
ADF_SERVER_URL   HTTP 서버 URL (설정 시 WSL 대신 HTTP 사용)
ADF_WSL_HOME     WSL 홈 디렉토리 override
ADF_WSL_PYTHON   WSL 내 Python 경로 override
ADF_WSL_SCRIPT   WSL 내 anime_bbox.py 경로 override
```

---

## 3. Python 파일별 역할

```
pipeline/
├── __init__.py           공개 API (run_pipeline, extract_features, FaceFeatureVector)
├── pipeline.py           Stage 2~6 오케스트레이션
├── adf_client.py         ADF WSL/HTTP 통신 레이어
├── geometry.py           순수 수학 헬퍼 + depth 샘플링 함수
├── avatar_keys.py        ADF 랜드마크 → Avatar Key 29개 계산
├── feature_extractor.py  FaceFeatureVector 추출 + 공개 API
├── pupil_detector.py     OpenCV 눈동자 검출 + 파이프라인 진입점
├── renderer.py           pyrender GLB 멀티뷰 렌더링
├── template_selector.py  코사인 유사도 템플릿 선택 + 슬라이더 매핑
├── parameter_specs.py    29개 Key 메타데이터 + apply_specs()
└── varco_client.py       VARCO / Meshy API 클라이언트

tools/
└── pupil_vis.py          눈동자 검출 시각화 스크립트 (디버그용)

main.py                   CLI 진입점
```

### 각 파일 상세

#### `pipeline.py`
Stage 2~6을 순서대로 호출하는 오케스트레이터.  
Stage 4 실패 시 `status: "failed_stage4"` JSON 반환.  
front_render 기준 depth 파일(str path)을 `_stage4_extract`에 전달해 depth override 보장.

#### `adf_client.py`
ADF와의 통신 전담. WSL subprocess를 persistent하게 유지해 매 호출마다 재시작하지 않음.  
`query_adf(img_path, img_bgr)` → `(bbox, kps)` 반환.  
`ADF_KP_GROUPS`: 28pt → 의미 그룹 딕셔너리.

#### `geometry.py`
계산에서 반복되는 순수 수학 함수들. 다른 모듈에 의존성 없음.  
- `_map_signed(x, lo, hi)`: x를 [-1, 1]로 정규화
- `_map_01(x, lo, hi)`: x를 [0, 1]로 정규화
- `_angle_at(a, b, c)`: 꼭짓점 b에서의 각도 (도)
- `_lid_flatness(...)`: 눈꺼풀 평탄도
- `_sample_depth(depth, cx, cy)`: depth map에서 원형 영역 중앙값
- `_compute_depth_features(...)`: front depth → 코 돌출도
- `_compute_cheek_from_side(...)`: side depth → 광대 돌출도

#### `avatar_keys.py`
ADF 28pt 랜드마크 → 29개 Avatar Key 계산의 핵심 파일.  
`compute_avatar_keys(kps, manual, _raw_out, depth, img_shape)` 단일 함수.  
`_raw_out` dict를 넘기면 정규화 전 raw 측정값도 기록됨.

#### `feature_extractor.py`
`FaceFeatureVector` dataclass 정의 + ADF 실행 + `_compute_features()`.  
`FaceFeatureVector`: 26개 얼굴 비율 특징 (template_selector용 코사인 유사도 입력).  
`extract_features_full()`: ADF 실행 → FaceFeatureVector + avatar_keys 반환.

#### `pupil_detector.py`
파이프라인의 실제 Stage 4 진입점.  
`extract_features_with_pupils()`: ADF + OpenCV 눈동자 검출을 한 번에 실행.  
`detect_pupils(img_bgr, kps)`: 양쪽 눈 ROI crop → HoughCircles → contour → bbox 중심 순 fallback.

#### `renderer.py`
GLB → 4방향 렌더 이미지 + depth map 저장.  
렌더 방향: front(0°) / left(90°) / right(-90°) / quarter(45°).  
depth 파일: `{view}_depth.npy`, `{view}_depth.png`, `{view}_mask.png` 동시 저장.

#### `template_selector.py`
`FaceFeatureVector` → 코사인 유사도로 cute/slim/mature 선택.  
`_TEMPLATE_REFS`: **현재 placeholder 값** — 실제 VRoid 템플릿 렌더 후 교체 필요.  
`slider_init`: 9개 UI 슬라이더 초기값 (0~1).

#### `parameter_specs.py`
29개 Avatar Key의 메타데이터 중앙 정의.  
`apply_specs(avatar_keys, raw)`: 값 클리핑 + `parameter_debug` 딕셔너리 생성.  
`parameter_debug`에는 key별 `value`, `raw`, `source`, `range`, `enabled`, `clipped`, `description` 포함.

---

## 4. ADF 28점 랜드마크 배치

```
인덱스  그룹          설명
0~4    face_contour  얼굴 외곽 (좌끝, 좌턱, 턱끝, 우턱, 우끝)
5~7    right_brow    오른쪽 눈썹 (outer→inner, 이미지 기준 좌→우)
8~10   left_brow     왼쪽 눈썹 (inner→outer)
11~16  right_eye     오른쪽 눈 upper(11,12,13) + lower(14,15,16)
17~22  left_eye      왼쪽 눈 upper(17,18,19) + lower(20,21,22)
23     nose          코 끝
24~27  mouth         [좌 corner, 상단 center, 우 corner, 하단 center]
```

이미지 좌표계: x → 오른쪽, y → 아래쪽 (OpenCV 표준).

---

## 5. Avatar Key 29개 — 계산 방식 및 상태

> **범례**  
> ✅ 실측 — ADF/depth/OpenCV로 직접 측정  
> 🔶 파생 실측 — 실측값 조합 composite  
> 🟡 조건부 실측 — 특정 조건(depth 존재 등)일 때만 실측  
> ⚠️ Proxy — 근사치, 정확도 제한  
> ❌ 기본값 — ADF 구조 한계로 측정 불가, 고정값

### 5-1. Eye 계열 (14개)

| Key | 범위 | 상태 | 계산식 | 비고 |
|-----|------|------|--------|------|
| Eye_Width | [-1, 1] | ✅ 실측 | `(R_eye_w + L_eye_w) / 2 / face_scale` → `_map_signed(lo=0.228, hi=0.266)` | |
| Eye_WidthV | [-1, 1] | ✅ 실측 | `(R_eye_h + L_eye_h) / 2 / face_scale` → `_map_signed(lo=0.105, hi=0.226)` | "눈 세로 크기", 개안도와 구분 필요 |
| Eye_Height | [-1, 1] | ✅ 실측 | `(face_mid_y - eye_center_y) / face_scale` → `_map_signed(lo=0.263, hi=0.319)` | 재보정 권장 (클립 잦음) |
| Eye_Dist | [-1, 1] | ✅ 실측 | `inner_corner_dist / face_scale` → `_map_signed(lo=0.347, hi=0.393)` | |
| Eye_Rot | [-1, 1] | ✅ 실측 | `avg((R_outer_y - R_inner_y)/R_w, (L_outer_y - L_inner_y)/L_w) / 0.35` | 양쪽 outer-inner 기준 통일 (부호 상쇄 버그 수정됨) |
| Eye_FrontHeight | [-1, 1] | ✅ 실측 | `avg((eye_mid_y - inner_y)/eye_h)` → `_map_signed(lo=-0.135, hi=0.070)` | |
| Eye_FrontFlat | [0, 1] | ✅ 실측 | inner half 꼭짓점 각도 → `_map_01(lo=40.5°, hi=83.5°)` | |
| Eye_TailHeight | [-1, 1] | ✅ 실측 | `avg((eye_mid_y - outer_y)/eye_h)` → `_map_signed(lo=-0.070, hi=0.135)` | |
| Eye_TopLidFlat | [0, 1] | ✅ 실측 | upper 3점 기준 lid 평탄도 (`_lid_flatness`) | |
| Eye_LowerLidFlat | [0, 1] | ✅ 실측 | lower 3점 기준 lid 평탄도 | |
| Eye_TopLidDown | [0, 1] | ❌ 기본값 0 | 수식은 있으나 애니 눈 wide-open → 항상 0 클램핑 | 눈꺼풀 처짐은 ADF 3pt로 불가 |
| Eye_LowerLidUp | [0, 1] | ❌ 기본값 0 | Eye_TopLidDown과 동일값 | |
| Eye_PupilWidth | [-1, 1] | ⚠️ Proxy | HoughCircles `2r / eye_w` → `_map_signed(lo=0.25, hi=0.80)` | 중심은 신뢰 가능, 반지름 r은 부정확 |
| Eye_PupilWidthV | [-1, 1] | ⚠️ Proxy | HoughCircles `2r / eye_h` → 애니 눈 eye_h 작아서 항상 1.0 클리핑 | 동일 원인, 수식 개선 필요 |

### 5-2. Brow 계열 (5개)

| Key | 범위 | 상태 | 계산식 | 비고 |
|-----|------|------|--------|------|
| Brow_Dist | [-1, 1] | ✅ 실측 | `inner_brow_dist / face_scale` → `_map_signed(lo=0.258, hi=0.445)` | |
| Brow_Height | [-1, 1] | ✅ 실측 | `avg(eye_top_y - brow_mid_y) / face_scale` → `_map_signed(lo=0.208, hi=0.361)` | 머리카락이 가리면 불안정 |
| Brow_Rot | [-1, 1] | ✅ 실측 | `avg((outer_y - inner_y)/brow_w) / 0.50` | Eye_Rot과 동일한 방향 기준 통일 적용 |
| Brow_Width | [-1, 1] | ✅ 실측 | `avg_brow_w / face_scale` → `_map_signed(lo=0.206, hi=0.371)` | 재보정 권장 (상한 근처 자주 붙음) |
| Brow_WidthV | [-1, 1] | ❌ 기본값 0 | ADF 3점으로 두께 측정 불가 | |

### 5-3. Nose 계열 (3개)

| Key | 범위 | 상태 | 계산식 | 비고 |
|-----|------|------|--------|------|
| Nose_Height | [-1, 1] | 🟡 조건부 실측 | **depth 있으면**: `(d_side - d_nose) / d_side` → `_map_signed(lo=0.02, hi=0.11)` / **없으면**: `(nose_tip_y - eye_y) / (mouth_y - eye_y)` → `_map_signed(lo=0.448, hi=0.583)` | parameter_debug의 raw로 어떤 방식인지 확인 가능 |
| Nose_Width | [0, 1] | ❌ 기본값 0.5 | ADF에 콧볼 랜드마크 없음 | |
| Nose_UnderNose | [-1, 1] | ✅ 실측 | `(mouth_top_y - nose_tip_y) / face_scale` → `_map_signed(lo=0.129, hi=0.192)` | 재보정 권장 |

### 5-4. Mouth 계열 (3개)

| Key | 범위 | 상태 | 계산식 | 비고 |
|-----|------|------|--------|------|
| Mouth_Width | [-1, 1] | ✅ 실측 | `mouth_corner_dist / face_scale` → `_map_signed(lo=0.217, hi=0.314)` | |
| Mouth_Height | [-1, 1] | ✅ 실측 | 입 중심 y 위치 (세로 두께 아님) → `_map_signed(lo=0.296, hi=0.375)` | "mouth vertical position" |
| Mouth_Corner | [-1, 1] | ✅ 실측 | `(mouth_center_y - corner_avg_y) / face_scale` → `_map_signed(lo=0.010, hi=0.059)` | |

### 5-5. Face 계열 (4개)

| Key | 범위 | 상태 | 계산식 | 비고 |
|-----|------|------|--------|------|
| Face_JawLine | [0, 1] | 🔶 파생 실측 | `0.5×angle_score + 0.3×width_score + 0.2×depth_score` | chin_angle(60~130°), chin_width_ratio(0.25~0.55), chin_depth_ratio(0.08~0.25) |
| Face_Cheek | [0, 1] | 🟡 조건부 실측 | **side depth 있으면**: `row_spread(cheek_y) / row_spread(brow_y) - 1` → `_map_01(lo=0.25, hi=0.80)` / **없으면**: 0.0 (source: unavailable) | parameter_debug.source로 확인 |
| Face_Roundness | [0, 1] | 🔶 파생 실측 | `0.45×wh_score + 0.35×chin_angle_score + 0.20×chin_depth_score` | parameter_debug에 3개 컴포넌트 별도 저장 |
| Face_ChinWidth | [0, 1] | ✅ 실측 | `jaw_width / face_width` → `_map_01(lo=0.713, hi=0.771)` | |

---

## 6. 정규화 방식

모든 Key는 26장 이미지에서 측정한 5th~95th percentile을 `lo/hi` 기준으로 사용.

```python
# [-1, 1] 범위 (양방향 특징)
_map_signed(x, lo, hi) = clip(2 * (x - lo) / (hi - lo) - 1, -1, 1)

# [0, 1] 범위 (단방향 특징)
_map_01(x, lo, hi)     = clip((x - lo) / (hi - lo), 0, 1)
```

`face_scale = 0.75 × face_width + 0.25 × lower_face_height`  
(얼굴 가로세로 비율을 함께 반영한 복합 기준)

---

## 7. 눈동자 검출 상세 (OpenCV)

OpenCV의 목적은 **눈동자 중심(center) 검출**이며, 반지름(r)은 부가 정보로만 사용됨.

```
eye ROI crop (pad=0.5)
     │
     ▼
CLAHE 전처리 (clipLimit=3.0, tileGrid=4×4)
     │
     ├─ 1차: GaussianBlur(3×3) → HoughCircles
     │         → 중심(cx, cy)은 신뢰 가능
     │         → 반지름 r은 anime 눈에서 부정확 (eye_h 대비 과대추정)
     │
     ├─ 2차 (HoughCircles 실패): Otsu 이진화 → 어두운 영역 contour centroid
     │         eye bbox 안에서 가장 큰 어두운 영역의 무게중심
     │
     └─ 3차 (fallback): eye bbox 중심 사용

결과: center (신뢰) + left/right/top/bottom (center ± r, 반지름 부정확)
```

검출 결과 → `manual` dict 형태로 `compute_avatar_keys()`에 전달:  
`{R_PL, R_PR, R_PT, R_PB, L_PL, L_PR, L_PT, L_PB}`  

> **주의**: PL/PR/PT/PB 모두 `center ± r`로 생성되므로 Eye_PupilWidth/V는  
> 중심 정확도와 무관하게 반지름 r의 품질에 의존함 → 현재 둘 다 Proxy.

---

## 8. 출력 JSON 구조 (`pipeline_result.json`)

```jsonc
{
  "status": "ok",                    // "ok" | "failed_stage4"
  "glb_path": "...",
  "renders": {
    "front": "output/renders/front.png",
    "left":  "...", "right": "...", "quarter": "..."
  },
  "feature_vector": { ... },         // FaceFeatureVector 26개 (template_selector 입력)
  "feature_source": "front_render",  // "front_render" | "original"
  "feature_debug": { ... },          // ADF 시도 기록
  "avatar_parameters": {             // Avatar Key 29개 최종값
    "Eye_Width": -0.007, ...
  },
  "parameter_debug": {               // Key별 메타데이터
    "Eye_Width": {
      "value": -0.007,               // 최종값 (클리핑 후)
      "raw": 0.247,                  // 정규화 전 측정값
      "source": "FaceFeatureVector", // 측정 출처
      "range": [-1.0, 1.0],
      "enabled": true,
      "clipped": false,
      "description": "Horizontal eye width (avg eye_w / face_w)."
    },
    "Face_Roundness": {
      "value": 0.674, "raw": 0.674,
      "width_height": 0.931,         // 컴포넌트별 기여 (튜닝용)
      "chin_angle": 0.655,
      "chin_depth": 0.127,
      ...
    },
    "Face_Cheek": {
      "source": "unavailable",       // side depth 없을 때
      "value": 0.0, ...
    }
  },
  "template": "slim",
  "confidence": 0.880,
  "all_scores": { "cute": 0.880, "slim": 0.880, "mature": 0.874 },
  "slider_init": {                   // UI 슬라이더 초기값 9개
    "eye_size": 1.0, "face_round": 0.42, ...
  }
}
```

---

## 9. 실행 방법

### 전체 파이프라인

```bash
python main.py run \
  --image input_image/01_original.png \
  --provider meshy \
  --api-key YOUR_KEY
```

### Stage 3~6만 (GLB 기존 것 사용)

```bash
python main.py run \
  --image input_image/01_original.png \
  --skip-3d \
  --glb output/avatar.glb
```

### 눈동자 검출 시각화

```bash
python tools/pupil_vis.py input_image/01_original.png
```

### Linux 서버에서 실행 (EGL 백엔드)

```bash
PYOPENGL_PLATFORM=egl python main.py run ...
```

---

## 10. 현재 한계점

| 항목 | 문제 | 원인 |
|------|------|------|
| Eye_PupilWidth / Eye_PupilWidthV | Width는 불안정, WidthV는 항상 1.0 | OpenCV로 눈동자 **중심**은 신뢰할 수 있으나 **크기(반지름)**는 HoughCircles 특성상 애니 눈에서 부정확. `2r / eye_h`는 eye_h가 매우 작아 항상 클리핑. |
| Eye_TopLidDown / Eye_LowerLidUp | 항상 0 | 애니 캐릭터 눈이 wide-open → `(0.35 - opening)/0.25` 항상 ≤ 0 |
| Nose_Width | 항상 0.5 | ADF 28pt에 콧볼 랜드마크 없음 |
| Brow_WidthV | 항상 0 | ADF 3점 랜드마크로 눈썹 두께 불가 |
| Face_Cheek | side depth 없으면 0.0 | 정면 렌더만으로 광대 돌출도 측정 불가 |
| 템플릿 레퍼런스 | placeholder 사용 중 | 실제 VRoid 3종 템플릿 렌더 후 교체 필요 |
| lo/hi 캘리브레이션 | 26장 기준 | 샘플 수 부족, 클리핑 잦은 key 존재 |
| ADF confidence | 조정 불가 | ADF 서버가 confidence threshold 파라미터 미지원 |

---

## 11. 향후 개선 과제

### 단기 (코드 변경으로 가능)

- [ ] **Eye_PupilWidth/V 수식 변경**  
  현재는 HoughCircles 반지름 r로 크기 추정 → 중심(center)은 정확하나 r은 불신뢰.  
  eye mask 내 dark region의 실제 x/y-span으로 교체하거나, iris 크기 자체를 별도 측정.

- [ ] **lo/hi 재보정**  
  50장 이상 이미지로 P5~P95 재측정 필요 대상: `Eye_Height`, `Brow_Width`, `Nose_UnderNose`

- [ ] **템플릿 레퍼런스 교체**  
  `template_selector.py`의 `_TEMPLATE_REFS`를 실제 VRoid 렌더 결과로 갱신

### 중기 (설계 변경 필요)

- [ ] **Eye_PupilWidth/V HoughCircles 경로 debug 추가**  
  1차(Hough) / 2차(contour) / 3차(fallback) 중 어느 경로로 검출됐는지 `raw`에 기록

- [ ] **Nose_Height depth source 표시**  
  parameter_debug에 `"depth"` vs `"2d_fallback"` 구분 필드 추가

### 장기 (추가 모델 필요)

- [ ] **Eye_TopLidDown / LowerLidUp 실측화**  
  iris occlusion 비율 또는 pixel segmentation 기반 눈꺼풀 처짐 검출

- [ ] **Brow_WidthV 실측화**  
  brow 영역 pixel mask로 두께 추정

- [ ] **Nose_Width 실측화**  
  3D geometry에서 콧볼 너비 직접 추출

- [ ] **템플릿 3종 → 더 세분화**  
  현재 cute/slim/mature 3종에서 더 다양한 스타일로 확장

---

## 12. 파일 의존성 요약

```
pipeline.py
  ├── pupil_detector.py  ← 파이프라인 Stage 4 진입점
  │     ├── feature_extractor.py  (ADF 실행, FaceFeatureVector)
  │     │     ├── adf_client.py   (WSL/HTTP 통신)
  │     │     └── geometry.py     (수학 헬퍼)
  │     ├── avatar_keys.py        (29개 Key 계산)
  │     │     └── geometry.py
  │     └── geometry.py
  ├── renderer.py         (Stage 3)
  ├── template_selector.py (Stage 5-6)
  ├── parameter_specs.py  (apply_specs, Key 메타데이터)
  └── varco_client.py     (Stage 2)
```
