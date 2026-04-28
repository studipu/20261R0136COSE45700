"""
AvatarSample_A.vrm — Clean Base Avatar Pipeline (v2)
=====================================================
Uses tris_to_quads (NOT QuadriFlow) to preserve UVs/textures perfectly.

Pipeline:
  1. Import original VRM
  2. Remove robo_arm mesh + bones + colliders
  3. Convert tris→quads on head/wear (preserves UVs, shape keys, weights)
  4. Clean up degenerate geometry
  5. Add 8 custom face shape keys
  6. Export .blend + .vrm

Usage:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python scripts/rebuild_avatar.py
"""
import bpy
import bmesh
import math
import os
import time
from mathutils import Vector

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VRM_PATH = os.path.join(BASE_DIR, "public", "models", "AvatarSample_A.vrm")
OUTPUT_BLEND = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Retopo.blend")
OUTPUT_VRM = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Retopo.vrm")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ── Step 1: Import ──
def step1_import():
    log("=== Step 1: Import VRM ===")
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()
    bpy.ops.import_scene.vrm(filepath=VRM_PATH)
    log(f"  Imported: {VRM_PATH}")

    meshes = {}
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            meshes[obj.name] = obj
            sk_count = len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0
            log(f"  Mesh: {obj.name} — {len(obj.data.vertices)}v, "
                f"{len(obj.data.polygons)}f, {sk_count} SKs, "
                f"{len(obj.material_slots)} mats")
    return meshes


# ── Step 2: Remove robo_arm + colliders ──
def step2_remove_roboarm():
    log("=== Step 2: Remove robo_arm & colliders ===")

    # Remove robo_arm mesh
    removed_meshes = []
    for obj in list(bpy.data.objects):
        if obj.type == 'MESH' and 'robo' in obj.name.lower():
            name = obj.name
            bpy.data.objects.remove(obj, do_unlink=True)
            removed_meshes.append(name)
    log(f"  Removed meshes: {removed_meshes}")

    # Remove robo bones from armature
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            robo_bones = [b.name for b in obj.data.edit_bones if 'robo' in b.name.lower()]
            for bn in robo_bones:
                bone = obj.data.edit_bones.get(bn)
                if bone:
                    obj.data.edit_bones.remove(bone)
            bpy.ops.object.mode_set(mode='OBJECT')
            log(f"  Removed {len(robo_bones)} robo bones")
            break

    # Remove collider empties
    removed_empties = 0
    for obj in list(bpy.data.objects):
        if obj.type == 'EMPTY':
            bpy.data.objects.remove(obj, do_unlink=True)
            removed_empties += 1
    log(f"  Removed {removed_empties} empties/colliders")

    # Remove robo vertex groups from remaining meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            robo_vgs = [vg for vg in obj.vertex_groups if 'robo' in vg.name.lower()]
            for vg in robo_vgs:
                obj.vertex_groups.remove(vg)
            if robo_vgs:
                log(f"  Removed {len(robo_vgs)} robo vertex groups from {obj.name}")


# ── Step 3: Tris → Quads conversion ──
def step3_tris_to_quads():
    log("=== Step 3: Tris → Quads (UV-preserving) ===")

    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue

        mesh = obj.data
        orig_faces = len(mesh.polygons)
        orig_tris = sum(1 for p in mesh.polygons if len(p.vertices) == 3)

        if orig_tris == 0:
            log(f"  {obj.name}: No triangles, skipping")
            continue

        # Select and activate
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Enter edit mode
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')

        # Remove degenerate geometry first
        bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
        bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)

        # Convert tris to quads — multiple passes with relaxed thresholds
        # Pass 1: strict angle
        bpy.ops.mesh.tris_convert_to_quads(
            face_threshold=0.523599,    # 30 degrees
            shape_threshold=0.523599,
            uvs=True,                   # Preserve UV seams
            vcols=True,                 # Preserve vertex colors
            seam=True,                  # Preserve seams
            sharp=True,                 # Preserve sharp edges
            materials=True,             # Preserve material boundaries
        )

        # Pass 2: more relaxed for remaining tris
        bpy.ops.mesh.tris_convert_to_quads(
            face_threshold=0.872665,    # 50 degrees
            shape_threshold=0.872665,
            uvs=True,
            vcols=True,
            seam=True,
            sharp=True,
            materials=True,
        )

        # Recalculate normals
        bpy.ops.mesh.normals_make_consistent(inside=False)

        bpy.ops.object.mode_set(mode='OBJECT')

        # Report
        new_faces = len(mesh.polygons)
        new_quads = sum(1 for p in mesh.polygons if len(p.vertices) == 4)
        new_tris = sum(1 for p in mesh.polygons if len(p.vertices) == 3)
        quad_pct = round(new_quads / new_faces * 100, 1) if new_faces else 0

        log(f"  {obj.name}: {orig_faces}f → {new_faces}f "
            f"({new_quads} quads [{quad_pct}%], {new_tris} tris)")


