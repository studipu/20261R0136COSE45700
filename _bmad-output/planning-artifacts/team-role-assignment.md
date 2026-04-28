# Virtual Avatar 프로젝트 — 5인 역할분담 상세안

**작성일:** 2026-04-16
**기준 문서:** PRD v2.0 (prd-restructured.md)
**팀 규모:** 5명
**개발 전략:** 3D 코어 우선 개발 → 프론트엔드 후속 진행

---

## 목차

1. [개발 전략 개요](#1-개발-전략-개요)
2. [팀원별 역할 총괄표](#2-팀원별-역할-총괄표)
3. [역할 1: 3D 템플릿 엔지니어 — 이현지, 조수빈, 최윤수](#3-역할-1-3d-템플릿-엔지니어--이현지-조수빈-최윤수)
4. [역할 2: 3D 뷰어 엔지니어 — 백승우, 이현지](#4-역할-2-3d-뷰어-엔지니어--백승우-이현지)
5. [역할 3: 백엔드 엔지니어 — 장동윤](#5-역할-3-백엔드-엔지니어--장동윤)
6. [이현지 — 겸임 역할 상세](#6-이현지--겸임-역할-상세)

7. [Phase 2: 프론트엔드 전환 계획](#7-phase-2-프론트엔드-전환-계획)
8. [역할 간 의존성 맵](#8-역할-간-의존성-맵)
9. [협업 인터페이스 정의](#9-협업-인터페이스-정의)
10. [스프린트별 전체 간트](#10-스프린트별-전체-간트)

---

## 1. 개발 전략 개요

### 핵심 원칙: 3D 코어 우선 (3D-First)

본 프로젝트의 핵심 가치는 **3D 템플릿 편집 + 뷰어**이다. 이 기능이 동작하지 않으면 나머지 서비스(인증, 결제, UI)가 아무리 완성되어도 제품 가치가 없다. 따라서 다음 전략을 채택한다:

```
[Phase 1] 3D 코어 우선 개발 (전원 3D 집중 + 백엔드 1명 병행)
    │
    │  3D 템플릿 + 뷰어 + 편집기 코어 완성
    │  백엔드 파이프라인 기반 구축
    │
    ▼
[Phase 2] 프론트엔드 전환 (3D 안정화 후 인력 재배치)
    │
    │  3D 팀 일부 → 프론트엔드 전환
    │  서비스 UI, 결제, 어드민 구축
    │
    ▼
[Phase 3] 통합 & QA
```

### 왜 3D 우선인가?

| 근거 | 설명 |
|------|------|
| **최고 리스크** | 템플릿 품질, morph target 변형, VRM 호환성이 프로젝트 성패를 결정 |
| **기술 검증 필수** | VARCO→MediaPipe→슬라이더 매핑 정확도를 조기에 검증해야 함 |
| **병렬 불가** | 3D 에셋(템플릿)이 완성되어야 뷰어 개발이 가능 → 인력 집중이 효율적 |
| **프론트엔드는 후순위** | 3D 코어가 확정된 후 UI를 입히는 것이 재작업을 줄임 |

### 팀 구성 (5명)

| 이름 | Phase 1 역할 | Phase 2 역할 (전환 후) |
|------|-------------|---------------------|
| **이현지** | 3D 템플릿 + 3D 뷰어 (겸임) | 3D 유지보수 + 프론트엔드 3D 통합 |
| **조수빈** | 3D 템플릿 | 프론트엔드 전환 |
| **최윤수** | 3D 템플릿 | 프론트엔드 전환 |
| **백승우** | 3D 뷰어 | 프론트엔드 3D 편집기 UI |
| **장동윤** | 백엔드 | 백엔드 (계속) |

---

## 2. 팀원별 역할 총괄표

### Phase 1: 3D 코어 집중 단계

| 역할 | 담당자 | 인원 | 담당 파이프라인 | 핵심 책임 | 핵심 기술스택 |
|------|--------|------|--------------|----------|-------------|
| **3D 템플릿** | 이현지, 조수빈, 최윤수 | 3명 | Stage 2, 3, 9 | 템플릿 제작, morph target/bone scale 정의, Unity VRM 변환 | Blender, Unity, UniVRM, Docker |
| **3D 뷰어** | 백승우, 이현지 | 2명 | Stage 5, 6, 7 | Three.js 뷰어, 슬라이더↔3D 연동, 렌더링 최적화 | Three.js, R3F, @pixiv/three-vrm, Zustand |
| **백엔드** | 장동윤 | 1명 | Stage 1, 2, 4, 전체 API | NestJS API, BullMQ 파이프라인, MediaPipe 연동 | NestJS, BullMQ, Redis, PostgreSQL, Python |

> **이현지**는 3D 템플릿과 3D 뷰어를 겸임한다. 템플릿 에셋 제작 경험을 바탕으로 뷰어에서의 로드/렌더링 호환성을 직접 검증하는 브릿지 역할을 수행한다.

### 인원 배분 근거

| 영역 | 인원 | 근거 |
|------|------|------|
| 3D 템플릿 (3명) | 이현지, 조수빈, 최윤수 | cute/slim/mature 3종 동시 제작. 각 템플릿당 morph target 45-50개 + 헤어/의상 프리셋 + 블렌드셰이프. 작업량이 가장 많음 |
| 3D 뷰어 (2명) | 백승우, 이현지 | Three.js 뷰어 + 슬라이더 컨트롤러 + 렌더링 최적화. 이현지가 템플릿 제작 경험으로 에셋 호환성 보장 |
| 백엔드 (1명) | 장동윤 | Phase 1에서는 파이프라인 기반(API, 큐, DB)만 구축. 서비스 기능(결제, 인증)은 Phase 2에서 본격화 |

---

## 3. 역할 1: 3D 템플릿 엔지니어 — 이현지, 조수빈, 최윤수

### 담당 범위

- **파이프라인:** Stage 2 (VARCO GLB 참조 모델), Stage 3 (GLB 렌더링), Stage 9 (Unity VRM Export)
- **에셋:** cute/slim/mature 3종 표준 VTuber 템플릿, 프리셋 헤어/의상
- **서버:** Unity headless Docker 컨테이너

### 팀원별 분담

| 담당자 | 주요 담당 | 상세 |
|--------|----------|------|
| **이현지** | cute 템플릿 + 뷰어 브릿지 | cute 템플릿 제작 + Three.js 렌더링 호환성 검증 (뷰어 겸임) |
| **조수빈** | slim 템플릿 + 프리셋 | slim 템플릿 제작 + 헤어/의상 프리셋 제작 |
| **최윤수** | mature 템플릿 + Unity 파이프라인 | mature 템플릿 제작 + Unity headless VRM 변환 파이프라인 |

### 필수 기술스택

| 기술 | 용도 | 담당자 |
|------|------|--------|
| Blender | 베이스 메시 모델링, morph target 제작, 리깅 | 전원 |
| Unity + C# | headless VRM 변환 서버 | 최윤수 (메인), 이현지 (서포트) |
| UniVRM | VRM 0.x/1.0 변환, humanoid bone mapping | 최윤수 |
| Docker | Unity headless 컨테이너 빌드/배포 | 최윤수 |
| VRM 표준 | humanoid bone, blendshape, spring bone 물리 | 전원 |

### 스프린트별 업무

#### Sprint 0 (2주) — 핵심 기술 검증

| 업무 | 담당자 | 산출물 | 완료 기준 |
|------|--------|--------|----------|
| cute 베이스 메시 프로토타입 | 이현지 | `.blend` 파일 | 폴리곤 2-5만, 토폴로지 검증 |
| slim 베이스 메시 프로토타입 | 조수빈 | `.blend` 파일 | 폴리곤 2-5만, 토폴로지 검증 |
| mature 베이스 메시 프로토타입 | 최윤수 | `.blend` 파일 | 폴리곤 2-5만, 토폴로지 검증 |
| morph target 공통 명세 정의 | 전원 협업 | morph target 명세서 | 20-30개 정의, 3종 통일 |
| bone scale 공통 명세 정의 | 전원 협업 | bone scale 명세서 | 10-15개 정의, 3종 통일 |
| Unity headless VRM 변환 PoC | 최윤수 | Docker 이미지, VRM 파일 | UniVRM 서버사이드 변환 성공, < 60초 |

#### Phase 1-1 (4주) — 템플릿 프로덕션 완성

| 업무 | 담당자 | 산출물 | 완료 기준 |
|------|--------|--------|----------|
| cute 템플릿 프로덕션 완성 | 이현지 | GLB 파일 | morph target 45-50개, bone scale 10-15개 |
| slim 템플릿 프로덕션 완성 | 조수빈 | GLB 파일 | morph target 45-50개, bone scale 10-15개 |
| mature 템플릿 프로덕션 완성 | 최윤수 | GLB 파일 | morph target 45-50개, bone scale 10-15개 |
| 블렌드셰이프 매핑 (3종 공통) | 이현지 | 블렌드셰이프 JSON | blink/joy/angry/sad/neutral + viseme |
| material slot 정의 (3종 공통) | 조수빈 | material 명세서 | 피부색, 눈동자 색, 머리 색 슬롯 |
| 프리셋 헤어 제작 | 조수빈 | 에셋 파일 | 헤어 10종+ |
| 프리셋 의상 제작 | 조수빈 | 에셋 파일 | 의상 15종+ |
| Spring Bone 물리 설정 | 최윤수 | 물리 파라미터 JSON | 머리카락, 의상 자연스러운 흔들림 |
| Stage 3 headless 렌더러 | 최윤수 | 렌더 스크립트 | GLB → 정면/측면 2D, < 30초 |
| Three.js 호환성 검증 | 이현지 | 호환성 리포트 | 3종 모두 Three.js 정상 로드 (뷰어팀과 연동) |

#### Phase 1-2 (4주) — Unity headless + 품질 완성

| 업무 | 담당자 | 산출물 | 완료 기준 |
|------|--------|--------|----------|
| Unity headless Docker 컨테이너 | 최윤수 | Dockerfile | 안정적 빌드/배포 |
| 파라미터 JSON → VRM 자동 변환 | 최윤수 | 변환 파이프라인 | Stage 9 완전 자동화, < 60초 |
| 자동 리깅 + humanoid bone mapping | 최윤수 | 리깅 검증 리포트 | VRM 표준 완전 준수 |
| VRM 0.x/1.0 양쪽 출력 | 최윤수 | 변환 옵션 | 두 버전 정상 출력 |
| 템플릿 morph target 품질 튜닝 | 이현지, 조수빈 | 수정된 템플릿 | 극단 값에서도 메시 깨짐 없음 |
| 헤어/의상 프리셋 추가 | 조수빈 | 추가 에셋 | 다양성 확보 |
| VSeeFace/VMagicMirror 호환성 테스트 | 이현지 | 호환성 리포트 | 99%+ 정상 동작 |

#### Phase 1-3 (2주) — QA & 최적화

| 업무 | 담당자 | 산출물 | 완료 기준 |
|------|--------|--------|----------|
| 베타 피드백 → 템플릿 미세 조정 | 전원 | 수정된 템플릿 | 피드백 80%+ 반영 |
| VRM 익스포트 안정성 테스트 | 최윤수 | 테스트 리포트 | 에러율 < 1% |
| 익스포트 시간 최적화 | 최윤수 | 성능 리포트 | < 60초 (P95) |

### 일상 업무

- **전원:** morph target 명세 통일 유지, 상호 코드/에셋 리뷰
- **이현지:** 뷰어팀(백승우)에게 에셋 전달 + Three.js 호환성 피드백 루프
- **조수빈:** 프리셋 에셋 품질 관리, 다양성 확보
- **최윤수:** 백엔드(장동윤)와 Unity headless Docker + BullMQ 연동

---

## 4. 역할 2: 3D 뷰어 엔지니어 — 백승우, 이현지

### 담당 범위

- **파이프라인:** Stage 5 (Template Select), Stage 6 (Slider Init), Stage 7 (Web Edit)
- **편집기:** morph target / bone scale / material 컨트롤러
- **유사도:** 3D 특징 벡터 기반 코사인 유사도 엔진

### 팀원별 분담

| 담당자 | 주요 담당 | 상세 |
|--------|----------|------|
| **백승우** | 뷰어 코어 + 편집기 전체 | Three.js 뷰어, 슬라이더 컨트롤러, 렌더링 최적화, 유사도 엔진 |
| **이현지** | 에셋 호환성 + 매핑 | 템플릿↔뷰어 연동 검증, feature_vector→슬라이더 매핑 테이블, 템플릿 자동 선택 |

> **이현지**는 3D 템플릿팀에서 에셋을 제작하면서 동시에 뷰어에서의 호환성을 직접 검증한다. 템플릿 구조를 가장 잘 이해하는 사람이 매핑 테이블과 자동 선택 로직을 담당하는 것이 효율적이다.

### 필수 기술스택

| 기술 | 용도 | 담당자 |
|------|------|--------|
| Three.js | WebGL 기반 3D 렌더링 | 백승우 |
| react-three-fiber (R3F) | React 선언적 3D API | 백승우 |
| @pixiv/three-vrm | VRM 네이티브 로드/제어 | 백승우 |
| Zustand | 3D 편집 상태 관리 (슬라이더 ↔ 뷰어) | 백승우 |
| GLSL (기초) | 커스텀 셰이더 (toon 렌더링 등) | 백승우 |
| WebGL 2.0 | 호환성, 성능 최적화 | 백승우 |
| KTX2/Basis | 텍스처 압축 | 백승우 |
| Blender + Three.js | 에셋 호환성 검증 | 이현지 |

### 스프린트별 업무

#### Sprint 0 (2주) — 뷰어 PoC

| 업무 | 담당자 | 산출물 | 완료 기준 |
|------|--------|--------|----------|
| Three.js + R3F 환경 구축 | 백승우 | 뷰어 프로토타입 | 기본 3D 씬 렌더링 성공 |
| @pixiv/three-vrm 템플릿 로드 | 백승우 | VRM 로더 모듈 | 360도 회전, 줌, 패닝 동작 |
| morph target 슬라이더 연동 테스트 | 백승우 | 슬라이더 1개 연동 데모 | 조작 → 변형 < 1초 반응 확인 |
| 템플릿↔Three.js 호환성 검증 | 이현지 | 호환성 리포트 | PoC 템플릿 정상 로드 확인 |
| MediaPipe 특징값 → 슬라이더 매핑 테이블 초안 | 이현지 | 매핑 테이블 JSON | 주요 특징 5-10개 매핑 |

#### Phase 1-1 (4주) — 편집기 코어

| 업무 | 담당자 | 산출물 | 완료 기준 |
|------|--------|--------|----------|
| morph target 컨트롤러 | 백승우 | MorphTargetCtrl 모듈 | 20-30개 슬라이더 → mesh deformation |
| bone scale 컨트롤러 | 백승우 | BoneScaleCtrl 모듈 | 10-15개 슬라이더 → skeleton transform |
| material 컨트롤러 | 백승우 | MaterialCtrl 모듈 | 색상 피커 → 피부/눈/머리 색 변경 |
| 프리셋 셀렉터 | 백승우 | PresetSelector 모듈 | 헤어/의상 메시 교체 로직 |
| Stage 5: 템플릿 자동 선택 알고리즘 | 이현지 | 분류 로직 | feature_vector → cute/slim/mature 매칭 |
| Stage 6: 슬라이더 초기값 매핑 테이블 | 이현지 | 매핑 테이블 완성본 | feature_vector → 전체 슬라이더 초기값 |
| 프로덕션 템플릿 호환성 검증 | 이현지 | 검증 리포트 | 3종 모두 모든 슬라이더 정상 동작 |

#### Phase 1-2 (4주) — 유사도 엔진 + 최적화

| 업무 | 담당자 | 산출물 | 완료 기준 |
|------|--------|--------|----------|
| 유사도 검증 엔진 | 백승우 | SimilarityEngine 모듈 | 3D 특징 벡터 추출 → 코사인 유사도 계산 |
| 편집 중 유사도 실시간 표시 | 백승우 | 유사도 게이지 컴포넌트 | 편집 변경 시 수치 즉시 갱신 |
| 유사도 85% 초과 경고 + 감소 가이드 | 백승우 | 가이드 로직 | 슬라이더 변경 추천 |
| LOD(Level of Detail) 적용 | 백승우 | LOD 시스템 | 카메라 거리별 메시 단순화 |
| 텍스처 압축 (KTX2/Basis) | 백승우 | 압축 파이프라인 | 텍스처 용량 50%+ 감소 |
| 렌더링 최적화 | 백승우 | 성능 프로파일 | 30 FPS+ 보장 (데스크톱) |
| 매핑 정확도 튜닝 | 이현지 | 튜닝 리포트 | 사용자 테스트 기반 조정 |

#### Phase 1-3 (2주) — QA & 성능 튜닝

| 업무 | 담당자 | 산출물 | 완료 기준 |
|------|--------|--------|----------|
| 슬라이더 편집 반응 시간 검증 | 백승우 | 성능 리포트 | P95 < 100ms (렌더링 포함 < 1초) |
| 크로스 브라우저 WebGL 호환성 | 백승우 | 호환성 리포트 | Chrome/Firefox/Safari/Edge 정상 |
| 베타 피드백 반영 | 백승우, 이현지 | 수정 사항 목록 | 슬라이더 UX, 매핑 정확도 조정 |
| WebGL 2.0 미지원 시 안내 | 백승우 | fallback UI | 미지원 브라우저 안내 메시지 |

### 일상 업무

- **백승우:** 뷰어 코어 개발, 렌더링 성능 프로파일링, 장동윤(백엔드)과 feature_vector 포맷 합의
- **이현지:** 템플릿팀에서 새 에셋 전달받을 때마다 Three.js 호환성 즉시 검증, 매핑 테이블 업데이트

---

## 5. 역할 3: 백엔드 엔지니어 — 장동윤

### 담당 범위

- **파이프라인:** Stage 1 (Upload + NSFW), Stage 2 (VARCO 호출), Stage 4 (MediaPipe 연동), Stage 9 (Unity 호출)
- **API:** 전체 REST API (Phase 1에서는 파이프라인 API 우선, Phase 2에서 인증/결제 추가)
- **인프라:** BullMQ + Redis 큐, PostgreSQL, S3, WebSocket

### Phase 1에서의 우선순위

장동윤은 처음부터 백엔드를 담당하되, Phase 1에서는 **3D 파이프라인 지원에 집중**한다.

```
Phase 1 우선순위:
1순위 — 파이프라인 큐 (BullMQ + Redis) + VARCO API 연동
2순위 — DB 스키마 + 기본 CRUD API
3순위 — Python MediaPipe Worker
4순위 — WebSocket (진행률 전달)
---
Phase 2 추가:
5순위 — 인증 (OAuth + 이메일)
6순위 — 결제/크레딧 시스템
7순위 — 어드민 API
```

### 필수 기술스택

| 기술 | 용도 |
|------|------|
| NestJS | 모듈형 DI 아키텍처, REST API |
| TypeScript | 타입 안정성 |
| BullMQ + Redis | 비동기 파이프라인 큐, pub/sub |
| PostgreSQL + Prisma | 관계형 DB, ORM, 마이그레이션 |
| Python | MediaPipe Worker (Face/Pose Landmarker), OpenCV |
| Docker | Python Worker, Unity headless 컨테이너 관리 |
| S3 (AWS/MinIO) | 이미지, GLB, VRM 대용량 저장 |
| WebSocket | 파이프라인 진행률 실시간 전달 |

### 스프린트별 업무

#### Sprint 0 (2주) — 인프라 PoC

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| NestJS 프로젝트 구조 설계 | 프로젝트 스캐폴드 | 모듈형 DI, 핵심 모듈 분리 |
| PostgreSQL + Prisma 스키마 초안 | schema.prisma | 9개 핵심 엔티티 정의 |
| BullMQ + Redis 큐 PoC | 큐 테스트 결과 | 작업 등록/처리/완료 흐름 검증 |
| VARCO 3D API 연동 테스트 | API 연동 리포트 | GLB 생성 성공, 응답 시간 측정 |
| Python MediaPipe Worker PoC | Worker 프로토타입 | 특징 추출 정확도 검증 |

#### Phase 1-1 (4주) — 파이프라인 구축

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| DB 스키마 완성 + 마이그레이션 | Prisma 스키마 | 9개 엔티티 (Users, Projects, Templates, Avatars, Avatar_Versions, Payments, Pipeline_Jobs, Similarity_DB, Reports) |
| Stage 1: 이미지 업로드 API | POST /api/avatars/upload | S3 저장 + NSFW 필터링 연동 |
| Stage 2: VARCO Worker | BullMQ Worker | VARCO API 호출, 재시도 3회, 서킷 브레이커 |
| Stage 4: MediaPipe Worker | Python subprocess | feature_vector JSON 콜백 |
| 파이프라인 오케스트레이터 | PipelineOrchestrator | Stage 1→2→3→4→5→6 자동 진행 |
| WebSocket 모듈 | WS Gateway | 파이프라인 진행률 실시간 전달 |
| 기본 CRUD API | REST endpoints | 프로젝트, 아바타, 템플릿, 버전 CRUD |

#### Phase 1-2 (4주) — Stage 9 + 유사도 + 인증 기반

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| Stage 9 Worker | BullMQ Worker | Unity headless 호출 (최윤수와 연동) → VRM S3 저장 |
| 유사도 검증 API | SimilarityEngine | 특징 벡터 DB 저장 + 코사인 유사도 |
| 인증 모듈 | AuthModule | OAuth 2.0 (Google/Discord) + 이메일/PW (bcrypt) |
| 보안 기본 적용 | 보안 미들웨어 | Rate limiting, TLS 1.3, OWASP Top 10 기본 |
| 실존 인물 모방 감지 | 감지 로직 | Stage 4 특징 추출 기반 |

#### Phase 1-3 (2주) — QA & 안정화

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| 통합 테스트 | E2E 테스트 스위트 | 전체 9단계 파이프라인 정상 동작 |
| 부하 테스트 | 부하 테스트 리포트 | 동시 편집 세션 100+ 검증 |
| 서킷 브레이커 전체 적용 | 장애 대응 검증 | 모든 외부 API 타임아웃 30초 + 서킷 브레이커 |
| 에러 핸들링 & 로깅 정비 | 로깅 시스템 | 구조화된 로그, 에러 추적 |

### Phase 2에서 추가되는 업무 (프론트엔드 전환 후)

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| 크레딧/결제 모듈 | CreditModule | Stripe/토스 연동, 충전/차감 로직 |
| 신고 모듈 | ReportModule | 신고 CRUD + 어드민 리뷰 API |
| 어드민 API | AdminModule | 통계 집계, 임계값 설정, 오탐 리뷰 |
| 프론트엔드 팀과 API 연동 | API 스펙 문서 | REST + WebSocket 인터페이스 확정 |

### 일상 업무

- 3D 템플릿팀(최윤수)과 Unity headless Docker + BullMQ 연동
- 3D 뷰어팀(백승우, 이현지)과 feature_vector JSON 포맷 합의
- DB 마이그레이션, 인프라 모니터링
- API 성능 모니터링 + 이슈 대응

### DB 스키마 (담당 영역)

```
핵심 엔티티 9개:
├── Users (인증, 크레딧)
├── Projects (프로젝트 관리)
├── Templates (3종 템플릿 메타데이터)
├── Avatars (아바타 상태, 파이프라인 단계)
├── Avatar_Versions (버전 스냅샷, 최대 5개)
├── Payments (결제/크레딧 이력)          ← Phase 2
├── Pipeline_Jobs (BullMQ 작업 추적)
├── Similarity_DB (유사도 특징 벡터)
└── Reports (저작권 침해 신고)           ← Phase 2
```

---

## 6. 이현지 — 겸임 역할 상세

이현지는 **3D 템플릿 + 3D 뷰어**를 겸임하는 브릿지 역할이다. 시간 배분과 책임 범위를 명확히 정의한다.

### 시간 배분

| 단계 | 3D 템플릿 비중 | 3D 뷰어 비중 | 설명 |
|------|-------------|-------------|------|
| **Sprint 0** | 70% | 30% | cute 템플릿 PoC 우선 + 뷰어 호환성 검증 |
| **Phase 1-1** | 60% | 40% | cute 템플릿 프로덕션 + 매핑 테이블/자동 선택 |
| **Phase 1-2** | 40% | 60% | 템플릿 품질 튜닝 + 매핑 정확도 튜닝 + VSeeFace 테스트 |
| **Phase 1-3** | 30% | 70% | 베타 피드백 반영 (뷰어 중심) |

### 겸임의 가치

| 항목 | 설명 |
|------|------|
| **에셋 호환성 보장** | 템플릿 제작자가 직접 Three.js에서 확인 → 전달 후 "안 돌아감" 이슈 사전 차단 |
| **매핑 정확도 향상** | morph target 구조를 이해하는 사람이 feature_vector→슬라이더 매핑을 설계 |
| **커뮤니케이션 비용 감소** | 템플릿↔뷰어 간 의사소통 병목 제거 |

### 겸임 리스크 & 대응

| 리스크 | 대응 |
|--------|------|
| 시간 부족으로 양쪽 모두 지연 | 템플릿 우선. 뷰어의 매핑/호환성 업무는 에셋 전달 시점에 맞춰 배치 |
| 컨텍스트 스위칭 비용 | 오전: 템플릿, 오후: 뷰어로 시간대 고정 |
| cute 템플릿 품질 저하 | 조수빈/최윤수가 크로스 리뷰, 필요 시 서포트 |

---

## 7. Phase 2: 프론트엔드 전환 계획

### 전환 조건

3D 코어가 다음 기준을 충족하면 프론트엔드 개발을 시작한다:

| 기준 | 구체적 조건 |
|------|-----------|
| 템플릿 완성 | 3종 GLB 프로덕션 품질 확정, morph target/bone scale 동결 |
| 뷰어 동작 | 모든 슬라이더 정상 동작, < 1초 반응, 30 FPS+ |
| 파이프라인 동작 | Stage 1→9 E2E 정상 동작 |
| VRM 익스포트 동작 | Unity headless → VRM 변환 자동화 완료 |

> **예상 전환 시점:** Phase 1-2 중반 (Week 7-8 경) 또는 Phase 1-3 시작 시점

### 전환 후 인력 재배치

| 이름 | Phase 1 (3D 집중) | Phase 2 (프론트엔드 전환 후) |
|------|------------------|--------------------------|
| **이현지** | 3D 템플릿 + 뷰어 겸임 | 3D 유지보수 + 프론트엔드 3D 편집기 통합 (R3F ↔ Next.js) |
| **조수빈** | 3D 템플릿 (slim + 프리셋) | **프론트엔드 전환** — 서비스 페이지 (랜딩, 프로젝트 목록, 결제 UI) |
| **최윤수** | 3D 템플릿 (mature + Unity) | **프론트엔드 전환** — 어드민 대시보드, 버전 관리 UI |
| **백승우** | 3D 뷰어 | 프론트엔드 3D 편집기 UI (슬라이더 패널, 유사도 표시, 익스포트 UI) |
| **장동윤** | 백엔드 | 백엔드 계속 (결제/인증/어드민 API 추가) |

### Phase 2 프론트엔드 업무 분배

#### 조수빈 — 서비스 페이지 담당

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| Next.js + TS + Tailwind + shadcn/ui 세팅 | 프로젝트 보일러플레이트 | 빌드/린트 정상 |
| 랜딩 페이지 (SSG) | 랜딩 페이지 | 서비스 소개, CTA, 반응형 |
| OAuth 로그인 UI | 로그인/회원가입 페이지 | Google/Discord + 이메일 동작 |
| 프로젝트 목록 | CRUD 페이지 | 아바타 썸네일 그리드 |
| 이미지 업로드 UI | 업로드 컴포넌트 | 드래그앤드롭, NSFW 경고 |
| 결제 플로우 UI | 크레딧/결제 페이지 | 충전, Basic/Edit/Export 결제 |
| 결제/크레딧 내역 페이지 | 내역 페이지 | 결제 로그, 크레딧 이력 |

#### 최윤수 — 관리/기능 페이지 담당

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| 3D 생성 진행률 UI | 프로그레스 컴포넌트 | WebSocket 기반, Stage 2-4 상태 |
| 버전 관리 UI | VersionManager 컴포넌트 | 저장(5개), 비교, 복원 |
| 저작권 확인서 UI | CopyrightCert 컴포넌트 | PDF 생성 + 다운로드 |
| 어드민 대시보드 | AdminDashboard 페이지 | 사용량 차트, 게이트 관리, 신고 |
| VRM 익스포트 UI | ExportManager 컴포넌트 | 진행률 + 다운로드 |

#### 백승우 — 3D 편집기 UI 담당

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| 편집기 레이아웃 | EditorLayout 컴포넌트 | 좌측 슬라이더 + 우측 3D 뷰어 |
| 슬라이더 편집 패널 | SliderPanel 컴포넌트 | 카테고리별 (얼굴/체형/색상/프리셋) |
| 유사도 표시 UI | SimilarityDisplay 컴포넌트 | 실시간 게이지, 경고 모달 |
| Zustand 스토어 통합 | EditorStore | 슬라이더↔3D 뷰어 상태 연동 |

#### 이현지 — 3D ↔ 프론트엔드 통합 담당

| 업무 | 산출물 | 완료 기준 |
|------|--------|----------|
| R3F ↔ Next.js 통합 | 편집기 통합 모듈 | 3D 뷰어가 Next.js 페이지에서 정상 동작 |
| 템플릿 로딩 최적화 | 로딩 파이프라인 | GLB 에셋 lazy load + 프로그레스 |
| 3D 관련 버그 수정 | 패치 | 프론트엔드 통합 후 발생하는 3D 이슈 대응 |

### Phase 2 프론트엔드 필수 기술스택

| 기술 | 용도 | 담당자 |
|------|------|--------|
| Next.js 14+ | SSR/SSG, 라우팅 | 조수빈 (메인), 최윤수 |
| TypeScript | 타입 안정성 | 전원 |
| Tailwind CSS + shadcn/ui | 스타일링 + 컴포넌트 | 조수빈, 최윤수 |
| Zustand | 편집 상태 관리 | 백승우, 이현지 |
| WebSocket | 진행률 실시간 수신 | 최윤수 |
| react-three-fiber | 편집기 내 3D 뷰어 | 백승우, 이현지 |

---

## 8. 역할 간 의존성 맵

### Phase 1 구조도

```
     3D 템플릿 (이현지, 조수빈, 최윤수)
          │
          │ GLB 에셋 전달
          │
          ▼
     3D 뷰어 (백승우, 이현지)
          │                    ┌─────────────────────┐
          │ feature_vector     │                     │
          │ 포맷 합의          │  Unity headless     │
          │                    │  Docker 연동        │
          ▼                    │                     │
     백엔드 (장동윤) ◄─────────┘                     │
          │                                          │
          │ VARCO API + BullMQ                       │
          │ MediaPipe Worker                         │
          └──────────────────────────────────────────┘
                        최윤수 ↔ 장동윤
                        (Unity headless 연동)
```

### Phase 2 구조도 (프론트엔드 전환 후)

```
     3D 유지보수 (이현지)
          │
          │ 3D↔프론트 통합
          ▼
     프론트엔드 편집기 UI (백승우)
          │
          ├──── 서비스 페이지 (조수빈) ──── API 연동 ──── 백엔드 (장동윤)
          │
          └──── 관리/기능 페이지 (최윤수) ── API 연동 ──┘
```

### 핵심 의존성 상세

| # | 의존 관계 | 내용 | 블로킹 여부 | 해소 시점 |
|---|----------|------|-----------|----------|
| 1 | **템플릿팀 → 뷰어팀** | 템플릿 GLB 에셋이 완성되어야 뷰어에서 로드/편집 가능 | **블로킹** | Sprint 0 PoC 템플릿으로 1차 해소 |
| 2 | **이현지 (브릿지)** | 템플릿↔뷰어 호환성 검증을 이현지가 직접 수행 → 의존성 내재화 | **해소됨** | 이현지 겸임으로 자동 해소 |
| 3 | **최윤수 ↔ 장동윤** | Unity headless Docker + BullMQ Worker 연동 (Stage 9) | **블로킹** | Phase 1-2 시작 시점 |
| 4 | **장동윤 → 백승우** | feature_vector JSON 포맷 합의 (Stage 4 출력 → Stage 5-6 입력) | **블로킹** | Sprint 0에서 포맷 확정 |
| 5 | **3D 코어 → 프론트엔드** | 3D 기능이 안정화되어야 프론트엔드 전환 가능 | **블로킹** | Phase 1-2 중반 ~ Phase 1-3 시작 |

### 의존성 해소 전략

- **Sprint 0에서 모든 인터페이스 확정:** GLB 에셋 포맷, feature_vector JSON 포맷, morph target/bone scale 명세
- **이현지 겸임으로 템플릿↔뷰어 의존성 내재화:** 별도 커뮤니케이션 비용 제거
- **Mock 데이터 활용:** 실제 에셋/API 완성 전 mock으로 병렬 개발
- **주간 통합 테스트:** 매주 금요일 전체 파이프라인 통합 동작 확인

---

## 9. 협업 인터페이스 정의

### 데이터 인터페이스

#### 템플릿팀 → 뷰어팀: 템플릿 에셋

```
파일: templates/{cute|slim|mature}/
├── base_mesh.glb          (베이스 메시)
├── morph_targets.json     (morph target 이름/범위 정의)
├── bone_scales.json       (bone scale 이름/범위 정의)
├── material_slots.json    (material 슬롯 정의)
├── hair_presets/           (헤어 프리셋 GLB 파일들)
├── outfit_presets/         (의상 프리셋 GLB 파일들)
└── blendshapes.json       (표정 + viseme 매핑)
```

**담당:** 이현지, 조수빈, 최윤수 → 백승우, 이현지(검증)

#### 장동윤 → 백승우, 이현지: feature_vector JSON (Stage 4 출력)

```json
{
  "face": {
    "eye_width_ratio": 0.35,
    "eye_height_ratio": 0.12,
    "nose_height_ratio": 0.28,
    "jaw_angle": 42.5,
    "face_roundness": 0.65
  },
  "body": {
    "shoulder_width_ratio": 0.38,
    "height_estimate": "medium",
    "limb_proportion": 0.45
  },
  "recommended_template": "cute"
}
```

#### 백승우 ↔ 프론트엔드팀: Zustand 스토어 인터페이스

```typescript
interface EditorStore {
  // 슬라이더 상태
  morphTargets: Record<string, number>;    // -1.0 ~ 1.0
  boneScales: Record<string, number>;      // 0.5 ~ 2.0
  materials: Record<string, string>;       // hex color
  selectedHairPreset: string;
  selectedOutfitPreset: string;

  // 액션
  setMorphTarget: (name: string, value: number) => void;
  setBoneScale: (name: string, value: number) => void;
  setMaterial: (name: string, color: string) => void;

  // 버전
  versions: VersionSnapshot[];
  saveVersion: () => void;
  restoreVersion: (id: string) => void;

  // 유사도
  similarityScore: number;
}
```

**담당:** 백승우(설계) → Phase 2에서 프론트엔드 팀 전원 사용

#### 장동윤 → 프론트엔드팀: WebSocket 이벤트

```typescript
// 파이프라인 진행률
{ event: "pipeline:progress", data: { avatarId, stage: 1-9, status, progress: 0-100 } }

// 파이프라인 완료
{ event: "pipeline:complete", data: { avatarId, stage, result } }

// 파이프라인 에러
{ event: "pipeline:error", data: { avatarId, stage, error, retryCount } }
```

---

## 10. 스프린트별 전체 간트

### Phase 1: 3D 코어 집중

```
Week     1   2   3   4   5   6   7   8   9  10  11  12
         ├───┤   ├───────────────┤   ├───────────────┤   ├───┤
         S0       Phase 1-1           Phase 1-2           1-3

이현지 (템플릿+뷰어 겸임)
         [cute PoC     ]  [cute 프로덕션 + 매핑   ]  [품질 튜닝 + 매핑  ]  [QA]
         [호환성 검증  ]  [자동선택 + 초기값매핑  ]  [정확도 + VSeeFace ]  [베타]

조수빈 (템플릿)
         [slim PoC     ]  [slim 프로덕션          ]  [morph 품질 튜닝   ]  [QA]
                          [헤어/의상 프리셋       ]  [프리셋 추가       ]

최윤수 (템플릿 + Unity)
         [mature PoC   ]  [mature 프로덕션        ]  [Unity headless    ]  [QA]
         [Unity PoC    ]  [Spring Bone + 렌더러   ]  [Docker + VRM 변환 ]

백승우 (뷰어)
         [Three.js PoC ]  [편집기 코어            ]  [유사도 + 최적화   ]  [QA]
         [R3F + VRM    ]  [morph/bone/material    ]  [LOD + 텍스처 압축 ]

장동윤 (백엔드)
         [NestJS PoC   ]  [파이프라인 구축        ]  [Stage 9 + 유사도  ]  [QA]
         [VARCO 연동   ]  [BullMQ + MediaPipe     ]  [인증 기반         ]
```

### Phase 2: 프론트엔드 전환 (Phase 1 완료 후)

```
Week    13  14  15  16  17  18
        ├───────────────┤   ├───┤
        Phase 2              QA

이현지 → 3D↔프론트 통합
        [R3F↔Next.js 통합    ]  [QA]
        [3D 버그 수정        ]

조수빈 → 프론트엔드 (서비스 페이지)
        [Next.js 세팅        ]  [QA]
        [랜딩/로그인/프로젝트 ]
        [결제 UI             ]

최윤수 → 프론트엔드 (관리/기능)
        [진행률/버전관리 UI   ]  [QA]
        [어드민/익스포트 UI   ]

백승우 → 프론트엔드 (편집기 UI)
        [편집기 레이아웃      ]  [QA]
        [슬라이더 패널        ]
        [유사도 표시 UI       ]

장동윤 → 백엔드 (서비스 기능)
        [결제/크레딧 모듈     ]  [QA]
        [어드민/신고 API      ]
        [프론트 API 연동      ]
```

### 전체 타임라인 요약

```
Week  1──2──3──4──5──6──7──8──9──10──11──12──13──14──15──16──17──18
      ├─────────── Phase 1: 3D 코어 ─────────────┤├── Phase 2: FE ──┤├QA┤
      │  S0  │    Phase 1-1    │    Phase 1-2    │1-3│               │   │
      │      │                 │                 │   │               │   │
      │ 3D   │ 3D 템플릿+뷰어 │ 3D 완성+Unity   │ QA│ 프론트엔드    │ QA│
      │ PoC  │ 코어 개발       │ VRM 파이프라인  │   │ 전환 개발     │   │
      │      │                 │                 │   │               │   │
      └──────┴─────────────────┴─────────────────┴───┴───────────────┴───┘
                                                  ↑
                                           프론트엔드 전환 시점
                                    (3D 코어 안정화 확인 후 결정)
```

---

*본 문서는 PRD v2.0 (prd-restructured.md) 기반으로 작성되었으며, Sprint 0 PoC 결과에 따라 역할 범위 및 일정이 조정될 수 있습니다. 프론트엔드 전환 시점은 3D 코어 안정화 상태에 따라 유동적으로 결정합니다.*
