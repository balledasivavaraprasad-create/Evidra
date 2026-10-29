import React, { useEffect, useRef } from "react";
import * as THREE from "three";
import { useTheme } from "../context/ThemeContext";

interface ParticleBackgroundProps {
  className?: string;
  /** Base particle count on desktop; reduced automatically on small screens. */
  count?: number;
}

/**
 * GPU-rendered particle field using native Three.js.
 *
 * Rendered on a transparent canvas fixed behind the page content. Theme-aware,
 * honours `prefers-reduced-motion`, pauses when the tab is hidden, and cleans
 * up all GPU resources on unmount (Strict Mode safe).
 */
export const ParticleBackground: React.FC<ParticleBackgroundProps> = ({
  className,
  count = 900,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const light = theme === "light";
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    // Particle colour per theme (subtle, low-contrast against the page bg).
    const particleColor = light ? 0x9ca3af : 0xd4d4d8;
    const particleOpacity = light ? 0.45 : 0.35;

    // Renderer
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        canvas,
        alpha: true,
        antialias: false,
        powerPreference: "high-performance",
      });
    } catch {
      // No WebGL available: leave the canvas blank (CSS bg still shows).
      return;
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(window.innerWidth, window.innerHeight, false);
    renderer.setClearColor(0x000000, 0);

    // Camera
    const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 0.1, 100);
    camera.position.set(0, 0, 5);

    const scene = new THREE.Scene();

    // Particle system
    const effectiveCount = window.innerWidth < 768 ? Math.round(count * 0.45) : count;

    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(effectiveCount * 3);
    const velocities = new Float32Array(effectiveCount * 3);

    const buildPositions = () => {
      const aspect = window.innerWidth / window.innerHeight;
      const viewH = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * camera.position.z;
      const viewW = viewH * aspect;
      const depth = 4;
      for (let i = 0; i < effectiveCount; i++) {
        const i3 = i * 3;
        positions[i3] = (Math.random() - 0.5) * viewW;
        positions[i3 + 1] = (Math.random() - 0.5) * viewH;
        positions[i3 + 2] = (Math.random() - 0.5) * depth;
        velocities[i3] = (Math.random() - 0.5) * 0.0006;
        velocities[i3 + 1] = (Math.random() - 0.5) * 0.0006;
        velocities[i3 + 2] = (Math.random() - 0.5) * 0.0003;
      }
      geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));
    };
    buildPositions();

    const material = new THREE.PointsMaterial({
      color: particleColor,
      size: light ? 0.045 : 0.05,
      transparent: true,
      opacity: particleOpacity,
      sizeAttenuation: true,
      depthWrite: false,
      blending: THREE.NormalBlending,
    });

    const points = new THREE.Points(geometry, material);
    scene.add(points);

    document.addEventListener("visibilitychange", handleVisibility);

    let raf = 0;
    let last = performance.now();
    let running = !reduceMotion;

    function handleVisibility() {
      if (document.hidden) {
        if (raf) {
          cancelAnimationFrame(raf);
          raf = 0;
        }
      } else if (running && !raf) {
        last = performance.now();
        raf = requestAnimationFrame(loop);
      }
    }

    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;

      if (!reduceMotion) {
        const pos = geometry.attributes.position as THREE.BufferAttribute;
        const arr = pos.array as Float32Array;
        const viewH = 2 * Math.tan(THREE.MathUtils.degToRad(camera.fov) / 2) * camera.position.z;
        const viewW = viewH * (window.innerWidth / window.innerHeight);
        const halfW = viewW / 2;
        const halfH = viewH / 2;
        const depth = 2;
        for (let i = 0; i < effectiveCount; i++) {
          const i3 = i * 3;
          arr[i3] += velocities[i3];
          arr[i3 + 1] += velocities[i3 + 1];
          arr[i3 + 2] += velocities[i3 + 2];

          // Wrap around edges
          if (arr[i3] > halfW) arr[i3] = -halfW;
          else if (arr[i3] < -halfW) arr[i3] = halfW;
          if (arr[i3 + 1] > halfH) arr[i3 + 1] = -halfH;
          else if (arr[i3 + 1] < -halfH) arr[i3 + 1] = halfH;
          if (arr[i3 + 2] > depth) arr[i3 + 2] = -depth;
          else if (arr[i3 + 2] < -depth) arr[i3 + 2] = depth;
        }
        pos.needsUpdate = true;
      }

      renderer.render(scene, camera);
      raf = requestAnimationFrame(loop);
    };

    const onResize = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h, false);
      buildPositions();
    };
    window.addEventListener("resize", onResize);

    // Initial render (also the only render for reduced motion)
    renderer.render(scene, camera);
    if (running) {
      last = performance.now();
      raf = requestAnimationFrame(loop);
    }

    return () => {
      running = false;
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      document.removeEventListener("visibilitychange", handleVisibility);

      geometry.dispose();
      material.dispose();
      renderer.dispose();
    };
  }, [theme, count]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className={`fixed inset-0 z-0 pointer-events-none ${className ?? ""}`}
    />
  );
};

export default ParticleBackground;
