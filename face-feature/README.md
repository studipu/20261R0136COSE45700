# face-feature

입력 이미지 한 장에서 VRM 아바타 슬라이더 파라미터 29개를 자동 추출하는 파이프라인.

---

## 환경 설정

### 1. `.env` 파일 생성

```
VARCO_API_KEY=your_api_key_here
ADF_SERVER_URL=http://127.0.0.1:8000
```

### 2. ADF 서버 실행 (WSL 필수)

파이프라인 실행 전 WSL 터미널에서 먼저 실행:

```bash
python tools/anime_bbox.py --http-server --host 127.0.0.1 --port 8000
```

`ready` 메시지가 뜨면 준비 완료. 서버는 실행 중 유지해야 함.

> `ADF_SERVER_URL`은 각자 로컬(`127.0.0.1`)이므로 팀원 모두 직접 실행해야 함.

---

## 실행 방법

### 단일 이미지 전체 파이프라인

```bash
python main.py run --image input_image/01_original.png
```

### 배치 처리 (여러 이미지)

```bash
python main.py batch-run --images input_image/
```

- GLB가 이미 있으면 Stage 2 (3D 생성) 스킵
- front/left/right.png가 이미 있으면 Stage 3 (렌더링) 스킵
- Stage 4 이후 (특징 추출 → 템플릿 → 슬라이더) 재실행

### 특징 추출만

```bash
python main.py extract --image input_image/01_original.png
```

### 랜드마크 시각화

```bash
python main.py debug --image input_image/01_original.png
```

---

## 파이프라인 단계

| 단계 | 내용 | 출력 |
|---|---|---|
| Stage 2 | 2D → 3D 변환 (VARCO API) | `avatar.glb` |
| Stage 3 | GLB 렌더링 (pyrender) | `front/left/right.png`, `*_depth.npy` |
| Stage 4 | 얼굴 특징 추출 (ADF + OpenCV) | avatar keys 29개 |
| Stage 5 | 템플릿 선택 | cute / slim / mature |
| Stage 6 | 슬라이더 초기값 매핑 | `slider_init` |

결과: `output/{이미지명}/pipeline_result.json`

---

## 캘리브레이션

avatar key의 lo/hi 범위를 전체 데이터셋 기준으로 재계산:

```bash
python tools/calibrate_keys.py
```

결과 확인 후 `pipeline/avatar_keys.py`의 `SIGNED_CALIBRATION` / `MAP01_CALIBRATION` 업데이트.

---

## 출력 구조

```
output/
└── 01_original/
    ├── avatar.glb
    ├── renders/
    │   ├── front.png
    │   ├── left.png
    │   ├── right.png
    │   └── *_depth.npy
    └── pipeline_result.json
```

---

## 관련 문서

- [PIPELINE_DOC.md](PIPELINE_DOC.md) — 전체 기술 문서 (avatar key 공식, 구조 설명)
