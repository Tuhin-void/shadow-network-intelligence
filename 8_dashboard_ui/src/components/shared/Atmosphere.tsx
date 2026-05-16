import { useEffect, useRef } from 'react';

interface AtmosphereProps {
  /** Particle count — kept modest for 60fps */
  density?: number;
  /** Whether to render the drifting depth fog */
  fog?: boolean;
  /** Whether to render scanlines + noise */
  veil?: boolean;
  /** Whether to render the heartbeat grid */
  grid?: boolean;
  /** Visual intensity (0..1) */
  intensity?: number;
}

/**
 * Atmosphere — the living environment.
 *
 *  • Canvas particle field (drifting points + occasional connecting lines)
 *  • Depth fog (radial drift via CSS)
 *  • Scanlines + tactical noise overlay
 *  • Optional tactical grid
 *
 * Performance: single rAF loop, capped at ~60fps via DOMHighRes timing,
 * with particle count clamped to a sensible upper bound.
 */
export function Atmosphere({
  density = 60,
  fog = true,
  veil = true,
  grid = false,
  intensity = 1,
}: AtmosphereProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let raf = 0;
    let running = true;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let w = 0;
    let h = 0;

    type P = { x: number; y: number; vx: number; vy: number; r: number; a: number; tw: number };
    let particles: P[] = [];
    const count = Math.min(120, Math.max(20, density));

    const rand = (a: number, b: number) => a + Math.random() * (b - a);

    function seed() {
      particles = Array.from({ length: count }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: rand(-0.05, 0.05),
        vy: rand(-0.04, 0.04),
        r: rand(0.4, 1.6),
        a: rand(0.15, 0.55) * intensity,
        tw: rand(0, Math.PI * 2),
      }));
    }

    function resize() {
      const rect = canvas!.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      canvas!.width = Math.floor(w * dpr);
      canvas!.height = Math.floor(h * dpr);
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0);
      seed();
    }

    const onResize = () => resize();
    resize();
    window.addEventListener('resize', onResize);

    let last = performance.now();
    const tick = (t: number) => {
      if (!running) return;
      const dt = Math.min(50, t - last);
      last = t;

      ctx.clearRect(0, 0, w, h);

      // Gentle drift + twinkle
      for (const p of particles) {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.tw += 0.003 * dt;
        if (p.x < -10) p.x = w + 10;
        if (p.x > w + 10) p.x = -10;
        if (p.y < -10) p.y = h + 10;
        if (p.y > h + 10) p.y = -10;
        const a = p.a * (0.65 + 0.35 * Math.sin(p.tw));
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(180, 220, 240, ${a})`;
        ctx.fill();
      }

      // Connecting lines (constellation feel) — restricted by distance
      const maxD = 140;
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i];
          const b = particles[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 < maxD * maxD) {
            const t = 1 - Math.sqrt(d2) / maxD;
            ctx.strokeStyle = `rgba(120, 200, 230, ${t * 0.08 * intensity})`;
            ctx.lineWidth = 0.5;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }

      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);

    return () => {
      running = false;
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', onResize);
    };
  }, [density, intensity]);

  return (
    <div className="fill pointer-events-none overflow-hidden">
      {grid && <div className="fill tactical-grid" />}
      {fog && <div className="fill depth-fog" />}
      <canvas
        ref={canvasRef}
        className="fill"
        style={{ display: 'block', opacity: 0.85 }}
      />
      {veil && <div className="fill tactical-noise" />}
      <div className="fill tactical-vignette" />
    </div>
  );
}
