"""
Blender headless: 마스터 VRM에 sliders.json 적용 후 결과 렌더.

Usage:
  blender --background --python apply_sliders.py -- \
    --master /path/to/master.vrm \
    --sliders /path/to/sliders.json \
    --output /path/to/result.png \
    [--save-blend /path/to/result.blend]
"""
import bpy
import sys
import os
import json
import argparse
import math
from mathutils import Vector, Euler


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--master", required=True)
    p.add_argument("--sliders", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--save-blend", default=None)
    p.add_argument("--cam-dist", type=float, default=0.5)
    p.add_argument("--res", type=int, default=512)
    return p.parse_args(argv)


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_master(path):
    if path.endswith(".vrm"):
        bpy.ops.import_scene.vrm(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)


def find_face_mesh():
    """Face mesh — 보통 'Face' 이름 또는 shape_keys가 있는 첫 mesh"""
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name == 'Face':
            return o
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.data.shape_keys:
            return o
    return None


def apply_sliders(face, sliders):
    keys = face.data.shape_keys.key_blocks
    applied, missing = [], []
    for k, v in sliders.items():
        if v is None:
            continue
        v = float(v)
        if k in keys:
            keys[k].value = v
            if v > 0:
                applied.append((k, v))
        else:
            missing.append(k)
    return applied, missing


def get_head_world(arm):
    if arm and arm.type == 'ARMATURE':
        head = arm.data.bones.get("J_Bip_C_Head")
        if head:
            return arm.matrix_world @ head.tail_local
    return None


def setup_render_camera(face_center, cam_dist, res, out_path):
    scene = bpy.context.scene
    engine_items = [e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items]
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engine_items else 'BLENDER_EEVEE'
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = out_path
    scene.render.film_transparent = False
    scene.view_settings.exposure = -1.0
    scene.view_settings.view_transform = 'Standard'

    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.85, 0.85, 0.85, 1.0)
        bg.inputs[1].default_value = 0.5

    bpy.ops.object.camera_add(location=face_center + Vector((0, -cam_dist, 0)))
    cam = bpy.context.object
    cam.rotation_euler = Euler((math.pi/2, 0, 0))
    cam.data.lens = 70
    scene.camera = cam

    bpy.ops.object.light_add(type='AREA',
        location=face_center + Vector((0.4, -0.5, 0.2)))
    bpy.context.object.data.energy = 30
    bpy.context.object.data.size = 1.5
    bpy.ops.object.light_add(type='AREA',
        location=face_center + Vector((-0.4, -0.4, 0.1)))
    bpy.context.object.data.energy = 15


def main():
    args = parse_args()
    clear()
    import_master(args.master)

    face = find_face_mesh()
    if face is None:
        print("ERROR: cannot find Face mesh with shape keys")
        sys.exit(1)
    print(f"Face mesh: '{face.name}' verts={len(face.data.vertices)}")

    with open(args.sliders) as f:
        data = json.load(f)
    sliders = data["sliders"]
    
    applied, missing = apply_sliders(face, sliders)
    print(f"\n✓ Applied {len(applied)} sliders:")
    for k, v in applied:
        print(f"  {k:20s} = {v:.3f}")
    if missing:
        print(f"⚠ Missing keys in master: {missing}")

    arm = next((o for o in bpy.data.objects if o.type == 'ARMATURE'), None)
    head_w = get_head_world(arm)
    face_center = head_w if head_w else Vector((0, 0, 1.4))

    setup_render_camera(face_center, args.cam_dist, args.res, args.output)
    bpy.ops.render.render(write_still=True)
    print(f"\n✓ Rendered: {args.output}")

    if args.save_blend:
        bpy.ops.wm.save_as_mainfile(filepath=args.save_blend)
        print(f"✓ Saved blend: {args.save_blend}")


if __name__ == "__main__":
    main()
