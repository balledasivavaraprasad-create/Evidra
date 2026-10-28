import React, { useRef, useMemo, useEffect, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

interface EvidenceCoreProps {
  scrollProgress: number;
}

const EvidenceCore: React.FC<EvidenceCoreProps> = ({ scrollProgress }) => {
  const coreRef = useRef<THREE.Mesh>(null);
  const outerRingRef = useRef<THREE.Group>(null);
  const innerRingRef = useRef<THREE.Group>(null);
  const beaconsGroupRef = useRef<THREE.Group>(null);

  // Procedural node points along orbital paths
  const orbitalNodes = useMemo(() => {
    const nodes: Array<[number, number, number]> = [];
    const count = 16;
    for (let i = 0; i < count; i++) {
      const angle = (i / count) * Math.PI * 2;
      const radius = 2.4 + (i % 3) * 0.4;
      nodes.push([Math.cos(angle) * radius, (Math.sin(angle * 2) * 0.3), Math.sin(angle) * radius]);
    }
    return nodes;
  }, []);

  useFrame((state, delta) => {
    // 1. Smooth rotation based on time + scroll damping
    if (coreRef.current) {
      coreRef.current.rotation.y += delta * (0.35 + scrollProgress * 0.8);
      coreRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.5) * 0.2 + scrollProgress * 0.6;
      
      // Dynamic scale morphing along scroll path
      const targetScale = 1.0 + Math.sin(scrollProgress * Math.PI) * 0.25;
      coreRef.current.scale.lerp(new THREE.Vector3(targetScale, targetScale, targetScale), 0.1);
    }

    if (outerRingRef.current) {
      outerRingRef.current.rotation.z += delta * 0.2;
      outerRingRef.current.rotation.y = THREE.MathUtils.lerp(
        outerRingRef.current.rotation.y,
        scrollProgress * Math.PI,
        0.08
      );
    }

    if (innerRingRef.current) {
      innerRingRef.current.rotation.x -= delta * 0.25;
      innerRingRef.current.rotation.z = THREE.MathUtils.lerp(
        innerRingRef.current.rotation.z,
        -scrollProgress * Math.PI * 1.2,
        0.08
      );
    }

    // PICO satellite convergence as user scrolls deeper into review synthesis
    if (beaconsGroupRef.current) {
      const convergence = 1.0 - scrollProgress * 0.45;
      beaconsGroupRef.current.scale.set(convergence, convergence, convergence);
      beaconsGroupRef.current.rotation.y += delta * 0.4;
    }

    // Camera dynamic tracking along scroll path
    const targetCameraY = 0.5 - scrollProgress * 1.5;
    const targetCameraZ = 5.0 - scrollProgress * 1.0;
    state.camera.position.y = THREE.MathUtils.lerp(state.camera.position.y, targetCameraY, 0.05);
    state.camera.position.z = THREE.MathUtils.lerp(state.camera.position.z, targetCameraZ, 0.05);
    state.camera.lookAt(0, 0, 0);
  });

  return (
    <group>
      {/* Ambient & Directional Lighting with Silver & Gold Sheen */}
      <ambientLight intensity={0.7} />
      <directionalLight position={[5, 8, 5]} intensity={1.5} color="#ffffff" />
      <directionalLight position={[-5, -4, -5]} intensity={0.9} color="#d4af37" />
      <pointLight position={[0, 0, 0]} intensity={2.0} color="#38bdf8" distance={6} />

      {/* Central Faceted Evidence Crystal (Icosahedron) */}
      <mesh ref={coreRef} position={[0, 0, 0]}>
        <icosahedronGeometry args={[1.1, 1]} />
        <meshPhysicalMaterial
          color="#e2e8f0"
          emissive="#0284c7"
          emissiveIntensity={0.3}
          metalness={0.85}
          roughness={0.12}
          clearcoat={1.0}
          clearcoatRoughness={0.1}
          wireframe={false}
        />
      </mesh>

      {/* Inner Orbit Ring (Europe PMC / PubMed Integration) */}
      <group ref={innerRingRef}>
        <mesh rotation={[Math.PI / 3, 0, 0]}>
          <torusGeometry args={[2.0, 0.018, 16, 100]} />
          <meshStandardMaterial color="#94a3b8" metalness={0.9} roughness={0.2} />
        </mesh>
      </group>

      {/* Outer Orbit Ring with Gold Accents */}
      <group ref={outerRingRef}>
        <mesh rotation={[-Math.PI / 4, 0, Math.PI / 6]}>
          <torusGeometry args={[2.8, 0.022, 16, 120]} />
          <meshStandardMaterial color="#d4af37" metalness={0.8} roughness={0.25} />
        </mesh>
      </group>

      {/* Orbiting Literature Records (Data Spheres) */}
      {orbitalNodes.map((pos, idx) => (
        <mesh key={idx} position={pos}>
          <sphereGeometry args={[0.065, 12, 12]} />
          <meshStandardMaterial
            color={idx % 2 === 0 ? "#38bdf8" : "#fbbf24"}
            emissive={idx % 2 === 0 ? "#0284c7" : "#d97706"}
            emissiveIntensity={0.6}
            metalness={0.7}
            roughness={0.3}
          />
        </mesh>
      ))}

      {/* PICO Entity Satellite Beacons */}
      <group ref={beaconsGroupRef}>
        {/* P - Population (Cyan) */}
        <mesh position={[1.8, 0.8, 0]}>
          <octahedronGeometry args={[0.2, 0]} />
          <meshStandardMaterial color="#06b6d4" emissive="#0891b2" emissiveIntensity={0.8} />
        </mesh>
        {/* I - Intervention (Purple) */}
        <mesh position={[-1.8, 0.8, 0]}>
          <octahedronGeometry args={[0.2, 0]} />
          <meshStandardMaterial color="#a855f7" emissive="#7e22ce" emissiveIntensity={0.8} />
        </mesh>
        {/* C - Comparison (Gold) */}
        <mesh position={[0, -1.6, 1.2]}>
          <octahedronGeometry args={[0.2, 0]} />
          <meshStandardMaterial color="#f59e0b" emissive="#b45309" emissiveIntensity={0.8} />
        </mesh>
        {/* O - Outcome (Emerald) */}
        <mesh position={[0, -1.6, -1.2]}>
          <octahedronGeometry args={[0.2, 0]} />
          <meshStandardMaterial color="#10b981" emissive="#059669" emissiveIntensity={0.8} />
        </mesh>
      </group>
    </group>
  );
};

