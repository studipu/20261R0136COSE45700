# 3D 버튜버 제작 파이프라인 (현업 기준 레퍼런스)

> 엔지니어 관점 + 제작 관점 통합 정리
> 작성일: 2026-04-09
> 용도: 버추얼 아바타 생성·수정 서비스 제작 참고 자료

---

## 전체 구조 한눈에 보기

3D 버튜버 파이프라인은 아래 4단으로 나뉜다:

```
[1] 아바타 제작 (Offline)
 → [2] 리깅/표정/물리 세팅
 → [3] 트래킹 시스템 연결 (Real-time input)
 → [4] 렌더링 + 방송 송출 (Real-time output)
```

실무적 표현:

```
Art → Rigging → Runtime Engine → Streaming Pipeline
```

---

## 1. 컨셉 & 캐릭터 설계 (Pre-production)

### 결정 사항

- 캐릭터 디자인 (외형, 의상, 헤어)
- 스타일 (애니풍 vs 현실풍)
- 사용 목적: 게임 스트리밍 / VR 공연 / AI 스트리머
- 기술 선택

### 기술 선택 (이후 파이프라인 고정)

| 선택 | 결과 |
|------|------|
| VRM 기반 | Unity 중심 |
| Unreal | 고퀄 렌더링 |
| VSeeFace | 간단 세팅 |
| 풀 커스텀 | 완전 자유 |

---

## 2. 3D 모델링 (Modeling)

### 사용 툴

- Blender (가장 많이 씀)
- Maya
- ZBrush (하이폴리 조형)
- Substance Painter (텍스처)

### 실제 작업 단계

#### (1) 베이스 메시 생성
- 얼굴, 몸, 손, 발
- topology 중요 (애니메이션 변형 때문)

#### (2) 헤어 제작
- 카드 방식 (anime 스타일)
- strand hair (리얼 스타일)

#### (3) 의상 제작
- separate mesh
- cloth simulation 고려

### 결과물
- `.fbx`, `.blend`
- 텍스처 (png, tga)

---

## 3. 리깅 (Rigging) — 가장 중요

이 단계가 **"움직이는 캐릭터" vs "조각상"**을 나눈다.

### 3-1. 스켈레톤 구성

```
Root
 ├── Spine
 │    ├── Chest
 │    ├── Neck
 │    └── Head
 ├── Arm (L/R)
 ├── Leg (L/R)
```

### 3-2. 스키닝 (Skinning)

각 vertex가 어떤 뼈의 영향을 받는지 설정

- 팔꿈치 → 상완 + 하완 영향
- 얼굴 → head bone + facial rig

### 3-3. 얼굴 리깅 (핵심)

#### (A) Blendshape (Morph Target) — 가장 일반적
표정별로 shape 저장:
- mouth_open, smile, blink, angry

#### (B) Bone-based facial rig
- 복잡하지만 유연함
- AAA 게임에서 많이 씀

### 3-4. VRM 표준화

3D 버튜버 대부분은 **VRM 포맷** 사용

VRM에서 요구하는 것:
- humanoid bone mapping
- blendshape proxy
- spring bone (물리)

---

## 4. 표정 & 립싱크 세팅

### 필수 표정
- blink, joy, angry, sad, neutral

### 립싱크 (Viseme)

```
A / I / U / E / O
```

또는:

```
sil, aa, ih, ou 등
```

---

## 5. 물리 시스템 (Physics)

이게 없으면 "로봇"처럼 보임

### 적용 대상
- 머리카락, 가슴, 옷, 악세서리

### 방식 (Unity 기준)
- Spring Bone
- Dynamic Bone
- Cloth simulation

### 핵심 파라미터
- stiffness, damping, gravity, delay

---

## 6. Unity / Runtime 엔진 세팅

### 왜 Unity를 쓰냐?
- VRM 지원
- 트래킹 연결 쉬움
- OBS 연동 쉬움

### Scene 구조

```
Camera
Light
Avatar (VRM)
Tracking Input
LipSync Module
```

### 주요 작업
- VRM import
- 카메라 위치 조정
- 조명 세팅
- 표정 키 매핑

---

