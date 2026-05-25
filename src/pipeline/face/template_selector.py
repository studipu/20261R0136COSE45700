"""
특징 벡터 → VTuber 템플릿 선택 + 슬라이더 초기값 매핑 (Stage 5-6)

cute  : 소두, 큰 눈, 둥근 얼굴 (아이돌/귀여운 스타일)
slim  : 표준 비율, 날카로운 인상 (일반/세련된 스타일)
mature: 성인 비율, 디테일한 얼굴 (성숙/리얼 스타일)

주의: _TEMPLATE_REFS 의 수치는 PoC 플레이스홀더.
      실제 VRoid 템플릿 3종을 렌더/추출한 후 여기에 반영 필요.
"""

from __future__ import annotations

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
from dataclasses import dataclass
from feature_extractor import FaceFeatureVector


TEMPLATE_NAMES = ("cute", "slim", "mature")


# ---------------------------------------------------------------------------
# 각 템플릿의 레퍼런스 특징 벡터
# Sprint 0에서 실제 VRoid 템플릿 이미지를 extract_features()로 추출해 여기에 채울 것
# ---------------------------------------------------------------------------
_TEMPLATE_REFS: dict[str, FaceFeatureVector] = {
    # NOTE: placeholder values — replace with extract_features() output from
    # actual VRoid template renders once they are available.
    "cute": FaceFeatureVector(
        eye_aspect_ratio=0.55, eye_distance_ratio=0.58, face_width_height_ratio=1.30,
        nose_height_ratio=0.08, nose_width_ratio=0.38, mouth_width_ratio=0.14,
        jaw_width_ratio=0.68, forehead_ratio=0.50, chin_ratio=0.50,
        eye_width_ratio=0.0, eye_height_ratio=0.0, eye_rot=0.0,
        eye_front_height=0.0, eye_front_flat=0.5, eye_tail_height=0.0,
        eye_top_lid_flat=0.5, eye_lower_lid_flat=0.5,
        eye_top_lid_down=0.3, eye_lower_lid_up=0.3,
        brow_dist_ratio=0.0, brow_height_ratio=0.0, brow_rot=0.0, brow_width_ratio=0.0,
        mouth_corner_ratio=0.0, mouth_height_ratio=0.0, nose_under_nose_ratio=0.0,
    ),
    "slim": FaceFeatureVector(
        eye_aspect_ratio=0.38, eye_distance_ratio=0.52, face_width_height_ratio=1.15,
        nose_height_ratio=0.12, nose_width_ratio=0.34, mouth_width_ratio=0.17,
        jaw_width_ratio=0.72, forehead_ratio=0.52, chin_ratio=0.48,
        eye_width_ratio=0.0, eye_height_ratio=0.0, eye_rot=0.0,
        eye_front_height=0.0, eye_front_flat=0.5, eye_tail_height=0.0,
        eye_top_lid_flat=0.5, eye_lower_lid_flat=0.5,
        eye_top_lid_down=0.3, eye_lower_lid_up=0.3,
        brow_dist_ratio=0.0, brow_height_ratio=0.0, brow_rot=0.0, brow_width_ratio=0.0,
        mouth_corner_ratio=0.0, mouth_height_ratio=0.0, nose_under_nose_ratio=0.0,
    ),
    "mature": FaceFeatureVector(
        eye_aspect_ratio=0.28, eye_distance_ratio=0.48, face_width_height_ratio=1.05,
        nose_height_ratio=0.16, nose_width_ratio=0.32, mouth_width_ratio=0.20,
        jaw_width_ratio=0.76, forehead_ratio=0.54, chin_ratio=0.46,
        eye_width_ratio=0.0, eye_height_ratio=0.0, eye_rot=0.0,
        eye_front_height=0.0, eye_front_flat=0.5, eye_tail_height=0.0,
        eye_top_lid_flat=0.5, eye_lower_lid_flat=0.5,
        eye_top_lid_down=0.3, eye_lower_lid_up=0.3,
        brow_dist_ratio=0.0, brow_height_ratio=0.0, brow_rot=0.0, brow_width_ratio=0.0,
        mouth_corner_ratio=0.0, mouth_height_ratio=0.0, nose_under_nose_ratio=0.0,
    ),
}

# 슬라이더 범위: (ref_value, half_range)
# 각 특징이 ref ± half_range 범위에 있을 때 0~1로 매핑
# 3D/템플릿 엔지니어 A의 morph target 범위 확정 후 함께 보정 필요
_SLIDER_RANGE: dict[str, float] = {
    "eye_aspect_ratio":       0.15,
    "eye_distance_ratio":     0.12,
    "face_width_height_ratio":0.20,
    "nose_height_ratio":      0.15,
    "nose_width_ratio":       0.12,
    "mouth_width_ratio":      0.12,
    "jaw_width_ratio":        0.15,
    "forehead_ratio":         0.15,
    "chin_ratio":             0.12,
}

# feature 이름 → slider 이름 매핑
_FEATURE_TO_SLIDER: dict[str, str] = {
    "eye_aspect_ratio":        "eye_size",
    "eye_distance_ratio":      "eye_distance",
    "face_width_height_ratio": "face_round",
    "nose_height_ratio":       "nose_height",
    "nose_width_ratio":        "nose_width",
    "mouth_width_ratio":       "mouth_width",
    "jaw_width_ratio":         "jaw_width",
    "forehead_ratio":          "forehead_height",
    "chin_ratio":              "chin_length",
}


@dataclass
class TemplateResult:
    template_name: str
    confidence: float           # 0~1, 선택된 템플릿과의 코사인 유사도
    all_scores: dict[str, float]  # {template_name: similarity} 전체 점수
    slider_init: dict[str, float] # {slider_name: 0~1} 초기값


def select_template(fv: FaceFeatureVector) -> TemplateResult:
    """
    코사인 유사도로 가장 가까운 템플릿을 선택하고 슬라이더 초기값을 반환한다.

    Args:
        fv: extract_features()가 반환한 FaceFeatureVector

    Returns:
        TemplateResult
    """
    fv_arr = fv.to_array()

    scores: dict[str, float] = {}
    for name, ref in _TEMPLATE_REFS.items():
        scores[name] = _cosine_similarity(fv_arr, ref.to_array())

    best_name = max(scores, key=lambda k: scores[k])
    slider_init = _map_to_sliders(fv, best_name)

    return TemplateResult(
        template_name=best_name,
        confidence=scores[best_name],
        all_scores=scores,
        slider_init=slider_init,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a < 1e-9 or norm_b < 1e-9:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _norm_to_01(val: float, ref: float, half_range: float) -> float:
    """ref ± half_range 구간을 0~1로 선형 매핑하고 clip."""
    low = ref - half_range
    span = 2.0 * half_range
    return float(np.clip((val - low) / (span + 1e-9), 0.0, 1.0))


def _map_to_sliders(fv: FaceFeatureVector, template_name: str) -> dict[str, float]:
    ref = _TEMPLATE_REFS[template_name]
    sliders: dict[str, float] = {}

    for feat_name, slider_name in _FEATURE_TO_SLIDER.items():
        val = getattr(fv, feat_name)
        ref_val = getattr(ref, feat_name)
        half_r = _SLIDER_RANGE[feat_name]
        sliders[slider_name] = _norm_to_01(val, ref_val, half_r)

    return sliders
