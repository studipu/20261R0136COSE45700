# Mesh Editing AI 기술 현황 리서치

> 작성일: 2026-04-09
> 목적: 자연어 입력으로 3D 아바타를 편집하는 핵심 기술의 현재 수준, 한계, 실현 가능한 범위 정의
> 연관 문서: [브레인스토밍 67개 아이디어](../brainstorming/brainstorming-session-2026-04-09.md)

---

## A. 학계 주요 연구 (2024–2026)

### 핵심 논문 비교

| 연구 | 기관 | 발표 | 핵심 기술 | 아바타 적용성 | 한계 |
|------|------|------|----------|-------------|------|
| **MeshLLM** | Tsinghua 외 | ICCV 2025 | LLM으로 3D mesh를 직접 이해·생성. Primitive-Mesh 분해로 1500k+ 데이터셋 구축 | mesh 구조 이해에 강점, 편집보다 생성에 초점 | 정밀 편집 제한적, 컨텍스트 윈도우에 mesh 복잡도 제약 |
| **TeRA** | - | ICCV 2025 | SMPL-X 기반 latent diffusion → 텍스트→리얼리스틱 3D 아바타 생성. Gaussian Attribute Maps 활용 | 아바타 전용, pose/shape 분리 제어. **12초 생성** (RTX 3090) | SMPL-X topology에 종속, 의상/악세서리 표현 제한 |
| **HeadEvolver** | HKUST-GZ | IEEE 2025 | per-face Jacobian 기반 locally learnable mesh deformation. 템플릿→텍스트 가이드 변형 | **가장 유망** — blendshape, UV 보존하며 텍스트 편집 가능 | 머리/얼굴 한정, 템플릿 토폴로지 변경 불가 (뿔 추가 등 불가) |
| **TECA** | MPI / Black Lab | 3DV 2024 | 메시(얼굴/몸) + NeRF(헤어/악세서리) 하이브리드. SMPL-X fitting + SDS | 컴포지셔널 아바타 생성·편집, 파츠 간 전이 가능 | NeRF 부분 mesh 변환 필요, 경계면 아티팩트 |
| **ClipFace** | TU Munich | SIGGRAPH 2023 | CLIP 기반 FLAME 3DMM 텍스처+지오메트리 편집. 단일 forward pass | 표정·외형 텍스트 제어, 시간 변화 텍스처 지원 | FLAME 파라미터 공간에 제한, diffusion 대비 디테일 부족 |
| **AvatarStudio** | MPI | SIGGRAPH Asia 2023 (ACM TOG) | NeRF 기반 동적 헤드 아바타 텍스트 편집. VT-SDS 도입 | 동적 아바타 외형 변경, canonical space에서 전 프레임 전파 | NeRF 기반 → mesh 변환 추가 필요, SDS 최적화 느림 |
| **Instant3dit** | - | CVPR 2025 | 멀티뷰 인페인팅으로 3D 편집. **SDS 없이 ~3초** | mesh/NeRF/Gaussian Splat 모두 지원 | 이미지 조건 필요 (순수 텍스트 불가), 인페인팅 품질 의존 |

### 핵심 기술 패러다임

#### 1. SDS (Score Distillation Sampling) — 현재 주류

2D diffusion 모델의 지식을 3D로 증류하는 방식. 대부분의 텍스트 기반 3D 편집의 기반.

**고질적 문제:**
- 과도한 스무딩 (디테일 손실)
- Janus 문제 (다면체 아티팩트)
- 느린 속도 (수분~수십분)

**최신 개선 (2024–2025):**

| 방법 | 발표 | 핵심 혁신 | 속도 향상 |
|------|------|----------|----------|
| **DaCapo** | CVPR 2025 | Stacked diffusion bridge로 편집/보존 분리 | **15x** (2,500 steps) |
| **DreamCatalyst** | ICLR 2025 | SDS를 diffusion sampling dynamics에 정렬 | **8–23x** |
| **UDS** | ICML 2025 | 생성+편집 통합 gradient framework | 통합 효율화 |
| **SDS-Bridge** | NeurIPS 2024 | SDS를 diffusion bridge로 재정의 | 안정성 향상 |

**연구 방향:** SDS를 아예 대체하는 feed-forward 방식 (LRM, Native 3D Diffusion)이 부상 중.

#### 2. 파라메트릭 모델 기반 (SMPL-X / FLAME)

