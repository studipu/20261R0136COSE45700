"""
landmark 좌표 기반 유틸리티.
Gemini가 추출한 reference + offset → 이미지 픽셀 좌표 → UV 좌표 변환.

landmark 인덱스 (kanosawa CFA 24pt):
  0: 왼쪽 얼굴 윤곽
  1: 턱
  2: 오른쪽 얼굴 윤곽
  3~5: 왼쪽 눈썹
  6~8: 오른쪽 눈썹
  9: 코
  10: 왼쪽 눈 왼쪽 끝
  11: 왼쪽 눈 위
  12: 왼쪽 눈 오른쪽 끝
  13: 왼쪽 눈 아래
  14: 왼쪽 눈 중심
  15: 오른쪽 눈 왼쪽 끝
  16: 오른쪽 눈 위
  17: 오른쪽 눈 오른쪽 끝
  18: 오른쪽 눈 아래
  19: 오른쪽 눈 중심
  20: 입 왼쪽
  21: 입 위
  22: 입 오른쪽
  23: 입 아래
"""
import numpy as np


# UV Y 좌표 보간 앵커 (이미지 Y 비율 → UV Y 비율)
# 실측 기반: 눈=0.487, 코=0.552, 입=0.600
_IMG_Y_ANCHORS = [0.00, 0.487, 0.552, 0.600, 1.00]
_UV_Y_ANCHORS  = [0.30, 0.541, 0.660, 0.760, 0.95]

# UV X는 이미지 X와 동일 비율 유지
# UV X 앵커 (이미지 X 비율 → UV X 비율)
# 이미지 눈 중심 X(0.404/0.599) → UV 볼 X(0.33/0.67)
# 실측: 이미지 눈 중심 X(0.404/0.599) → UV X(0.37/0.63) 조정
_IMG_X_ANCHORS = [0.00, 0.34, 0.404, 0.50, 0.599, 0.66, 1.00]
_UV_X_ANCHORS  = [0.00, 0.20, 0.370, 0.50, 0.630, 0.80, 1.00]

def img_to_uv(img_x: float, img_y: float, img_w: int, img_h: int) -> tuple:
    """이미지 픽셀 좌표 → UV 비율 좌표 (0~1)"""
    x_ratio = img_x / img_w
    y_ratio = img_y / img_h
    uv_y = float(np.interp(y_ratio, _IMG_Y_ANCHORS, _UV_Y_ANCHORS))
    uv_x = float(np.interp(x_ratio, _IMG_X_ANCHORS, _UV_X_ANCHORS))
    return uv_x, uv_y


def get_reference_point(lm: list, reference: str) -> np.ndarray:
    """reference 문자열 → 이미지 픽셀 좌표"""
    lm = np.array(lm)

    # 좌우 대칭 쌍의 Y를 평균으로 강제
    eye_y_avg   = (lm[14][1] + lm[19][1]) / 2
    cheek_y_avg = (lm[13][1] * 0.85 + lm[1][1] * 0.15 +
                   lm[18][1] * 0.85 + lm[1][1] * 0.15) / 2

    ref_map = {
        "left_eye":    np.array([lm[14][0], eye_y_avg]),
        "right_eye":   np.array([lm[19][0], eye_y_avg]),
        "nose":        lm[9],
        "mouth":       (lm[20] + lm[22]) / 2,
        "left_cheek":  np.array([
            lm[14][0] * 0.7 + lm[0][0] * 0.3,
            cheek_y_avg
        ]),
        "right_cheek": np.array([
            lm[19][0] * 0.7 + lm[2][0] * 0.3,
            cheek_y_avg
        ]),
        "forehead":    (lm[3] + lm[8]) / 2 + np.array([0, -60]),
        "chin":        lm[1],
    }
    return ref_map.get(reference, lm[14])


def get_eye_unit(lm: list, side: str) -> tuple:
    """
    눈 크기를 단위로 반환 (offset 계산용).
    좌우 평균으로 대칭 강제.
    반환: (eye_w, eye_h) 픽셀
    """
    lm = np.array(lm)
    left_w  = abs(lm[12][0] - lm[10][0])
    left_h  = abs(lm[13][1] - lm[11][1])
    right_w = abs(lm[17][0] - lm[15][0])
    right_h = abs(lm[18][1] - lm[16][1])
    avg_w = (left_w + right_w) / 2
    avg_h = (left_h + right_h) / 2
    return float(avg_w), float(avg_h)


