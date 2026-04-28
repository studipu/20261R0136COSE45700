# 백엔드 연동 구현 참고사항

**작성자:** 백승우 (3D 뷰어 엔지니어)
**작성일:** 2026-04-28
**대상:** 백엔드 개발자, 프론트엔드 협업자
**상태:** Sprint 0 완료 기준

---

## 1. 현재 프론트엔드 아키텍처 요약

### 1-1. 기술스택

| 영역 | 기술 | 버전 |
|------|------|------|
| 프레임워크 | Next.js + TypeScript | 16.2.4 |
| 3D 렌더링 | Three.js + react-three-fiber + @pixiv/three-vrm | 0.184 / 9.6 / 3.5 |
| 상태 관리 | Zustand | 5.0 |
| UI | shadcn/ui + Tailwind CSS | 4.x |

### 1-2. 전체 구조

```
사용자 조작 (슬라이더)
    │
    ▼
┌─────────────────────┐
│  Zustand Store      │  ← 편집 상태의 단일 진실 원천 (Single Source of Truth)
│  (editorStore.ts)   │     클라이언트 메모리에서만 동작, 서버와 직접 통신하지 않음
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼
 VRMModel   API Layer ─────▶  현재: localStorage
 (매 프레임               교체 후: HTTP → 백엔드 REST API
  렌더링)
```

### 1-3. 핵심 원칙

- **실시간 편집은 100% 클라이언트사이드.** 슬라이더 조작 → 3D 변형은 서버를 거치지 않는다.
- **서버 통신은 저장/로드/익스포트 시점에만 발생.** 편집 중에는 네트워크 호출 없음.
- **API Layer 추상화 완료.** 인터페이스가 정의되어 있어 구현체만 교체하면 된다.

---

## 2. 프론트↔백엔드 핵심 데이터 구조

### 2-1. AvatarParameters — 가장 중요한 JSON 스키마

프론트엔드가 서버에 저장/로드하는 편집 상태의 전체 구조:

```typescript
// src/types/editor.ts

interface AvatarParameters {
  morphTargets: MorphTargetMap;
  boneScales: BoneScaleMap;
  materials: MaterialMap;
}

// --- 세부 타입 ---

interface MorphTargetMap {
  [name: string]: number;  // 값 범위: 0.0 ~ 1.0 (일부 expression은 -1.0 ~ 1.0)
}
// 예시: { "face_eye_size": 0.7, "face_nose_width": 0.3, "happy": 0.5 }

interface BoneScaleMap {
  [boneName: string]: { x: number; y: number; z: number };
}
// 예시: { "head": { "x": 1.0, "y": 1.2, "z": 1.0 }, "chest": { "x": 1.1, "y": 1.0, "z": 1.0 } }

interface MaterialSlot {
  name: string;
  color?: string;       // hex "#ff0000"
  metalness?: number;    // 0.0 ~ 1.0
  roughness?: number;    // 0.0 ~ 1.0
  opacity?: number;      // 0.0 ~ 1.0
  textureUrl?: string;
}

interface MaterialMap {
  [slotName: string]: MaterialSlot;
}
// 예시: { "Skin": { "name": "Skin", "color": "#ffd5c8" }, "Hair": { "name": "Hair", "color": "#3a2a1a" } }
```

**백엔드 DB 저장 권장:** `AvatarParameters`를 JSONB 컬럼 하나에 그대로 저장. 필드별 분리 불필요.

### 2-2. AvatarVersion — 버전 스냅샷

```typescript
interface AvatarVersion {
  id: string;                    // "v-1714300000000-a1b2"
  name: string;                  // "버전 1"
  parameters: AvatarParameters;  // 위의 전체 편집 상태 스냅샷
  thumbnailDataUrl?: string;     // base64 PNG (128x128)
  createdAt: string;             // ISO 8601
}
```

- 아바타당 최대 **5개** 버전 제한 (프론트에서 강제)
- 썸네일은 Canvas에서 캡처한 base64 이미지 (~10-30KB)

### 2-3. TemplateMetadata — 템플릿 정보

