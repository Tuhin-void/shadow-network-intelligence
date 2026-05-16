import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, useMotionValue, useSpring } from 'framer-motion';
import { useIntelStore } from '@/store/intel-store';

/**
 * Operational awakening — production-grade.
 *
 *  The world is already in existence. The analyst is entering. The
 *  topology doesn't draw itself — it is discovered, anchor first, then
 *  tendrils outward, then distant signals. The system "calls" three times
 *  through expanding sonar rings; then synchronizes; then the operational
 *  identity quietly resolves beneath the field.
 *
 *  Choreography:
 *    T+0.4   anchor light appears at center
 *    T+1.0   first heartbeat ring — the system pings outward
 *    T+1.0+  spokes trace outward; inner-ring nodes appear at terminus
 *    T+2.4   second heartbeat ring
 *    T+2.8+  inner-ring perimeter + cross-chords trace
 *    T+3.6+  outer halo nodes fade in as faint stars
 *    T+4.0   third heartbeat ring; outer-halo edges trace
 *    T+6.1   the arrival moment — topology field synchronizes
 *    T+6.3   climax status line
 *    T+7.1   classified identity caption resolves letter-by-letter
 *    T+8.2   analyst presence chip
 *    T+11.0  hand-off into /home (continuous, never a cut)
 */

const STATUS_LINES = [
  'investigation memory · restored',
  'relational surfaces · active',
  'structural analysis · stabilized',
  'link intelligence · online',
  'environmental context · verified',
];

const CLIMAX_LINE = 'topology field · synchronized';
const TITLE = 'SHADOW NETWORK INTELLIGENCE';

// Organic cadence — varies slightly so timing doesn't feel metronomic.
const LINE_DELAYS = [1200, 1020, 1080, 1100, 1100];

const SYNC_MOMENT_MS = 6100;
const CLIMAX_LINE_MS = 6320;
const IDENTITY_FADE_MS = 7100;
const ANALYST_FADE_MS = 8200;
const AUTO_NAV_MS = 11200;

