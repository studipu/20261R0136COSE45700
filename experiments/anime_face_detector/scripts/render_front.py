"""
Blender headless 정면 렌더 — GLB/VRM 입력 → 얼굴 정면 PNG.

Usage (Blender headless):
  blender --background --python render_front.py -- \
    --input /path/to/model.glb \
    --output /path/to/face_front.png \
    [--face-z 0.22] [--cam-dist 0.55] [--lens 35]

GLB 좌표계는 보통 +Y가 정면. VRM은 -Y가 정면 (VRoid 표준).
--vrm 플래그가 있으면 카메라를 -Y에 두고 +Y 봄.
"""
import bpy
import sys
import os
import argparse
import math
from mathutils import Vector, Euler

def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True, help="GLB or VRM file")
    p.add_argument("--output", required=True, help="PNG output path")
    p.add_argument("--face-z", type=float, default=None,
                   help="얼굴 중심 Z (auto: bbox top - height*0.18)")
    p.add_argument("--cam-dist", type=float, default=0.55)
    p.add_argument("--lens", type=float, default=35)
    p.add_argument("--res", type=int, default=512)
    p.add_argument("--vrm", action="store_true",
                   help="VRM 모델 (카메라를 -Y에 둠). default: GLB(+Y 정면)")
    return p.parse_args(argv)


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_model(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".vrm":
        bpy.ops.import_scene.vrm(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)


def get_bbox():
    """모든 mesh의 world bbox"""
    xs, ys, zs = [], [], []
    for o in bpy.data.objects:
        if o.type == 'MESH' and not o.hide_get():
            for c in o.bound_box:
                w = o.matrix_world @ Vector(c)
                xs.append(w.x); ys.append(w.y); zs.append(w.z)
    if not xs:
        return None
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def setup_render(out_path, res):
    scene = bpy.context.scene
    engine_items = [e.identifier for e in scene.render.bl_rna.properties['engine'].enum_items]
    scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in engine_items else 'BLENDER_EEVEE'
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = out_path

    # 회색 배경 (헤어와 구분)
    world = scene.world or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.85, 0.85, 0.85, 1.0)
        bg.inputs[1].default_value = 0.5

    # exposure 낮춤 (burn out 방지)
    scene.view_settings.exposure = -1.0
    scene.view_settings.view_transform = 'Standard'


def setup_camera_lights(face_center, cam_dist, lens, vrm_mode):
    if vrm_mode:
        # VRM: -Y가 정면. 카메라 -Y, 보는 방향 +Y
        cam_loc = face_center + Vector((0, -cam_dist, 0))
        cam_rot = Euler((math.pi/2, 0, 0))
    else:
        # GLB (VARCO): +Y가 정면 X. -Y가 정면 (Blender import 시).
        # 어제 검증: VARCO도 -Y가 정면이어서 같은 설정.
        cam_loc = face_center + Vector((0, -cam_dist, 0))
        cam_rot = Euler((math.pi/2, 0, 0))
    
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.object
    cam.rotation_euler = cam_rot
    cam.data.lens = lens
    cam.data.sensor_width = 36
    bpy.context.scene.camera = cam
    
    # Lights
    bpy.ops.object.light_add(type='AREA',
        location=face_center + Vector((0.4, -0.5, 0.2)))
    bpy.context.object.data.energy = 30
    bpy.context.object.data.size = 1.5
    bpy.ops.object.light_add(type='AREA',
        location=face_center + Vector((-0.4, -0.4, 0.1)))
    bpy.context.object.data.energy = 15


def main():
    args = parse_args()
    clear_scene()
    import_model(args.input)
    
    bb = get_bbox()
    if bb is None:
        print(f"ERROR: no mesh found in {args.input}")
        sys.exit(1)
    xmin, xmax, ymin, ymax, zmin, zmax = bb
    print(f"Bbox: X[{xmin:.3f},{xmax:.3f}] Y[{ymin:.3f},{ymax:.3f}] Z[{zmin:.3f},{zmax:.3f}]")
    
    # 얼굴 중심 추정
    if args.face_z is not None:
        face_z = args.face_z
    else:
        # 흉상/캐릭터: 위쪽 18%가 얼굴 중심
        face_z = zmax - (zmax - zmin) * 0.18
    face_center = Vector(((xmin + xmax) / 2, (ymin + ymax) / 2, face_z))
    print(f"Face center: {[round(v,3) for v in face_center]}")
    
    setup_render(args.output, args.res)
    setup_camera_lights(face_center, args.cam_dist, args.lens, args.vrm)
    
    bpy.ops.render.render(write_still=True)
    print(f"✓ Rendered: {args.output}")


if __name__ == "__main__":
    main()