```typescript
interface TemplateMetadata {
  id: string;              // "cute", "slim", "mature"
  name: string;            // "귀여운 스타일"
  description: string;
  thumbnailUrl: string;    // 템플릿 미리보기 이미지 URL
  vrmUrl: string;          // VRM 파일 URL (S3 등)
  defaultValues?: {        // 템플릿 기본 슬라이더 값
    morphTargets?: MorphTargetMap;
    boneScales?: BoneScaleMap;
    materials?: MaterialMap;
  };
  tags?: string[];
}
```

프론트엔드는 `vrmUrl`을 받아 Three.js로 직접 로드한다. 별도 변환 불필요.

---

## 3. 필요 API 엔드포인트 목록

### 3-1. 현재 정의된 API 인터페이스

`src/lib/api/types.ts`에 프론트엔드가 호출하는 인터페이스가 정의되어 있다:

```typescript
interface APIClient {
  avatar: AvatarAPI;
  version: VersionAPI;
  template: TemplateAPI;
}
```

### 3-2. AvatarAPI

| 메서드 | 대응 HTTP | URL (제안) | 설명 |
|--------|-----------|-----------|------|
| `saveAvatar(data)` | `PUT /api/avatars/{id}/parameters` | 편집 상태 저장 |
| `loadAvatar(avatarId)` | `GET /api/avatars/{id}` | 아바타 + 파라미터 로드 |
| `listAvatars()` | `GET /api/avatars` | 사용자의 아바타 목록 |
| `deleteAvatar(avatarId)` | `DELETE /api/avatars/{id}` | 아바타 삭제 |

**saveAvatar 요청 본문:**

```json
{
  "avatarId": "abc-123",
  "templateId": "cute",
  "parameters": {
    "morphTargets": { "face_eye_size": 0.7, "face_nose_width": 0.3 },
    "boneScales": { "head": { "x": 1.0, "y": 1.2, "z": 1.0 } },
    "materials": { "Skin": { "name": "Skin", "color": "#ffd5c8" } }
  }
}
```

**saveAvatar 응답:**

```json
{
  "avatarId": "abc-123",
  "templateId": "cute",
  "parameters": { ... },
  "updatedAt": "2026-04-28T10:30:00Z"
}
```

### 3-3. VersionAPI

| 메서드 | 대응 HTTP | URL (제안) |
|--------|-----------|-----------|
| `saveVersion(avatarId, version)` | `POST /api/avatars/{id}/versions` |
| `listVersions(avatarId)` | `GET /api/avatars/{id}/versions` |
| `deleteVersion(avatarId, versionId)` | `DELETE /api/avatars/{id}/versions/{vid}` |
| `updateVersion(avatarId, versionId, updates)` | `PATCH /api/avatars/{id}/versions/{vid}` |

**saveVersion 요청 본문:**

```json
{
  "id": "v-1714300000000-a1b2",
  "name": "버전 1",
  "parameters": { "morphTargets": {...}, "boneScales": {...}, "materials": {...} },
  "thumbnailDataUrl": "data:image/png;base64,iVBOR...",
  "createdAt": "2026-04-28T10:30:00Z"
}
```

> **썸네일 처리 옵션:** base64를 요청 본문에 포함하거나, 별도 `POST /api/upload/thumbnail` 엔드포인트로 분리 가능. 크기가 작으므로(~30KB) 본문 포함 권장.

### 3-4. TemplateAPI

| 메서드 | 대응 HTTP | URL (제안) |
|--------|-----------|-----------|
| `listTemplates()` | `GET /api/templates` |
| `getTemplate(templateId)` | `GET /api/templates/{id}` |

**listTemplates 응답 예시:**

```json
[
  {
    "id": "cute",
    "name": "귀여운 스타일",
    "description": "2-3등신, 큰 눈, 동글 체형",
    "thumbnailUrl": "https://cdn.example.com/templates/cute-thumb.png",
    "vrmUrl": "https://cdn.example.com/templates/cute-v1.vrm",
    "defaultValues": {
      "morphTargets": { "face_eye_size": 0.7 }
    },
    "tags": ["cute", "idol"]
  }
]
```

### 3-5. 파이프라인 API (신규 — PRD Stage 1~6, 9)

