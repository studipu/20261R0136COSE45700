'use client';

import { useThree } from '@react-three/fiber';
import { useEffect } from 'react';
import * as THREE from 'three';

export function SceneLighting() {
  const { scene } = useThree();

  useEffect(() => {
    // Studio-style gradient background
    const topColor = new THREE.Color(0x1a1530);
    const bottomColor = new THREE.Color(0x0d0b14);
    scene.background = new THREE.Color(0x110f1a);

    // Subtle fog for depth
    scene.fog = new THREE.Fog(0x110f1a, 4, 12);

    return () => {
      scene.background = null;
      scene.fog = null;
    };
  }, [scene]);

  return (
    <>
      {/* Key light — warm, slightly right */}
      <directionalLight
        position={[3, 4, 2]}
        intensity={1.8}
        color="#fff5ee"
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      {/* Fill light — cool blue tint from left */}
      <directionalLight position={[-3, 2, -1]} intensity={0.6} color="#c4d4ff" />
      {/* Rim light — purple accent from behind */}
      <directionalLight position={[0, 3, -4]} intensity={0.8} color="#a78bfa" />
      {/* Bottom bounce light */}
      <directionalLight position={[0, -1, 2]} intensity={0.15} color="#e8d5f5" />
      {/* Ambient — soft purple tint */}
      <ambientLight intensity={0.35} color="#e8e0f0" />
      {/* Hemisphere for sky/ground color blend */}
      <hemisphereLight args={['#c4b5fd', '#1e1b2e', 0.3]} />
    </>
  );
}
