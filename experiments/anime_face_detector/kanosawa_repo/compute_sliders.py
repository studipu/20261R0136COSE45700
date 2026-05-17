"""
baseline(master) + user(varco) 측정값 → blendshape slider 값 산출.
단방향 가정: user_value > baseline → 슬라이더 비례 / user <= baseline → 0
"""
import json, sys, argparse

# blendshape_key → (metric_name, max_change_ratio_for_slider_1.0)
# eye_rot_deg / brow_rot_deg / mouth_corner_dy는 절대 변화량 사용
KEY_MAPPING = {
    # ── Eye ──
    "Eye_Width":      ("eye_width",       "ratio", 0.30),
    "Eye_WidthV":     ("eye_widthV",      "ratio", 0.30),
    "Eye_Dist":       ("eye_dist",        "ratio", 0.30),
    "Eye_Height":     ("eye_y_norm",      "ratio", 0.20),
    "Eye_Rot":        ("eye_rot_deg",     "abs",   15.0),  # 도 단위
    "Eye_PupilWidth": None,   # 동공 추출은 별도 (Phase 2)
    "Eye_PupilWidthV":None,
    "Eye_FrontHeight":None, "Eye_FrontFlat": None, "Eye_TailHeight": None,
    "Eye_TopLidFlat": None, "Eye_LowerLidFlat": None,
    "Eye_TopLidDown": None, "Eye_LowerLidUp": None,
    # ── Brow ──
    "Brow_Width":     ("brow_width",      "ratio", 0.30),
    "Brow_WidthV":    None,   # 눈썹 두께 측정 안 함
    "Brow_Dist":      ("brow_dist",       "ratio", 0.30),
    "Brow_Height":    ("brow_y_norm",     "ratio", 0.30),
    "Brow_Rot":       ("brow_rot_deg",    "abs",   15.0),
    # ── Mouth ──
    "Mouth_Width":    ("lip_width_norm",  "ratio", 0.30),
    "Mouth_Height":   ("mouth_y_norm",    "ratio", 0.20),
    "Mouth_Corner":   ("mouth_corner_dy", "abs",   0.03),
    # ── Nose ──
    "Nose_Height":    None,   # 측면 렌더 필요
    "Nose_Width":     None,
    "Nose_UnderNose": None,
    # ── Face ──
    "Face_JawLine":   None,
    "Face_Cheek":     None,
    "Face_Roundness": None,
    "Face_ChinWidth": None,
}


def compute_slider(user_val, baseline_val, mode, max_ratio):
    """단방향 매핑: user > baseline일 때만 비례 산출"""
    if mode == "ratio":
        if baseline_val == 0:
            return 0.0
        delta = (user_val - baseline_val) / abs(baseline_val)
    else:  # abs
        delta = abs(user_val) - abs(baseline_val)
    if delta <= 0:
        return 0.0
    return float(min(delta / max_ratio, 1.0))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("baseline_json")
    p.add_argument("user_json")
    p.add_argument("output_json")
    args = p.parse_args()
    
    with open(args.baseline_json) as f:
        baseline = json.load(f)["measurements"]
    with open(args.user_json) as f:
        user = json.load(f)["measurements"]
    
    sliders = {}
    debug_table = []
    for key, mapping in KEY_MAPPING.items():
        if mapping is None:
            sliders[key] = None  # 추출 미지원
            debug_table.append((key, "—", "—", "—", "—", "—"))
            continue
        metric, mode, mr = mapping
        b = baseline.get(metric, 0)
        u = user.get(metric, 0)
        sv = compute_slider(u, b, mode, mr)
        sliders[key] = round(sv, 3)
        debug_table.append((key, metric, f"{b:.4f}", f"{u:.4f}", mode, f"{sv:.3f}"))
    
    out = {
        "baseline_source": args.baseline_json,
        "user_source":     args.user_json,
        "sliders":         sliders,
    }
    with open(args.output_json, 'w') as f:
        json.dump(out, f, indent=2)
    
    print(f"{'key':25s} {'metric':18s} {'base':>8s} {'user':>8s} {'mode':6s} {'slider':>7s}")
    print("-" * 80)
    for row in debug_table:
        print(f"{row[0]:25s} {row[1]:18s} {row[2]:>8s} {row[3]:>8s} {row[4]:6s} {row[5]:>7s}")
    
    n_active = sum(1 for v in sliders.values() if v is not None and v > 0)
    print(f"\n✓ Saved {args.output_json}")
    print(f"  Active sliders (> 0): {n_active}")


if __name__ == "__main__":
    main()
