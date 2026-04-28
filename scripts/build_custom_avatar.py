"""
CustomizableCharacter.blend → Base Avatar Pipeline
===================================================
1. Remove duplicate objects (.001)
2. Add 8 custom face shape keys (Phase 1 spec)
3. Export .blend + .vrm

Usage:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python scripts/build_custom_avatar.py
"""
import bpy
import bmesh
import math
import os
import time
from mathutils import Vector

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCE_BLEND = os.path.join(BASE_DIR, "public", "models", "CustomizableCharacter.blend")
OUTPUT_BLEND = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Custom.blend")
OUTPUT_VRM = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Custom.vrm")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ── Step 1: Open & Clean Duplicates ──
def step1_clean_duplicates():
    log("=== Step 1: Open & Remove Duplicates ===")
    bpy.ops.wm.open_mainfile(filepath=SOURCE_BLEND)
    log(f"  Opened: {SOURCE_BLEND}")

    # List all objects
    for obj in bpy.data.objects:
        log(f"  Object: {obj.name} (type: {obj.type})")

    # Remove .001 duplicates
    removed = []
    for obj in list(bpy.data.objects):
        if obj.name.endswith('.001'):
            name = obj.name
            bpy.data.objects.remove(obj, do_unlink=True)
            removed.append(name)

    log(f"  Removed duplicates: {removed}")

    # Purge orphan data
    bpy.ops.outliner.orphans_purge(do_recursive=True)

    # Report remaining
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            sk = len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0
            log(f"  Remaining: {obj.name} — {len(obj.data.vertices)}v, "
                f"{len(obj.data.polygons)}f, {sk} SKs, {len(obj.material_slots)} mats")


