'use client';

import { useEffect, useRef } from 'react';
import { useThree, useFrame } from '@react-three/fiber';
import { useEditorStore } from '@/stores/editorStore';
import { loadHairGLB, type HairLoadResult } from '@/lib/hair-loader';
import { getBaseVRM } from '@/lib/vrm-ref';
import type { VRMSpringBoneManager } from '@pixiv/three-vrm-springbone';
import * as THREE from 'three';

// ---------------------------------------------------------------------------
// Color utilities (unchanged from original)
// ---------------------------------------------------------------------------

function applyColorToGroup(group: THREE.Group, hex: string) {
  const color = new THREE.Color(hex);
  group.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const mat of mats) {
      const std = mat as THREE.MeshStandardMaterial;
      if (!std.color) continue;

      // Store original map on first color application
      if (std.map && !mat.userData._origMap) {
        mat.userData._origMap = std.map;
      }
      // Remove texture so color is applied directly (not multiplied)
      std.map = null;
      std.color.set(color);
      std.needsUpdate = true;
    }
  });
}

function restoreOriginalColor(group: THREE.Group) {
  group.traverse((obj) => {
    const mesh = obj as THREE.Mesh;
    if (!mesh.isMesh) return;
    const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
    for (const mat of mats) {
      const std = mat as THREE.MeshStandardMaterial;
      if (mat.userData._origMap) {
        std.map = mat.userData._origMap;
        std.color.set(0xffffff);
        delete mat.userData._origMap;
        std.needsUpdate = true;
      }
    }
  });
}

// ---------------------------------------------------------------------------
// Bone reparenting & skeleton rebinding (following OutfitAttachment pattern)
// ---------------------------------------------------------------------------

/**
 * Reparent hair-only bones (J_Sec_Hair*, etc.) to matching parent bones
 * in the base model so world matrices are computed correctly.
 * Also reparents collider Object3Ds that are children of base-model bones.
 */
