"""
AvatarSample_A.vrm — Clean Quad Retopology + Shape Key Pipeline
================================================================
Blender 5.1 headless script.

Pipeline:
  Stage 1: Import VRM, save shape key data
  Stage 2: Retopologize head/wear to clean quads (QuadriFlow)
  Stage 3: Transfer shape keys & bone weights to new topology
  Stage 4: Add 8 custom face shape keys (Phase 1 spec)
  Stage 5: Cleanup, symmetry enforcement, export .blend

Usage:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python scripts/retopo_avatar.py
"""
import bpy
import bmesh
import json
import math
import os
import sys
import time
from mathutils import Vector, kdtree

# ── Paths ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VRM_PATH = os.path.join(BASE_DIR, "public", "models", "AvatarSample_A.vrm")
OUTPUT_BLEND = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Retopo.blend")
OUTPUT_VRM = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Retopo.vrm")
REPORT_PATH = os.path.join(BASE_DIR, "scripts", "retopo_report.json")

# ── Configuration ──
HEAD_TARGET_FACES = 5000   # quad target for head mesh
WEAR_TARGET_FACES = 12000  # quad target for wear mesh
HAIR_TARGET_FACES = 4000   # quad target for hair mesh
SYMMETRY_THRESHOLD = 0.0005  # X-axis symmetry tolerance


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ============================================================
# Stage 1: Import & Save Shape Key Data
# ============================================================
def stage1_import_and_save():
    log("=== Stage 1: Import VRM & Save Shape Key Data ===")

    # Clear scene
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # Import VRM
    try:
        bpy.ops.import_scene.vrm(filepath=VRM_PATH)
        log(f"VRM imported: {VRM_PATH}")
    except Exception as e:
        log(f"VRM import failed, trying glTF: {e}")
        bpy.ops.import_scene.gltf(filepath=VRM_PATH)

    # Catalog all meshes
    meshes = {}
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            meshes[obj.name] = obj
            log(f"  Found mesh: {obj.name} ({len(obj.data.vertices)} verts)")

    # Save shape key data from head mesh
    shape_key_data = {}
    head_obj = None
    for name, obj in meshes.items():
        if 'head' in name.lower() and 'hair' not in name.lower():
            head_obj = obj
            break

    if head_obj and head_obj.data.shape_keys:
        basis = head_obj.data.shape_keys.key_blocks[0]
        basis_coords = [v.co.copy() for v in basis.data]

        for sk in head_obj.data.shape_keys.key_blocks:
            deltas = []
            for i, v in enumerate(sk.data):
                delta = v.co - basis_coords[i]
                if delta.length > 1e-7:
                    deltas.append({
                        "index": i,
                        "basis_pos": list(basis_coords[i]),
                        "delta": list(delta),
                    })
            shape_key_data[sk.name] = {
                "vertex_count": len(sk.data),
                "nonzero_deltas": len(deltas),
                "deltas": deltas,
            }
        log(f"  Saved {len(shape_key_data)} shape keys from {head_obj.name}")
    else:
        log("  WARNING: No head mesh with shape keys found!")

    return meshes, shape_key_data, head_obj