## 7. 트래킹 시스템 연결 (실시간 입력 파이프라인)

### 7-1. 얼굴 트래킹

| 방식 | 설명 |
|------|------|
| Webcam | 저렴 |
| iPhone (ARKit) | 최고 품질 |
| mocap 장비 | 프로급 |

#### ARKit 출력
52개 blendshape 값:
```
jawOpen, eyeBlinkLeft, browInnerUp, mouthSmile ...
```

#### 매핑
```
ARKit → VRM blendshape
```

### 7-2. 몸 트래킹

- VR tracker (Vive)
- mocap suit
- pose estimation (AI)

#### 데이터 흐름
```
센서 → 좌표 → bone transform → avatar
```

---

## 8. 립싱크 (Audio → Mouth)

### (1) amplitude 기반
- 소리 크기 → 입 열림

### (2) phoneme 기반
- 음성 → 발음 → mouth shape

### 실무
- 대부분 amplitude + smoothing
- 고급은 phoneme 모델

---

## 9. 렌더링 파이프라인

Unity 내부:
```
Input → Animation Update → Physics → Rendering
```

### 중요 요소
- FPS (60 이상)
- latency (낮을수록 좋음)
- shader (toon vs realistic)

---

## 10. OBS 연결 (Streaming Pipeline)

### OBS에서 하는 것
- Unity 화면 캡처
- 투명 배경 처리
- 게임 화면 추가
- 채팅창, 알림

### 최종 구조

```
[Unity Avatar]
        ↓
[OBS Scene Composition]
        ↓
[Encoder (x264 / NVENC)]
        ↓
[Streaming Platform]
```

---

## 11. 실제 실행 흐름 (Runtime) — 핵심

### 전체 데이터 흐름

```
[Camera / iPhone]
        ↓
[Face Tracking]
        ↓
[Blendshape 값]
        ↓
[Avatar Rig]
        ↓
[Animation Update]
        ↓
[Physics]
        ↓
[Rendering]
        ↓
[OBS]
        ↓
[Stream]
```

---

## 12. AI 버튜버 확장

추가되는 파이프라인:

```
Chat → LLM → Text
                ↓
             TTS
                ↓
           Lip Sync
                ↓
            Avatar
```

---

## 13. 병목 포인트

| 병목 | 설명 |
|------|------|
| 트래킹 지연 | 얼굴 → 아바타 반영 delay |
| 렌더링 부하 | GPU bottleneck |
| 립싱크 mismatch | audio vs animation sync |
| OBS encoding | CPU/GPU 사용량 |
| AI pipeline | LLM latency + TTS latency |

---

## 14. 핵심 요약 (엔지니어 버전)

3D 버튜버 시스템:

```
Real-time Input System
 + Animation System
 + Physics Engine
 + Rendering Engine
 + Streaming Pipeline
```

이 5개가 동시에 돌아가는 구조.

**한 줄 핵심:**
> "센서 입력을 받아 → 리깅된 캐릭터를 변형 → 실시간 렌더링 → 방송으로 출력하는 인터랙티브 그래픽 시스템"

---

## AI/LLM 관점 핵심 포인트

이것은 사실 **멀티모달 실시간 에이전트 시스템**

핵심 문제:
- **latency** — 실시간 응답 속도
- **synchronization** — 오디오/비주얼/트래킹 동기화
- **memory (state 유지)** — 컨텍스트 지속
- **perception → action mapping** — 입력에서 출력까지의 매핑

---

## 우리 서비스와의 연결점

이 파이프라인에서 우리 서비스(VARCO AI + AI 기반 Mesh Editing)가 혁신할 수 있는 구간:

1. **2단계(모델링)**: VARCO Image-to-3D로 사진 → 3D 모델 자동 생성
2. **3단계(리깅)**: 자동 리깅 + VRM 변환 자동화
3. **자연어 편집**: Mesh Editing AI로 전문 지식 없이 수정
4. **실시간 커스텀**: 방송 중에도 자연어로 아바타 즉시 변경

> 기존 파이프라인의 1~3단계(수주~수개월)를 "사진 업로드 + 자연어 지시"로 단축하는 것이 핵심 가치
