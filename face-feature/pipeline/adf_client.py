"""
ADF (hysts/anime-face-detector) client — WSL subprocess or HTTP server.

Runs the detector inside a persistent WSL Ubuntu process and returns
28 keypoints + face bbox for a given image.

Environment variables:
  ADF_SERVER_URL   If set, use HTTP server instead of WSL subprocess.
  ADF_WSL_HOME     Override WSL home directory.
  ADF_WSL_PYTHON   Override path to python inside WSL conda env.
  ADF_WSL_SCRIPT   Override path to anime_bbox.py inside WSL.
"""

import json as _json
import os
import subprocess
import threading

import cv2
import numpy as np
from pathlib import Path

_wsl_proc: "subprocess.Popen | None" = None
_wsl_lock = threading.Lock()

_ADF_SERVER_URL: str = os.environ.get("ADF_SERVER_URL", "")
_WSL_HOME   = os.environ.get("ADF_WSL_HOME", "")
_WSL_PYTHON = os.environ.get(
    "ADF_WSL_PYTHON",
    f"{_WSL_HOME or _wsl_home_default()}/miniconda3/envs/anime-detector/bin/python",
) if False else ""  # resolved below after _wsl_home_default is defined
_WSL_SCRIPT = ""    # resolved below

# ADF 28-point keypoint → semantic group mapping
ADF_KP_GROUPS = {
    "face_contour": [0, 1, 2, 3, 4],
    "right_brow":   [5, 6, 7],
    "left_brow":    [8, 9, 10],
    "right_eye":    [11, 12, 13, 14, 15, 16],
    "left_eye":     [17, 18, 19, 20, 21, 22],
    "nose":         [23],
    "mouth":        [24, 25, 26, 27],
}


def _wsl_home_default() -> str:
    try:
        out = subprocess.check_output(
            ["wsl", "-d", "Ubuntu", "--", "sh", "-c", "echo $HOME"],
            stderr=subprocess.DEVNULL, text=True,
        )
        return out.strip()
    except Exception:
        return "/home/user"


_wsl_home = os.environ.get("ADF_WSL_HOME", "") or _wsl_home_default()
_WSL_PYTHON = os.environ.get(
    "ADF_WSL_PYTHON",
    f"{_wsl_home}/miniconda3/envs/anime-detector/bin/python",
)
_WSL_SCRIPT = os.environ.get(
    "ADF_WSL_SCRIPT",
    f"{_wsl_home}/anime_bbox.py",
)


def win_to_wsl_path(win_path: str) -> str:
    p = Path(win_path).resolve()
    drive = p.drive.rstrip(":").lower()
    rest  = str(p)[len(p.drive):].replace("\\", "/")
    return f"/mnt/{drive}{rest}"


def _get_wsl_proc() -> "subprocess.Popen | None":
    global _wsl_proc
    with _wsl_lock:
        if _wsl_proc is not None and _wsl_proc.poll() is None:
            return _wsl_proc
        try:
            _wsl_proc = subprocess.Popen(
                ["wsl", "-d", "Ubuntu", "--", _WSL_PYTHON, "-u", _WSL_SCRIPT, "--server"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                bufsize=1,
            )
            for _ in range(30):
                line = _wsl_proc.stdout.readline().strip()
                if line == "ready":
                    print("[adf] WSL server started")
                    return _wsl_proc
            _wsl_proc.kill()
            _wsl_proc = None
            print("[adf] WSL server did not send 'ready'")
            return None
        except Exception as exc:
            print(f"[adf] WSL server start failed: {exc}")
            _wsl_proc = None
            return None


def _query_http(img_bgr: np.ndarray) -> "tuple | None":
    try:
        import requests  # type: ignore[import-untyped]
    except ImportError:
        print("[adf] 'requests' package not found — pip install requests")
        return None
    try:
        _, buf = cv2.imencode(".png", img_bgr)
        resp = requests.post(
            _ADF_SERVER_URL.rstrip("/") + "/detect",
            data=buf.tobytes(),
            headers={"Content-Type": "application/octet-stream"},
            timeout=30,
        )
        data = resp.json()
        if data is None:
            return None
        bbox = (data["x1"], data["y1"], data["x2"], data["y2"])
        kps  = data.get("keypoints")
        if kps is None or len(kps) < 28:
            return None
        return bbox, kps
    except Exception as exc:
        print(f"[adf] HTTP query failed: {exc}")
        return None


def _query_wsl(img_path: str) -> "tuple | None":
    proc = _get_wsl_proc()
    if proc is None:
        return None
    try:
        proc.stdin.write(win_to_wsl_path(img_path) + "\n")
        proc.stdin.flush()
        line = proc.stdout.readline().strip()
        if not line or line == "null":
            return None
        data = _json.loads(line)
        bbox = (data["x1"], data["y1"], data["x2"], data["y2"])
        kps  = data.get("keypoints")
        if kps is None or len(kps) < 28:
            return None
        return bbox, kps
    except Exception as exc:
        print(f"[adf] WSL query failed: {exc}")
        return None


def query_adf(img_path: str, img_bgr: np.ndarray) -> "tuple | None":
    """
    Returns (bbox, kps) where bbox=(x1,y1,x2,y2) and kps is list of 28 [x,y].
    Uses HTTP server if ADF_SERVER_URL is set, otherwise WSL subprocess.
    """
    if _ADF_SERVER_URL:
        return _query_http(img_bgr)
    return _query_wsl(img_path)