export const EvidenceScene3D: React.FC = () => {
  const [scrollProgress, setScrollProgress] = useState(0);
  const [hasWebGL, setHasWebGL] = useState(true);

  // Check WebGL availability and track window scroll
  useEffect(() => {
    try {
      const canvas = document.createElement("canvas");
      const gl = canvas.getContext("webgl") || canvas.getContext("experimental-webgl");
      if (!gl) setHasWebGL(false);
    } catch {
      setHasWebGL(false);
    }

    const handleScroll = () => {
      const totalScroll = document.documentElement.scrollHeight - window.innerHeight;
      if (totalScroll > 0) {
        setScrollProgress(Math.min(1, Math.max(0, window.scrollY / totalScroll)));
      }
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  if (!hasWebGL) {
    return null; // Gracefully unmounts and falls back to HeroStatic
  }

  return (
    <div className="w-full h-full min-h-[380px] sm:min-h-[460px] relative overflow-hidden rounded-2xl">
      <Canvas
        camera={{ position: [0, 0.5, 5], fov: 45 }}
        dpr={[1, 1.5]}
        gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
        className="w-full h-full cursor-grab active:cursor-grabbing"
      >
        <EvidenceCore scrollProgress={scrollProgress} />
      </Canvas>
    </div>
  );
};

export default EvidenceScene3D;