function reparentOrphanBones(
  hairScene: THREE.Object3D,
  baseBoneMap: Map<string, THREE.Bone>,
): THREE.Bone[] {
  const reparented: THREE.Bone[] = [];

  // Collect all hair bones before modifying hierarchy
  const hairBones: THREE.Bone[] = [];
  hairScene.traverse((obj) => {
    if ((obj as THREE.Bone).isBone) {
      hairBones.push(obj as THREE.Bone);
    }
  });

  for (const bone of hairBones) {
    // If the base already has this bone, skip — we'll rebind to it
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
 * Reparent SpringBone collider Object3Ds to the corresponding base bone.
 * Colliders reference a node (Object3D) that must be in the correct skeleton
 * hierarchy for collision detection to work.
 */
function reparentColliders(
  springBoneManager: VRMSpringBoneManager,
  baseBoneMap: Map<string, THREE.Bone>,
): THREE.Object3D[] {
  const reparented: THREE.Object3D[] = [];

  for (const collider of springBoneManager.colliders) {
    const obj = collider.shape ? (collider as unknown as { bone?: THREE.Object3D }).bone : null;
    // The collider itself is an Object3D — check its parent
    const colliderObj = collider as unknown as THREE.Object3D;
    if (!colliderObj.parent) continue;

    const parentName = colliderObj.parent.name;
    if (parentName && baseBoneMap.has(parentName)) {
      const baseParent = baseBoneMap.get(parentName)!;
      if (colliderObj.parent !== baseParent) {
        baseParent.add(colliderObj);
        reparented.push(colliderObj);
      }
    }
  }

  return reparented;
}

/**
 * Rebind a SkinnedMesh to use the base model's bone nodes.
 */
function rebindToBaseSkeleton(
  mesh: THREE.SkinnedMesh,
  baseBoneMap: Map<string, THREE.Bone>,
) {
  const oldSkeleton = mesh.skeleton;
  const newBones: THREE.Bone[] = [];

  for (const oldBone of oldSkeleton.bones) {
    newBones.push(baseBoneMap.get(oldBone.name) ?? oldBone);
  }

  const newSkeleton = new THREE.Skeleton(newBones);
  mesh.bind(newSkeleton);
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface HairSlotState {
  group: THREE.Group | null;
  meshes: THREE.SkinnedMesh[];
  reparentedBones: THREE.Bone[];
  reparentedColliders: THREE.Object3D[];
}

function emptySlot(): HairSlotState {
  return { group: null, meshes: [], reparentedBones: [], reparentedColliders: [] };
}

export function HairAttachment() {
  const { scene } = useThree();
  const frontRef = useRef<HairSlotState>(emptySlot());
  const backRef = useRef<HairSlotState>(emptySlot());
  const frontManagerRef = useRef<VRMSpringBoneManager | null>(null);
  const backManagerRef = useRef<VRMSpringBoneManager | null>(null);
  const prevFrontUrl = useRef<string | null>(null);
  const prevBackUrl = useRef<string | null>(null);
  const prevColor = useRef<string | null>(null);

  // --- SpringBone physics update each frame ---
  useFrame((_, delta) => {
    frontManagerRef.current?.update(delta);
    backManagerRef.current?.update(delta);
  });

  useEffect(() => {
    function cleanupSlot(
      slotRef: React.MutableRefObject<HairSlotState>,
      managerRef: React.MutableRefObject<VRMSpringBoneManager | null>,
    ) {
      const slot = slotRef.current;

      // Remove meshes from scene
      for (const mesh of slot.meshes) {
        scene.remove(mesh);
        mesh.geometry.dispose();
      }

      // Remove reparented colliders
      for (const obj of slot.reparentedColliders) {
        obj.parent?.remove(obj);
      }

      // Remove reparented bones from base model
      for (const bone of slot.reparentedBones) {
        bone.parent?.remove(bone);
      }

      managerRef.current = null;
      slotRef.current = emptySlot();
    }

    async function loadHairSlot(
      url: string,
      slotRef: React.MutableRefObject<HairSlotState>,
      managerRef: React.MutableRefObject<VRMSpringBoneManager | null>,
      prevUrlRef: React.MutableRefObject<string | null>,
    ) {
      const baseVrm = getBaseVRM();
      if (!baseVrm) {
        console.error('[HairAttachment] Base VRM not loaded yet');
        return;
      }

      let result: HairLoadResult;
      try {
        result = await loadHairGLB(url);
      } catch (err) {
        console.error('[HairAttachment] Failed to load hair:', err);
        return;
      }

      // Stale check — URL may have changed while loading
      if (prevUrlRef.current !== url) return;

      const { scene: hairScene, springBoneManager } = result;

      // Ensure base VRM world matrices are up-to-date
      baseVrm.scene.updateWorldMatrix(true, true);

      // Build base bone map
      const baseBoneMap = new Map<string, THREE.Bone>();
      baseVrm.scene.traverse((obj) => {
        if ((obj as THREE.Bone).isBone) {
          baseBoneMap.set(obj.name, obj as THREE.Bone);
        }
      });

      // Update hair scene matrices
      hairScene.updateWorldMatrix(true, true);

      // Reparent hair-only bones to base skeleton
      const reparentedBones = reparentOrphanBones(hairScene, baseBoneMap);

      // Reparent colliders to base skeleton
      let reparentedColliders: THREE.Object3D[] = [];
      if (springBoneManager) {
        reparentedColliders = reparentColliders(springBoneManager, baseBoneMap);
      }

      // Update world matrices after reparenting
      baseVrm.scene.updateWorldMatrix(true, true);

      // Extract and rebind SkinnedMeshes
      const meshes: THREE.SkinnedMesh[] = [];
      hairScene.traverse((obj) => {
        if ((obj as THREE.SkinnedMesh).isSkinnedMesh) {
          meshes.push(obj as THREE.SkinnedMesh);
        }
      });

      for (const mesh of meshes) {
        rebindToBaseSkeleton(mesh, baseBoneMap);
        mesh.rotation.y = Math.PI;
        mesh.frustumCulled = false;
        // Apply current hair color if set
        const currentColor = useEditorStore.getState().hairColor;
        if (currentColor) {
          const color = new THREE.Color(currentColor);
          const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
          for (const mat of mats) {
            const std = mat as THREE.MeshStandardMaterial;
            if (!std.color) continue;
            if (std.map && !mat.userData._origMap) {
              mat.userData._origMap = std.map;
            }
            std.map = null;
            std.color.set(color);
            std.needsUpdate = true;
          }
        }
        scene.add(mesh);
      }

      // Reset SpringBone initial state after reparenting
      if (springBoneManager) {
        springBoneManager.setInitState();
        managerRef.current = springBoneManager;
        const jointCount = springBoneManager.joints.size;
        console.log(
          `[HairAttachment] SpringBone manager loaded with ${jointCount} joint(s)`,
        );
      }

      slotRef.current = {
        group: hairScene,
        meshes,
        reparentedBones,
        reparentedColliders,
      };
    }

    const unsubscribe = useEditorStore.subscribe((state) => {
      const { hairFrontUrl, hairBackUrl, hairColor } = state;

      // Handle front hair
      if (hairFrontUrl !== prevFrontUrl.current) {
        prevFrontUrl.current = hairFrontUrl;
        cleanupSlot(frontRef, frontManagerRef);

        if (hairFrontUrl) {
          loadHairSlot(hairFrontUrl, frontRef, frontManagerRef, prevFrontUrl);
        }
      }

      // Handle back hair
      if (hairBackUrl !== prevBackUrl.current) {
        prevBackUrl.current = hairBackUrl;
        cleanupSlot(backRef, backManagerRef);

        if (hairBackUrl) {
          loadHairSlot(hairBackUrl, backRef, backManagerRef, prevBackUrl);
        }
      }

      // Handle hair color change
      if (hairColor !== prevColor.current) {
        prevColor.current = hairColor;
        for (const slotRef of [frontRef, backRef]) {
          const group = slotRef.current.group;
          if (!group) continue;
          if (hairColor) {
            applyColorToGroup(group, hairColor);
          } else {
            restoreOriginalColor(group);
          }
        }
      }
    });

    return () => {
      unsubscribe();
      cleanupSlot(frontRef, frontManagerRef);
      cleanupSlot(backRef, backManagerRef);
    };
  }, [scene]);

  return null;
}
