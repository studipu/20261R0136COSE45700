'use client';

import { useEffect, useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { useVRM } from '@/hooks/useVRM';
import { useEditorStore } from '@/stores/editorStore';
import { applyMaterialColor, applyMaterialProperty, detectMaterials } from '@/lib/vrm/materials';
import type { DetectedMaterial } from '@/lib/vrm/materials';
import type { VRM } from '@pixiv/three-vrm';
import * as THREE from 'three';

interface VRMModelProps {
  url: string;
  onLoaded?: (
    expressionNames: string[],
    morphTargetNames: string[],
    boneNames: string[],
    detectedMaterials: DetectedMaterial[]
  ) => void;
}

export function VRMModel({ url, onLoaded }: VRMModelProps) {
  const { vrm, expressionNames, morphTargetNames, error } = useVRM(url);
  const vrmRef = useRef<VRM | null>(null);
  const onLoadedRef = useRef(onLoaded);
  onLoadedRef.current = onLoaded;
  const prevMaterialsRef = useRef<string>('');
  // Track which slots are skin category
  const skinSlotsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (vrm) {
      vrmRef.current = vrm;

      const boneNames: string[] = [];
      if (vrm.humanoid) {
        const humanBones = vrm.humanoid.humanBones;
        for (const boneName of Object.keys(humanBones)) {
          if (humanBones[boneName as keyof typeof humanBones]?.node) {
            boneNames.push(boneName);
          }
        }
      }

      const detectedMats = detectMaterials(vrm);

      // Cache skin slot names for use in useFrame
      skinSlotsRef.current = new Set(
        detectedMats.filter((m) => m.category === 'skin').map((m) => m.slotName)
      );

      console.log('[VRM] Loaded successfully');
      console.log('[VRM] Expressions:', expressionNames);
      console.log('[VRM] MorphTargets:', morphTargetNames);
      console.log('[VRM] Bones:', boneNames);
      console.log('[VRM] Skin slots:', Array.from(skinSlotsRef.current));
      onLoadedRef.current?.(expressionNames, morphTargetNames, boneNames, detectedMats);
    }
  }, [vrm, expressionNames, morphTargetNames]);

  useFrame((_, delta) => {
    const currentVrm = vrmRef.current;
    if (!currentVrm) return;

    const { morphTargets, boneScales, materials } = useEditorStore.getState();

    // Separate expression-managed names from raw morph targets
    const expressionSet = new Set<string>();
    if (currentVrm.expressionManager) {
      for (const expr of currentVrm.expressionManager.expressions) {
        expressionSet.add(expr.expressionName);
      }
    }

    // Apply VRM Expression API (only for registered expressions)
    if (currentVrm.expressionManager) {
      for (const [name, value] of Object.entries(morphTargets)) {
        if (expressionSet.has(name)) {
          currentVrm.expressionManager.setValue(name, value);
        }
      }
    }

    // Apply bone scales via VRM Humanoid
    if (currentVrm.humanoid) {
      const humanBones = currentVrm.humanoid.humanBones;
      for (const [boneName, scale] of Object.entries(boneScales)) {
        const boneEntry = humanBones[boneName as keyof typeof humanBones];
        if (boneEntry?.node) {
          boneEntry.node.scale.set(scale.x, scale.y, scale.z);
        }
      }
    }

    // Apply material changes (only when changed to avoid per-frame overhead)
    const materialKey = JSON.stringify(materials);
    if (materialKey !== prevMaterialsRef.current) {
      prevMaterialsRef.current = materialKey;
      for (const [slotName, slot] of Object.entries(materials)) {
        const isSkin = skinSlotsRef.current.has(slotName);
        if (slot.color) {
          applyMaterialColor(currentVrm, slotName, slot.color as string, isSkin);
        }
        if (slot.metalness !== undefined) {
          applyMaterialProperty(currentVrm, slotName, 'metalness', slot.metalness as number);
        }
        if (slot.roughness !== undefined) {
          applyMaterialProperty(currentVrm, slotName, 'roughness', slot.roughness as number);
        }
        if (slot.opacity !== undefined) {
          applyMaterialProperty(currentVrm, slotName, 'opacity', slot.opacity as number);
        }
      }
    }

    // Update VRM internals (expressions, spring bones, etc.)
    currentVrm.update(delta);

    // Apply raw morphTargetInfluences (face_*, body_* from Blender)
    currentVrm.scene.traverse((object) => {
      const mesh = object as THREE.Mesh;
      if (mesh.isMesh && mesh.morphTargetDictionary && mesh.morphTargetInfluences) {
        for (const [name, value] of Object.entries(morphTargets)) {
          if (!expressionSet.has(name)) {
            const index = mesh.morphTargetDictionary[name];
            if (index !== undefined) {
              mesh.morphTargetInfluences[index] = value;
            }
          }
        }
      }
    });
  });

  if (error) {
    console.error('VRM load error:', error);
    return null;
  }

  if (!vrm) return null;

  return <primitive object={vrm.scene} />;
}
