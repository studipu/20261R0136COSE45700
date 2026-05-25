"""
Usage:
    python tools/visualize_avatar_keys.py --image input_image/01_original.png
    python tools/visualize_avatar_keys.py --image output/02_nohair/renders/front.png

Requires: ADF WSL server running (or ADF_SERVER_URL env set).
Output:   output_test/avatar_keys_<stem>.png
"""

import argparse
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.feature_extractor import extract_features_full, visualize_landmarks


# Key_ID ranges: True = (-1,1), False = (0,1)
_SIGNED = {
    "Eye_Width", "Eye_WidthV", "Eye_Height", "Eye_Dist", "Eye_Rot",
    "Eye_FrontHeight", "Eye_TailHeight",
    "Eye_PupilWidth", "Eye_PupilWidthV",
    "Brow_Dist", "Brow_Height", "Brow_Rot", "Brow_Width", "Brow_WidthV",
    "Nose_Height", "Nose_UnderNose",
    "Mouth_Width", "Mouth_Height", "Mouth_Corner",
}

# Key_IDs that are fixed/default (no real measurement)
_FIXED = {"Nose_Width", "Brow_WidthV", "Eye_PupilWidth", "Eye_PupilWidthV"}

_GROUPS = [
    ("Eye shape",    ["Eye_Width", "Eye_WidthV", "Eye_Height", "Eye_Dist", "Eye_Rot"]),
    ("Eye lid",      ["Eye_FrontHeight", "Eye_FrontFlat", "Eye_TailHeight",
                      "Eye_TopLidFlat", "Eye_LowerLidFlat",
                      "Eye_TopLidDown", "Eye_LowerLidUp"]),
    ("Eye pupil",    ["Eye_PupilWidth", "Eye_PupilWidthV"]),
    ("Brow",         ["Brow_Dist", "Brow_Height", "Brow_Rot", "Brow_Width", "Brow_WidthV"]),
    ("Nose",         ["Nose_Height", "Nose_Width", "Nose_UnderNose"]),
    ("Mouth",        ["Mouth_Width", "Mouth_Height", "Mouth_Corner"]),
    ("Face",         ["Face_JawLine", "Face_Cheek", "Face_Roundness", "Face_ChinWidth"]),
]


def plot_keys(avatar_keys: dict, save_path: str, title: str = ""):
    labels, values, colors, x_lo, x_hi = [], [], [], [], []

    for group_name, keys in _GROUPS:
        labels.append(f"── {group_name}")
        values.append(None)
        colors.append("none")
        x_lo.append(None); x_hi.append(None)
        for k in keys:
            v = avatar_keys.get(k)
            labels.append(k)
            values.append(v)
            is_fixed = k in _FIXED
            if is_fixed:
                colors.append("#bbbbbb")
            elif k in _SIGNED:
                colors.append("#4c9be8")
            else:
                colors.append("#55c47a")
            if k in _SIGNED:
                x_lo.append(-1.0); x_hi.append(1.0)
            else:
                x_lo.append(0.0); x_hi.append(1.0)

    n = len(labels)
    fig, ax = plt.subplots(figsize=(11, n * 0.32 + 1.5))
    fig.patch.set_facecolor("#1e1e2e")
    ax.set_facecolor("#1e1e2e")

    for spine in ax.spines.values():
        spine.set_color("#444466")

    ax.tick_params(colors="#ccccdd")
    ax.xaxis.label.set_color("#ccccdd")
    ax.title.set_color("#ffffff")

    y_positions = list(range(n - 1, -1, -1))

    for i, (label, val, col, lo, hi) in enumerate(zip(labels, values, colors, x_lo, x_hi)):
        y = y_positions[i]
        if val is None:
            ax.text(-1.05, y, label, va="center", ha="left",
                    fontsize=8.5, color="#888899", fontstyle="italic", fontweight="bold")
            ax.axhline(y=y - 0.5, color="#333355", linewidth=0.5)
            continue

        # background bar (range)
        ax.barh(y, hi - lo, left=lo, height=0.55,
                color="#2a2a3e", edgecolor="#444466", linewidth=0.4)
        # value bar
        if lo < 0:
            bar_left  = min(0.0, val)
            bar_width = abs(val)
        else:
            bar_left  = lo
            bar_width = val - lo
        ax.barh(y, bar_width, left=bar_left, height=0.55, color=col, alpha=0.85)
        # zero line
        if lo < 0:
            ax.axvline(x=0, color="#666688", linewidth=0.6, alpha=0.5)

        # label
        ax.text(-1.08, y, label, va="center", ha="left", fontsize=8.5, color="#ddddee")
        # value text
        ax.text(hi + 0.02, y, f"{val:+.3f}", va="center", ha="left",
                fontsize=7.5, color="#aaaacc")

    ax.set_xlim(-1.15, 1.25)
    ax.set_ylim(-1, n)
    ax.set_yticks([])
    ax.set_xlabel("value", color="#888899", fontsize=8)
    ax.set_xticks([-1, -0.5, 0, 0.5, 1])
    ax.set_xticklabels(["-1", "-0.5", "0", "0.5", "1"], fontsize=7, color="#888899")
    ax.set_title(title or "Avatar Key_ID values", color="#ffffff", fontsize=11, pad=8)

    legend = [
        mpatches.Patch(color="#4c9be8", label="signed  (-1 ~ +1)"),
        mpatches.Patch(color="#55c47a", label="strength (0 ~ 1)"),
        mpatches.Patch(color="#bbbbbb", label="fixed / unmeasured"),
    ]
    ax.legend(handles=legend, loc="lower right", fontsize=7,
              facecolor="#2a2a3e", edgecolor="#444466", labelcolor="#ccccdd")

    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"[Viz] saved: {save_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="input image path")
    parser.add_argument("--output-dir", default="output_test", dest="output_dir")
    parser.add_argument("--min-confidence", type=float, default=0.4, dest="min_confidence")
    args = parser.parse_args()

    image_path = args.image
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = Path(image_path).stem

    print(f"[Viz] extracting features from: {image_path}")
    fv, avatar_keys, _ = extract_features_full(image_path, min_confidence=args.min_confidence)

    if avatar_keys is None:
        print("[Viz] ERROR: face not detected")
        sys.exit(1)

    print("[Viz] avatar_keys:")
    for k, v in avatar_keys.items():
        print(f"  {k:<20} {v:+.4f}")

    # bar chart
    chart_path = str(out_dir / f"avatar_keys_{stem}.png")
    plot_keys(avatar_keys, chart_path, title=f"Avatar keys — {stem}")

    # landmark overlay
    lm_path = str(out_dir / f"landmarks_{stem}.png")
    visualize_landmarks(image_path, save_path=lm_path)
    print(f"[Viz] landmarks saved: {lm_path}")


if __name__ == "__main__":
    main()
