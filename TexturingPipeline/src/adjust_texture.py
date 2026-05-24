"""
마스터 텍스처를 features.json 기반으로 HSV 색조 보정 + 특징 반영.
원본 RGBA PNG의 알파 채널을 그대로 유지.

Usage:
  python3 adjust_texture.py \
    --features features.json \
    --input_dir assets/textures \
    --output_dir adjusted_textures
"""
import cv2
import numpy as np
import json
import os
import shutil
import argparse
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))
from landmark_utils import (
    marking_to_uv_coords,
    blush_to_img_coords,
    img_to_uv
)


def load_features(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_rgba(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img.shape[2] == 3:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2BGRA)
    return img


def adjust_hue(
    texture_bgra: np.ndarray,
    target_rgb: list,
    opacity: float = 1.0
) -> np.ndarray:
    """
    알파 > 0인 영역의 Hue/Saturation을 target_rgb 기준으로 보정.
    opacity로 보정 강도 조절 (0.0 = 원본 유지, 1.0 = 완전 보정).
    """
    result = texture_bgra.copy()
    bgr = texture_bgra[:, :, :3]
    alpha = texture_bgra[:, :, 3]

    hsv_orig = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv_new = hsv_orig.copy()

    target_bgr = np.uint8([[[target_rgb[2], target_rgb[1], target_rgb[0]]]])
    target_hsv = cv2.cvtColor(target_bgr, cv2.COLOR_BGR2HSV)[0][0].astype(np.float32)

    ys, xs = np.where(alpha > 0)
    if len(ys) == 0:
        return result

    region = hsv_orig[ys, xs]
    orig_s_mean = np.mean(region[:, 1]) + 1e-6

    hsv_new[ys, xs, 0] = target_hsv[0]

    # 원본 채도가 낮을 때(무채색에 가까울 때) 타겟 채도를 직접 적용
    # 비율 곱셈 대신 원본 채도 + 타겟 채도 블렌딩으로 처리
    if orig_s_mean < 30:
        # 채도 낮은 경우: 타겟 채도를 opacity 비율로 직접 추가
        hsv_new[ys, xs, 1] = np.clip(
            region[:, 1] + target_hsv[1] * opacity * 0.5, 0, 255
        )
    else:
        hsv_new[ys, xs, 1] = np.clip(
            region[:, 1] * (target_hsv[1] / orig_s_mean), 0, 255
        )

    # opacity 블렌딩
    hsv_blended = hsv_orig.copy()
    hsv_blended[ys, xs] = (
        hsv_orig[ys, xs] * (1 - opacity) + hsv_new[ys, xs] * opacity
    )

    new_bgr = cv2.cvtColor(hsv_blended.astype(np.uint8), cv2.COLOR_HSV2BGR)
    result[:, :, :3] = new_bgr
    result[:, :, 3] = alpha
    return result


# UV 좌표 상수 (UV_Face.png 실측 + uv_grid 시각 확인 기반)
# 눈 구멍: Y=0.541 (실측), 좌X=0.341, 우X=0.657
# 볼터치:  Y=0.62, X=0.25(좌)/0.75(우) (시각 확인)
# 점:      Y=0.64, X=0.33(좌)/0.67(우) (시각 확인)
# 코:      Y=0.66 (실측)
# 입:      Y=0.76 (실측)
UV_FACE = {
    "eye_y":          0.541,
    "eye_left_x":     0.341,
    "eye_right_x":    0.657,
    "cheek_high_y":   0.600,
    "cheek_center_y": 0.620,  # 확정값
    "cheek_low_y":    0.645,
    "cheek_left_x":   0.250,  # 확정값
    "cheek_right_x":  0.750,  # 확정값
    "nose_y":         0.660,
    "mouth_y":        0.760,
}

# 정면 얼굴 → UV Y 좌표 보간 앵커
# 정면 기준점: 눈=0.40, 볼=0.65, 코=0.67, 입=0.75
# UV 실측값:   눈=0.541, 볼=0.620, 코=0.660, 입=0.760
_FACE_Y_ANCHORS = [0.00,  0.40,  0.65,  0.67,  0.75,  1.00]
_UV_Y_ANCHORS   = [0.30,  0.541, 0.620, 0.660, 0.760, 0.95]

def face_to_uv(x_ratio: float, y_ratio: float) -> tuple:
    """
    정면 얼굴 비율(0~1) → Face UV 좌표 변환.
    실측 앵커 기반 선형 보간.
    """
    uv_y = float(np.interp(y_ratio, _FACE_Y_ANCHORS, _UV_Y_ANCHORS))
    uv_x = x_ratio
    return uv_x, uv_y


def add_blush(
    texture_bgra: np.ndarray,
    blush_color_rgb: list,
    blush_opacity: float,
    position: str,
    lm: list,
    img_w: int = 1024,
    img_h: int = 1024
) -> np.ndarray:
    """볼터치 오버레이 추가 — landmark 기반 UV 좌표"""
    result = texture_bgra.copy()
    h, w = result.shape[:2]

    # UV 고정 좌표 직접 사용 (이미지 좌표 변환 불필요)
    from landmark_utils import blush_to_uv_coords
    luv, ruv = blush_to_uv_coords(position)

    centers = [
        (int(luv[0] * w), int(luv[1] * h)),
        (int(ruv[0] * w), int(ruv[1] * h)),
    ]

    blush_bgr = (blush_color_rgb[2], blush_color_rgb[1], blush_color_rgb[0])
    radius_x = int(w * 0.07)
    radius_y = int(h * 0.05)

    # 볼터치 마스크 생성 (볼터치 영역만 따로)
    blush_mask = np.zeros((h, w), dtype=np.float32)
    for cx, cy in centers:
        cv2.ellipse(blush_mask, (cx, cy), (radius_x, radius_y), 0, 0, 360, 1.0, -1)

    kernel_size = int(w * 0.12) | 1
    blush_mask_blurred = cv2.GaussianBlur(blush_mask, (kernel_size, kernel_size), 0)
    blush_mask_blurred = np.clip(blush_mask_blurred * blush_opacity, 0, 1)

    alpha = result[:, :, 3]
    valid = alpha > 0

    # 볼터치 색상 배열 생성
    blush_layer = np.full((h, w, 3), blush_bgr, dtype=np.float32)

    # 볼터치 마스크 영역에서만 원본과 블렌딩
    mask_3ch = blush_mask_blurred[:, :, np.newaxis]
    result[:, :, :3] = np.where(
        (mask_3ch > 0) & (alpha[:, :, np.newaxis] > 0),
        np.clip(
            result[:, :, :3].astype(np.float32) * (1 - mask_3ch) +
            blush_layer * mask_3ch,
            0, 255
        ).astype(np.uint8),
        result[:, :, :3]
    )

    return result


def add_markings(
    texture_bgra: np.ndarray,
    markings: list,
    lm: list,
    img_w: int = 1024,
    img_h: int = 1024
) -> np.ndarray:
    """점/문양 추가 — landmark 기반 UV 좌표"""
    result = texture_bgra.copy()
    h, w = result.shape[:2]

    size_radius = {"tiny": 3, "small": 5, "medium": 8, "large": 12}

    # 같은 reference를 가진 left/right 쌍의 UV Y를 평균으로 대칭화
    uv_coords = {}
    for marking in markings:
        uv_x, uv_y = marking_to_uv_coords(marking, lm, img_w, img_h)
        uv_coords[id(marking)] = (uv_x, uv_y)

    # reference별로 left/right 쌍 찾아서 Y 평균화
    ref_groups = {}
    for marking in markings:
        ref = marking.get("reference", "")
        side = marking.get("side", "center")
        if side in ("left", "right"):
            if ref not in ref_groups:
                ref_groups[ref] = {}
            ref_groups[ref][side] = marking

    for ref, sides in ref_groups.items():
        if "left" in sides and "right" in sides:
            l_uv = uv_coords[id(sides["left"])]
            r_uv = uv_coords[id(sides["right"])]
            avg_y = (l_uv[1] + r_uv[1]) / 2
            uv_coords[id(sides["left"])]  = (l_uv[0], avg_y)
            uv_coords[id(sides["right"])] = (r_uv[0], avg_y)

    for marking in markings:
        uv_x, uv_y = uv_coords[id(marking)]
        cx = int(uv_x * w)
        cy = int(uv_y * h)
        color_rgb = marking.get("color", [40, 20, 20])
        color_bgra = (color_rgb[2], color_rgb[1], color_rgb[0], 255)
        r = size_radius.get(marking.get("size", "tiny"), 3)
        mtype = marking.get("type", "mole")

        if mtype == "mole":
            cv2.circle(result, (cx, cy), r, color_bgra, -1)
            cv2.circle(result, (cx, cy), r + 2, (*color_bgra[:3], 60), 1)

        elif mtype == "star":
            pts = []
            for i in range(5):
                angle = np.radians(i * 72 - 90)
                pts.append([cx + int(r * 2 * np.cos(angle)),
                             cy + int(r * 2 * np.sin(angle))])
                angle2 = np.radians(i * 72 - 90 + 36)
                pts.append([cx + int(r * np.cos(angle2)),
                             cy + int(r * np.sin(angle2))])
            cv2.fillPoly(result, [np.array(pts)], color_bgra)

        elif mtype == "teardrop":
            cv2.circle(result, (cx, cy), r, color_bgra, -1)
            tip = np.array([[cx, cy + r * 3], [cx - r, cy], [cx + r, cy]])
            cv2.fillPoly(result, [tip], color_bgra)

        elif mtype in ["triangle", "diamond"]:
            if mtype == "triangle":
                pts = np.array([[cx, cy - r*2], [cx - r, cy + r], [cx + r, cy + r]])
            else:
                pts = np.array([[cx, cy - r*2], [cx + r, cy], [cx, cy + r*2], [cx - r, cy]])
            cv2.fillPoly(result, [pts], color_bgra)

        else:
            # 기타: 작은 원으로 fallback
            cv2.circle(result, (cx, cy), r, color_bgra, -1)

    return result


def adjust_face(texture_bgra: np.ndarray, features: dict, lm: list = None, img_w: int = 1024, img_h: int = 1024) -> np.ndarray:
    face = features["face"]
    result = adjust_hue(texture_bgra, face["skin_tone"])

    if lm and face.get("blush_present"):
        result = add_blush(
            result,
            face["blush_color"],
            face.get("blush_opacity", 0.6),
            face.get("blush_position", "cheek_center"),
            lm, img_w, img_h
        )

    if lm and face.get("markings"):
        result = add_markings(result, face["markings"], lm, img_w, img_h)

    return result


def adjust_eyebrow(texture_bgra: np.ndarray, features: dict) -> np.ndarray:
    eyebrow = features["eyebrow"]
    opacity = eyebrow.get("opacity", 1.0)
    result = adjust_hue(texture_bgra, eyebrow["color"], opacity)
    return result


def adjust_eyeline(texture_bgra: np.ndarray, features: dict) -> np.ndarray:
    eyeline = features["eyeline"]
    result = texture_bgra.copy()
    h, w = result.shape[:2]
    alpha = result[:, :, 3]

    # 상단 40% = 쌍커풀 라인 영역, 하단 60% = 아이라인 영역
    crease_boundary = int(h * 0.4)

    # 쌍커풀 영역 마스크
    crease_mask = np.zeros((h, w), dtype=np.uint8)
    crease_mask[:crease_boundary, :] = alpha[:crease_boundary, :]

    # 아이라인 영역 마스크
    liner_mask = np.zeros((h, w), dtype=np.uint8)
    liner_mask[crease_boundary:, :] = alpha[crease_boundary:, :]

    # 쌍커풀: eyelid_crease_color 기반, 깊이에 따라 opacity 조정
    crease_depth_opacity = {"shallow": 0.4, "medium": 0.7, "deep": 1.0}
    crease_opacity = crease_depth_opacity.get(
        eyeline.get("eyelid_crease_depth", "medium"), 0.7
    ) if eyeline.get("has_eyelid_crease") else 0.0

    if crease_opacity > 0:
        temp = result.copy()
        temp[:, :, 3] = crease_mask
        temp = adjust_hue(temp, eyeline["eyelid_crease_color"], crease_opacity)
        valid = crease_mask > 0
        result[valid] = temp[valid]

    # 아이라인: eyeliner_color 기반
    liner_thickness_opacity = {"thin": 0.7, "medium": 0.9, "thick": 1.0}
    liner_opacity = liner_thickness_opacity.get(
        eyeline.get("eyeliner_thickness", "medium"), 0.9
    )
    temp = result.copy()
    temp[:, :, 3] = liner_mask
    temp = adjust_hue(temp, eyeline["eyeliner_color"], liner_opacity)
    valid = liner_mask > 0
    result[valid] = temp[valid]

    result[:, :, 3] = alpha
    return result


def adjust_pupil(texture_bgra: np.ndarray, features: dict) -> np.ndarray:
    """
    BaseTexture 원본 질감을 유지하면서 색상만 위치별로 보정.
    하이라이트는 반투명 오버레이로만 적용.
    """
    pupil = features.get("pupil", {})
    h, w = texture_bgra.shape[:2]
    result = texture_bgra.copy()
    alpha = texture_bgra[:, :, 3]

    def rgb2bgr(c): return (c[2], c[1], c[0])

    top    = np.array(rgb2bgr(pupil.get("iris_top_color",    [150, 100, 200])), dtype=np.float32)
    bottom = np.array(rgb2bgr(pupil.get("iris_bottom_color", [200, 180, 220])), dtype=np.float32)
    left   = np.array(rgb2bgr(pupil.get("iris_left_color",   [160, 120, 180])), dtype=np.float32)
    right  = np.array(rgb2bgr(pupil.get("iris_right_color",  [160, 120, 180])), dtype=np.float32)
    center = np.array(rgb2bgr(pupil.get("iris_center_color", [130, 100, 160])), dtype=np.float32)

    # UV 기반 좌/우 눈 영역
    eyes = [
        {"cx": int(0.250 * w), "cy": int(0.512 * h), "rx": int(0.115 * w), "ry": int(0.260 * h)},
        {"cx": int(0.750 * w), "cy": int(0.512 * h), "rx": int(0.115 * w), "ry": int(0.260 * h)},
    ]

    def apply_pupil_darkening(img, cx, cy, rx, ry, pupil_ratio, pupil_color_bgr, pupil_cx_offset=6):
        """동공 색상 적용 + 경계 안쪽으로 어두운 림 효과"""
        pr  = int(rx * pupil_ratio)
        pry = int(ry * pupil_ratio)
        pcx = cx + pupil_cx_offset

        alpha = img[:, :, 3]
        valid = alpha > 0

        # 동공 마스크
        pupil_mask = np.zeros((h, w), dtype=np.float32)
        cv2.ellipse(pupil_mask, (pcx, cy), (pr, pry), 0, 0, 360, 1.0, -1)

        # 림(limbal ring): 동공 경계 안쪽에서 안으로 페이드아웃 (절반으로 줄임)
        rim_width = max(int(pr * 0.18), 3)
        inner_mask = np.zeros((h, w), dtype=np.float32)
        cv2.ellipse(inner_mask, (pcx, cy), (max(pr-rim_width, 2), max(pry-rim_width, 2)), 0, 0, 360, 1.0, -1)

        rim_mask = np.clip(pupil_mask - inner_mask, 0, 1)
        rim_mask = cv2.GaussianBlur(rim_mask, (rim_width*2+1, rim_width*2+1), 0)

        # HSV로 채도 올리고 Value 낮추는 방식으로 림 처리
        m = rim_mask[:, :, np.newaxis]
        orig_f = img[:, :, :3].astype(np.uint8)
        orig_hsv = cv2.cvtColor(orig_f, cv2.COLOR_BGR2HSV).astype(np.float32)

        # 채도 +40%, Value -20%
        boosted_s = np.clip(orig_hsv[:,:,1] * 1.4, 0, 255)
        lowered_v = np.clip(orig_hsv[:,:,2] * 0.8, 0, 255)

        modified_hsv = orig_hsv.copy()
        modified_hsv[:,:,1] = boosted_s
        modified_hsv[:,:,2] = lowered_v
        modified_bgr = cv2.cvtColor(modified_hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)

        img[:, :, :3] = np.where(
            (rim_mask[:, :, np.newaxis] > 0) & valid[:, :, np.newaxis],
            np.clip(orig_f.astype(np.float32) * (1 - m) + modified_bgr * m, 0, 255).astype(np.uint8),
            img[:, :, :3]
        )
        return img

    for eye in eyes:
        cx, cy, rx, ry = eye["cx"], eye["cy"], eye["rx"], eye["ry"]

        for py in range(max(0, cy - ry), min(h, cy + ry)):
            for px in range(max(0, cx - rx), min(w, cx + rx)):
                if alpha[py, px] == 0:
                    continue

                nx = (px - cx) / rx  # -1~1
                ny = (py - cy) / ry  # -1~1
                if nx*nx + ny*ny > 1.0:
                    continue

                # 5방향 가중치 보간으로 타겟 색상 계산
                w_top    = max(0, -ny)
                w_bottom = max(0,  ny)
                w_left   = max(0, -nx)
                w_right  = max(0,  nx)
                w_center = max(0, 1 - (abs(nx) + abs(ny)))
                total = w_top + w_bottom + w_left + w_right + w_center + 1e-6

                target_bgr = (
                    top * w_top + bottom * w_bottom +
                    left * w_left + right * w_right +
                    center * w_center
                ) / total

                # 원본 밝기 비율을 타겟 밝기 기준으로 리매핑 후 색상 적용
                orig = result[py, px, :3].astype(np.uint8)
                orig_hsv = cv2.cvtColor(orig.reshape(1,1,3), cv2.COLOR_BGR2HSV)[0][0].astype(np.float32)
                tgt_hsv  = cv2.cvtColor(target_bgr.reshape(1,1,3).astype(np.uint8), cv2.COLOR_BGR2HSV)[0][0].astype(np.float32)

                orig_v_norm = orig_hsv[2] / 255.0
                tgt_v = tgt_hsv[2]
                remapped_v = np.clip(tgt_v * 0.7 + orig_v_norm * tgt_v * 0.6, 0, 255)

                new_hsv = np.array([tgt_hsv[0], tgt_hsv[1], remapped_v], dtype=np.uint8)
                new_bgr = cv2.cvtColor(new_hsv.reshape(1,1,3), cv2.COLOR_HSV2BGR)[0][0]
                result[py, px, :3] = new_bgr

        # 상단 그라데이션 (눈동자 위쪽 어둡게)
        top_shadow = pupil.get("top_shadow_ratio", 0.3)
        if top_shadow > 0:
            for py in range(max(0, cy - ry), cy):
                for px in range(max(0, cx - rx), min(w, cx + rx)):
                    if result[py, px, 3] == 0:
                        continue
                    nx = (px - cx) / rx
                    ny = (py - cy) / ry
                    if nx*nx + ny*ny > 1.0:
                        continue
                    # 위쪽일수록 강하게 (ny가 -1에 가까울수록)
                    t = (-ny) * top_shadow * 0.6
                    orig_hsv = cv2.cvtColor(
                        result[py, px, :3].reshape(1,1,3), cv2.COLOR_BGR2HSV
                    )[0][0].astype(np.float32)
                    orig_hsv[2] = np.clip(orig_hsv[2] * (1 - t), 0, 255)
                    result[py, px, :3] = cv2.cvtColor(
                        orig_hsv.astype(np.uint8).reshape(1,1,3), cv2.COLOR_HSV2BGR
                    )[0][0]

        # 동공 경계 어둡게 + 블렌딩 (고정 위치/크기)
        pupil_color_bgr = tuple(reversed(pupil.get("pupil_color", [20, 10, 20])))
        PUPIL_RATIO = 0.35   # BaseTexture 기준 고정값
        pupil_offset = 6 if eye == eyes[0] else -6
        result = apply_pupil_darkening(result, cx, cy, rx, ry, PUPIL_RATIO, pupil_color_bgr, pupil_cx_offset=pupil_offset)



    return result


def process(input_dir: str, output_dir: str, features: dict):
    os.makedirs(output_dir, exist_ok=True)

    # landmarks 로드
    lm = None
    lm_path = os.path.join(os.path.dirname(args.features if hasattr(args, 'features') else '.'), "landmarks.json")
    landmarks_path = Path(args.features).parent / "landmarks.json"
    if landmarks_path.exists():
        with open(landmarks_path) as f:
            lm_data = json.load(f)
        lm = lm_data[0]["landmarks"] if lm_data else None
        print(f"landmarks.json 로드 완료: {len(lm)}개 포인트\n")
    else:
        print("landmarks.json 없음 — blush/marking 적용 스킵\n")

    generate_targets = [
        ("BaseTexture_Generate_Face.png",    adjust_face,    "Face 피부톤 + 볼터치 + 점"),
        ("BaseTexture_Generate_Eyebrow.png", adjust_eyebrow, "Eyebrow 눈썹"),
        ("BaseTexture_Generate_Eyeline.png", adjust_eyeline, "Eyeline 쌍커풀 + 아이라인"),
        ("BaseTexture_Generate_Pupil.png",   adjust_pupil,   "Pupil 눈동자"),
    ]

    static_targets = [
        "BaseTexture_Static_EyeWhite.png",
        "BaseTexture_Static_EyeHighlight.png",
        "BaseTexture_Static_MouthInside.png",
    ]

    print("=== Generate 텍스처 보정 ===\n")
    for tex_name, adjust_fn, label in generate_targets:
        print(f"  [{label}]")
        tex_path = os.path.join(input_dir, tex_name)
        out_path = os.path.join(output_dir, tex_name)

        if not Path(tex_path).exists():
            print(f"    건너뜀: {tex_path} 없음\n")
            continue

        texture = read_rgba(tex_path)
        h, w = texture.shape[:2]
        valid_px = np.count_nonzero(texture[:, :, 3])
        print(f"    텍스처: {w}x{h}, 유효 픽셀: {valid_px}")

        if adjust_fn == adjust_face:
            result = adjust_fn(texture, features, lm)
        else:
            result = adjust_fn(texture, features)
        cv2.imwrite(out_path, result)
        print(f"    저장: {out_path}\n")

    print("=== Static 텍스처 복사 ===\n")
    for name in static_targets:
        src = os.path.join(input_dir, name)
        dst = os.path.join(output_dir, name)
        if Path(src).exists():
            shutil.copy2(src, dst)
            print(f"  복사: {name}")
        else:
            print(f"  건너뜀: {name} 없음")

    print(f"\n완료. 결과 폴더: {output_dir}")


if __name__ == "__main__":
    # 프로젝트 루트 = src/ 의 상위 폴더
    PROJECT_ROOT = Path(__file__).parent.parent

    parser = argparse.ArgumentParser()
    parser.add_argument("--features",   default=str(PROJECT_ROOT / "features.json"))
    parser.add_argument("--input_dir",  default=str(PROJECT_ROOT / "assets/textures"))
    parser.add_argument("--output_dir", default=str(PROJECT_ROOT / "output"))
    args = parser.parse_args()

    features = load_features(args.features)
    print(f"특징값 로드 완료: {args.features}\n")

    process(args.input_dir, args.output_dir, features)