현재 프론트엔드에 미구현. 백엔드 구현 시 함께 프론트에 추가해야 할 API:

| 단계 | HTTP | URL (제안) | 설명 |
|------|------|-----------|------|
| Stage 1 | `POST /api/avatars/upload` | 참고 이미지 업로드 + NSFW 체크 |
| Stage 2 | `POST /api/avatars/{id}/generate` | VARCO GLB 생성 시작 |
| Stage 3-4 | (서버 내부) | 렌더 + 특징 추출 (프론트 호출 불필요) |
| Stage 5 | `POST /api/avatars/{id}/template` | 템플릿 선택/자동 매칭 결과 |
| Stage 6 | `GET /api/avatars/{id}/features` | 추출 특징값 + 슬라이더 초기값 |
| Stage 9 | `POST /api/avatars/{id}/export` | VRM 익스포트 요청 |
| 공통 | `GET /api/avatars/{id}/pipeline` | 파이프라인 진행 상태 조회 |
| 공통 | `GET /api/jobs/{jobId}` | 비동기 작업 상태 + 다운로드 URL |

**파이프라인 진행률 — WebSocket 제안:**

```
WS /ws/pipeline/{avatarId}

서버 → 클라이언트 메시지 형식:
{
  "stage": 2,
  "status": "processing",    // "queued" | "processing" | "completed" | "failed"
  "progress": 65,            // 0-100
  "message": "VARCO 3D 생성 중..."
}
```

프론트엔드에서는 이 메시지를 받아 프로그레스 바를 표시한다.

---

## 4. 프론트엔드 API 교체 방법

### 4-1. 현재 구조 (localStorage)

```
src/lib/api/
├── types.ts      ← 인터페이스 (변경 없음)
├── local.ts      ← localStorage 구현 (현재 사용 중)
├── provider.tsx   ← React Context 주입
└── index.ts
```

### 4-2. 백엔드 연결 시 추가할 파일

```
src/lib/api/
├── types.ts      ← 변경 없음
├── local.ts      ← 개발/오프라인용으로 유지
├── remote.ts     ← [신규] HTTP 기반 구현
├── provider.tsx   ← remoteAPIClient로 교체
└── index.ts
```

### 4-3. provider.tsx 교체

```typescript
// 변경 전
const APIContext = createContext<APIClient>(localAPIClient);

// 변경 후
import { remoteAPIClient } from './remote';
const APIContext = createContext<APIClient>(remoteAPIClient);

// 또는 환경변수로 분기
const defaultClient = process.env.NEXT_PUBLIC_API_MODE === 'local'
  ? localAPIClient
  : remoteAPIClient;
```

### 4-4. remote.ts 구현 패턴

```typescript
const BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8080';

async function fetchWithAuth(path: string, options?: RequestInit) {
  const token = getAuthToken(); // 인증 모듈에서 가져오기
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: res.statusText }));
    throw new Error(error.message || `API Error ${res.status}`);
  }
  return res.json();
}

const remoteAvatarAPI: AvatarAPI = {
  async saveAvatar(data) {
    return fetchWithAuth(`/api/avatars/${data.avatarId}/parameters`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  },
  async loadAvatar(avatarId) {
    return fetchWithAuth(`/api/avatars/${avatarId}`);
  },
  async listAvatars() {
    return fetchWithAuth('/api/avatars');
  },
  async deleteAvatar(avatarId) {
    return fetchWithAuth(`/api/avatars/${avatarId}`, { method: 'DELETE' });
  },
};
```

---

## 5. VRM 파일 로딩 — URL 소스 변경

### 5-1. 현재 (로컬 파일)

```typescript
// src/app/dev/viewer/page.tsx
const DEFAULT_MODEL_URL = '/models/CustomizableCharacter.vrm';
```

`public/models/` 디렉토리에 VRM 파일을 배치하여 Next.js 정적 서빙.

### 5-2. 백엔드 연결 후 (S3/CDN URL)

```typescript
// 템플릿 API 응답에서 VRM URL을 받음
const template = await api.template.getTemplate('cute');
const modelUrl = template.vrmUrl; // "https://cdn.example.com/templates/cute-v1.vrm"
```

