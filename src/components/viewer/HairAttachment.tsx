'use client';

import { useEffect, useRef } from 'react';
import { useThree } from '@react-three/fiber';
import { useEditorStore } from '@/stores/editorStore';
import { loadGLB } from '@/lib/glb-loader';
import * as THREE from 'three';

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

export function HairAttachment() {
  const { scene } = useThree();
  const frontRef = useRef<THREE.Group | null>(null);
  const backRef = useRef<THREE.Group | null>(null);
  const prevFrontUrl = useRef<string | null>(null);
  const prevBackUrl = useRef<string | null>(null);
  const prevColor = useRef<string | null>(null);

  useEffect(() => {
    const unsubscribe = useEditorStore.subscribe((state) => {
      const { hairFrontUrl, hairBackUrl, hairColor } = state;

      // Handle front hair
      if (hairFrontUrl !== prevFrontUrl.current) {
        prevFrontUrl.current = hairFrontUrl;

        if (frontRef.current) {
          scene.remove(frontRef.current);
          frontRef.current = null;
        }

        if (hairFrontUrl) {
          loadGLB(hairFrontUrl).then((group) => {
            if (prevFrontUrl.current !== hairFrontUrl) return;
            group.rotation.y = Math.PI;
            // Apply current hair color if set
            const currentColor = useEditorStore.getState().hairColor;
            if (currentColor) applyColorToGroup(group, currentColor);
            scene.add(group);
            frontRef.current = group;
          }).catch((err) => {
            console.error('[HairAttachment] Failed to load front hair:', err);
          });
        }
      }

      // Handle back hair
      if (hairBackUrl !== prevBackUrl.current) {
        prevBackUrl.current = hairBackUrl;

        if (backRef.current) {
          scene.remove(backRef.current);
          backRef.current = null;
        }

        if (hairBackUrl) {
          loadGLB(hairBackUrl).then((group) => {
            if (prevBackUrl.current !== hairBackUrl) return;
            group.rotation.y = Math.PI;
            const currentColor = useEditorStore.getState().hairColor;
            if (currentColor) applyColorToGroup(group, currentColor);
            scene.add(group);
            backRef.current = group;
          }).catch((err) => {
            console.error('[HairAttachment] Failed to load back hair:', err);
          });
        }
      }

      // Handle hair color change
      if (hairColor !== prevColor.current) {
        prevColor.current = hairColor;
        if (hairColor) {
          if (frontRef.current) applyColorToGroup(frontRef.current, hairColor);
          if (backRef.current) applyColorToGroup(backRef.current, hairColor);
        } else {
          // Reset to original texture
          if (frontRef.current) restoreOriginalColor(frontRef.current);
          if (backRef.current) restoreOriginalColor(backRef.current);
        }
      }
    });

    return () => {
      unsubscribe();
      if (frontRef.current) {
        scene.remove(frontRef.current);
        frontRef.current = null;
      }
      if (backRef.current) {
        scene.remove(backRef.current);
        backRef.current = null;
      }
    };
  }, [scene]);

  return null;
}