구조화된 인체/얼굴 mesh 위에서 파라미터를 조절하는 방식.

| 모델 | 용도 | 파라미터 | vertex 수 | 사용 논문 |
|------|------|---------|-----------|----------|
| **SMPL-X** | 전신 (몸+손+얼굴) | shape(β), pose(θ), expression | ~10,475 | TeRA, TECA, DreamWaltz-G |
| **FLAME** | 머리/얼굴 전용 | identity, expression, jaw/neck pose | ~5,023 | ClipFace, HeadEvolver |

**장점:** 빠르고 안정적 (실시간 가능), 리깅/blendshape와 자연스럽게 호환
**단점:** 파라미터 공간 밖의 표현 불가 (판타지 캐릭터, 극단적 변형 등)

**최근 트렌드:**
- GUAVA (ICCV 2025): SMPL-X 헤드를 FLAME으로 교체한 EHM 모델 제안
- DreamWaltz-G (TPAMI 2025): SMPL-X + FLAME + VPoser 통합 스켈레톤 가이드 아바타
- LLM → SMPL-X 파라미터 매핑: 초기 연구 단계, 학습 데이터 부족이 병목

#### 3. LLM 기반 Mesh 직접 처리

mesh를 텍스트 토큰으로 직렬화하여 LLM에 입력.

| 연구 | 접근 | mesh 표현 | 한계 |
|------|------|----------|------|
| **LLaMA-Mesh** (NVIDIA) | OBJ 포맷을 텍스트 토큰으로. LLaMA-3.1-8B fine-tune | vertex 좌표를 [0,64] 정수로 양자화 | 저해상도, 복잡한 mesh 불가 |
| **MeshLLM** | Primitive-Mesh 분해로 구조적 서브유닛 | 얼굴 연결성을 vertex에서 추론 | 오브젝트 수준, 아바타 미검증 |

**평가:** 이해(understanding)는 가능하나 정밀 편집(editing)은 초기 단계. 프로덕션 활용까지 1–2년 이상 필요.

#### 4. Native 3D 편집 (멀티뷰 우회)

| 연구 | 발표 | 접근 | 성능 |
|------|------|------|------|
| **Native 3D Editing** | Under Review (2025) | 3D 직접 조작, feed-forward. 추가/삭제/수정 태스크용 대규모 데이터셋 | 뷰 불일치 문제 해결 |
| **Masked LRM** | ICCV 2025 (Meta) | 조건부 LRM으로 마스크 영역 재구성. 단일 forward pass | **2–10x 빠름** (기존 대비) |
| **CraftsMan3D** | CVPR 2025 | 3D DiT + normal 기반 geometry refinement | 25초 생성, 편집은 인터랙티브 |

---

## B. 산업계 3D AI 플랫폼 현황 (2026)

### 플랫폼 비교

| 플랫폼 | 생성 | 편집 | 속도 | 가격 (엔트리) | 특징 |
|--------|------|------|------|-------------|------|
| **VARCO 3D** (NCSoft) | Text/Image→3D | 오브젝트 추가/제거, remesh, texture variation | ~3분 | 무료 (2,000크레딧/월) | CaPa 기술, 4K 텍스처, 애니메이션 지원 |
| **Meshy v6** | Text/Image→3D | AI 텍스처 편집 (지오메트리 불가) | ~25초 | 무료 (100크레딧/월) | Sculpting-level 디테일, 3D 프린팅 지원 |
| **Tripo v3.0** | Text/Image→3D | 토폴로지 선택 (quad/tri/low-poly) | ~10초 | 무료 (300크레딧/월) | 깨끗한 quad topology, 자동 애니메이션 |
| **3D AI Studio** | Text/Image→3D | retopology, remesh, mesh repair | 엔진별 상이 | $14/월 | 14+ 모델 통합 메타 플랫폼 |
| **Rodin Gen-2** (Hyper) | Text/Image→3D | 없음 | ~1-2분 | 무료 ($1.50/credit) | **10B 파라미터** 최고 품질, 4K 텍스처 |
| **SPAR3D** (Stability AI) | Image→3D만 | 포인트 클라우드 편집 (삭제/복사/변형/색변경) | **0.7초** | 무료 (오픈소스) | 최고 속도, 로컬 추론 가능 |
| **Hunyuan 3D 2.5** (Tencent) | Text/Image→3D | 없음 | 수초 | 무료 (오픈소스, Apache 2.0) | 10B 파라미터, 하루 20회 무료 |

