import React, { useEffect, useRef } from "react";
import { useTheme } from "../context/ThemeContext";

/**
 * Interactive jittered dash grid (Codyssey / confetti-sprinkle style).
 *
 * Small rounded coloured dashes sit on a jittered grid. They gently drift and
 * sway on their own, a slow wave ripples across the field, and dashes near the
 * cursor turn to point at it, swell, brighten and get nudged outward.
 * Pure Canvas 2D, theme-aware, honours prefers-reduced-motion.
 */

type Dash = {
  hx: number; // jittered home position
  hy: number;
  x: number; // current (eased) position
  y: number;
  base: number; // resting angle
  angle: number; // current (eased) angle
  len: number;
  scale: number; // current (eased) scale
  color: number;
  alpha: number;
  phase: number;
  freq: number;
  drift: number;
};

type RGB = [number, number, number];

// Google-ish confetti hues + soft pastels
const COLORS: RGB[] = [
  [66, 133, 244], // blue
  [234, 67, 53], // red
  [251, 188, 5], // yellow
  [52, 168, 83], // green
  [161, 194, 250], // light blue
  [246, 174, 169], // light red
  [253, 214, 99], // light yellow
  [129, 201, 149], // light green
];
const WEIGHTS = [16, 12, 14, 13, 14, 10, 11, 10];

const pickColor = () => {
  const total = WEIGHTS.reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (let i = 0; i < WEIGHTS.length; i++) {
    r -= WEIGHTS[i];
    if (r <= 0) return i;
  }
  return 0;
};

const SPACING = 30; // grid cell size in CSS px
const RADIUS = 170; // cursor influence radius

const shortestAngle = (from: number, to: number) => {
  let d = (to - from) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return d;
};

export const DashGridBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const light = theme === "light";
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let width = 0;
    let height = 0;
    let dashes: Dash[] = [];
    let raf = 0;
    let last = performance.now();
    const mouse = { x: -9999, y: -9999, active: false, strength: 0 };

    const build = () => {
      dashes = [];
      const cols = Math.ceil(width / SPACING) + 1;
      const rows = Math.ceil(height / SPACING) + 1;
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          // Leave some cells empty so it reads as scattered, not a rigid grid
          if (Math.random() < 0.3) continue;
          const hx = c * SPACING + (Math.random() - 0.5) * SPACING * 0.9;
          const hy = r * SPACING + (Math.random() - 0.5) * SPACING * 0.9;
          const base = (Math.random() - 0.5) * Math.PI * 1.4 + Math.PI / 2;
          dashes.push({
            hx,
            hy,
            x: hx,
            y: hy,
            base,
            angle: base,
            len: 4 + Math.random() * 6,
            scale: 1,
            color: pickColor(),
            alpha: light ? 0.3 + Math.random() * 0.45 : 0.18 + Math.random() * 0.42,
            phase: Math.random() * Math.PI * 2,
            freq: 0.4 + Math.random() * 0.8,
            drift: 1.5 + Math.random() * 3,
          });
        }
      }
    };

    const resize = () => {
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      build();
    };

    const draw = (dt: number, t: number) => {
      ctx.clearRect(0, 0, width, height);
      ctx.lineCap = "round";
      ctx.lineWidth = 1.7;

      // Fade cursor influence in/out smoothly
      mouse.strength += ((mouse.active ? 1 : 0) - mouse.strength) * Math.min(1, dt * 4);
      const ease = Math.min(1, dt * 7);

      for (let i = 0; i < dashes.length; i++) {
        const d = dashes[i];

        // Ambient motion: small orbit-like drift + a slow diagonal wave of rotation
        const wave = Math.sin(t * 0.7 - d.hx * 0.006 - d.hy * 0.004);
        let tx = d.hx + Math.sin(t * d.freq + d.phase) * d.drift;
        let ty = d.hy + Math.cos(t * d.freq * 0.8 + d.phase) * d.drift;
        let ta = d.base + wave * 0.45 + Math.sin(t * d.freq * 0.6 + d.phase) * 0.15;
        let ts = 1 + Math.max(0, wave) * 0.15;
        let extraAlpha = 0;

        // Cursor interaction
        if (mouse.strength > 0.01) {
          const dx = d.hx - mouse.x;
          const dy = d.hy - mouse.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < RADIUS * 1.6) {
            const k = Math.exp(-((dist / RADIUS) ** 2)) * mouse.strength;
            tx += (dx / dist) * k * 16;
            ty += (dy / dist) * k * 16;
            ta += shortestAngle(ta, Math.atan2(dy, dx)) * k;
            ts += k * 0.9;
            extraAlpha = k * 0.5;
          }
        }

        if (reduceMotion) {
          d.x = tx;
          d.y = ty;
          d.angle = ta;
          d.scale = ts;
        } else {
          d.x += (tx - d.x) * ease;
          d.y += (ty - d.y) * ease;
          d.angle += shortestAngle(d.angle, ta) * ease;
          d.scale += (ts - d.scale) * ease;
        }

        const half = (d.len * d.scale) / 2;
        const cx = Math.cos(d.angle) * half;
        const cy = Math.sin(d.angle) * half;
        const [r, g, b] = COLORS[d.color];
        ctx.strokeStyle = `rgba(${r},${g},${b},${Math.min(1, d.alpha + extraAlpha)})`;
        ctx.beginPath();
        ctx.moveTo(d.x - cx, d.y - cy);
        ctx.lineTo(d.x + cx, d.y + cy);
        ctx.stroke();
      }
    };

    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      draw(dt, now / 1000);
      raf = requestAnimationFrame(loop);
    };

    const onMove = (e: PointerEvent) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;
    };
    const onLeave = () => {
      mouse.active = false;
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onMove, { passive: true });
    document.addEventListener("pointerleave", onLeave);
    window.addEventListener("blur", onLeave);

    if (reduceMotion) {
      draw(0, 0);
    } else {
      raf = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onMove);
      document.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("blur", onLeave);
    };
  }, [theme]);

  return (
    <canvas
      ref={canvasRef}
      aria-hidden="true"
      className="fixed inset-0 z-0 pointer-events-none"
    />
  );
};

export default DashGridBackground;