# ── Step 2: Analyze Face Regions ──
def step2_analyze_face():
    """Analyze actual vertex distribution to calibrate shape key regions."""
    log("=== Step 2: Analyze Face Vertex Distribution ===")

    face_obj = None
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and obj.name.lower() == 'face':
            face_obj = obj
            break

    if not face_obj:
        log("  ERROR: Face mesh not found!")
        return None

    mesh = face_obj.data
    basis = mesh.shape_keys.key_blocks["Basis"] if mesh.shape_keys else None

    if not basis:
        log("  ERROR: No Basis shape key on Face mesh!")
        return None

    # Analyze Z distribution
    zs = [v.co.z for v in basis.data]
    z_min, z_max = min(zs), max(zs)
    z_range = z_max - z_min
    log(f"  Face Z range: {z_min:.4f} — {z_max:.4f} (range: {z_range:.4f})")

    # Analyze X distribution
    xs = [abs(v.co.x) for v in basis.data]
    log(f"  Face X range: 0 — {max(xs):.4f}")

    # Analyze Y distribution
    ys = [v.co.y for v in basis.data]
    log(f"  Face Y range: {min(ys):.4f} — {max(ys):.4f}")

    # Sample vertex density by Z bands
    bands = 10
    band_size = z_range / bands
    for i in range(bands):
        z_lo = z_min + i * band_size
        z_hi = z_lo + band_size
        count = sum(1 for v in basis.data if z_lo <= v.co.z < z_hi)
        z_mid = (z_lo + z_hi) / 2
        bar = '#' * (count // 10)
        label = ""
        if z_mid > 1.52:
            label = " (forehead)"
        elif z_mid > 1.48:
            label = " (eyes upper)"
        elif z_mid > 1.44:
            label = " (eyes/nose)"
        elif z_mid > 1.41:
            label = " (nose/cheek)"
        elif z_mid > 1.38:
            label = " (mouth/cheek)"
        else:
            label = " (jaw/chin)"
        log(f"    Z [{z_lo:.3f}-{z_hi:.3f}]: {count:4d} verts {bar}{label}")

    return face_obj


# ── Step 3: Add Custom Shape Keys ──
def cosine_falloff(value, edge_start, edge_end):
    if edge_end <= edge_start:
        return 1.0
    t = max(0, min(1, (value - edge_start) / (edge_end - edge_start)))
    return 0.5 * (1.0 - math.cos(t * math.pi))


def compute_weight(co, z_min, z_max, x_min=None, x_max=None,
                   y_min=None, y_max=None, falloff=0.006):
    # Z
    if co.z < z_min - falloff or co.z > z_max + falloff:
        return 0.0
    wz = 1.0
    if co.z < z_min + falloff:
        wz = cosine_falloff(co.z, z_min - falloff, z_min + falloff)
    elif co.z > z_max - falloff:
        wz = cosine_falloff(co.z, z_max + falloff, z_max - falloff)

    # X (symmetric)
    wx = 1.0
    ax = abs(co.x)
    if x_min is not None:
        if ax < x_min - falloff:
            return 0.0
        if ax < x_min + falloff:
            wx *= cosine_falloff(ax, x_min - falloff, x_min + falloff)
    if x_max is not None:
        if ax > x_max + falloff:
            return 0.0
        if ax > x_max - falloff:
            wx *= cosine_falloff(ax, x_max + falloff, x_max - falloff)

    # Y
    wy = 1.0
    if y_min is not None:
        if co.y < y_min - falloff:
            return 0.0
        if co.y < y_min + falloff:
            wy *= cosine_falloff(co.y, y_min - falloff, y_min + falloff)
    if y_max is not None:
        if co.y > y_max + falloff:
            return 0.0
        if co.y > y_max - falloff:
            wy *= cosine_falloff(co.y, y_max + falloff, y_max - falloff)

    return wz * wx * wy


def enforce_symmetry(sk, basis, threshold=0.0005):
    verts = sk.data
    bv = basis.data
    n = len(verts)
    processed = set()

    for i in range(n):
        if i in processed:
            continue
        ci = bv[i].co
        if abs(ci.x) < threshold:
            d = verts[i].co - ci
            d.x = 0
            verts[i].co = ci + d
            processed.add(i)
            continue

        mx = Vector((-ci.x, ci.y, ci.z))
        best_j, best_d = -1, threshold * 10
        for j in range(n):
            if j == i or j in processed:
                continue
            d = (bv[j].co - mx).length
            if d < best_d:
                best_d = d
                best_j = j

        if best_j >= 0 and best_d < threshold * 5:
            di = verts[i].co - bv[i].co
            dj = verts[best_j].co - bv[best_j].co
            avg = Vector((
                (abs(di.x) + abs(dj.x)) / 2,
                (di.y + dj.y) / 2,
                (di.z + dj.z) / 2,
            ))
            si = 1 if ci.x >= 0 else -1
            verts[i].co = bv[i].co + Vector((avg.x * si, avg.y, avg.z))
            verts[best_j].co = bv[best_j].co + Vector((avg.x * -si, avg.y, avg.z))
            processed.add(i)
            processed.add(best_j)


def step3_add_shape_keys(face_obj):
    log("=== Step 3: Add 8 Custom Shape Keys ===")

    mesh = face_obj.data
    if not mesh.shape_keys:
        face_obj.shape_key_add(name="Basis", from_mix=False)
    basis = mesh.shape_keys.key_blocks["Basis"]

    existing = set(k.name for k in mesh.shape_keys.key_blocks)

    # Shape key definitions — calibrated to CustomizableCharacter Face mesh
    # Face Z range: 1.337 — 1.571
    shape_defs = {
        "face_eye_size": {
            "z_min": 1.455, "z_max": 1.500,
            "x_min": 0.01, "x_max": 0.07,
            "transform": "scale_xyz",
            "magnitude": 0.15,
        },
        "face_eye_width": {
            "z_min": 1.455, "z_max": 1.500,
            "x_min": 0.01, "x_max": 0.07,
            "transform": "scale_x",
            "magnitude": 0.12,
        },
        "face_eye_height": {
            "z_min": 1.455, "z_max": 1.500,
            "x_min": 0.01, "x_max": 0.07,
            "transform": "scale_z",
            "magnitude": 0.10,
        },
        "face_nose_width": {
            "z_min": 1.420, "z_max": 1.460,
            "x_max": 0.025,
            "transform": "scale_x",
            "magnitude": 0.10,
        },
        "face_nose_length": {
            "z_min": 1.420, "z_max": 1.460,
            "x_max": 0.025,
            "transform": "translate_y",
            "magnitude": -0.006,
        },
        "face_jaw_width": {
            "z_min": 1.337, "z_max": 1.390,
            "transform": "scale_x",
            "magnitude": 0.10,
        },
        "face_jaw_length": {
            "z_min": 1.337, "z_max": 1.390,
            "transform": "translate_z_bottom",
            "magnitude": -0.010,
        },
        "face_cheek_fullness": {
            "z_min": 1.390, "z_max": 1.430,
            "x_min": 0.02, "x_max": 0.08,
            "transform": "inflate_xy",
            "magnitude": 0.006,
        },
    }

    for sk_name, params in shape_defs.items():
        if sk_name in existing:
            log(f"    Skipping {sk_name} (already exists)")
            continue

        sk = face_obj.shape_key_add(name=sk_name, from_mix=False)

        z_min = params["z_min"]
        z_max = params["z_max"]
        x_min = params.get("x_min")
        x_max = params.get("x_max")
        y_min = params.get("y_min")
        y_max = params.get("y_max")
        transform = params["transform"]
        mag = params["magnitude"]

        # Collect region vertices
        region = []
        for vi, v in enumerate(basis.data):
            w = compute_weight(v.co, z_min, z_max, x_min, x_max, y_min, y_max)
            if w > 0.01:
                region.append((vi, v.co.copy(), w))

        if not region:
            log(f"    WARNING: {sk_name} — no vertices in region!")
            continue

        # Region center
        center = Vector((0, 0, 0))
        tw = 0
        for vi, co, w in region:
            center += co * w
            tw += w
        center /= tw

        affected = 0
        for vi, co, w in region:
            offset = Vector((0, 0, 0))

            if transform == "scale_xyz":
                offset = (co - center) * mag * w
            elif transform == "scale_x":
                sign = 1 if co.x >= 0 else -1
                offset.x = (abs(co.x) - abs(center.x)) * mag * w * sign
            elif transform == "scale_z":
                offset.z = (co.z - center.z) * mag * w
            elif transform == "translate_y":
                offset.y = mag * w
            elif transform == "translate_z_bottom":
                zr = z_max - z_min
                bf = 1.0 - ((co.z - z_min) / zr) if zr > 0 else 1.0
                offset.z = mag * w * bf
            elif transform == "inflate_xy":
                cy = center.y
                dx = co.x
                dy = co.y - cy
                d = math.sqrt(dx * dx + dy * dy)
                if d > 0.001:
                    offset.x = (dx / d) * mag * w
                    offset.y = (dy / d) * mag * w

            sk.data[vi].co = co + offset
            if offset.length > 1e-7:
                affected += 1

        enforce_symmetry(sk, basis)
        log(f"    Created: {sk_name} — {affected}/{len(region)} verts affected")


# ── Step 4: Export ──
def step4_export():
    log("=== Step 4: Export ===")

    # Smooth shading
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.shade_smooth()

    # Final report
    log("  Final state:")
    total_verts = 0
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            sk = len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0
            custom = 0
            if obj.data.shape_keys:
                custom = sum(1 for k in obj.data.shape_keys.key_blocks
                             if k.name.startswith('face_') or k.name.startswith('body_'))
            log(f"    {obj.name}: {len(obj.data.vertices)}v, {len(obj.data.polygons)}f, "
                f"{sk} SKs ({custom} custom), {len(obj.material_slots)} mats")
            total_verts += len(obj.data.vertices)
        elif obj.type == 'ARMATURE':
            log(f"    {obj.name}: {len(obj.data.bones)} bones")

    log(f"  Total vertices: {total_verts}")

    # Save .blend
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    log(f"  Saved: {OUTPUT_BLEND}")

    # Export VRM
    try:
        bpy.ops.export_scene.vrm(filepath=OUTPUT_VRM)
        log(f"  Exported VRM: {OUTPUT_VRM}")
    except Exception as e:
        log(f"  VRM export error: {e}")
        # Fallback to GLB
        glb_path = OUTPUT_VRM.replace('.vrm', '.glb')
        try:
            bpy.ops.export_scene.gltf(filepath=glb_path, export_format='GLB')
            log(f"  Fallback GLB: {glb_path}")
        except Exception as e2:
            log(f"  GLB export also failed: {e2}")


def main():
    log("=" * 60)
    log("CustomizableCharacter → Base Avatar Pipeline")
    log("=" * 60)
    t0 = time.time()

    step1_clean_duplicates()
    face_obj = step2_analyze_face()
    if face_obj:
        step3_add_shape_keys(face_obj)
    step4_export()

    log(f"\nCompleted in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
