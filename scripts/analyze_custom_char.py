"""Analyze CustomizableCharacter.blend topology."""
import bpy
import bmesh
import json
import os
from collections import Counter

BLEND_PATH = '/Users/seungu/Desktop/project/virtual_avatar/public/models/CustomizableCharacter.blend'
REPORT_PATH = '/Users/seungu/Desktop/project/virtual_avatar/scripts/custom_char_report.json'

bpy.ops.wm.open_mainfile(filepath=BLEND_PATH)

print('=' * 60)
print('CustomizableCharacter.blend Topology Analysis')
print('=' * 60)

report = {"meshes": []}

for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        face_sides = Counter(len(f.verts) for f in bm.faces)
        tris = face_sides.get(3, 0)
        quads = face_sides.get(4, 0)
        ngons = sum(v for k, v in face_sides.items() if k > 4)
        total = len(bm.faces)

        edge_counts = Counter(len(v.link_edges) for v in bm.verts)
        regular = edge_counts.get(4, 0)

        boundary = sum(1 for e in bm.edges if e.is_boundary)
        non_manifold = sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary)
        loose = sum(1 for v in bm.verts if not v.link_edges)

        # Edge length stats
        edge_lengths = [e.calc_length() for e in bm.edges]
        min_edge = min(edge_lengths) if edge_lengths else 0
        max_edge = max(edge_lengths) if edge_lengths else 0
        avg_edge = sum(edge_lengths) / len(edge_lengths) if edge_lengths else 0

        # Symmetry check
        threshold = 0.001
        sym_count = 0
        for v in bm.verts:
            if abs(v.co.x) < threshold:
                sym_count += 1
                continue
            mirror_x = -v.co.x
            for v2 in bm.verts:
                if (abs(v2.co.x - mirror_x) < threshold and
                    abs(v2.co.y - v.co.y) < threshold and
                    abs(v2.co.z - v.co.z) < threshold):
                    sym_count += 1
                    break

        # Shape keys
        sk_count = 0
        sk_names = []
        if mesh.shape_keys:
            sk_count = len(mesh.shape_keys.key_blocks)
            sk_names = [k.name for k in mesh.shape_keys.key_blocks]

        # UV layers
        uv_count = len(mesh.uv_layers)
        uv_names = [uv.name for uv in mesh.uv_layers]

        # Vertex groups
        vg_count = len(obj.vertex_groups)
        vg_names = [vg.name for vg in obj.vertex_groups]

        # Materials
        mat_count = len(obj.material_slots)
        mat_names = [ms.material.name if ms.material else "None" for ms in obj.material_slots]

        # Bounds
        xs = [v.co.x for v in bm.verts]
        ys = [v.co.y for v in bm.verts]
        zs = [v.co.z for v in bm.verts]

        # Face regions (if it looks like a head mesh)
        face_regions = None
        if any(z > 1.2 for z in zs) and any(z < 0.5 for z in zs):
            pass  # full body, skip face regions

        entry = {
            "name": obj.name,
            "vertices": len(bm.verts),
            "edges": len(bm.edges),
            "faces": total,
            "tris": tris,
            "quads": quads,
            "ngons": ngons,
            "quad_pct": round(quads / total * 100, 1) if total else 0,
            "tri_pct": round(tris / total * 100, 1) if total else 0,
            "pole_regularity": round(regular / len(bm.verts) * 100, 1) if bm.verts else 0,
            "boundary_edges": boundary,
            "non_manifold": non_manifold,
            "loose_verts": loose,
            "watertight": boundary == 0 and non_manifold == 0,
            "edge_min": round(min_edge, 6),
            "edge_max": round(max_edge, 6),
            "edge_avg": round(avg_edge, 6),
            "edge_ratio": round(max_edge / min_edge, 1) if min_edge > 0 else 0,
            "symmetry_pct": round(sym_count / len(bm.verts) * 100, 1) if bm.verts else 0,
            "shape_keys": sk_count,
            "shape_key_names": sk_names,
            "uv_layers": uv_count,
            "uv_names": uv_names,
            "vertex_groups": vg_count,
            "vg_names": vg_names[:20],  # first 20 only
            "materials": mat_count,
            "mat_names": mat_names,
            "bounds": {
                "x": [round(min(xs), 4), round(max(xs), 4)],
                "y": [round(min(ys), 4), round(max(ys), 4)],
                "z": [round(min(zs), 4), round(max(zs), 4)],
            },
        }

        report["meshes"].append(entry)

        print(f'\n--- {obj.name} ---')
        print(f'  Verts: {len(bm.verts)}, Edges: {len(bm.edges)}, Faces: {total}')
        print(f'  Quads: {quads} ({entry["quad_pct"]}%), Tris: {tris} ({entry["tri_pct"]}%), Ngons: {ngons}')
        print(f'  Pole regularity (4-edge): {entry["pole_regularity"]}%')
        print(f'  Boundary: {boundary}, Non-manifold: {non_manifold}, Loose: {loose}')
        print(f'  Watertight: {entry["watertight"]}')
        print(f'  Edge length: min={min_edge:.6f}, max={max_edge:.6f}, ratio={entry["edge_ratio"]}')
        print(f'  X-symmetry: {entry["symmetry_pct"]}%')
        print(f'  Shape keys: {sk_count}')
        if sk_names:
            print(f'    Names: {sk_names}')
        print(f'  UV layers: {uv_count} {uv_names}')
        print(f'  Vertex groups: {vg_count}')
        print(f'  Materials: {mat_count} {mat_names}')
        print(f'  Bounds: X[{min(xs):.3f}, {max(xs):.3f}] Y[{min(ys):.3f}, {max(ys):.3f}] Z[{min(zs):.3f}, {max(zs):.3f}]')

        bm.free()

# Armatures
for obj in bpy.data.objects:
    if obj.type == 'ARMATURE':
        print(f'\n--- Armature: {obj.name} ---')
        print(f'  Bones: {len(obj.data.bones)}')
        bone_names = [b.name for b in obj.data.bones]
        print(f'  Names: {bone_names[:30]}...' if len(bone_names) > 30 else f'  Names: {bone_names}')

with open(REPORT_PATH, 'w') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f'\nReport saved: {REPORT_PATH}')
