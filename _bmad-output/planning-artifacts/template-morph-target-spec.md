# 템플릿팀 Morph Target 요구사항 명세서

**작성자:** 백승우 (3D 뷰어 엔지니어)
**대상:** 이현지 (템플릿 구축 리더), 조수빈, 최윤수
**작성일:** 2026-04-23
**상태:** Draft

---

## 1. 개요

3D 아바타 편집기에서 사용자가 슬라이더로 아바타 외형을 세밀하게 조정하려면, 각 템플릿 VRM 모델에 **커스텀 Morph Target (BlendShape/Shape Key)**이 내장되어 있어야 합니다.

현재 Sprint 0에서는 런타임 자동 생성으로 데모를 구현했으나, 프로덕션에서는 Blender에서 정밀하게 스컬프팅한 morph target이 필요합니다.

---

## 2. 필수 Morph Target 목록

### 2-1. 얼굴 (Face)

| 이름 | 설명 | 범위 | 비고 |
|------|------|------|------|
| `face_eye_size` | 눈 전체 크기 (비례 확대/축소) | 0.0 ~ 1.0 | 양쪽 눈 동시 |
| `face_eye_width` | 눈 가로폭 | 0.0 ~ 1.0 | |
| `face_eye_height` | 눈 세로폭 | 0.0 ~ 1.0 | |
| `face_eye_tilt` | 눈매 각도 (올라감/내려감) | 0.0 ~ 1.0 | 0.5 = 기본 |
| `face_eye_spacing` | 눈 사이 간격 | 0.0 ~ 1.0 | |
| `face_eyebrow_height` | 눈썹 높이 | 0.0 ~ 1.0 | |
| `face_eyebrow_thickness` | 눈썹 두께 | 0.0 ~ 1.0 | |
| `face_nose_height` | 코 높이 (세로 위치) | 0.0 ~ 1.0 | |
| `face_nose_width` | 코 너비 | 0.0 ~ 1.0 | |
| `face_nose_length` | 코 길이 (돌출 정도) | 0.0 ~ 1.0 | |
| `face_jaw_width` | 턱 너비 | 0.0 ~ 1.0 | |
| `face_jaw_length` | 턱 길이 (V라인 정도) | 0.0 ~ 1.0 | |
| `face_chin_shape` | 턱 끝 형태 (둥근/뾰족) | 0.0 ~ 1.0 | |
| `face_cheek_fullness` | 볼 볼륨 | 0.0 ~ 1.0 | |
| `face_lip_thickness` | 입술 두께 | 0.0 ~ 1.0 | |
| `face_lip_width` | 입 너비 | 0.0 ~ 1.0 | |
| `face_forehead_height` | 이마 높이 | 0.0 ~ 1.0 | |
| `face_forehead_width` | 이마 너비 | 0.0 ~ 1.0 | |

### 2-2. 체형 (Body) — Morph Target 권장, Bone Scale 병행

| 이름 | 설명 | 범위 |
|------|------|------|
| `body_shoulder_width` | 어깨 너비 | 0.0 ~ 1.0 |
| `body_chest_size` | 가슴 크기 | 0.0 ~ 1.0 |
| `body_waist_width` | 허리 너비 | 0.0 ~ 1.0 |
| `body_hip_width` | 골반 너비 | 0.0 ~ 1.0 |
| `body_arm_thickness` | 팔 굵기 | 0.0 ~ 1.0 |
| `body_leg_thickness` | 다리 굵기 | 0.0 ~ 1.0 |
| `body_height_ratio` | 상/하체 비율 | 0.0 ~ 1.0 |

---

## 3. 기술 요구사항

### 3-1. 네이밍 규칙

- **접두사**: `face_` (얼굴), `body_` (체형)
- **언더스코어** 구분: `face_eye_size`
- **소문자만 사용**
- 기존 VRM 표준 expression (happy, blink 등)과 **이름 충돌 금지**