### 핵심 발견

> **대부분의 플랫폼이 "생성"에만 집중. AI 기반 자연어 mesh 편집을 제공하는 플랫폼은 현재 없음.**
>
> 가장 가까운 상업적 기능:
> - VARCO 3D: 영역 보존하며 오브젝트 추가/제거 (부분 편집)
> - SPAR3D: 포인트 클라우드 레벨 실시간 편집 (mesh 전 단계)
> - Meshy / 3D AI Studio: 텍스처만 텍스트로 편집 (지오메트리 불변)
>
> **→ 자연어 기반 mesh 지오메트리 편집은 우리 서비스의 명확한 차별화 기회.**

---

## C. VARCO 3D 심층 분석

### 기반 기술 — CaPa (Carve-n-Paint)

[논문](https://arxiv.org/abs/2501.09433) | [GitHub](https://github.com/ncsoft/CaPa) | [프로젝트 페이지](https://ncsoft.github.io/CaPa/)

**2단계 파이프라인:**
1. **Carve (지오메트리 생성):** 3D latent diffusion model로 멀티뷰 일관성 보장. 깨끗한 mesh topology 생성
2. **Paint (텍스처 합성):** Spatially Decoupled Attention으로 4K 텍스처 생성. 3D-aware occlusion inpainting으로 가려진 영역 자동 채움

**현재 제공 기능:**
- Text-to-3D, Image-to-3D 생성
- 오브젝트 추가/제거 (특정 영역 보존)
- 조절 가능한 폴리곤 수 및 토폴로지
- PBR 재질 (다중 머티리얼 타입)
- 자동 리메시 (Plus/Premium)
- 애니메이션 지원 (NCSoft 게임 애니메이션 라이브러리 활용)
- OBJ/FBX/GLB 익스포트

**가격 체계:**
| 플랜 | 월 가격 | 크레딧/월 | 동시 생성 |
|------|--------|----------|----------|
| Free | 0 | 2,000 | 1 |
| Plus | ~22,000원 (~$16) | 10,000 | 5 |
| Premium | ~110,000원 (~$80) | 50,000 | 20 |

**API:** [api.varco.ai](https://api.varco.ai/) — Image-to-3D 등 생성 AI API 제공. 현재 한국어 중심, 상세 개발 문서는 제한적 접근.

### VARCO 3D에 없는 기능 (우리가 만들어야 할 것)

| 필요 기능 | 현재 상태 | 기술 접근 |
|----------|----------|----------|
| 자연어 기반 특정 부위 편집 ("코 작게", "머리 길게") | ❌ 미지원 | SMPL-X/FLAME 파라미터 매핑 (MVP) → HeadEvolver 방식 (Phase 2) |
| 레퍼런스 이미지 기반 스타일 트랜스퍼 | ❌ 미지원 | CLIP embedding → 스타일 유사도 매칭 |
| 실시간 편집 (< 1초 반응) | ❌ 배치 처리 | 파라메트릭 모델은 즉시 가능, SDS 기반은 DaCapo 등 필요 |
| 아바타 특화 편집 (blendshape/리깅 보존) | ❌ 미지원 | HeadEvolver의 Jacobian deformation 방식 적용 |
| 취향 학습 기반 자동 보정 | ❌ 미지원 | 편집 이력 기반 preference learning |

---

## D. 핵심 기술 격차 분석

### 현재 가능 vs 아직 어려운 것

```
현재 가능한 것:
├── 이미지/텍스트 → 3D 모델 생성          ✅  (VARCO, Meshy, Tripo 등)
├── 전체 스타일 변환                       ✅  (VARCO mesh variation)
├── 텍스처 편집                            ✅  (VARCO texture variation, Meshy AI texture)
├── 자동 리메시 / 토폴로지 최적화           ✅  (VARCO, 3D AI Studio, Tripo)
├── 포맷 변환 (VRM/FBX/GLB/USDZ)          ✅  (Tripo 7종, Rodin 5종)
└── 자동 애니메이션                         ✅  (Tripo auto-animation, VARCO)

아직 어려운 것:
├── 자연어 → 특정 부위 mesh 지오메트리 변형  ⚠️  (학계 연구 단계)
│   └── HeadEvolver: 얼굴만 가능, 전신 미지원
│   └── Instant3dit: 3초 편집 가능하나 이미지 조건 필요
├── 실시간 편집 (< 1초)                     ⚠️  (파라메트릭은 가능, SDS는 불가)
│   └── SPAR3D: 0.7초 가능하나 포인트클라우드 레벨
│   └── TeRA: 12초 생성, 편집은 별도
├── 편집 중 리깅/blendshape 보존             ⚠️  (HeadEvolver만 부분 해결)
│   └── 대부분 방법: 편집 후 리깅 재작업 필요
├── 레퍼런스 이미지 기반 부분 편집            ⚠️  (연구 초기)
│   └── Masked LRM: 이미지 조건 편집 가능하나 상용화 전
└── 프로덕션 레벨 안정성/일관성               ❌  (학계 데모 수준)
    └── 동일 프롬프트 → 동일 결과 보장 미흡
```

### 브레인스토밍 아이디어 기술 실현성 매핑

67개 아이디어를 기술 실현성 기준으로 분류:

**즉시 실현 가능 (기존 API/기술 활용):**
- #51 텍스트 생성, #52 스케치 생성 — VARCO/Meshy Text/Image-to-3D
- #16 VRM 익스포트 — 포맷 변환 파이프라인
- #57 스와이프 필터 UX — VARCO mesh variation + 프론트엔드
- #59 아바타 크기 스펙트럼 — mesh 자동 simplification
- #6 세이브/로드, #7 비교 뷰 — 순수 프론트엔드 기능
- #38 듀얼 과금 — 비즈니스 모델 설계

**MVP에서 파라메트릭 모델로 실현 가능 (3–6개월):**
- #1 레퍼런스 이미지 스타일 트랜스퍼 — CLIP embedding + 파라미터 매핑
- #2 하이브리드 입력 — 이미지 분석 + 자연어 파라미터 조정
- #4 스타일 강도 슬라이더 — 파라미터 보간
- #42 자동 미세 보정 — 대칭 교정, 텍스처 스무딩 자동화
- #49 성형외과 컨셉 — AI가 파라미터 기반 제안
- #53 터치 편집 — 터치 좌표 → 가장 가까운 파라미터 매핑

**Phase 2에서 실현 가능 (6–12개월):**
- #5 요소별 분리 적용 — 파츠별 독립 deformation
- #8 버전 간 부분 머지 — 파라메트릭 파츠 조합
- #15 실시간 mesh 변형 — DaCapo/HeadEvolver 최적화
- #17 표정 팩 자동 생성 — FLAME blendshape 자동 생성
- #18 의상 라이브러리 — cloth simulation + mesh fitting
- #43 음성 편집 — STT + 파라미터 매핑
- #60 시간축 변형 — aging/de-aging 파라미터

**장기 R&D 필요 (12개월+):**
- #41 취향 학습 엔진 — 편집 이력 기반 preference learning
- #65 원샷 완성 — 사용자별 최적 파라미터 예측
- #35 스타일 변환 엔진 — 크로스 플랫폼 mesh 변환
- #39 자기 진화 아바타 — 사용 패턴 학습

**기술 종속성 없음 (UX/비즈니스 설계):**
- #22-30 저작권/보안 시스템 — 3D feature vector DB + 유사도 비교
- #34 B2B API, #36 화이트라벨 — API 래핑
- #54 즉시 라이브 스트리밍 — VRM 파이프라인 자동화
- #9-14 크리에이터 기능 — 애니메이션/이벤트 시스템

---

## E. 실현 가능한 기술 전략

### 단기: MVP (3–6개월)

**핵심 접근: VARCO API + 파라메트릭 모델(SMPL-X/FLAME) 하이브리드**

```
사용자 입력                    처리                           출력
───────────                  ─────                         ─────
사진 업로드          →  VARCO Image-to-3D API    →  베이스 3D 모델
"코 작게 해줘"       →  LLM → nose_length -= 0.3  →  파라미터 변형된 모델
레퍼런스 이미지       →  CLIP embedding 추출       →  유사 스타일 파라미터 적용
```

**구현 스택:**
1. **생성:** VARCO Image-to-3D API (베이스 모델)
2. **편집:** SMPL-X/FLAME 파라미터 매핑
   - LLM이 자연어를 파라미터 값으로 변환
   - "코 작게" → `nose_length: -0.3`, "눈 크게" → `eye_scale: +0.2`
   - 실시간 반응 (< 1초) — 파라메트릭 변환은 GPU 불필요
3. **스타일:** VARCO mesh/texture variation으로 전체 스타일 변환
4. **보호:** 3D feature vector 기반 유사도 게이트

**장점:** 빠르고 안정적 (< 1초 반응), blendshape/리깅 보존 용이
**한계:** SMPL-X/FLAME 파라미터 공간에 제한 (판타지 캐릭터 불가)

### 중기: Phase 2 (6–12개월)

**핵심 접근: HeadEvolver 방식 + 빠른 SDS**

1. **HeadEvolver 적용:** per-face Jacobian 기반 locally learnable deformation
   - blendshape/UV 보존하며 텍스트 가이드 자유 변형
   - 얼굴 → 전신으로 확장 연구
2. **DaCapo/Instant3dit 통합:** 빠른 텍스처/지오메트리 편집
   - DaCapo: 15x 빠른 SDS (기존 수십분 → 수분)
   - Instant3dit: SDS 없이 ~3초 편집
3. **레퍼런스 이미지 편집:** CLIP embedding → 스타일 트랜스퍼
4. **파츠별 독립 편집:** 메시 세그멘테이션 + 독립 deformation

### 장기: Phase 3 (12개월+)

1. **MeshLLM 방식의 네이티브 mesh 이해·편집**
   - LLM이 mesh 토폴로지를 직접 이해하고 수정
   - Primitive-Mesh 분해로 복잡한 아바타도 처리
2. **실시간 GPU mesh 변형**
   - feed-forward 방식 (Masked LRM 등) 활용
   - 편집 latency < 0.5초 목표
3. **편집 히스토리 기반 취향 학습 엔진**
   - 사용자 수정 패턴 → preference model
   - 다음 아바타 생성 시 첫 결과물부터 취향 반영

---

## F. 기술 의사결정 근거

### MVP에서 파라메트릭 모델을 선택하는 이유

| 기준 | 파라메트릭 (SMPL-X/FLAME) | SDS 기반 | LLM 기반 |
|------|--------------------------|---------|---------|
| **속도** | < 1초 ✅ | 수분~수십분 ❌ | 수초 (저품질) ⚠️ |
| **안정성** | 동일 입력 → 동일 결과 ✅ | 확률적 변동 ❌ | 확률적 변동 ❌ |
| **리깅 보존** | 자연 호환 ✅ | 재작업 필요 ❌ | 미지원 ❌ |
| **blendshape 보존** | 자연 호환 ✅ | HeadEvolver만 ⚠️ | 미지원 ❌ |
| **표현 범위** | 파라미터 공간 내 ⚠️ | 자유 변형 ✅ | 저해상도 ❌ |
| **프로덕션 준비** | 즉시 가능 ✅ | 연구 단계 ❌ | 연구 초기 ❌ |

**결론:** MVP는 속도·안정성·리깅 호환이 핵심. 파라메트릭 모델이 유일한 현실적 선택.
Phase 2에서 HeadEvolver/DaCapo로 표현 범위를 점진 확장.

---

## Sources

### 학계 논문

| 연구 | arXiv / 공식 | GitHub |
|------|-------------|--------|
| MeshLLM | [arxiv.org/abs/2508.01242](https://arxiv.org/abs/2508.01242) | [github.com/Fangkang515/MeshLLM](https://github.com/Fangkang515/MeshLLM) |
| TeRA | [arxiv.org/abs/2509.02466](https://arxiv.org/abs/2509.02466) | [yanwen-w.github.io/TeRA-Page](https://yanwen-w.github.io/TeRA-Page/) |
| HeadEvolver | [arxiv.org/abs/2403.09326](https://arxiv.org/abs/2403.09326) | [duotun-wang.co.uk/HeadEvolver](https://www.duotun-wang.co.uk/HeadEvolver/) |
| TECA | [arxiv.org/abs/2309.07125](https://arxiv.org/abs/2309.07125) | [github.com/HaoZhang990127/TECA](https://github.com/HaoZhang990127/TECA) |
| ClipFace | [arxiv.org/abs/2212.01406](https://arxiv.org/abs/2212.01406) | [github.com/shivangi-aneja/ClipFace](https://github.com/shivangi-aneja/ClipFace) |
| AvatarStudio | [arxiv.org/abs/2306.00547](https://arxiv.org/abs/2306.00547) | [vcai.mpi-inf.mpg.de/projects/AvatarStudio](https://vcai.mpi-inf.mpg.de/projects/AvatarStudio/) |
| DaCapo | [CVPR 2025 Paper](https://openaccess.thecvf.com/content/CVPR2025/papers/Huang_DaCapo_Score_Distillation_as_Stacked_Bridge_for_Fast_and_High-quality_CVPR_2025_paper.pdf) | [sds-bridge.github.io](https://sds-bridge.github.io/) |
| UDS | [arxiv.org/abs/2505.01888](https://arxiv.org/abs/2505.01888) | [github.com/xingy038/UDS](https://github.com/xingy038/UDS) |
| LLaMA-Mesh | [arxiv.org/abs/2411.09595](https://arxiv.org/abs/2411.09595) | [github.com/nv-tlabs/LLaMA-Mesh](https://github.com/nv-tlabs/LLaMA-Mesh) |
| Instant3dit | [arxiv.org/abs/2412.00518](https://arxiv.org/abs/2412.00518) | [github.com/amirbarda/Instant3dit](https://github.com/amirbarda/Instant3dit) |
| Masked LRM | [arxiv.org/abs/2412.08641](https://arxiv.org/abs/2412.08641) | [chocolatebiscuit.github.io/MaskedLRM](https://chocolatebiscuit.github.io/MaskedLRM/) |
| CraftsMan3D | [arxiv.org/abs/2405.14979](https://arxiv.org/abs/2405.14979) | [github.com/HKUST-SAIL/CraftsMan3D](https://github.com/HKUST-SAIL/CraftsMan3D) |
| Native 3D Editing | [arxiv.org/abs/2511.17501](https://arxiv.org/abs/2511.17501) | - |
| DreamCatalyst | [arxiv.org/abs/2407.11394](https://arxiv.org/abs/2407.11394) | - |
| FaceG2E | [CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/html/Wu_Text-Guided_3D_Face_Synthesis_-_From_Generation_to_Editing_CVPR_2024_paper.html) | [github.com/JiejiangWu/FaceG2E](https://github.com/JiejiangWu/FaceG2E) |
| GaussianEditor | [arxiv.org/abs/2311.16037](https://arxiv.org/abs/2311.16037) | [github.com/buaacyw/GaussianEditor](https://github.com/buaacyw/GaussianEditor) |
| Text-Guided 3D Editing Survey | [Springer (2024)](https://link.springer.com/article/10.1007/s10462-024-10937-6) | - |

### 산업 플랫폼

| 플랫폼 | 공식 URL | 비고 |
|--------|---------|------|
| VARCO 3D | [3d.varco.ai](https://3d.varco.ai/) | CaPa: [ncsoft.github.io/CaPa](https://ncsoft.github.io/CaPa/) |
| VARCO API | [api.varco.ai](https://api.varco.ai/) | 개발자 플랫폼 |
| Meshy | [meshy.ai](https://www.meshy.ai/) | API: [docs.meshy.ai](https://docs.meshy.ai/) |
| Tripo | [tripo3d.ai](https://www.tripo3d.ai/) | API: [platform.tripo3d.ai](https://platform.tripo3d.ai/) |
| 3D AI Studio | [3daistudio.com](https://www.3daistudio.com/) | 메타 플랫폼 |
| Rodin (Hyper) | [hyper3d.ai](https://hyper3d.ai/) | API: [developer.hyper3d.ai](https://developer.hyper3d.ai/) |
| SPAR3D (Stability) | [stability.ai/news/stable-point-aware-3d](https://stability.ai/news/stable-point-aware-3d) | GitHub: [Stability-AI/stable-point-aware-3d](https://github.com/Stability-AI/stable-point-aware-3d) |
| Hunyuan 3D | [hunyuan-3d.com](https://hunyuan-3d.com/) | GitHub: [Tencent-Hunyuan/Hunyuan3D-2](https://github.com/Tencent-Hunyuan/Hunyuan3D-2) |

### 파라메트릭 모델

| 모델 | 공식 | 비고 |
|------|-----|------|
| SMPL-X | [smpl-x.is.tue.mpg.de](https://smpl-x.is.tue.mpg.de/) | MPI 제공 |
| FLAME | [flame.is.tue.mpg.de](https://flame.is.tue.mpg.de/) | MPI 제공 |
