"""
AvatarSample_A.vrm 토폴로지 분석 스크립트
Blender 5.1에서 실행 — headless mode
"""
import bpy
import bmesh
import json
import sys
import os
from collections import Counter, defaultdict

# ── 설정 ──
VRM_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "public", "models", "AvatarSample_A.vrm")
OUTPUT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "topology_report.json")

def import_vrm(path):
    """VRM 파일 임포트"""
    # 기존 오브젝트 제거
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete()

    # VRM 임포트 시도
    try:
        bpy.ops.import_scene.vrm(filepath=path)
        print(f"[OK] VRM imported: {path}")
        return True
    except Exception as e:
        print(f"[WARN] VRM addon import failed: {e}")
        # fallback: glTF로 시도
        try:
            bpy.ops.import_scene.gltf(filepath=path)
            print(f"[OK] Imported as glTF: {path}")
            return True
        except Exception as e2:
            print(f"[ERROR] glTF import also failed: {e2}")
            return False

def analyze_mesh(obj):
    """단일 메시 오브젝트의 토폴로지 분석"""
    mesh = obj.data
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    result = {
        "name": obj.name,
        "vertices": len(bm.verts),
        "edges": len(bm.edges),
        "faces": len(bm.faces),
    }

    # ── 폴리곤 타입 분석 (tri / quad / ngon) ──
    face_sides = Counter(len(f.verts) for f in bm.faces)
    result["face_types"] = {
        "triangles": face_sides.get(3, 0),
        "quads": face_sides.get(4, 0),
        "ngons": sum(v for k, v in face_sides.items() if k > 4),
    }
    total_faces = len(bm.faces)
    result["quad_ratio"] = round(face_sides.get(4, 0) / total_faces * 100, 1) if total_faces else 0
    result["tri_ratio"] = round(face_sides.get(3, 0) / total_faces * 100, 1) if total_faces else 0

    # ── Pole 분석 (버텍스에 연결된 엣지 수) ──
    edge_counts = Counter(len(v.link_edges) for v in bm.verts)
    poles = {
        "e_poles_3edges": edge_counts.get(3, 0),  # E-pole: 3 edges
        "regular_4edges": edge_counts.get(4, 0),   # Regular: 4 edges
        "n_poles_5edges": edge_counts.get(5, 0),   # N-pole: 5 edges
        "star_6plus": sum(v for k, v in edge_counts.items() if k >= 6),
    }
    result["poles"] = poles
    result["pole_regularity"] = round(
        edge_counts.get(4, 0) / len(bm.verts) * 100, 1
    ) if len(bm.verts) else 0

    # ── 경계/비매니폴드 분석 ──
    boundary_edges = [e for e in bm.edges if e.is_boundary]
    non_manifold_edges = [e for e in bm.edges if not e.is_manifold and not e.is_boundary]
    loose_verts = [v for v in bm.verts if not v.link_edges]
    result["topology_issues"] = {
        "boundary_edges": len(boundary_edges),
        "non_manifold_edges": len(non_manifold_edges),
        "loose_vertices": len(loose_verts),
        "is_watertight": len(boundary_edges) == 0 and len(non_manifold_edges) == 0,
    }

    # ── UV 분석 ──
    uv_layers = mesh.uv_layers
    result["uv_layers"] = len(uv_layers)
    if uv_layers:
        result["uv_layer_names"] = [uv.name for uv in uv_layers]

    # ── Shape Key 분석 ──
    if mesh.shape_keys:
        sk = mesh.shape_keys.key_blocks
        result["shape_keys"] = {
            "count": len(sk),
            "names": [k.name for k in sk],
        }
    else:
        result["shape_keys"] = {"count": 0, "names": []}

    # ── Vertex Group 분석 ──
    result["vertex_groups"] = {
        "count": len(obj.vertex_groups),
        "names": [vg.name for vg in obj.vertex_groups],
    }

    # ── 버텍스 위치 범위 (바운딩 박스) ──
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    result["bounds"] = {
        "x": [round(min(xs), 4), round(max(xs), 4)],
        "y": [round(min(ys), 4), round(max(ys), 4)],
        "z": [round(min(zs), 4), round(max(zs), 4)],
    }

    # ── 엣지 길이 분포 ──
    edge_lengths = [e.calc_length() for e in bm.edges]
    if edge_lengths:
        result["edge_length"] = {
            "min": round(min(edge_lengths), 6),
            "max": round(max(edge_lengths), 6),
            "avg": round(sum(edge_lengths) / len(edge_lengths), 6),
            "ratio_max_min": round(max(edge_lengths) / min(edge_lengths), 1) if min(edge_lengths) > 0 else float('inf'),
        }

    # ── Face 면적 분포 ──
    face_areas = [f.calc_area() for f in bm.faces]
    if face_areas:
        result["face_area"] = {
            "min": round(min(face_areas), 8),
            "max": round(max(face_areas), 8),
            "avg": round(sum(face_areas) / len(face_areas), 8),
        }

    # ── 대칭성 분석 (X축) ──
    tolerance = 0.001
    symmetric_count = 0
    for v in bm.verts:
        if abs(v.co.x) < tolerance:
            symmetric_count += 1
            continue
        # 미러 포인트 찾기
        mirror_x = -v.co.x
        for v2 in bm.verts:
            if (abs(v2.co.x - mirror_x) < tolerance and
                abs(v2.co.y - v.co.y) < tolerance and
                abs(v2.co.z - v.co.z) < tolerance):
                symmetric_count += 1
                break
    result["symmetry"] = {
        "x_symmetric_verts": symmetric_count,
        "symmetry_ratio": round(symmetric_count / len(bm.verts) * 100, 1),
    }

    # ── 얼굴 영역별 버텍스 밀도 (head 메시 전용) ──
    if "head" in obj.name.lower():
        regions = {
            "eye_region": {"z_min": 1.455, "z_max": 1.494},
            "nose_region": {"z_min": 1.415, "z_max": 1.455, "x_range": 0.03},
            "jaw_region": {"z_min": 1.298, "z_max": 1.376},
            "cheek_region": {"z_min": 1.376, "z_max": 1.42, "x_min": 0.02},
            "forehead_region": {"z_min": 1.494, "z_max": 1.56},
            "mouth_region": {"z_min": 1.376, "z_max": 1.415, "x_range": 0.04},
        }
        region_analysis = {}
        for name, bounds in regions.items():
            verts_in_region = []
            for v in bm.verts:
                if v.co.z < bounds["z_min"] or v.co.z > bounds["z_max"]:
                    continue
                if "x_range" in bounds and abs(v.co.x) > bounds["x_range"]:
                    continue
                if "x_min" in bounds and abs(v.co.x) < bounds["x_min"]:
                    continue
                verts_in_region.append(v)
            region_analysis[name] = {
                "vertex_count": len(verts_in_region),
                "density_percent": round(len(verts_in_region) / len(bm.verts) * 100, 2),
            }
        result["face_regions"] = region_analysis

    # ── Edge Loop 검출 (주요 루프) ──
    # 눈, 입 주변 edge loop이 존재하는지 간접 확인
    if "head" in obj.name.lower():
        # 눈 영역 엣지 루프: z=1.455~1.494 내부에서 연결된 엣지 체인 수
        eye_edges = [e for e in bm.edges
                     if all(1.45 < v.co.z < 1.50 for v in e.verts)]
        mouth_edges = [e for e in bm.edges
                       if all(1.37 < v.co.z < 1.42 for v in e.verts)]
        result["edge_loops_hint"] = {
            "eye_region_edges": len(eye_edges),
            "mouth_region_edges": len(mouth_edges),
        }

    bm.free()
    return result