### 3-2. 값 범위

- 모든 morph target: **0.0 (최소) ~ 1.0 (최대)**
- 0.5 = 기본 상태 (양방향 조절이 필요한 경우)
- 프론트엔드 슬라이더는 이 범위 내에서 0.01 단위 조절

### 3-3. BlendShape 정렬 (정점 일관성)

**중요:** 여러 morph target을 동시에 적용했을 때 메시가 깨지지 않아야 합니다.

- 모든 morph target은 **동일한 베이스 메시** 기준으로 제작
- Shape Key 간 **정점 인덱스 일관성** 유지
- 극단적 조합 테스트: 모든 슬라이더를 최대/최소로 설정해도 메시 파괴 없어야 함
- 인접 영역의 morph target은 **가중치 블렌딩** 영역이 겹쳐야 자연스러운 전환

### 3-4. VRM 내보내기

- **VRM 1.0** 포맷 사용
- Blender에서 Shape Key로 제작 → VRM Addon for Blender로 내보내기
- 커스텀 morph target은 VRM의 `mesh.primitives[].extras` 또는 `morphTargetNames`에 등록
- VRM 표준 expression (happy, sad, blink 등)은 별도로 유지

### 3-5. 파일 규격

- 각 템플릿별 1개 VRM 파일
- 파일 크기: **20MB 이하** 권장 (웹 로딩 성능)
- 텍스처: **KTX2/Basis** 압축 권장
- 폴리곤 수: **50,000 이하** 권장

---

## 4. 템플릿별 적용

3종 템플릿 (cute / slim / mature) 모두에 동일한 morph target 목록 적용:

| 템플릿 | 특징 | 비고 |
|--------|------|------|
| cute | 2등신~3등신, 큰 눈, 동글 체형 | face_eye_size 기본값이 높음 |
| slim | 6등신~7등신, 날씬한 체형 | body_waist_width 기본값이 낮음 |
| mature | 7등신~8등신, 성숙한 체형 | face_jaw_length 기본값이 높음 |

각 템플릿의 **기본값(default value)**은 해당 스타일을 반영하되, 사용자가 슬라이더로 자유롭게 조절 가능해야 합니다.

---

## 5. 프론트엔드 연동 방식

```
[VRM 파일 로드]
    ↓
[mesh.morphTargetDictionary에서 "face_*", "body_*" 추출]
    ↓
[슬라이더 UI 자동 생성]
    ↓
[슬라이더 조작 → mesh.morphTargetInfluences[index] = value]
    ↓
[실시간 메시 변형 (< 16ms per frame)]
```

프론트엔드는 morph target 이름을 기준으로 자동 인식하므로, 위 네이밍 규칙만 지키면 추가 코드 수정 없이 연동됩니다.

---

## 6. 우선순위

### Phase 1 (Sprint 1 목표)
- `face_eye_size`, `face_eye_width`, `face_eye_height`
- `face_nose_width`, `face_nose_length`
- `face_jaw_width`, `face_jaw_length`
- `face_cheek_fullness`

### Phase 2
- 나머지 얼굴 morph target
- 체형 morph target

---

## 7. 검증 방법

1. VRM 파일을 `public/models/`에 배치
2. `npm run dev` → `http://localhost:3000/dev/viewer` 접속
3. "얼굴 편집" 탭에서 슬라이더 조작
4. 실시간 메시 변형 확인
5. 극단적 조합 테스트 (모든 슬라이더 최대/최소)

---

## 8. 참고 자료

- [VRM 1.0 Specification](https://vrm.dev/en/vrm1/)
- [VRM Addon for Blender](https://github.com/saturday06/VRM-Addon-for-Blender)
- [Blender Shape Key 가이드](https://docs.blender.org/manual/en/latest/animation/shape_keys/index.html)
- PRD: `_bmad-output/planning-artifacts/prd-restructured.md` §7 시스템 설계