# ── Step 4: Add 8 Custom Shape Keys ──
def cosine_falloff(value, edge_start, edge_end):
    if edge_end <= edge_start:
        return 1.0
    t = max(0, min(1, (value - edge_start) / (edge_end - edge_start)))
    return 0.5 * (1.0 - math.cos(t * math.pi))


def compute_region_weight(co, z_min, z_max, x_min=None, x_max=None,
                          y_min=None, y_max=None, falloff_dist=0.008):
    # Z weight
    if co.z < z_min - falloff_dist or co.z > z_max + falloff_dist:
        return 0.0
    wz = 1.0
    if co.z < z_min + falloff_dist:
        wz = cosine_falloff(co.z, z_min - falloff_dist, z_min + falloff_dist)
    elif co.z > z_max - falloff_dist:
        wz = cosine_falloff(co.z, z_max + falloff_dist, z_max - falloff_dist)

    # X weight (symmetric)
    wx = 1.0
    ax = abs(co.x)
    if x_min is not None:
        if ax < x_min - falloff_dist:
            return 0.0
        if ax < x_min + falloff_dist:
            wx *= cosine_falloff(ax, x_min - falloff_dist, x_min + falloff_dist)
    if x_max is not None:
        if ax > x_max + falloff_dist:
            return 0.0
        if ax > x_max - falloff_dist:
            wx *= cosine_falloff(ax, x_max + falloff_dist, x_max - falloff_dist)

    # Y weight
    wy = 1.0
    if y_min is not None:
        if co.y < y_min - falloff_dist:
            return 0.0
        if co.y < y_min + falloff_dist:
            wy *= cosine_falloff(co.y, y_min - falloff_dist, y_min + falloff_dist)
    if y_max is not None:
        if co.y > y_max + falloff_dist:
            return 0.0
        if co.y > y_max - falloff_dist:
            wy *= cosine_falloff(co.y, y_max + falloff_dist, y_max - falloff_dist)

    return wz * wx * wy


def enforce_shapekey_symmetry(shape_key, basis, threshold=0.0005):
    verts = shape_key.data
    basis_verts = basis.data
    n = len(verts)

    processed = set()
    for i in range(n):
        if i in processed:
            continue
        co_i = basis_verts[i].co
        if abs(co_i.x) < threshold:
            delta = verts[i].co - co_i
            delta.x = 0
            verts[i].co = co_i + delta
            processed.add(i)
            continue

        mirror_co = Vector((-co_i.x, co_i.y, co_i.z))
        best_j = -1
        best_dist = threshold * 10
        for j in range(n):
            if j == i or j in processed:
                continue
            dist = (basis_verts[j].co - mirror_co).length
            if dist < best_dist:
                best_dist = dist
                best_j = j

        if best_j >= 0 and best_dist < threshold * 5:
            delta_i = verts[i].co - basis_verts[i].co
            delta_j = verts[best_j].co - basis_verts[best_j].co
            avg_delta = Vector((
                (abs(delta_i.x) + abs(delta_j.x)) / 2,
                (delta_i.y + delta_j.y) / 2,
                (delta_i.z + delta_j.z) / 2,
            ))
            sign_i = 1 if co_i.x >= 0 else -1
            verts[i].co = basis_verts[i].co + Vector((avg_delta.x * sign_i, avg_delta.y, avg_delta.z))
            verts[best_j].co = basis_verts[best_j].co + Vector((avg_delta.x * -sign_i, avg_delta.y, avg_delta.z))
            processed.add(i)
            processed.add(best_j)


