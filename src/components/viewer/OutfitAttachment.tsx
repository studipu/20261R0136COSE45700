'use client';

import { useEffect, useRef } from 'react';
import { useThree } from '@react-three/fiber';
import { useEditorStore } from '@/stores/editorStore';
import { getBaseVRM } from '@/lib/vrm-ref';
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

/**
 * Extract SkinnedMesh objects relevant to the outfit:
 * - CLOTH materials (the outfit itself)
 * - Body SKIN materials (body mesh fitted to the outfit, excludes face/eye)
 *
 * The outfit VRM includes a body mesh shaped to avoid clipping with its
 * clothes. We use it to replace the base model's body mesh.
 */
function extractOutfitMeshes(scene: THREE.Object3D): THREE.SkinnedMesh[] {
  const result: THREE.SkinnedMesh[] = [];
  scene.traverse((obj) => {
    if (!(obj as THREE.SkinnedMesh).isSkinnedMesh) return;
    const mesh = obj as THREE.SkinnedMesh;
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    const isRelevant = mats.some((m) => {
      if (!m) return false;
      // CLOTH materials (outfit garments)
      if (/CLOTH/i.test(m.name)) return true;
      // Body SKIN materials (fitted body, excludes face)
      if (/SKIN/i.test(m.name) && /Body/i.test(m.name)) return true;
      return false;
    });
    if (isRelevant) {
      result.push(mesh);
    }
  });
  return result;
}

/**
 * Reparent outfit-only bones (skirt physics, etc.) to matching parent bones
 * in the base model so their world matrices are computed correctly.
 * Returns the root bones that were reparented (for cleanup).
 */
function reparentOrphanBones(
  outfitScene: THREE.Object3D,
  baseBoneMap: Map<string, THREE.Bone>
): THREE.Bone[] {
  const reparented: THREE.Bone[] = [];

  // Collect all outfit bones before modifying the hierarchy
  const outfitBones: THREE.Bone[] = [];
  outfitScene.traverse((obj) => {
    if ((obj as THREE.Bone).isBone) {
      outfitBones.push(obj as THREE.Bone);
    }
  });

  for (const bone of outfitBones) {
    if (baseBoneMap.has(bone.name)) continue;

    const parent = bone.parent;
    if (!parent || !(parent as THREE.Bone).isBone) continue;
    if (!baseBoneMap.has(parent.name)) continue;

    // This bone's parent exists in the base model — reparent the subtree
    const baseParent = baseBoneMap.get(parent.name)!;
    if (bone.parent !== baseParent) {
      baseParent.add(bone);
      reparented.push(bone);
    }
    // Register so child orphans can find this bone as their parent
    baseBoneMap.set(bone.name, bone);
  }

  return reparented;
}

/**
 * Rebind a SkinnedMesh to use the base model's bone nodes.
 * Recalculates boneInverses from the base bones' current world matrices
 * so that the skinning is correct even when the base model has been
 * transformed (e.g. VRM scene rotation).
 */
function rebindToBaseSkeleton(
  mesh: THREE.SkinnedMesh,
  baseBoneMap: Map<string, THREE.Bone>
) {
  const oldSkeleton = mesh.skeleton;
  const newBones: THREE.Bone[] = [];

  for (const oldBone of oldSkeleton.bones) {
    newBones.push(baseBoneMap.get(oldBone.name) ?? oldBone);
  }

  // Create skeleton WITHOUT old boneInverses — Three.js will auto-calculate
  // them from the base bones' current matrixWorld values.
  const newSkeleton = new THREE.Skeleton(newBones);
  mesh.bind(newSkeleton);
}

export function OutfitAttachment() {
  const { scene } = useThree();
  const meshesRef = useRef<THREE.SkinnedMesh[]>([]);
  const reparentedBonesRef = useRef<THREE.Bone[]>([]);
  const prevUrl = useRef<string | null>(null);
  const loaderRef = useRef<GLTFLoader | null>(null);

  useEffect(() => {
    if (!loaderRef.current) {
      loaderRef.current = new GLTFLoader();
    }
    const loader = loaderRef.current;

    function cleanup() {
      for (const mesh of meshesRef.current) {
        scene.remove(mesh);
        mesh.geometry.dispose();
      }
      meshesRef.current = [];

      // Remove reparented bones from the base model
      for (const bone of reparentedBonesRef.current) {
        bone.parent?.remove(bone);
      }
      reparentedBonesRef.current = [];
    }

    const unsubscribe = useEditorStore.subscribe((state) => {
      const { outfitUrl } = state;

      if (outfitUrl !== prevUrl.current) {
        prevUrl.current = outfitUrl;
        cleanup();

        if (outfitUrl) {
          const baseVrm = getBaseVRM();
          if (!baseVrm) {
            console.error('[OutfitAttachment] Base VRM not loaded yet');
            return;
          }

          loader.loadAsync(outfitUrl).then((gltf) => {
            if (prevUrl.current !== outfitUrl) return;

            // Ensure base VRM world matrices are up-to-date before
            // we read bone.matrixWorld for boneInverse calculation.
            baseVrm.scene.updateWorldMatrix(true, true);

            // Build base bone map
            const baseBoneMap = new Map<string, THREE.Bone>();
            baseVrm.scene.traverse((obj) => {
              if ((obj as THREE.Bone).isBone) {
                baseBoneMap.set(obj.name, obj as THREE.Bone);
              }
            });

            // Update outfit scene matrices for correct reparenting
            gltf.scene.updateWorldMatrix(true, true);

            // Reparent outfit-only bones (skirt physics, etc.) to base model
            const reparented = reparentOrphanBones(gltf.scene, baseBoneMap);
            reparentedBonesRef.current = reparented;

            // After reparenting, update world matrices again so new bones
            // have correct matrixWorld values for boneInverse calculation.
            baseVrm.scene.updateWorldMatrix(true, true);

            // Extract outfit meshes (cloth + fitted body)
            const outfitMeshes = extractOutfitMeshes(gltf.scene);
            console.log(
              `[OutfitAttachment] ${outfitMeshes.length} outfit mesh(es), ${reparented.length} bone(s) reparented`
            );

            for (const mesh of outfitMeshes) {
              rebindToBaseSkeleton(mesh, baseBoneMap);
              // Match base VRM orientation (VRM faces +Z, scene.rotation.y = PI)
              mesh.rotation.y = Math.PI;
              // Prevent frustum-culling issues with rebound skeleton
              mesh.frustumCulled = false;
              scene.add(mesh);
              meshesRef.current.push(mesh);
            }
          }).catch((err) => {
            console.error('[OutfitAttachment] Failed to load outfit:', err);
          });
        }
      }
    });

    return () => {
      unsubscribe();
      cleanup();
    };
  }, [scene]);

  return null;
}
