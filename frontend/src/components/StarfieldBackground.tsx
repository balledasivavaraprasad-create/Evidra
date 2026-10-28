import React, { useEffect, useRef } from "react";
import { useTheme } from "../context/ThemeContext";

/**
 * Full-screen "fly-through" starfield: small multi-coloured particles drift
 * towards the viewer and stream past the edges of the screen.
 * Pure Canvas 2D (no three.js) so it stays cheap on every page.
 */

type Particle = {
  x: number; // world-space x, roughly [-1.6, 1.6]
  y: number; // world-space y
  z: number; // depth, 1 = far away, ~0 = at the viewer
  speed: number;
  size: number;
  color: number; // index into palette
  phase: number; // twinkle phase
  twinkle: number; // twinkle speed
  px: number; // previous projected x (for streaks)
  py: number;
};

// [r, g, b, weight]
const DARK_PALETTE: Array<[number, number, number, number]> = [
  [255, 255, 255, 30], // pure white
  [203, 213, 225, 16], // silver
  [125, 211, 252, 16], // ice blue
  [96, 165, 250, 10], // royal blue
  [251, 191, 36, 12], // gold
  [253, 230, 138, 6], // champagne
  [248, 113, 113, 6], // crimson red
  [192, 132, 252, 4], // violet accent
];

const LIGHT_PALETTE: Array<[number, number, number, number]> = [
  [71, 85, 105, 26], // slate silver
  [30, 64, 175, 18], // deep blue
  [2, 132, 199, 14], // ocean blue
  [180, 83, 9, 14], // burnished gold
  [202, 138, 4, 10], // gold
  [185, 28, 28, 8], // crimson
  [109, 40, 217, 4], // violet
  [15, 23, 42, 6], // ink
];

const pickWeighted = (palette: Array<[number, number, number, number]>) => {
  const total = palette.reduce((s, c) => s + c[3], 0);
  let r = Math.random() * total;
  for (let i = 0; i < palette.length; i++) {
    r -= palette[i][3];
    if (r <= 0) return i;
  }
  return 0;
};

/** Pre-render one soft glowing dot per colour so drawing is just drawImage. */
const buildSprites = (palette: Array<[number, number, number, number]>, light: boolean) =>
  palette.map(([r, g, b]) => {
    const s = 64;
    const c = document.createElement("canvas");
    c.width = c.height = s;
    const ctx = c.getContext("2d")!;
    const grad = ctx.createRadialGradient(s / 2, s / 2, 0, s / 2, s / 2, s / 2);
    if (light) {
      grad.addColorStop(0, `rgba(${r},${g},${b},1)`);
      grad.addColorStop(0.35, `rgba(${r},${g},${b},0.75)`);
      grad.addColorStop(1, `rgba(${r},${g},${b},0)`);
    } else {
      grad.addColorStop(0, "rgba(255,255,255,1)");
      grad.addColorStop(0.18, `rgba(${r},${g},${b},0.95)`);
      grad.addColorStop(0.45, `rgba(${r},${g},${b},0.28)`);
      grad.addColorStop(1, `rgba(${r},${g},${b},0)`);
    }
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, s, s);
    return c;
  });

export const StarfieldBackground: React.FC = () => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const { theme } = useTheme();

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const light = theme === "light";
    const palette = light ? LIGHT_PALETTE : DARK_PALETTE;
    const sprites = buildSprites(palette, light);
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    let width = 0;
    let height = 0;
    let dpr = 1;
    let particles: Particle[] = [];
    let raf = 0;
    let last = performance.now();

    // Smoothed pointer parallax
    const pointer = { x: 0, y: 0, sx: 0, sy: 0 };

    const spawn = (p: Partial<Particle> = {}, far = true): Particle => ({
      x: (Math.random() * 2 - 1) * 1.6,
      y: (Math.random() * 2 - 1) * 1.1,
      z: far ? 0.75 + Math.random() * 0.25 : 0.05 + Math.random() * 0.95,
      speed: 0.035 + Math.random() * 0.075,
      size: 0.6 + Math.random() * 1.4,
      color: pickWeighted(palette),
      phase: Math.random() * Math.PI * 2,
      twinkle: 1 + Math.random() * 3,
      px: NaN,
      py: NaN,
      ...p,
    });

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio || 1, 2);
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${width}px`;
      canvas.style.height = `${height}px`;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

      const target = Math.min(900, Math.max(220, Math.floor((width * height) / 2200)));
      if (particles.length < target) {
        for (let i = particles.length; i < target; i++) particles.push(spawn({}, false));
      } else {
        particles = particles.slice(0, target);
      }
    };

    const draw = (dt: number, t: number) => {
      ctx.clearRect(0, 0, width, height);

      pointer.sx += (pointer.x - pointer.sx) * Math.min(1, dt * 2);
      pointer.sy += (pointer.y - pointer.sy) * Math.min(1, dt * 2);

      const focal = Math.max(width, height) * 0.5;
      const cx = width / 2 - pointer.sx * 40;
      const cy = height / 2 - pointer.sy * 40;

      ctx.globalCompositeOperation = light ? "source-over" : "lighter";

      for (let i = 0; i < particles.length; i++) {
        const p = particles[i];
        p.z -= p.speed * dt;

        const sx = cx + (p.x / p.z) * focal * 0.55;
        const sy = cy + (p.y / p.z) * focal * 0.55;

        if (p.z <= 0.02 || sx < -60 || sx > width + 60 || sy < -60 || sy > height + 60) {
          particles[i] = spawn();
          continue;
        }

        // Closer => bigger & brighter. Fade in from far away.
        const depth = 1 - p.z;
        const fadeIn = Math.min(1, (1 - p.z) / 0.2);
        const tw = 0.7 + 0.3 * Math.sin(t * p.twinkle + p.phase);
        const alpha = Math.min(1, (0.25 + depth * 0.9) * fadeIn * tw) * (light ? 0.55 : 1);
        const r = Math.max(0.4, p.size * (0.35 + depth * depth * 3.2));

        // Light speed streak for particles very close to the viewer
        if (!Number.isNaN(p.px) && depth > 0.72) {
          const [cr, cg, cb] = palette[p.color];
          ctx.strokeStyle = `rgba(${cr},${cg},${cb},${alpha * 0.35})`;
          ctx.lineWidth = r * 0.6;
          ctx.beginPath();
          ctx.moveTo(p.px, p.py);
          ctx.lineTo(sx, sy);
          ctx.stroke();
        }

        ctx.globalAlpha = alpha;
        const glow = r * (light ? 2.4 : 4.2);
        ctx.drawImage(sprites[p.color], sx - glow, sy - glow, glow * 2, glow * 2);
        ctx.globalAlpha = 1;

        p.px = sx;
        p.py = sy;
      }
      ctx.globalCompositeOperation = "source-over";
    };

    const loop = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      draw(dt, now / 1000);
      raf = requestAnimationFrame(loop);
    };

    const onPointer = (e: PointerEvent) => {
      pointer.x = (e.clientX / width) * 2 - 1;
      pointer.y = (e.clientY / height) * 2 - 1;
    };

    resize();
    window.addEventListener("resize", resize);
    window.addEventListener("pointermove", onPointer, { passive: true });

    if (reduceMotion) {
      draw(0, 0);
    } else {
      raf = requestAnimationFrame(loop);
    }

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", onPointer);
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

export default StarfieldBackground;