def analyze_armature(obj):
    """아마추어(스켈레톤) 분석"""
    arm = obj.data
    return {
        "name": obj.name,
        "bone_count": len(arm.bones),
        "bone_names": [b.name for b in arm.bones],
    }


def main():
    print("=" * 60)
    print("AvatarSample_A.vrm Topology Analysis")
    print("=" * 60)

    if not os.path.exists(VRM_PATH):
        print(f"[ERROR] VRM file not found: {VRM_PATH}")
        sys.exit(1)

    if not import_vrm(VRM_PATH):
        sys.exit(1)

    report = {"meshes": [], "armatures": [], "other_objects": []}

    for obj in bpy.data.objects:
        print(f"  Found object: {obj.name} (type: {obj.type})")
        if obj.type == 'MESH':
            print(f"  Analyzing mesh: {obj.name}...")
            analysis = analyze_mesh(obj)
            report["meshes"].append(analysis)
        elif obj.type == 'ARMATURE':
            analysis = analyze_armature(obj)
            report["armatures"].append(analysis)
        else:
            report["other_objects"].append({"name": obj.name, "type": obj.type})

    # JSON 출력
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Report saved to: {OUTPUT_PATH}")

    # 콘솔 요약
    for m in report["meshes"]:
        print(f"\n--- {m['name']} ---")
        print(f"  Verts: {m['vertices']}, Edges: {m['edges']}, Faces: {m['faces']}")
        ft = m['face_types']
        print(f"  Tris: {ft['triangles']}, Quads: {ft['quads']}, Ngons: {ft['ngons']}")
        print(f"  Quad ratio: {m['quad_ratio']}%, Tri ratio: {m['tri_ratio']}%")
        print(f"  Pole regularity (4-edge): {m['pole_regularity']}%")
        ti = m['topology_issues']
        print(f"  Boundary edges: {ti['boundary_edges']}, Non-manifold: {ti['non_manifold_edges']}")
        print(f"  Watertight: {ti['is_watertight']}")
        print(f"  Shape keys: {m['shape_keys']['count']}")
        print(f"  Vertex groups: {m['vertex_groups']['count']}")
        if 'symmetry' in m:
            print(f"  X-symmetry: {m['symmetry']['symmetry_ratio']}%")
        if 'face_regions' in m:
            print(f"  Face regions:")
            for rname, rdata in m['face_regions'].items():
                print(f"    {rname}: {rdata['vertex_count']} verts ({rdata['density_percent']}%)")


if __name__ == "__main__":
    main()
