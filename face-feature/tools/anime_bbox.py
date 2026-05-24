#!/usr/bin/env python3
"""
Adapter for hysts/anime-face-detector.

This script implements the protocol expected by pipeline/adf_client.py:

  - server mode prints "ready" once on startup
  - then reads one image path per stdin line
  - writes one JSON object per line, or "null" when no face is detected

It can also run as a tiny HTTP server compatible with ADF_SERVER_URL.
"""

from __future__ import annotations

import argparse
import inspect
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import cv2
import numpy as np


def _load_detector(model: str, device: str):
    try:
        from anime_face_detector import create_detector
    except ImportError as exc:
        raise RuntimeError(
            "anime-face-detector is not installed in this Python environment. "
            "Install the ADF stack in WSL, then run this script with that Python."
        ) from exc

    # Older releases default to CUDA. Force CPU when the runtime is CPU-only.
    kwargs: dict[str, Any] = {}
    sig = inspect.signature(create_detector)
    if "device" in sig.parameters:
        kwargs["device"] = device
    return create_detector(model, **kwargs)


def _read_image_path(path: str) -> np.ndarray | None:
    data = np.fromfile(path, dtype=np.uint8)
    if data.size == 0:
        return None
    return cv2.imdecode(data, cv2.IMREAD_COLOR)


def _read_image_bytes(data: bytes) -> np.ndarray | None:
    arr = np.frombuffer(data, dtype=np.uint8)
    if arr.size == 0:
        return None
    return cv2.imdecode(arr, cv2.IMREAD_COLOR)


def _score(pred: dict[str, Any]) -> float:
    bbox = pred.get("bbox")
    if bbox is None or len(bbox) < 5:
        return 0.0
    return float(bbox[4])


def _detect(detector, image: np.ndarray | None) -> dict[str, Any] | None:
    if image is None:
        return None

    preds = detector(image)
    if not preds:
        return None

    pred = max(preds, key=_score)
    bbox = np.asarray(pred.get("bbox"), dtype=float).reshape(-1)
    keypoints = np.asarray(pred.get("keypoints"), dtype=float)

    if bbox.size < 4 or keypoints.shape[0] < 28 or keypoints.shape[1] < 2:
        return None

    return {
        "x1": float(bbox[0]),
        "y1": float(bbox[1]),
        "x2": float(bbox[2]),
        "y2": float(bbox[3]),
        "score": float(bbox[4]) if bbox.size >= 5 else None,
        "keypoints": keypoints[:28, :2].astype(float).tolist(),
    }


def run_stdio_server(detector) -> int:
    print("ready", flush=True)
    for line in sys.stdin:
        path = line.strip()
        if not path:
            continue
        try:
            result = _detect(detector, _read_image_path(path))
            print("null" if result is None else json.dumps(result), flush=True)
        except Exception as exc:
            print(f"[anime_bbox] detect failed for {path}: {exc}", file=sys.stderr, flush=True)
            print("null", flush=True)
    return 0


def run_once(detector, image_path: str) -> int:
    result = _detect(detector, _read_image_path(image_path))
    print("null" if result is None else json.dumps(result, indent=2))
    return 1 if result is None else 0


def run_http_server(detector, host: str, port: int) -> int:
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            if self.path.rstrip("/") != "/detect":
                self.send_response(404)
                self.end_headers()
                return

            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            try:
                result = _detect(detector, _read_image_bytes(body))
                payload = b"null" if result is None else json.dumps(result).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
            except Exception as exc:
                payload = json.dumps({"error": str(exc)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        def log_message(self, format: str, *args: Any) -> None:
            print(f"[anime_bbox:http] {format % args}", file=sys.stderr)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"ready http://{host}:{port}", flush=True)
    server.serve_forever()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="ADF adapter for face-feature")
    parser.add_argument("image", nargs="?", help="single image path for one-shot mode")
    parser.add_argument("--server", action="store_true", help="stdio server mode for adf_client.py")
    parser.add_argument("--http-server", action="store_true", help="HTTP /detect server mode")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--model", default="yolov3")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    detector = _load_detector(args.model, args.device)

    if args.server:
        return run_stdio_server(detector)
    if args.http_server:
        return run_http_server(detector, args.host, args.port)
    if args.image:
        return run_once(detector, args.image)

    parser.error("provide an image path, --server, or --http-server")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