`useVRM(url)` 훅은 URL 문자열만 변경되면 자동으로 새 모델을 로드한다. 프론트엔드 코드 수정 불필요.

### 5-3. CORS 설정 필수

프론트엔드(localhost:3000 또는 프로덕션 도메인)에서 S3/CDN의 VRM 파일을 직접 fetch하므로, **S3 버킷 또는 CDN에 CORS 허용**이 필요하다:

```
Access-Control-Allow-Origin: https://your-domain.com
Access-Control-Allow-Methods: GET
Access-Control-Allow-Headers: Range
```

`Range` 헤더 허용은 대용량 VRM 파일 부분 로딩에 필요할 수 있다.

---

## 6. 인증 연동

### 6-1. 프론트엔드에서 필요한 것

```typescript
// 모든 API 요청에 포함
Authorization: Bearer <access_token>
```

### 6-2. 필요 인증 엔드포인트

| HTTP | URL | 설명 |
|------|-----|------|
| `POST /api/auth/login` | `{ provider: "google", token: "..." }` → `{ user, accessToken }` |
| `POST /api/auth/register` | `{ email, password }` → `{ user, accessToken }` |
| `POST /api/auth/refresh` | `{ refreshToken }` → `{ accessToken }` |
| `GET /api/users/me` | 현재 사용자 정보 |

### 6-3. 토큰 관리 방식 협의 필요

| 방식 | 장점 | 단점 |
|------|------|------|
| **JWT in localStorage** | 구현 간단 | XSS 취약 |
| **JWT in httpOnly cookie** | XSS 안전 | CSRF 대응 필요, SSR 호환 용이 |
| **Access + Refresh 토큰** | 보안 강화 | 갱신 로직 복잡 |

프론트엔드는 어떤 방식이든 대응 가능. 백엔드에서 결정 후 공유 필요.

---

## 7. 에러 응답 규격 (제안)

프론트엔드에서 일관된 에러 처리를 위해 통일된 에러 응답 형식 필요:

```json
{
  "error": {
    "code": "AVATAR_NOT_FOUND",
    "message": "아바타를 찾을 수 없습니다",
    "status": 404
  }
}
```

### 주요 에러 코드 (제안)

| 코드 | HTTP | 설명 |
|------|------|------|
| `UNAUTHORIZED` | 401 | 인증 필요 / 토큰 만료 |
| `FORBIDDEN` | 403 | 권한 없음 (타인의 아바타) |
| `AVATAR_NOT_FOUND` | 404 | 아바타 ID 없음 |
| `TEMPLATE_NOT_FOUND` | 404 | 템플릿 ID 없음 |
| `VERSION_LIMIT_EXCEEDED` | 400 | 버전 5개 초과 |
| `INSUFFICIENT_CREDITS` | 402 | 크레딧 부족 |
| `PIPELINE_FAILED` | 500 | 파이프라인 단계 실패 |
| `VARCO_TIMEOUT` | 504 | VARCO API 타임아웃 |

---

## 8. 저장 타이밍 전략

### 8-1. 현재 동작

- 슬라이더 조작 → Zustand Store만 업데이트 (메모리)
- "버전 저장" 버튼 → localStorage에 스냅샷 저장
- 페이지 닫으면 미저장 편집 내용은 유실됨

### 8-2. 백엔드 연결 후 권장 전략

```
[편집 중]
  슬라이더 조작 → Zustand만 (서버 호출 없음)
                    │
                    ├─ 자동 저장: 마지막 조작 후 5초 무조작 시 PUT /api/avatars/{id}/parameters
                    │             (디바운스, 선택적으로 구현)
                    │
                    └─ 수동 저장: "버전 저장" 버튼 클릭 시 POST /api/avatars/{id}/versions

[페이지 이탈]
  beforeunload 이벤트 → 미저장 변경 경고 표시
```

### 8-3. 서버 부하 고려

| 동작 | 빈도 | 데이터 크기 |
|------|------|------------|
| 슬라이더 조작 | 초당 10~60회 | 서버 호출 없음 |
| 자동 저장 | 편집 세션당 수~수십 회 | ~2-5KB JSON |
| 버전 저장 | 사용자 명시적 클릭 | ~30KB (썸네일 포함) |
| VRM 익스포트 | 세션당 1~3회 | 서버사이드 처리 |