def step4_add_custom_shape_keys():
    log("=== Step 4: Add Custom Shape Keys ===")

    # Find head mesh
    head_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and 'head' in obj.name.lower() and 'hair' not in obj.name.lower():
            head_obj = obj
            break

    if not head_obj:
        log("  ERROR: head mesh not found!")
        return

    mesh = head_obj.data

    # Ensure Basis exists
    if not mesh.shape_keys:
        head_obj.shape_key_add(name="Basis", from_mix=False)
    basis = mesh.shape_keys.key_blocks["Basis"]

    shape_defs = {
        "face_eye_size": {
            "z_min": 1.455, "z_max": 1.494,
            "x_min": 0.01, "x_max": 0.08,
            "transform": "scale_xyz",
            "magnitude": 0.15,
        },
        "face_eye_width": {
            "z_min": 1.455, "z_max": 1.494,
            "x_min": 0.01, "x_max": 0.08,
            "transform": "scale_x",
            "magnitude": 0.12,
        },
        "face_eye_height": {
            "z_min": 1.455, "z_max": 1.494,
            "x_min": 0.01, "x_max": 0.08,
            "transform": "scale_z",
            "magnitude": 0.10,
        },
        "face_nose_width": {
            "z_min": 1.415, "z_max": 1.455,
            "x_max": 0.03,
            "transform": "scale_x",
            "magnitude": 0.10,
        },
        "face_nose_length": {
            "z_min": 1.415, "z_max": 1.455,
            "x_max": 0.03,
            "transform": "translate_y",
            "magnitude": -0.008,
        },
        "face_jaw_width": {
            "z_min": 1.298, "z_max": 1.376,
            "transform": "scale_x",
            "magnitude": 0.12,
        },
        "face_jaw_length": {
            "z_min": 1.298, "z_max": 1.376,
            "transform": "translate_z_bottom",
            "magnitude": -0.012,
        },
        "face_cheek_fullness": {
            "z_min": 1.376, "z_max": 1.42,
            "x_min": 0.02, "x_max": 0.09,
            "transform": "inflate_xy",
            "magnitude": 0.008,
        },
    }

    # Check for existing custom shape keys and skip them
    existing_sks = set()
    if mesh.shape_keys:
        existing_sks = set(k.name for k in mesh.shape_keys.key_blocks)

    for sk_name, params in shape_defs.items():
        if sk_name in existing_sks:
            log(f"    Skipping {sk_name} (already exists)")
            continue

        sk = head_obj.shape_key_add(name=sk_name, from_mix=False)

        z_min = params["z_min"]
        z_max = params["z_max"]
        x_min = params.get("x_min")
        x_max = params.get("x_max")
        y_min = params.get("y_min")
        y_max = params.get("y_max")
        transform = params["transform"]
        mag = params["magnitude"]

        # Collect region vertices
        region_verts = []
        for vi, v in enumerate(basis.data):
            w = compute_region_weight(v.co, z_min, z_max, x_min, x_max, y_min, y_max)
            if w > 0.01:
                region_verts.append((vi, v.co.copy(), w))

        if not region_verts:
            log(f"    WARNING: {sk_name} — no vertices in region!")
            continue

        # Region center
        center = Vector((0, 0, 0))
        total_w = 0
        for vi, co, w in region_verts:
            center += co * w
            total_w += w
        center /= total_w

        affected = 0
        for vi, co, w in region_verts:
            offset = Vector((0, 0, 0))

            if transform == "scale_xyz":
                diff = co - center
                offset = diff * mag * w
            elif transform == "scale_x":
                sign = 1 if co.x >= 0 else -1
                offset.x = (abs(co.x) - abs(center.x)) * mag * w * sign
            elif transform == "scale_z":
                offset.z = (co.z - center.z) * mag * w
            elif transform == "translate_y":
                offset.y = mag * w
            elif transform == "translate_z_bottom":
                z_range = z_max - z_min
                bottom_factor = 1.0 - ((co.z - z_min) / z_range) if z_range > 0 else 1.0
                offset.z = mag * w * bottom_factor
            elif transform == "inflate_xy":
                face_center_y = center.y
                dx = co.x
                dy = co.y - face_center_y
                dist_xy = math.sqrt(dx * dx + dy * dy)
                if dist_xy > 0.001:
                    offset.x = (dx / dist_xy) * mag * w
                    offset.y = (dy / dist_xy) * mag * w

            sk.data[vi].co = co + offset
            if offset.length > 1e-7:
                affected += 1

        enforce_shapekey_symmetry(sk, basis)
        log(f"    Created: {sk_name} — {affected}/{len(region_verts)} verts")


# ── Step 5: Export ──
def step5_export():
    log("=== Step 5: Cleanup & Export ===")

    # Smooth shading
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.shade_smooth()

    # Purge orphans
    bpy.ops.outliner.orphans_purge(do_recursive=True)

    # Final report
    log("  Final meshes:")
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            sk_count = len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0
            quads = sum(1 for p in obj.data.polygons if len(p.vertices) == 4)
            tris = sum(1 for p in obj.data.polygons if len(p.vertices) == 3)
            total = len(obj.data.polygons)
            quad_pct = round(quads / total * 100, 1) if total else 0
            log(f"    {obj.name}: {len(obj.data.vertices)}v, {total}f "
                f"({quads}q/{tris}t, {quad_pct}% quad), "
                f"{sk_count} SKs, {len(obj.material_slots)} mats")

    # Save .blend
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    log(f"  Saved: {OUTPUT_BLEND}")

    # Export VRM
    try:
        bpy.ops.export_scene.vrm(filepath=OUTPUT_VRM)
        log(f"  Exported: {OUTPUT_VRM}")
    except Exception as e:
        log(f"  VRM export error (non-fatal): {e}")


# ── Main ──
def main():
    log("=" * 60)
    log("Avatar Rebuild Pipeline v2 (UV-preserving)")
    log("=" * 60)
    t0 = time.time()

    step1_import()
    step2_remove_roboarm()
    step3_tris_to_quads()
    step4_add_custom_shape_keys()
    step5_export()

    log(f"\nCompleted in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