def marking_to_img_coords(marking: dict, lm: list) -> tuple:
    """
    Gemini marking JSON → 이미지 픽셀 좌표 (x, y)

    marking 필드:
      reference: "left_eye/right_eye/nose/mouth/left_cheek/right_cheek/forehead/chin"
      offset_x:  "far_left/left/center/right/far_right"
      offset_y:  "far_above/above/same/below/far_below"
      side:      "left/right/center"
    """
    reference = marking.get("reference", "left_eye")
    offset_x  = marking.get("offset_x", "center")
    offset_y  = marking.get("offset_y", "same")
    side      = marking.get("side", "left")

    # reference 기준점
    base = get_reference_point(lm, reference)

    # 눈 크기 단위 (offset 스케일)
    eye_side = "right" if "right" in reference else "left"
    eye_w, eye_h = get_eye_unit(lm, eye_side)

    # offset 매핑 (눈 크기 배수)
    x_offset_map = {
        "far_left":  -eye_w * 1.2,
        "left":      -eye_w * 0.6,
        "center":     0,
        "right":      eye_w * 0.6,
        "far_right":  eye_w * 1.2,
    }
    y_offset_map = {
        "far_above": -eye_h * 2.0,
        "above":     -eye_h * 1.0,
        "same":       0,
        "center":     0,  # Gemini가 same 대신 center를 쓸 경우 fallback
        "below":      eye_h * 1.0,
        "far_below":  eye_h * 2.0,
    }

    dx = x_offset_map.get(offset_x, 0)
    dy = y_offset_map.get(offset_y, 0)

    x = base[0] + dx
    y = base[1] + dy
    return float(x), float(y)


def marking_to_uv_coords(marking: dict, lm: list, img_w: int, img_h: int) -> tuple:
    """
    Gemini marking JSON → UV 비율 좌표 (uv_x, uv_y)
    """
    img_x, img_y = marking_to_img_coords(marking, lm)
    uv_x, uv_y = img_to_uv(img_x, img_y, img_w, img_h)
    return uv_x, uv_y


# UV 고정 좌표 (UV_Face.png 실측 + 시각 확인 기반)
UV_LANDMARKS = {
    "eye_y":         0.541,                          # 눈 구멍 중심 Y
    "eye_left_x":    0.341,                          # 왼쪽 눈 중심 X
    "eye_right_x":   0.657,                          # 오른쪽 눈 중심 X
    "nose_y":        0.660,                          # 코 Y
    "mouth_y":       0.760,                          # 입 Y
    "cheek_left_x":  0.341,                          # 왼쪽 볼 X (눈과 동일)
    "cheek_right_x": 0.657,                          # 오른쪽 볼 X
    "cheek_y":       0.541 + (0.660 - 0.541) * 0.8, # 볼 Y (눈~코 사이 80%)
}

def blush_to_uv_coords(position: str) -> tuple:
    """
    blush_position → UV 좌표 직접 반환 (UV 고정값 사용)
    반환: [(left_uv_x, left_uv_y), (right_uv_x, right_uv_y)]
    """
    base_y = UV_LANDMARKS["cheek_y"]

    # position에 따라 Y를 미세 조정
    y_offset_map = {
        "cheek_high":   -0.015,
        "cheek_center":  0.0,
        "cheek_low":     0.015,
    }
    dy = y_offset_map.get(position, 0.0)
    blush_y = base_y + dy

    left_uv  = (UV_LANDMARKS["cheek_left_x"],  blush_y)
    right_uv = (UV_LANDMARKS["cheek_right_x"], blush_y)
    return left_uv, right_uv


def blush_to_img_coords(lm: list, position: str) -> tuple:
    """하위 호환용 — 내부적으로 UV 고정값 사용"""
    # 더 이상 lm 사용 안 함, UV 고정값으로 대체
    return blush_to_uv_coords(position)


if __name__ == "__main__":
    import json
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).parent.parent

    with open(PROJECT_ROOT / "landmarks.json") as f:
        lm_data = json.load(f)
    lm = lm_data[0]["landmarks"]
    img_w, img_h = 1024, 1024

    # 테스트 marking
    test_marking = {
        "type": "mole",
        "reference": "left_eye",
        "offset_x": "center",
        "offset_y": "below",
        "side": "left"
    }

    img_x, img_y = marking_to_img_coords(test_marking, lm)
    uv_x, uv_y = marking_to_uv_coords(test_marking, lm, img_w, img_h)
    print(f"이미지 좌표: ({img_x:.1f}, {img_y:.1f})")
    print(f"UV 좌표:    ({uv_x:.3f}, {uv_y:.3f})")

    # 볼터치 테스트
    left_blush, right_blush = blush_to_img_coords(lm, "cheek_high")
    print(f"\n볼터치 이미지 좌표:")
    print(f"  왼쪽: ({left_blush[0]:.1f}, {left_blush[1]:.1f})")
    print(f"  오른쪽: ({right_blush[0]:.1f}, {right_blush[1]:.1f})")