# ============================================================
# Stage 2: Retopologize to Clean Quads
# ============================================================
def retopo_mesh(obj, target_faces, name_label):
    """Retopologize a single mesh using QuadriFlow."""
    log(f"  Retopologizing {name_label}: {obj.name} → target {target_faces} faces")

    # Store original vertex groups data for later transfer
    vgroup_data = save_vertex_groups(obj)

    # Select and make active
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    # Remove all shape keys first (QuadriFlow needs no shape keys)
    if obj.data.shape_keys:
        while obj.data.shape_keys and len(obj.data.shape_keys.key_blocks) > 0:
            obj.active_shape_key_index = 0
            bpy.ops.object.shape_key_remove(all=True)
        log(f"    Removed shape keys from {obj.name}")

    # Enter edit mode for pre-cleanup
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Remove degenerate geometry
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
    bpy.ops.mesh.delete_loose(use_verts=True, use_edges=True, use_faces=False)

    # Merge by distance (remove duplicate vertices)
    bpy.ops.mesh.remove_doubles(threshold=0.0001)

    bpy.ops.object.mode_set(mode='OBJECT')

    orig_verts = len(obj.data.vertices)
    orig_faces = len(obj.data.polygons)
    log(f"    After cleanup: {orig_verts} verts, {orig_faces} faces")

    # Apply QuadriFlow remesh
    try:
        bpy.ops.object.quadriflow_remesh(
            target_faces=target_faces,
            use_mesh_symmetry=True,
            use_preserve_sharp=True,
            use_preserve_boundary=True,
            seed=42,
        )
        new_verts = len(obj.data.vertices)
        new_faces = len(obj.data.polygons)
        log(f"    QuadriFlow result: {new_verts} verts, {new_faces} faces")
    except Exception as e:
        log(f"    QuadriFlow failed: {e}")
        log(f"    Falling back to tris_to_quads...")
        fallback_tris_to_quads(obj)

    # Post-cleanup
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    return vgroup_data


