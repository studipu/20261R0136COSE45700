'use client';

import { useRef, useImperativeHandle, forwardRef, useEffect } from 'react';
import { useThree } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import * as THREE from 'three';

const DEFAULT_POSITION = new THREE.Vector3(0, 1.2, 2);
const DEFAULT_TARGET = new THREE.Vector3(0, 1.0, 0);

export const CameraControls = forwardRef<{ reset: () => void }>(
  function CameraControls(_, ref) {
    const controlsRef = useRef<OrbitControlsImpl>(null);
    const { camera } = useThree();

    // Save initial state after mount so reset() works correctly
    useEffect(() => {
      const controls = controlsRef.current;
      if (controls) {
        controls.target.copy(DEFAULT_TARGET);
        controls.object.position.copy(DEFAULT_POSITION);
        controls.saveState();
      }
    }, []);

    useImperativeHandle(ref, () => ({
      reset: () => {
        const controls = controlsRef.current;
        if (controls) {
          controls.target.copy(DEFAULT_TARGET);
          camera.position.copy(DEFAULT_POSITION);
          controls.update();
        }
      },
    }));

    return (
      <OrbitControls
        ref={controlsRef}
        target={[DEFAULT_TARGET.x, DEFAULT_TARGET.y, DEFAULT_TARGET.z]}
        minDistance={0.5}
        maxDistance={5}
        enablePan={true}
        enableDamping={true}
        dampingFactor={0.1}
      />
    );
  }
);
