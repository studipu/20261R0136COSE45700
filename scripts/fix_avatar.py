"""
Fix retopologized avatar:
1. Remove robo_arm mesh + related bones/empties
2. Transfer UVs from original model to retopologized meshes
3. Re-export VRM

Usage:
  /Applications/Blender.app/Contents/MacOS/Blender --background \
      --python scripts/fix_avatar.py
"""
import bpy
import bmesh
import os
import time
from mathutils import Vector, kdtree

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIGINAL_VRM = os.path.join(BASE_DIR, "public", "models", "AvatarSample_A.vrm")
RETOPO_BLEND = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Retopo.blend")
OUTPUT_BLEND = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Retopo.blend")
OUTPUT_VRM = os.path.join(BASE_DIR, "public", "models", "AvatarBase_Retopo.vrm")


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


def import_original_as_reference():
    """Import original VRM into a separate collection for UV reference."""
    log("Importing original VRM as UV reference...")

    # Create reference collection
    ref_col = bpy.data.collections.new("_OriginalRef")
    bpy.context.scene.collection.children.link(ref_col)

    # Record existing objects before import
    existing_objs = set(obj.name for obj in bpy.data.objects)

    # Import original VRM
    bpy.ops.import_scene.vrm(filepath=ORIGINAL_VRM)

    # Find newly imported objects (not in existing set)
    ref_meshes = {}
    new_objs = [obj for obj in bpy.data.objects if obj.name not in existing_objs]
    for obj in new_objs:
        # Move to reference collection
        for col in list(obj.users_collection):
            col.objects.unlink(obj)
        ref_col.objects.link(obj)
        if obj.type == 'MESH':
            old_name = obj.name
            obj.name = f"_ref_{old_name}"
            ref_meshes[old_name] = obj

    log(f"  Imported {len(ref_meshes)} reference meshes: {list(ref_meshes.keys())}")
    return ref_col, ref_meshes


def transfer_uvs_via_data_transfer(target_obj, source_obj):
    """Transfer UVs from source (original) to target (retopo) using Data Transfer modifier."""
    log(f"  Transferring UVs: {source_obj.name} -> {target_obj.name}")

    # Ensure target is active
    bpy.ops.object.select_all(action='DESELECT')
    target_obj.select_set(True)
    bpy.context.view_layer.objects.active = target_obj

    # Ensure target has a UV layer
    if not target_obj.data.uv_layers:
        target_obj.data.uv_layers.new(name="UVMap")

    # Add Data Transfer modifier
    mod = target_obj.modifiers.new(name="UVTransfer", type='DATA_TRANSFER')
    mod.object = source_obj
    mod.use_loop_data = True
    mod.data_types_loops = {'UV'}
    mod.loop_mapping = 'POLYINTERP_NEAREST'

    # Apply the modifier
    bpy.ops.object.modifier_apply(modifier=mod.name)
    log(f"    UV transfer applied to {target_obj.name}")


def transfer_materials(target_obj, source_obj):
    """Copy materials from source to target."""
    # Clear existing materials
    target_obj.data.materials.clear()

    # Copy materials from source
    for mat_slot in source_obj.material_slots:
        if mat_slot.material:
            target_obj.data.materials.append(mat_slot.material)

    log(f"    Materials transferred: {len(source_obj.material_slots)} materials")


def remove_robo_arm():
    """Remove robo_arm mesh and all related objects (bones, colliders)."""
    log("Removing robo_arm and related objects...")

    removed = []

    # Remove robo_arm mesh
    for obj in list(bpy.data.objects):
        name_lower = obj.name.lower()
        if name_lower.startswith('_ref_'):
            continue  # Skip reference objects

        if 'robo' in name_lower:
            obj_name = obj.name
            bpy.data.objects.remove(obj, do_unlink=True)
            removed.append(obj_name)

    log(f"  Removed objects: {removed}")

    # Remove robo_arm bones from armature
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and not obj.name.startswith('_ref_'):
            arm = obj.data
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')

            robo_bones = [b.name for b in arm.edit_bones if 'robo' in b.name.lower()]
            for bone_name in robo_bones:
                bone = arm.edit_bones.get(bone_name)
                if bone:
                    arm.edit_bones.remove(bone)

            bpy.ops.object.mode_set(mode='OBJECT')
            log(f"  Removed {len(robo_bones)} robo bones from armature")
            break


