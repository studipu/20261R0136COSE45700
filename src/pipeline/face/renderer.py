"""
Render a GLB file to multi-view 2D images using pyrender.

Platform backends:
  - macOS:  pyglet (requires display)
  - Linux:  EGL (headless)
    Set PYOPENGL_PLATFORM=egl before importing pyrender.

Output views: front, left, right
Each view produces: {view}.png, {view}_depth.npy, {view}_mask.png, {view}_depth.png
Plus render_quality.json with per-view quality scores.
"""

from __future__ import annotations

import os
import sys
import math
import json
import platform
import numpy as np
from pathlib import Path
from PIL import Image

# Set OpenGL platform before importing pyrender.
# OffscreenRenderer supports 'egl' and 'osmesa' only (NOT 'pyglet').
# macOS: use EGL via Homebrew Mesa (brew install mesa)
# Linux: use EGL via GPU driver
if "PYOPENGL_PLATFORM" not in os.environ:
    os.environ["PYOPENGL_PLATFORM"] = "egl"

# macOS: ensure Homebrew Mesa EGL library is discoverable
if platform.system() == "Darwin":
    import subprocess
    try:
        mesa_prefix = subprocess.check_output(
            ["brew", "--prefix", "mesa"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        mesa_lib = os.path.join(mesa_prefix, "lib")
        if os.path.isdir(mesa_lib):
            existing = os.environ.get("DYLD_LIBRARY_PATH", "")
            if mesa_lib not in existing:
                os.environ["DYLD_LIBRARY_PATH"] = f"{mesa_lib}:{existing}" if existing else mesa_lib
    except Exception:
        pass

import trimesh
import pyrender


VIEWS = {
    "front": {"yaw": 0,   "pitch": 0},
    "left":  {"yaw": 90,  "pitch": 0},
    "right": {"yaw": -90, "pitch": 0},
}

RESOLUTION = (512, 512)
BBOX_AREA_TARGET = 0.4


def _make_camera_pose(
    yaw_deg: float,
    pitch_deg: float,
    distance: float = 1.5,
    target: np.ndarray | None = None,
) -> np.ndarray:
    """
    Build a 4x4 camera pose matrix.
    yaw  : Y-axis rotation (left/right)
    pitch: X-axis rotation (up/down)
    Camera looks at target from the given distance.
    """
    yaw = math.radians(yaw_deg)
    pitch = math.radians(pitch_deg)

    x = distance * math.sin(yaw) * math.cos(pitch)
    y = distance * math.sin(pitch)
    z = distance * math.cos(yaw) * math.cos(pitch)

    target_pos = (
        np.array([0.0, 0.0, 0.0], dtype=np.float64)
        if target is None
        else np.asarray(target, dtype=np.float64)
    )
    cam_pos = target_pos + np.array([x, y, z], dtype=np.float64)

    forward = target_pos - cam_pos
    forward_norm = np.linalg.norm(forward)
    if forward_norm < 1e-9:
        forward = np.array([0.0, 0.0, -1.0], dtype=np.float64)
        forward_norm = 1.0
    forward = forward / forward_norm

    world_up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, world_up)
    if np.linalg.norm(right) < 1e-6:
        right = np.array([1.0, 0.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)

    pose = np.eye(4)
    pose[:3, 0] = right
    pose[:3, 1] = up
    pose[:3, 2] = -forward
    pose[:3, 3] = cam_pos
    return pose


def _load_scene(glb_path: str) -> pyrender.Scene:
    mesh_or_scene = trimesh.load(glb_path, force="scene")

    scene = pyrender.Scene(bg_color=[1.0, 1.0, 1.0, 1.0], ambient_light=[0.5, 0.5, 0.5])

    if isinstance(mesh_or_scene, trimesh.Scene):
        for mesh in _iter_scene_meshes_with_transforms(mesh_or_scene):
            if len(mesh.vertices) == 0:
                continue
            pr_mesh = pyrender.Mesh.from_trimesh(mesh, smooth=False)
            scene.add(pr_mesh)
    else:
        pr_mesh = pyrender.Mesh.from_trimesh(mesh_or_scene, smooth=False)
        scene.add(pr_mesh)

    return scene


def _iter_scene_meshes_with_transforms(trimesh_scene: trimesh.Scene):
    for node_name in trimesh_scene.graph.nodes_geometry:
        try:
            transform, geom_name = trimesh_scene.graph.get(node_name)
        except Exception:
            continue

        geom = trimesh_scene.geometry.get(geom_name)
        if geom is None:
            continue
        if not isinstance(geom, trimesh.Trimesh):
            continue

        mesh = geom.copy()
        mesh.apply_transform(transform)
        yield mesh


def _add_lighting(scene: pyrender.Scene, view_yaw: float, target: np.ndarray):
    light = pyrender.DirectionalLight(color=[1.0, 1.0, 1.0], intensity=2.5)
    scene.add(light, pose=_make_camera_pose(view_yaw, 18, 2.0, target=target))

    fill = pyrender.DirectionalLight(color=[0.9, 0.9, 1.0], intensity=1.0)
    scene.add(fill, pose=_make_camera_pose(view_yaw + 35, 10, 2.0, target=target))


def _center_scene_bounds(glb_path: str) -> tuple[float, np.ndarray]:
    """Compute camera distance and center target from GLB bounds."""
    mesh_or_scene = trimesh.load(glb_path, force="scene")
    if isinstance(mesh_or_scene, trimesh.Scene):
        bounds = mesh_or_scene.bounds
    else:
        bounds = mesh_or_scene.bounds

    if bounds is None:
        return 1.5, np.array([0.0, 0.0, 0.0], dtype=np.float64)

    center_xyz = (bounds[0] + bounds[1]) / 2.0
    size = np.linalg.norm(bounds[1] - bounds[0])
    distance = max(size * 1.2, 1e-3)
    return distance, center_xyz


def _compute_depth_mask(depth: np.ndarray) -> np.ndarray:
    return np.isfinite(depth) & (depth > 0)


def _save_depth_artifacts(depth: np.ndarray, mask: np.ndarray, output_dir: Path, view_name: str):
    depth_f32 = depth.astype(np.float32, copy=False)
    np.save(str(output_dir / f"{view_name}_depth.npy"), depth_f32)

    mask_img = (mask.astype(np.uint8) * 255)
    Image.fromarray(mask_img, mode="L").save(str(output_dir / f"{view_name}_mask.png"))

    depth_vis = np.zeros(depth.shape, dtype=np.uint8)
    if mask.any():
        valid_depth = depth[mask]
        depth_min = float(valid_depth.min())
        depth_max = float(valid_depth.max())
        if depth_max > depth_min:
            normalized = (depth - depth_min) / (depth_max - depth_min)
            depth_vis[mask] = np.clip(normalized[mask] * 255, 0, 255).astype(np.uint8)
        else:
            depth_vis[mask] = 255

    Image.fromarray(depth_vis, mode="L").save(str(output_dir / f"{view_name}_depth.png"))


def _compute_quality_metadata(depth: np.ndarray, mask: np.ndarray) -> dict:
    height, width = depth.shape
    total_pixels = width * height
    valid_pixels = int(mask.sum())

    if valid_pixels == 0:
        return {
            "valid_depth_ratio": 0.0,
            "bbox": None,
            "bbox_area_ratio": 0.0,
            "center_offset": None,
            "depth_min": None,
            "depth_max": None,
            "quality_score": 0.0,
        }

    ys, xs = np.where(mask)
    x_min = int(xs.min())
    x_max = int(xs.max())
    y_min = int(ys.min())
    y_max = int(ys.max())
    bbox_width = x_max - x_min + 1
    bbox_height = y_max - y_min + 1
    bbox_area_ratio = float((bbox_width * bbox_height) / total_pixels)

    bbox_center_x = (x_min + x_max) / 2.0
    bbox_center_y = (y_min + y_max) / 2.0
    image_center_x = (width - 1) / 2.0
    image_center_y = (height - 1) / 2.0
    max_center_distance = math.sqrt(image_center_x ** 2 + image_center_y ** 2)
    center_distance = math.sqrt(
        (bbox_center_x - image_center_x) ** 2 + (bbox_center_y - image_center_y) ** 2
    )
    center_offset = float(center_distance / max_center_distance) if max_center_distance > 0 else 0.0

    valid_depth = depth[mask]
    valid_depth_ratio = float(valid_pixels / total_pixels)
    depth_min = float(valid_depth.min())
    depth_max = float(valid_depth.max())

    bbox_presence_score = min(bbox_area_ratio / BBOX_AREA_TARGET, 1.0)
    center_score = 1.0 - center_offset if center_offset is not None else 0.0
    quality_score = (
        0.5 * valid_depth_ratio
        + 0.3 * bbox_presence_score
        + 0.2 * center_score
    )
    quality_score = float(np.clip(quality_score, 0.0, 1.0))

    return {
        "valid_depth_ratio": valid_depth_ratio,
        "bbox": {
            "x_min": x_min,
            "y_min": y_min,
            "x_max": x_max,
            "y_max": y_max,
            "width": bbox_width,
            "height": bbox_height,
        },
        "bbox_area_ratio": bbox_area_ratio,
        "center_offset": center_offset,
        "depth_min": depth_min,
        "depth_max": depth_max,
        "quality_score": quality_score,
    }


def render_multiview(glb_path: str, output_dir: str = None, resolution: tuple = RESOLUTION) -> dict[str, Image.Image]:
    """
    Render a GLB file from multiple angles defined in VIEWS.

    Args:
        glb_path: Input GLB file path
        output_dir: Directory to save images (None = don't save)
        resolution: Output resolution (width, height)

    Returns:
        {view_name: PIL.Image} dict
    """
    distance, center_xyz = _center_scene_bounds(glb_path)

    renderer = pyrender.OffscreenRenderer(*resolution)
    camera = pyrender.PerspectiveCamera(yfov=math.radians(40), aspectRatio=resolution[0] / resolution[1])

    results = {}
    quality_metadata = {}
    output_path = Path(output_dir) if output_dir else None
    if output_path:
        output_path.mkdir(parents=True, exist_ok=True)

    for view_name, angles in VIEWS.items():
        scene = _load_scene(glb_path)
        _add_lighting(scene, angles["yaw"], center_xyz)

        cam_pose = _make_camera_pose(
            angles["yaw"],
            angles["pitch"],
            distance,
            target=center_xyz,
        )
        scene.add(camera, pose=cam_pose)

        color, depth = renderer.render(scene)
        img = Image.fromarray(color)
        results[view_name] = img

        if output_path:
            mask = _compute_depth_mask(depth)
            quality_metadata[view_name] = _compute_quality_metadata(depth, mask)

            img.save(str(output_path / f"{view_name}.png"))
            _save_depth_artifacts(depth, mask, output_path, view_name)
            print(f"[Renderer] saved {view_name}.png")

    if output_path:
        quality_path = output_path / "render_quality.json"
        quality_path.write_text(json.dumps(quality_metadata, indent=2), encoding="utf-8")
        print(f"[Renderer] saved render_quality.json")

    renderer.delete()
    return results