export function BootSequence() {
  const navigate = useNavigate();
  const envMode = useIntelStore((s) => s.envMode);
  const active = useIntelStore((s) => s.active);

  const [lineIndex, setLineIndex] = useState(0);
  const [reveal, setReveal] = useState(0);
  const [synced, setSynced] = useState(false);
  const [climaxShown, setClimaxShown] = useState(false);
  const [identityShown, setIdentityShown] = useState(false);
  const [analystShown, setAnalystShown] = useState(false);

  // Cursor lantern — soft attention-aware glow that follows the mouse.
  // Spring-eased so the light trails the cursor with felt mass.
  const cursorX = useMotionValue(
    typeof window === 'undefined' ? 0 : window.innerWidth / 2
  );
  const cursorY = useMotionValue(
    typeof window === 'undefined' ? 0 : window.innerHeight / 2
  );
  const lanternX = useSpring(cursorX, { stiffness: 38, damping: 22, mass: 0.9 });
  const lanternY = useSpring(cursorY, { stiffness: 38, damping: 22, mass: 0.9 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      cursorX.set(e.clientX);
      cursorY.set(e.clientY);
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    return () => window.removeEventListener('mousemove', onMove);
  }, [cursorX, cursorY]);

  // Pre-apply the same data attributes the Worldspace will use.
  useEffect(() => {
    const root = document.documentElement;
    root.setAttribute('data-env-mode', envMode);
    root.setAttribute('data-route-mood', 'graph');
    root.style.setProperty('--world-density', '0.38');
    root.style.setProperty('--world-severity', '0');
  }, [envMode]);

  // Dev / prod session gate. In DEV the sequence always replays so iteration
  // isn't blocked. ?boot=1 forces replay in prod; ?boot=0 forces skip in dev.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const forceBoot = params.get('boot') === '1';
    const forceSkip = params.get('boot') === '0';
    if (forceSkip) {
      navigate('/home', { replace: true });
      return;
    }
    if (forceBoot || import.meta.env.DEV) {
      sessionStorage.removeItem('shadow:booted');
      return;
    }
    const alreadyBooted = sessionStorage.getItem('shadow:booted') === '1';
    if (alreadyBooted) {
      navigate('/home', { replace: true });
      return;
    }
    sessionStorage.setItem('shadow:booted', '1');
  }, [navigate]);

  // Reveal envelope — eased ramp over ~6s so emergence stays organic.
  useEffect(() => {
    let raf = 0;
    const start = performance.now();
    const tick = (t: number) => {
      const e = Math.min(1, (t - start) / 6200);
      setReveal(1 - Math.pow(1 - e, 3));
      if (e < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, []);

  useEffect(() => {
    if (lineIndex >= STATUS_LINES.length) return;
    const delay = LINE_DELAYS[lineIndex] ?? 1100;
    const t = window.setTimeout(() => setLineIndex((i) => i + 1), delay);
    return () => window.clearTimeout(t);
  }, [lineIndex]);

  useEffect(() => {
    const ts: number[] = [];
    ts.push(window.setTimeout(() => setSynced(true), SYNC_MOMENT_MS));
    ts.push(window.setTimeout(() => setClimaxShown(true), CLIMAX_LINE_MS));
    ts.push(window.setTimeout(() => setIdentityShown(true), IDENTITY_FADE_MS));
    ts.push(window.setTimeout(() => setAnalystShown(true), ANALYST_FADE_MS));
    ts.push(window.setTimeout(() => navigate('/home', { replace: true }), AUTO_NAV_MS));
    return () => ts.forEach((id) => window.clearTimeout(id));
  }, [navigate]);

  const armed = useRef(false);
  useEffect(() => {
    const armT = window.setTimeout(() => {
      armed.current = true;
    }, 1400);
    const skip = () => {
      if (!armed.current) return;
      navigate('/home', { replace: true });
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' || e.key === 'Enter' || e.key === ' ') skip();
    };
    window.addEventListener('keydown', onKey);
    window.addEventListener('click', skip);
    return () => {
      window.clearTimeout(armT);
      window.removeEventListener('keydown', onKey);
      window.removeEventListener('click', skip);
    };
  }, [navigate]);

  return (
    <div className="fill overflow-hidden bg-[var(--color-void)] text-[var(--color-text-primary)]">
      {/* Directional light — a single soft source from upper-right */}
      <div
        className="fill pointer-events-none"
        style={{
          background:
            'radial-gradient(900px 700px at 78% 14%, rgba(34,211,238,0.075), transparent 60%)',
          opacity: 0.45 + reveal * 0.55,
          transition: 'opacity 1.6s cubic-bezier(0.16, 1, 0.3, 1)',
        }}
      />
      <div
        className="fill pointer-events-none"
        style={{
          background:
            'radial-gradient(900px 700px at 22% 86%, rgba(0,0,0,0.55), transparent 60%)',
          opacity: 0.65 + reveal * 0.3,
        }}
      />

      <motion.div
        className="fill depth-fog"
        initial={{ opacity: 0 }}
        animate={{
          opacity: synced
            ? [reveal * 0.62, reveal * 0.88, reveal * 0.62]
            : reveal * 0.62,
        }}
        transition={
          synced
            ? { duration: 1.8, times: [0, 0.25, 1], ease: [0.16, 1, 0.3, 1] }
            : { duration: 0.5 }
        }
      />

      <TopologyField reveal={reveal} synced={synced} seed={active.id} />

      <SyncWave triggered={synced} />

      {/* Cursor lantern — soft attention-aware glow following the mouse.
       *  mix-blend-screen so it lifts the underlying topology rather
       *  than painting on top. Subtle, never dominant. */}
      <motion.div
        className="fixed pointer-events-none"
        style={{
          x: lanternX,
          y: lanternY,
          width: 520,
          height: 520,
          marginLeft: -260,
          marginTop: -260,
          background:
            'radial-gradient(circle, rgba(34,211,238,0.085), rgba(34,211,238,0.025) 38%, transparent 65%)',
          mixBlendMode: 'screen',
          opacity: 0.7 * reveal,
        }}
      />

      <div
        className="fill pointer-events-none worldspace-vignette"
        style={{
          background:
            'radial-gradient(ellipse 92% 72% at center, transparent 32%, rgba(0,0,0,0.62) 100%)',
          opacity: 0.55 + reveal * 0.35,
        }}
      />

      <StatusTelemetry lineIndex={lineIndex} climaxShown={climaxShown} />

      <IdentityAnchor visible={identityShown} />
      <AnalystTrace visible={analystShown} />
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* StatusTelemetry                                                            */
/* -------------------------------------------------------------------------- */

function StatusTelemetry({
  lineIndex,
  climaxShown,
}: {
  lineIndex: number;
  climaxShown: boolean;
}) {
  const visible = STATUS_LINES.slice(0, lineIndex);

  return (
    <div className="absolute left-10 bottom-10 pointer-events-none flex flex-col gap-2.5 font-mono text-[10.5px] tracking-[0.22em] lowercase">
      {visible.map((line, i) => {
        const isLast = i === visible.length - 1 && !climaxShown;
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 6, filter: 'blur(3px)' }}
            animate={{
              opacity: isLast ? 0.85 : 0.32,
              y: 0,
              filter: 'blur(0)',
            }}
            transition={{
              duration: isLast ? 1.0 : 0.85,
              ease: [0.16, 1, 0.3, 1],
            }}
            className="flex items-center gap-2.5"
          >
            <span
              className="w-[5px] h-[5px] rounded-full"
              style={{
                background: isLast
                  ? 'var(--color-ice-400)'
                  : 'rgba(100,116,139,0.55)',
                boxShadow: isLast
                  ? '0 0 12px rgba(34,211,238,0.55)'
                  : 'none',
              }}
            />
            <span
              style={{
                color: isLast
                  ? 'var(--color-text-bright)'
                  : 'var(--color-text-muted)',
              }}
            >
              {line}
            </span>
          </motion.div>
        );
      })}
      {climaxShown && (
        <motion.div
          key="climax"
          initial={{ opacity: 0, y: 6, filter: 'blur(3px)' }}
          animate={{ opacity: 1, y: 0, filter: 'blur(0)' }}
          transition={{ duration: 1.3, ease: [0.16, 1, 0.3, 1] }}
          className="flex items-center gap-2.5"
        >
          <span
            className="w-[6px] h-[6px] rounded-full"
            style={{
              background: 'var(--color-ice-300)',
              boxShadow: '0 0 18px rgba(34,211,238,0.7)',
            }}
          />
          <span className="text-[var(--color-ice-300)]">{CLIMAX_LINE}</span>
        </motion.div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* IdentityAnchor                                                             */
/*                                                                            */
/* Letter-by-letter classified-document reveal. Each letter unblurs from a    */
/* 6px gaussian — like a redacted designation being decoded into legibility.  */
/* Restrained, institutional, never a hero element.                           */
/* -------------------------------------------------------------------------- */

function IdentityAnchor({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 1.8, ease: [0.16, 1, 0.3, 1] }}
      className="absolute left-1/2 -translate-x-1/2 bottom-[19%] pointer-events-none flex flex-col items-center"
    >
      <motion.div
        initial={{ width: 0, opacity: 0 }}
        animate={{ width: 240, opacity: 0.55 }}
        transition={{ delay: 0.2, duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
        className="h-px mb-5"
        style={{
          background:
            'linear-gradient(90deg, transparent, rgba(34,211,238,0.6), transparent)',
        }}
      />
      <div
        className="text-[15px] font-extralight tracking-[0.42em] uppercase text-[var(--color-text-bright)] select-none"
        style={{ fontFamily: 'Inter, sans-serif' }}
      >
        {Array.from(TITLE).map((ch, i) => (
          <motion.span
            key={`${ch}-${i}`}
            initial={{ opacity: 0, filter: 'blur(6px)' }}
            animate={{ opacity: 1, filter: 'blur(0)' }}
            transition={{
              delay: 0.35 + i * 0.038,
              duration: 0.7,
              ease: [0.16, 1, 0.3, 1],
            }}
            style={{ display: 'inline-block', whiteSpace: 'pre' }}
          >
            {ch === ' ' ? '  ' : ch}
          </motion.span>
        ))}
      </div>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.75 }}
        transition={{ delay: 1.4, duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
        className="mt-4 font-mono text-[9.5px] tracking-[0.48em] uppercase text-[var(--color-text-secondary)]"
      >
        classified · operational · node-0xA1
      </motion.div>
      <motion.div
        initial={{ width: 0, opacity: 0 }}
        animate={{ width: 240, opacity: 0.35 }}
        transition={{ delay: 1.8, duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
        className="h-px mt-5"
        style={{
          background:
            'linear-gradient(90deg, transparent, rgba(34,211,238,0.35), transparent)',
        }}
      />
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/* AnalystTrace                                                               */
/* -------------------------------------------------------------------------- */

function AnalystTrace({ visible }: { visible: boolean }) {
  if (!visible) return null;
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 0.55 }}
      transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
      className="absolute top-9 right-12 pointer-events-none flex items-center gap-2.5 font-mono text-[9.5px] tracking-[0.32em] lowercase text-[var(--color-text-secondary)]"
    >
      <span className="relative inline-flex w-1.5 h-1.5">
        <span className="absolute inset-0 rounded-full bg-[var(--color-ice-400)] anim-pulse-ring-slow opacity-30" />
        <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-[var(--color-ice-400)]" />
      </span>
      <span>analyst · 0xA1</span>
      <span className="opacity-40">·</span>
      <span>node trust validated</span>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/* SyncWave — the arrival moment radial response                              */
/* -------------------------------------------------------------------------- */

function SyncWave({ triggered }: { triggered: boolean }) {
  if (!triggered) return null;
  return (
    <>
      <motion.div
        key="sync-wave-1"
        className="absolute top-1/2 left-1/2 rounded-full pointer-events-none"
        initial={{ width: 12, height: 12, opacity: 0.6 }}
        animate={{ width: 820, height: 820, opacity: 0 }}
        transition={{ duration: 2.6, ease: [0.16, 1, 0.3, 1] }}
        style={{
          border: '1px solid rgba(34,211,238,0.55)',
          transform: 'translate(-50%, -50%)',
          boxShadow:
            '0 0 32px rgba(34,211,238,0.35), inset 0 0 24px rgba(34,211,238,0.1)',
        }}
      />
      <motion.div
        key="sync-wave-2"
        className="absolute top-1/2 left-1/2 rounded-full pointer-events-none"
        initial={{ width: 8, height: 8, opacity: 0.38 }}
        animate={{ width: 600, height: 600, opacity: 0 }}
        transition={{
          duration: 2.2,
          delay: 0.18,
          ease: [0.16, 1, 0.3, 1],
        }}
        style={{
          border: '1px solid rgba(168,85,247,0.45)',
          transform: 'translate(-50%, -50%)',
        }}
      />
      <motion.div
        key="sync-wave-3"
        className="absolute top-1/2 left-1/2 rounded-full pointer-events-none"
        initial={{ width: 4, height: 4, opacity: 0.30 }}
        animate={{ width: 360, height: 360, opacity: 0 }}
        transition={{
          duration: 1.8,
          delay: 0.36,
          ease: [0.16, 1, 0.3, 1],
        }}
        style={{
          border: '1px solid rgba(251,191,36,0.35)',
          transform: 'translate(-50%, -50%)',
        }}
      />
    </>
  );
}

/* -------------------------------------------------------------------------- */
/* TopologyField                                                              */
/*                                                                            */
/* The constellation discovers itself, anchor outward. Spring-eased mouse     */
/* parallax gives it spatial presence. Sonar-style heartbeat rings emanate    */
/* from the anchor pre-sync — the system pinging outward. At synchronization, */
/* the whole field's brightness lifts as one.                                 */
/* -------------------------------------------------------------------------- */

type EdgeTier = 'spoke' | 'ring' | 'cross' | 'halo';
interface WhisperEdge {
  ai: number;
  bi: number;
  tier: EdgeTier;
  // Within-tier order for stable stagger
  order: number;
}

const TIER_BASE_DELAY: Record<EdgeTier, number> = {
  spoke: 1.0,
  ring: 2.8,
  cross: 3.0,
  halo: 4.0,
};
const TIER_STEP: Record<EdgeTier, number> = {
  spoke: 0.05,
  ring: 0.06,
  cross: 0.14,
  halo: 0.10,
};
const TIER_DURATION: Record<EdgeTier, number> = {
  spoke: 1.4,
  ring: 1.5,
  cross: 1.6,
  halo: 1.5,
};

function TopologyField({
  reveal,
  synced,
  seed,
}: {
  reveal: number;
  synced: boolean;
  seed: string;
}) {
  const size = 540;
  const nodes = useMemo(() => whisperNodes(seed, size), [seed]);
  const edges = useMemo(() => whisperEdges(nodes), [nodes]);

  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const sx = useSpring(mx, { stiffness: 14, damping: 24, mass: 0.9 });
  const sy = useSpring(my, { stiffness: 14, damping: 24, mass: 0.9 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      const nx = e.clientX / window.innerWidth - 0.5;
      const ny = e.clientY / window.innerHeight - 0.5;
      mx.set(-nx * 18);
      my.set(-ny * 14);
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    return () => window.removeEventListener('mousemove', onMove);
  }, [mx, my]);

  // Group nodes by emergence tier — anchor first, inner ring, then outer halo
  const innerRing = useMemo(() => nodes.slice(1, 13), [nodes]);
  const outerHalo = useMemo(() => nodes.slice(13), [nodes]);

  return (
    <motion.div
      className="absolute inset-0 flex items-center justify-center pointer-events-none"
      style={{
        opacity: reveal,
        x: sx,
        y: sy,
        filter: `blur(${(1 - reveal) * 1.6}px)`,
      }}
    >
      <motion.svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="block"
        animate={
          synced
            ? { filter: ['brightness(1)', 'brightness(1.9)', 'brightness(1.18)'] }
            : { filter: ['brightness(0.96)', 'brightness(1.02)', 'brightness(0.96)'] }
        }
        transition={
          synced
            ? { duration: 1.9, times: [0, 0.22, 1], ease: [0.16, 1, 0.3, 1] }
            : { duration: 8.4, repeat: Infinity, ease: 'easeInOut' }
        }
      >
        <defs>
          <radialGradient id="topology-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(34,211,238,0.10)" />
            <stop offset="55%" stopColor="rgba(34,211,238,0.025)" />
            <stop offset="100%" stopColor="rgba(34,211,238,0)" />
          </radialGradient>
          <radialGradient id="topology-glow-rose" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="rgba(244,63,94,0.18)" />
            <stop offset="40%" stopColor="rgba(244,63,94,0.04)" />
            <stop offset="100%" stopColor="rgba(244,63,94,0)" />
          </radialGradient>
        </defs>

        {/* Atmospheric halos — operational core hidden in fog */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.42}
          fill="url(#topology-glow)"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={size * 0.18}
          fill="url(#topology-glow-rose)"
        />

        {/* Sonar heartbeat rings — the anchor pings outward three times
         *  before the field synchronizes. Each ring expands and fades. The
         *  effect is felt: the system is calling. */}
        {!synced &&
          [0, 1, 2].map((i) => (
            <motion.circle
              key={`ping-${i}`}
              cx={size / 2}
              cy={size / 2}
              fill="none"
              stroke={
                i === 0
                  ? 'rgba(34,211,238,0.6)'
                  : i === 1
                  ? 'rgba(34,211,238,0.5)'
                  : 'rgba(34,211,238,0.4)'
              }
              strokeWidth={0.8}
              initial={{ r: 4, opacity: 0 }}
              animate={{ r: 124, opacity: [0, 0.6, 0] }}
              transition={{
                delay: 1.0 + i * 1.4,
                duration: 2.0,
                times: [0, 0.22, 1],
                ease: [0.16, 1, 0.3, 1],
              }}
            />
          ))}

        {/* Anchor — appears first. Has a faint surrounding glow ring that
         *  pulses gently in addition to the heartbeat pings. The system's
         *  point of awareness. */}
        <motion.circle
          cx={size / 2}
          cy={size / 2}
          r={3.4}
          fill="rgba(244,63,94,0.7)"
          initial={{ opacity: 0, scale: 0.6 }}
          animate={{
            opacity: synced ? 0.95 : 0.78,
            scale: 1,
          }}
          transition={{
            duration: 1.2,
            delay: 0.4,
            ease: [0.16, 1, 0.3, 1],
          }}
          style={{
            transformOrigin: `${size / 2}px ${size / 2}px`,
            filter: 'drop-shadow(0 0 9px rgba(244,63,94,0.65))',
          }}
        />

        {/* Edges by tier — spokes first, then ring perimeter, then chords,
         *  then halo connectors. Each edge traces from start to end with
         *  pathLength so the line feels drawn outward from the anchor. */}
        {edges.map((edge, i) => {
          const A = nodes[edge.ai];
          const B = nodes[edge.bi];
          const delay =
            TIER_BASE_DELAY[edge.tier] + edge.order * TIER_STEP[edge.tier];
          const duration = TIER_DURATION[edge.tier];
          const baseOpacity =
            edge.tier === 'halo' ? 0.28 : edge.tier === 'cross' ? 0.38 : 0.42;
          return (
            <motion.line
              key={`e-${i}`}
              x1={A.x}
              y1={A.y}
              x2={B.x}
              y2={B.y}
              stroke="rgba(34,211,238,0.42)"
              strokeWidth={edge.tier === 'cross' ? 0.7 : 0.55}
              initial={{ pathLength: 0, opacity: 0 }}
              animate={{ pathLength: 1, opacity: baseOpacity }}
              transition={{
                duration,
                delay,
                ease: [0.16, 1, 0.3, 1],
              }}
            />
          );
        })}

        {/* Inner-ring nodes — appear at the moment their spoke is nearly
         *  complete. Each is the terminus of a tendril reaching outward. */}
        {innerRing.map((n, i) => (
          <motion.circle
            key={`inner-${i}`}
            cx={n.x}
            cy={n.y}
            r={n.r}
            fill="rgba(34,211,238,0.48)"
            initial={{ opacity: 0, scale: 0.55 }}
            animate={{ opacity: 0.62, scale: 1 }}
            transition={{
              duration: 0.9,
              delay: 2.0 + i * 0.05,
              ease: [0.16, 1, 0.3, 1],
            }}
            style={{
              transformOrigin: `${n.x}px ${n.y}px`,
              filter: 'drop-shadow(0 0 4px rgba(34,211,238,0.38))',
            }}
          />
        ))}

        {/* Outer halo nodes — faint distant signals, late appearance */}
        {outerHalo.map((n, i) => (
          <motion.circle
            key={`outer-${i}`}
            cx={n.x}
            cy={n.y}
            r={n.r}
            fill="rgba(34,211,238,0.42)"
            initial={{ opacity: 0, scale: 0.7 }}
            animate={{ opacity: 0.38, scale: 1 }}
            transition={{
              duration: 1.4,
              delay: 3.6 + i * 0.12,
              ease: [0.16, 1, 0.3, 1],
            }}
            style={{
              transformOrigin: `${n.x}px ${n.y}px`,
              filter: 'drop-shadow(0 0 2px rgba(34,211,238,0.28))',
            }}
          />
        ))}

        {/* Center coherence marker — appears at synchronization. A tiny
         *  bright pip at the heart of the field, lit from within. */}
        {synced && (
          <>
            <motion.circle
              cx={size / 2}
              cy={size / 2}
              r={2.6}
              fill="rgba(34,211,238,1)"
              initial={{ opacity: 0, scale: 0.4 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
              style={{ filter: 'drop-shadow(0 0 14px rgba(34,211,238,0.95))' }}
            />
            <motion.circle
              cx={size / 2}
              cy={size / 2}
              r={12}
              fill="none"
              stroke="rgba(34,211,238,0.9)"
              strokeWidth={0.6}
              initial={{ opacity: 0.85, scale: 0.4 }}
              animate={{ opacity: 0, scale: 2.4 }}
              transition={{
                duration: 1.1,
                ease: [0.16, 1, 0.3, 1],
                delay: 0.1,
              }}
              style={{ transformOrigin: `${size / 2}px ${size / 2}px` }}
            />
          </>
        )}
      </motion.svg>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */
/* Deterministic constellation                                                */
/* -------------------------------------------------------------------------- */

interface WhisperNode {
  x: number;
  y: number;
  r: number;
}

function whisperNodes(seed: string, size: number): WhisperNode[] {
  let h = 2166136261;
  for (let i = 0; i < seed.length; i += 1) {
    h ^= seed.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const rand = () => {
    h = Math.imul(h ^ (h >>> 15), 2246822507);
    h = Math.imul(h ^ (h >>> 13), 3266489909);
    return ((h ^= h >>> 16) >>> 0) / 4294967295;
  };
  const cx = size / 2;
  const cy = size / 2;
  const nodes: WhisperNode[] = [{ x: cx, y: cy, r: 3.4 }];
  const ringCount = 12;
  for (let i = 0; i < ringCount; i += 1) {
    const ang = (i / ringCount) * Math.PI * 2 + (rand() - 0.5) * 0.55;
    const rad = 96 + rand() * 112;
    nodes.push({
      x: cx + Math.cos(ang) * rad,
      y: cy + Math.sin(ang) * rad,
      r: 1.7 + rand() * 1.4,
    });
  }
  for (let i = 0; i < 6; i += 1) {
    const ang = rand() * Math.PI * 2;
    const rad = 215 + rand() * 60;
    nodes.push({
      x: cx + Math.cos(ang) * rad,
      y: cy + Math.sin(ang) * rad,
      r: 1.0 + rand() * 0.7,
    });
  }
  return nodes;
}

function whisperEdges(nodes: WhisperNode[]): WhisperEdge[] {
  const edges: WhisperEdge[] = [];
  // Center → inner ring spokes
  for (let i = 1; i <= 12; i += 1) {
    edges.push({ ai: 0, bi: i, tier: 'spoke', order: i - 1 });
  }
  // Inner-ring perimeter (with one intentional gap for asymmetry)
  let ringOrder = 0;
  for (let i = 1; i <= 12; i += 1) {
    if (i === 6) continue;
    const j = (i % 12) + 1;
    edges.push({ ai: i, bi: j, tier: 'ring', order: ringOrder });
    ringOrder += 1;
  }
  // Long cross-chords — sparse, structural
  edges.push({ ai: 1, bi: 7, tier: 'cross', order: 0 });
  edges.push({ ai: 3, bi: 9, tier: 'cross', order: 1 });
  edges.push({ ai: 5, bi: 11, tier: 'cross', order: 2 });
  // Halo connectors — outer dots reach inward at irregular points
  let haloOrder = 0;
  for (let i = 13; i < nodes.length; i += 1) {
    const innerIdx = 1 + ((i * 5) % 12);
    edges.push({ ai: i, bi: innerIdx, tier: 'halo', order: haloOrder });
    haloOrder += 1;
  }
  return edges;
}
