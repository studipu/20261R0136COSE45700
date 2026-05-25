"""Face feature extraction CLI wrapper.

Called by the Next.js API route:
    python run_extract.py --image <path> --output <path>

Writes a JSON file with avatar_parameters, template, confidence, etc.
"""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from pupil_detector import extract_features_with_pupils
from parameter_specs import apply_specs
from template_selector import select_template


def main():
    parser = argparse.ArgumentParser(description="Extract face features → avatar keys")
    parser.add_argument("--image", required=True, help="Input image path")
    parser.add_argument("--output", required=True, help="Output JSON path")
    args = parser.parse_args()

    if not os.path.isfile(args.image):
        result = {"status": "error", "error": f"이미지 파일을 찾을 수 없습니다: {args.image}"}
        with open(args.output, "w") as f:
            json.dump(result, f, ensure_ascii=False)
        return

    fv, avatar_keys, raw_out = extract_features_with_pupils(args.image)

    if fv is None:
        result = {"status": "error", "error": "얼굴을 감지하지 못했습니다"}
    else:
        avatar_parameters, parameter_debug = apply_specs(avatar_keys, raw=raw_out)
        tmpl = select_template(fv)
        result = {
            "status": "ok",
            "feature_vector": fv.to_dict(),
            "avatar_parameters": avatar_parameters,
            "parameter_debug": parameter_debug,
            "template": tmpl.template_name,
            "confidence": tmpl.confidence,
            "all_scores": tmpl.all_scores,
            "slider_init": tmpl.slider_init,
        }

    with open(args.output, "w") as f:
        json.dump(result, f, ensure_ascii=False)

    print(f"[FacePipeline] Result written to {args.output} (status: {result['status']})")


if __name__ == "__main__":
    main()