---

## 9. 파일 구조 요약

```
src/
├── app/dev/viewer/page.tsx         # 개발용 뷰어 (현재 메인 페이지)
│
├── components/
│   ├── viewer/
│   │   ├── ThreeJSViewer.tsx       # R3F Canvas + 씬 구성
│   │   ├── VRMModel.tsx            # VRM 로드 + 매 프레임 편집 적용
│   │   ├── CameraControls.tsx      # 360도 회전/줌/패닝
│   │   ├── SceneLighting.tsx       # 3점 조명
│   │   ├── WebGLCheck.tsx          # WebGL 2.0 감지
│   │   └── ViewerToolbar.tsx       # 뷰어 상단 도구
│   └── editor/
│       ├── MorphTargetSlider.tsx    # 모프 타겟 슬라이더
│       ├── BoneScaleSlider.tsx      # 본 스케일 슬라이더
│       ├── MaterialEditor.tsx       # 재질/색상 에디터
│       ├── ColorPicker.tsx          # 컬러 피커
│       ├── VersionPanel.tsx         # 버전 저장/비교/복원
│       ├── TemplateSelector.tsx     # 템플릿 선택 UI
│       ├── PresetGrid.tsx           # 스타일 프리셋 그리드
│       ├── QuickPresets.tsx         # 빠른 프리셋 버튼
│       ├── SliderSearch.tsx         # 슬라이더 검색/필터
│       └── CollapsibleSection.tsx   # 접을 수 있는 섹션
│
├── hooks/
│   ├── useVRM.ts                   # VRM 로딩 훅 (URL → VRM 객체)
│   ├── useCanvasScreenshot.ts      # Canvas 캡처 (썸네일용)
│   ├── useKeyboardShortcuts.ts     # 키보드 단축키
│   └── useTheme.ts                 # 다크/라이트 테마
│
├── stores/
│   └── editorStore.ts              # ★ Zustand 중앙 상태 (핵심)
│
├── lib/
│   ├── api/
│   │   ├── types.ts                # ★ API 인터페이스 정의 (계약서)
│   │   ├── local.ts                # localStorage 구현 (현재)
│   │   ├── provider.tsx            # React Context 주입
│   │   └── index.ts
│   ├── vrm/
│   │   ├── loader.ts               # GLTFLoader + VRMLoaderPlugin
│   │   └── materials.ts            # 재질 감지/적용 유틸
│   ├── storage/
│   │   └── versions.ts             # 버전 localStorage 유틸
│   └── webgl/
│       └── detect.ts               # WebGL 2.0 감지
│
├── types/
│   ├── editor.ts                   # ★ 편집 데이터 타입 (AvatarParameters 등)
│   ├── template.ts                 # 템플릿 메타데이터 타입
│   └── preset.ts                   # 프리셋 타입
│
└── data/
    ├── templates.ts                # 하드코딩 템플릿 데이터 (→ API로 교체 대상)
    └── presets.ts                  # 하드코딩 프리셋 데이터
```

**★ 표시 파일이 백엔드 연동 시 핵심 참조 대상.**

---

## 10. 체크리스트 — 백엔드 연동 전 합의 필요 사항

- [ ] `AvatarParameters` JSON 스키마를 DB에 그대로 JSONB로 저장할 것인지 확인
- [ ] VRM 파일 저장소 (S3) CORS 설정
- [ ] 인증 방식 결정 (JWT cookie vs header, 토큰 갱신 전략)
- [ ] 에러 응답 형식 통일
- [ ] 버전 썸네일 저장 방식 (base64 inline vs 별도 업로드)
- [ ] 파이프라인 진행률 전달 방식 (WebSocket vs SSE vs polling)
- [ ] 자동 저장 구현 여부 및 디바운스 간격
- [ ] API 기본 URL 및 환경변수 네이밍 (`NEXT_PUBLIC_API_URL`)
- [ ] 개발 환경 프록시 설정 (Next.js rewrites로 CORS 우회할지)
