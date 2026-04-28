"""Export original CustomizableCharacter.blend as VRM without modifications."""
import bpy
import os

BLEND = '/Users/seungu/Desktop/project/virtual_avatar/public/models/CustomizableCharacter.blend'
OUT_VRM = '/Users/seungu/Desktop/project/virtual_avatar/public/models/CustomizableCharacter.vrm'

# Open original blend
bpy.ops.wm.open_mainfile(filepath=BLEND)

# Remove duplicates (.001) for clean export
for obj in list(bpy.data.objects):
    if obj.name.endswith('.001'):
        name = obj.name
        bpy.data.objects.remove(obj, do_unlink=True)
        print(f"Removed duplicate: {name}")

bpy.ops.outliner.orphans_purge(do_recursive=True)

# List remaining
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        sk = len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0
        print(f"Mesh: {obj.name} — {len(obj.data.vertices)}v, {sk} SKs")

# Export VRM
try:
    bpy.ops.export_scene.vrm(filepath=OUT_VRM)
    print(f"Exported: {OUT_VRM}")
except Exception as e:
    print(f"VRM export failed: {e}")

print("Done.")
