"""Verify retopologized model topology."""
import bpy, bmesh
from collections import Counter

VRM_PATH = '/Users/seungu/Desktop/project/virtual_avatar/public/models/AvatarBase_Retopo.vrm'
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.vrm(filepath=VRM_PATH)

print('=== NEW MODEL TOPOLOGY ===')
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        face_sides = Counter(len(f.verts) for f in bm.faces)
        tris = face_sides.get(3, 0)
        quads = face_sides.get(4, 0)
        total = len(bm.faces)
        edge_counts = Counter(len(v.link_edges) for v in bm.verts)
        regular = edge_counts.get(4, 0)
        boundary = sum(1 for e in bm.edges if e.is_boundary)
        sk_count = len(mesh.shape_keys.key_blocks) if mesh.shape_keys else 0
        sk_names = [k.name for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else []
        custom_sks = [n for n in sk_names if n.startswith('face_') or n.startswith('body_')]
        print(f'--- {obj.name} ---')
        print(f'  Verts: {len(bm.verts)}, Faces: {total}')
        print(f'  Quads: {quads} ({round(quads/total*100,1)}%), Tris: {tris}')
        print(f'  Pole regularity: {round(regular/len(bm.verts)*100,1)}%')
        print(f'  Boundary edges: {boundary}')
        print(f'  Shape keys: {sk_count} (custom: {len(custom_sks)})')
        if custom_sks:
            print(f'  Custom SKs: {custom_sks}')
        bm.free()