def remove_colliders_and_empties():
    """Remove collider empties and unused objects."""
    log("Removing colliders and unused empties...")

    removed = []
    for obj in list(bpy.data.objects):
        if obj.name.startswith('_ref_'):
            continue
        if obj.type == 'EMPTY':
            obj_name = obj.name
            bpy.data.objects.remove(obj, do_unlink=True)
            removed.append(obj_name)

    log(f"  Removed {len(removed)} empties")


def cleanup_references(ref_col, ref_meshes):
    """Remove all reference objects."""
    log("Cleaning up reference objects...")

    for obj in list(ref_col.objects):
        bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.collections.remove(ref_col)
    log("  Reference objects cleaned up")


def main():
    log("=" * 60)
    log("Avatar Fix: Remove robo_arm + Fix UVs/Textures")
    log("=" * 60)

    t0 = time.time()

    # Clear scene and load retopo blend
    bpy.ops.wm.open_mainfile(filepath=RETOPO_BLEND)
    log(f"Opened: {RETOPO_BLEND}")

    # List current objects
    main_meshes = {}
    for obj in bpy.data.objects:
        if obj.type == 'MESH' and not obj.name.startswith('_ref_'):
            main_meshes[obj.name] = obj
            log(f"  Main mesh: {obj.name} ({len(obj.data.vertices)} verts)")

    # Step 1: Import original as reference
    ref_col, ref_meshes = import_original_as_reference()

    # Step 2: Transfer UVs and materials for retopologized meshes
    log("=== Transferring UVs and Materials ===")

    # Map retopo mesh names to original mesh names
    mesh_mapping = {
        'head': 'head',
        'wear': 'wear',
    }

    for retopo_name, orig_name in mesh_mapping.items():
        target = main_meshes.get(retopo_name)

        # Find reference mesh — original name key or by scanning objects
        source = ref_meshes.get(orig_name)
        if not source:
            # Name might have .001 suffix from duplicate import
            for rname, robj in ref_meshes.items():
                if orig_name in rname:
                    source = robj
                    break
        if not source:
            for obj in bpy.data.objects:
                if obj.type == 'MESH' and obj.name.startswith("_ref_") and orig_name in obj.name:
                    source = obj
                    break

        if target and source:
            transfer_uvs_via_data_transfer(target, source)
            transfer_materials(target, source)
        else:
            log(f"  WARNING: Could not find pair for {retopo_name}")
            log(f"    target={target}, source={source}")
            if not source:
                log(f"    Available refs: {[o.name for o in bpy.data.objects if o.name.startswith('_ref_')]}")

    # Step 3: Remove robo_arm
    remove_robo_arm()

    # Step 4: Remove colliders/empties (simplify for clean base)
    remove_colliders_and_empties()

    # Step 5: Cleanup reference objects
    cleanup_references(ref_col, ref_meshes)

    # Step 6: Clean up unused data
    bpy.ops.outliner.orphans_purge(do_recursive=True)

    # Step 7: Smooth shading on all meshes
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.shade_smooth()

    # Step 8: Save and export
    log("=== Saving & Exporting ===")

    # Report final state
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            sk_count = len(obj.data.shape_keys.key_blocks) if obj.data.shape_keys else 0
            mat_count = len(obj.material_slots)
            uv_count = len(obj.data.uv_layers)
            log(f"  {obj.name}: {len(obj.data.vertices)}v, {len(obj.data.polygons)}f, "
                f"{sk_count} SKs, {mat_count} mats, {uv_count} UVs")

    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)
    log(f"  Saved .blend: {OUTPUT_BLEND}")

    try:
        bpy.ops.export_scene.vrm(filepath=OUTPUT_VRM)
        log(f"  Exported VRM: {OUTPUT_VRM}")
    except Exception as e:
        log(f"  VRM export failed: {e}")
        # Fallback: export as glTF
        gltf_path = OUTPUT_VRM.replace('.vrm', '.glb')
        try:
            bpy.ops.export_scene.gltf(filepath=gltf_path, export_format='GLB')
            log(f"  Exported glTF fallback: {gltf_path}")
        except Exception as e2:
            log(f"  glTF export also failed: {e2}")

    elapsed = time.time() - t0
    log(f"\nFix completed in {elapsed:.1f}s")


if __name__ == "__main__":
    main()