def fallback_tris_to_quads(obj):
    """Fallback: convert tris to quads if QuadriFlow fails."""
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.tris_convert_to_quads(
        face_threshold=0.698132,  # 40 degrees
        shape_threshold=0.698132,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

    # Analyze result
    mesh = obj.data
    quads = sum(1 for p in mesh.polygons if len(p.vertices) == 4)
    tris = sum(1 for p in mesh.polygons if len(p.vertices) == 3)
    log(f"    Tris→Quads fallback: {quads} quads, {tris} tris remaining")


def save_vertex_groups(obj):
    """Save vertex group assignments for later transfer."""
    vgroup_data = {}
    for vg in obj.vertex_groups:
        weights = []
        for vi in range(len(obj.data.vertices)):
            try:
                w = vg.weight(vi)
                if w > 0.001:
                    weights.append({
                        "pos": list(obj.data.vertices[vi].co),
                        "weight": w,
                    })
            except RuntimeError:
                pass
        vgroup_data[vg.name] = weights
    return vgroup_data


def restore_vertex_groups(obj, vgroup_data):
    """Restore vertex groups to retopologized mesh using nearest-vertex mapping."""
    if not vgroup_data:
        return

    # Build KD-tree for new mesh
    mesh = obj.data
    size = len(mesh.vertices)
    kd = kdtree.KDTree(size)
    for i, v in enumerate(mesh.vertices):
        kd.insert(v.co, i)
    kd.balance()

    for vg_name, weights in vgroup_data.items():
        if not weights:
            continue
        # Create or get vertex group
        if vg_name not in obj.vertex_groups:
            vg = obj.vertex_groups.new(name=vg_name)
        else:
            vg = obj.vertex_groups[vg_name]

        # For each original weighted vertex, find nearest new vertex
        for w_data in weights:
            orig_pos = Vector(w_data["pos"])
            weight = w_data["weight"]
            # Find nearest vertices and spread weight with distance falloff
            results = kd.find_n(orig_pos, 3)
            for co, idx, dist in results:
                if dist < 0.01:  # within 1cm
                    falloff = max(0, 1.0 - dist / 0.01)
                    vg.add([idx], weight * falloff, 'ADD')

    log(f"    Restored {len(vgroup_data)} vertex groups to {obj.name}")


def stage2_retopologize(meshes, head_obj):
    log("=== Stage 2: Retopologize Meshes ===")

    vgroup_backups = {}

    for name, obj in meshes.items():
        name_lower = name.lower()
        if 'head' in name_lower and 'hair' not in name_lower:
            vgroup_backups[name] = retopo_mesh(obj, HEAD_TARGET_FACES, "HEAD")
        elif 'wear' in name_lower:
            vgroup_backups[name] = retopo_mesh(obj, WEAR_TARGET_FACES, "WEAR")
        elif 'hair' in name_lower:
            # Hair meshes are non-manifold — skip retopology, keep original
            log(f"  Skipping {name} (hair mesh — non-manifold, keep original)")
        else:
            log(f"  Skipping {name} (non-target mesh)")

    return vgroup_backups


# ============================================================
# Stage 3: Transfer Shape Keys to New Topology
# ============================================================
def build_kdtree_from_positions(positions):
    """Build KD-tree from a list of Vector positions."""
    size = len(positions)
    kd = kdtree.KDTree(size)
    for i, pos in enumerate(positions):
        kd.insert(pos, i)
    kd.balance()
    return kd


def transfer_shape_keys(head_obj, shape_key_data):
    """Transfer saved shape keys to retopologized head mesh."""
    log("=== Stage 3: Transfer Shape Keys ===")

    if not shape_key_data:
        log("  No shape key data to transfer")
        return

    mesh = head_obj.data
    new_vert_count = len(mesh.vertices)
    log(f"  New head mesh: {new_vert_count} vertices")

    # Build KD-tree from original basis positions
    basis_data = shape_key_data.get("Basis", {})
    if not basis_data:
        log("  ERROR: No Basis shape key in saved data")
        return

    # Collect all original basis positions
    all_orig_positions = {}
    for sk_name, sk_data in shape_key_data.items():
        for d in sk_data["deltas"]:
            idx = d["index"]
            if idx not in all_orig_positions:
                all_orig_positions[idx] = Vector(d["basis_pos"])

    # Also need ALL basis positions, not just those with deltas
    # We'll reconstruct from any shape key that has basis_pos data
    orig_positions = []
    orig_vert_count = list(shape_key_data.values())[0]["vertex_count"]

    # Build a map of original index → basis position from delta data
    orig_pos_map = {}
    for sk_name, sk_data in shape_key_data.items():
        for d in sk_data["deltas"]:
            orig_pos_map[d["index"]] = Vector(d["basis_pos"])

    # Build KD-tree from original positions
    orig_positions_list = list(orig_pos_map.values())
    orig_indices_list = list(orig_pos_map.keys())

    if not orig_positions_list:
        log("  ERROR: No original positions to build KD-tree from")
        return

    kd = kdtree.KDTree(len(orig_positions_list))
    for i, pos in enumerate(orig_positions_list):
        kd.insert(pos, i)
    kd.balance()

    # Create basis shape key on new mesh
    if not mesh.shape_keys:
        head_obj.shape_key_add(name="Basis", from_mix=False)

    # For each saved shape key (except Basis), transfer deltas
    transferred = 0
    for sk_name, sk_data in shape_key_data.items():
        if sk_name == "Basis":
            continue
        if not sk_data["deltas"]:
            continue

        # Create new shape key
        new_sk = head_obj.shape_key_add(name=sk_name, from_mix=False)

        # Build a map: original_index → delta
        delta_map = {}
        for d in sk_data["deltas"]:
            delta_map[d["index"]] = Vector(d["delta"])

        # For each new vertex, find nearest original vertex and apply delta
        applied = 0
        for vi, v in enumerate(mesh.vertices):
            co, kd_idx, dist = kd.find(v.co)
            if dist < 0.02:  # within 2cm tolerance
                orig_idx = orig_indices_list[kd_idx]
                if orig_idx in delta_map:
                    delta = delta_map[orig_idx]
                    # Apply with distance-based falloff
                    falloff = max(0, 1.0 - dist / 0.02)
                    new_sk.data[vi].co = v.co + delta * falloff
                    applied += 1

        transferred += 1
        log(f"    Transferred: {sk_name} ({applied} vertices affected)")

    log(f"  Total shape keys transferred: {transferred}")


# ============================================================
# Stage 4: Add 8 Custom Face Shape Keys
# ============================================================
def cosine_falloff(value, edge_start, edge_end):
    """Smooth cosine falloff: returns 0 at edge_start, 1 at full interior."""
    if edge_end <= edge_start:
        return 1.0
    t = max(0, min(1, (value - edge_start) / (edge_end - edge_start)))
    return 0.5 * (1.0 - math.cos(t * math.pi))


def compute_region_weight(co, z_min, z_max, x_min=None, x_max=None,
                          y_min=None, y_max=None, falloff_dist=0.008):
    """Compute smooth weight for a vertex based on region bounds."""
    # Z-axis weight
    if co.z < z_min - falloff_dist or co.z > z_max + falloff_dist:
        return 0.0
    wz = 1.0
    if co.z < z_min + falloff_dist:
        wz = cosine_falloff(co.z, z_min - falloff_dist, z_min + falloff_dist)
    elif co.z > z_max - falloff_dist:
        wz = cosine_falloff(co.z, z_max + falloff_dist, z_max - falloff_dist)

    # X-axis weight (use abs for symmetry)
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

    # Y-axis weight
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


def add_custom_shape_keys(head_obj):
    """Add 8 custom face shape keys per Phase 1 spec."""
    log("=== Stage 4: Add Custom Shape Keys ===")

    mesh = head_obj.data

    # Ensure Basis exists
    if not mesh.shape_keys:
        head_obj.shape_key_add(name="Basis", from_mix=False)

    basis = mesh.shape_keys.key_blocks["Basis"]

    # ── Shape Key Definitions ──
    # Each key: region bounds + transform direction + magnitude
    shape_defs = {
        "face_eye_size": {
            "desc": "Eye proportional scale (XYZ)",
            "z_min": 1.455, "z_max": 1.494,
            "x_min": 0.01, "x_max": 0.08,
            "transform": "scale_xyz",
            "magnitude": 0.15,
        },
        "face_eye_width": {
            "desc": "Eye X-axis width",
            "z_min": 1.455, "z_max": 1.494,
            "x_min": 0.01, "x_max": 0.08,
            "transform": "scale_x",
            "magnitude": 0.12,
        },
        "face_eye_height": {
            "desc": "Eye Z-axis height",
            "z_min": 1.455, "z_max": 1.494,
            "x_min": 0.01, "x_max": 0.08,
            "transform": "scale_z",
            "magnitude": 0.10,
        },
        "face_nose_width": {
            "desc": "Nose X-axis width",
            "z_min": 1.415, "z_max": 1.455,
            "x_max": 0.03,
            "transform": "scale_x",
            "magnitude": 0.10,
        },
        "face_nose_length": {
            "desc": "Nose Y-axis protrusion",
            "z_min": 1.415, "z_max": 1.455,
            "x_max": 0.03,
            "transform": "translate_y",
            "magnitude": -0.008,  # forward (negative Y in this model)
        },
        "face_jaw_width": {
            "desc": "Jaw X-axis width",
            "z_min": 1.298, "z_max": 1.376,
            "transform": "scale_x",
            "magnitude": 0.12,
        },
        "face_jaw_length": {
            "desc": "Jaw Z-axis downward extension",
            "z_min": 1.298, "z_max": 1.376,
            "transform": "translate_z_bottom",
            "magnitude": -0.012,  # downward
        },
        "face_cheek_fullness": {
            "desc": "Cheek XY inflation",
            "z_min": 1.376, "z_max": 1.42,
            "x_min": 0.02, "x_max": 0.09,
            "transform": "inflate_xy",
            "magnitude": 0.008,
        },
    }

    for sk_name, params in shape_defs.items():
        sk = head_obj.shape_key_add(name=sk_name, from_mix=False)

        z_min = params["z_min"]
        z_max = params["z_max"]
        x_min = params.get("x_min")
        x_max = params.get("x_max")
        y_min = params.get("y_min")
        y_max = params.get("y_max")
        transform = params["transform"]
        mag = params["magnitude"]

        # Compute region center for scale operations
        region_verts = []
        for vi, v in enumerate(basis.data):
            w = compute_region_weight(v.co, z_min, z_max, x_min, x_max, y_min, y_max)
            if w > 0.01:
                region_verts.append((vi, v.co.copy(), w))

        if not region_verts:
            log(f"    WARNING: {sk_name} — no vertices in region!")
            continue

        # Compute region center (for scale transforms)
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
                # Scale outward from center on X axis (symmetric)
                sign = 1 if co.x >= 0 else -1
                offset.x = (abs(co.x) - abs(center.x)) * mag * w * sign

            elif transform == "scale_z":
                offset.z = (co.z - center.z) * mag * w

            elif transform == "translate_y":
                offset.y = mag * w

            elif transform == "translate_z_bottom":
                # More effect on lower vertices
                z_range = z_max - z_min
                bottom_factor = 1.0 - ((co.z - z_min) / z_range) if z_range > 0 else 1.0
                offset.z = mag * w * bottom_factor

            elif transform == "inflate_xy":
                # Push outward from face center (0, y_center, z_center)
                face_center_y = center.y
                dx = co.x  # already symmetric from center
                dy = co.y - face_center_y
                dist_xy = math.sqrt(dx * dx + dy * dy)
                if dist_xy > 0.001:
                    offset.x = (dx / dist_xy) * mag * w
                    offset.y = (dy / dist_xy) * mag * w

            sk.data[vi].co = co + offset
            if offset.length > 1e-7:
                affected += 1

        # Enforce X-axis symmetry on the shape key
        enforce_shapekey_symmetry(sk, basis, SYMMETRY_THRESHOLD)

        log(f"    Created: {sk_name} — {affected}/{len(region_verts)} verts affected")


def enforce_shapekey_symmetry(shape_key, basis, threshold):
    """Ensure shape key deltas are X-axis symmetric."""
    verts = shape_key.data
    basis_verts = basis.data
    n = len(verts)

    # Build pairs of mirrored vertices
    processed = set()
    for i in range(n):
        if i in processed:
            continue
        co_i = basis_verts[i].co
        if abs(co_i.x) < threshold:
            # Center vertex — zero out X delta
            delta = verts[i].co - co_i
            delta.x = 0
            verts[i].co = co_i + delta
            processed.add(i)
            continue

        # Find mirror vertex
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
            # Average the deltas symmetrically
            delta_i = verts[i].co - basis_verts[i].co
            delta_j = verts[best_j].co - basis_verts[best_j].co

            avg_delta = Vector((
                (abs(delta_i.x) + abs(delta_j.x)) / 2,
                (delta_i.y + delta_j.y) / 2,
                (delta_i.z + delta_j.z) / 2,
            ))

            sign_i = 1 if co_i.x >= 0 else -1
            sign_j = -sign_i

            verts[i].co = basis_verts[i].co + Vector((avg_delta.x * sign_i, avg_delta.y, avg_delta.z))
            verts[best_j].co = basis_verts[best_j].co + Vector((avg_delta.x * sign_j, avg_delta.y, avg_delta.z))

            processed.add(i)
            processed.add(best_j)


# ============================================================
# Stage 5: Final Cleanup & Export
# ============================================================
def enforce_mesh_symmetry(obj, threshold=SYMMETRY_THRESHOLD):
    """Enforce X-axis symmetry on mesh basis shape."""
    log(f"  Enforcing X-symmetry on {obj.name}...")
    mesh = obj.data
    verts = mesh.vertices

    processed = set()
    fixed = 0
    for i in range(len(verts)):
        if i in processed:
            continue
        co = verts[i].co
        if abs(co.x) < threshold:
            verts[i].co.x = 0.0
            processed.add(i)
            continue

        mirror = Vector((-co.x, co.y, co.z))
        best_j = -1
        best_dist = threshold * 10
        for j in range(len(verts)):
            if j == i or j in processed:
                continue
            d = (verts[j].co - mirror).length
            if d < best_dist:
                best_dist = d
                best_j = j

        if best_j >= 0 and best_dist < threshold * 5:
            avg_y = (verts[i].co.y + verts[best_j].co.y) / 2
            avg_z = (verts[i].co.z + verts[best_j].co.z) / 2
            avg_x = (abs(verts[i].co.x) + abs(verts[best_j].co.x)) / 2

            sign_i = 1 if co.x >= 0 else -1
            verts[i].co = Vector((avg_x * sign_i, avg_y, avg_z))
            verts[best_j].co = Vector((-avg_x * sign_i, avg_y, avg_z))
            processed.add(i)
            processed.add(best_j)
            fixed += 1

    log(f"    Fixed {fixed} vertex pairs")


def generate_report(meshes):
    """Generate topology report for the retopologized model."""
    report = {"meshes": []}
    for name, obj in meshes.items():
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        polys = mesh.polygons
        quads = sum(1 for p in polys if len(p.vertices) == 4)
        tris = sum(1 for p in polys if len(p.vertices) == 3)
        ngons = sum(1 for p in polys if len(p.vertices) > 4)

        sk_count = 0
        sk_names = []
        if mesh.shape_keys:
            sk_count = len(mesh.shape_keys.key_blocks)
            sk_names = [k.name for k in mesh.shape_keys.key_blocks]

        report["meshes"].append({
            "name": obj.name,
            "vertices": len(mesh.vertices),
            "faces": len(polys),
            "quads": quads,
            "tris": tris,
            "ngons": ngons,
            "quad_ratio": round(quads / len(polys) * 100, 1) if polys else 0,
            "vertex_groups": len(obj.vertex_groups),
            "shape_keys": sk_count,
            "shape_key_names": sk_names,
        })

    with open(REPORT_PATH, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    log(f"  Report saved: {REPORT_PATH}")
    return report


def stage5_cleanup_and_export(meshes, vgroup_backups):
    log("=== Stage 5: Cleanup & Export ===")

    # Restore vertex groups
    for name, vg_data in vgroup_backups.items():
        if name in meshes:
            restore_vertex_groups(meshes[name], vg_data)

    # Enforce symmetry on key meshes
    for name, obj in meshes.items():
        name_lower = name.lower()
        if 'head' in name_lower or 'wear' in name_lower:
            enforce_mesh_symmetry(obj)

    # Smooth normals on all meshes
    for name, obj in meshes.items():
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.shade_smooth()

    # Generate report
    report = generate_report(meshes)
    for m in report["meshes"]:
        log(f"  {m['name']}: {m['vertices']}v, {m['faces']}f, "
            f"{m['quad_ratio']}% quads, {m['shape_keys']} shape keys")

    # Save .blend
    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    log(f"  Saved .blend: {OUTPUT_BLEND}")

    # Try VRM export
    try:
        bpy.ops.export_scene.vrm(filepath=OUTPUT_VRM)
        log(f"  Exported VRM: {OUTPUT_VRM}")
    except Exception as e:
        log(f"  VRM export failed (expected — needs manual setup): {e}")
        log(f"  The .blend file is ready for manual VRM export in Blender GUI")


# ============================================================
# Main Pipeline
# ============================================================
def main():
    log("=" * 60)
    log("Avatar Retopology Pipeline")
    log("=" * 60)

    if not os.path.exists(VRM_PATH):
        log(f"ERROR: VRM not found: {VRM_PATH}")
        sys.exit(1)

    t0 = time.time()

    # Stage 1
    meshes, shape_key_data, head_obj = stage1_import_and_save()

    # Stage 2
    vgroup_backups = stage2_retopologize(meshes, head_obj)

    # Refresh head_obj reference (might have changed after remesh)
    head_obj = None
    for name, obj in meshes.items():
        if 'head' in name.lower() and 'hair' not in name.lower():
            head_obj = obj
            break

    # Stage 3
    if head_obj and shape_key_data:
        transfer_shape_keys(head_obj, shape_key_data)

    # Stage 4
    if head_obj:
        add_custom_shape_keys(head_obj)

    # Stage 5
    stage5_cleanup_and_export(meshes, vgroup_backups)

    elapsed = time.time() - t0
    log(f"\nPipeline completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
