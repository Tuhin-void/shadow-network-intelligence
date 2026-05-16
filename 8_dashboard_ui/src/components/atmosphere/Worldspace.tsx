import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { AnimatePresence, motion, useMotionValue, useSpring } from 'framer-motion';
import { useIntelStore } from '@/store/intel-store';

/**
 * Worldspace — the operational environment layer.
 *
 *  • Persistent across route changes (mounted by WorkspaceShell, never unmounts
 *    until the analyst leaves the operational shell). Route changes therefore
 *    feel like the camera shifting *within* the same space, not a page reload.
 *
 *  • Adaptive atmosphere — composition reacts to:
 *      – envMode  (ambient / calm / cinematic) via global data-env-mode
 *      – route family (graph / analytical / reading) via data-route-mood
 *      – focusModeOn (chrome dissolves + world dims) via data-focus
 *      – selected entity tier (critical/high/medium/low) tints the ambient
 *  • Spatial parallax — fog drifts opposite the cursor, very subtle, giving
 *    the screen a felt z-depth without obvious 3D.
 *  • Scene-flash — every focus-mode toggle emits a soft full-scene wash so
 *    the transition is felt environmentally, not just at the toggle.
 *
 * The layer is intentionally NOT a component children compose with. It's
 * a passive worldspace — pages render *inside* its atmosphere.
 */
export function Worldspace() {
  const focusModeOn = useIntelStore((s) => s.focusModeOn);
  const focusTransitionId = useIntelStore((s) => s.focusTransitionId);
  const selectedId = useIntelStore((s) => s.selectedEntityId);
  const active = useIntelStore((s) => s.active);
  const envMode = useIntelStore((s) => s.envMode);
  const narration = useIntelStore((s) => s.narration);
  const ringCount = useIntelStore((s) => s.surfacedRings.size);
  const pathCount = useIntelStore((s) => s.surfacedPaths.size);
  const discoveredCount = useIntelStore((s) => s.discoveredEntities.size);
  const location = useLocation();

  // Risk-reactive ambient tint — the selected entity's risk tier breathes
  // a faint undertone into the world. Critical = rose. High = amber.
  const tier = useMemo(() => {
    if (!selectedId) return null;
    return active.graph.entities.find((e) => e.id === selectedId)?.tier ?? null;
  }, [active, selectedId]);

  const tierTint = useMemo(() => {
    switch (tier) {
      case 'critical':
        return 'rgba(244,63,94,0.055)';
      case 'high':
        return 'rgba(251,191,36,0.045)';
      case 'medium':
        return 'rgba(34,211,238,0.035)';
      default:
        return 'rgba(34,211,238,0.020)';
    }
  }, [tier]);

  // Mousemove parallax — the fog drifts opposite the cursor. Spring-eased so
  // it feels physical, not robotic. Disabled in calm mode for restraint.
  const mx = useMotionValue(0);
  const my = useMotionValue(0);
  const sx = useSpring(mx, { stiffness: 22, damping: 26, mass: 0.8 });
  const sy = useSpring(my, { stiffness: 22, damping: 26, mass: 0.8 });

  useEffect(() => {
    if (envMode === 'calm') {
      mx.set(0);
      my.set(0);
      return;
    }
    const strength = envMode === 'cinematic' ? 14 : 9;
    const onMove = (e: MouseEvent) => {
      const nx = e.clientX / window.innerWidth - 0.5;
      const ny = e.clientY / window.innerHeight - 0.5;
      mx.set(-nx * strength);
      my.set(-ny * strength);
    };
    window.addEventListener('mousemove', onMove, { passive: true });
    return () => window.removeEventListener('mousemove', onMove);
  }, [envMode, mx, my]);

  // Apply data attributes so CSS can tune the environment without rendering
  // an inflated component tree.
  const [routeChangeId, setRouteChangeId] = useState(0);
  const firstRoute = useRef(true);
  useEffect(() => {
    const root = document.documentElement;
    const mood = routeMood(location.pathname);
    root.setAttribute('data-route-mood', mood);
    if (firstRoute.current) {
      firstRoute.current = false;
    } else {
      setRouteChangeId((n) => n + 1);
    }
  }, [location.pathname]);

  useEffect(() => {
    document.documentElement.setAttribute('data-focus', focusModeOn ? 'on' : 'off');
  }, [focusModeOn]);

  useEffect(() => {
    if (tier) document.documentElement.setAttribute('data-tier', tier);
    else document.documentElement.removeAttribute('data-tier');
  }, [tier]);

  // Density + severity → CSS vars on root. Vignette CSS reads these to
  // deepen the worldspace as topology gets denser or as a critical tier
  // anchor is selected. Tiny envelope so the world feels reactive but
  // never becomes oppressive.
  useEffect(() => {
    const total = active.graph.entities.length || 1;
    const density = Math.min(1, discoveredCount / total);
    document.documentElement.style.setProperty(
      '--world-density',
      density.toFixed(3)
    );
  }, [active, discoveredCount]);

  useEffect(() => {
    const severity =
      tier === 'critical' ? 1 : tier === 'high' ? 0.55 : tier === 'medium' ? 0.2 : 0;
    document.documentElement.style.setProperty(
      '--world-severity',
      severity.toFixed(2)
    );
  }, [tier]);

  // Narration flash — when a query lands a new narration line, briefly
  // intensify the ambient so the world feels reactive.
  const lastNarration = useRef<string | null>(null);
  const [narrationFlashId, setNarrationFlashId] = useState(0);
  useEffect(() => {
    if (narration && narration !== lastNarration.current) {
      lastNarration.current = narration;
      setNarrationFlashId((n) => n + 1);
    }
  }, [narration]);

  // Graph-reactive flashes — when a ring surfaces or a hidden path lands,
  // the world breathes in the corresponding accent. Color-coded so the
  // analyst feels what just changed without looking at a notification.
  const lastRingCount = useRef(ringCount);
  const lastPathCount = useRef(pathCount);
  const [ringFlashId, setRingFlashId] = useState(0);
  const [pathFlashId, setPathFlashId] = useState(0);
  useEffect(() => {
    if (ringCount > lastRingCount.current) setRingFlashId((n) => n + 1);
    lastRingCount.current = ringCount;
  }, [ringCount]);
  useEffect(() => {
    if (pathCount > lastPathCount.current) setPathFlashId((n) => n + 1);
    lastPathCount.current = pathCount;
  }, [pathCount]);

  return (
    <div
      className="fixed inset-0 z-0 pointer-events-none overflow-hidden"
      aria-hidden="true"
    >
      {/* Parallaxed deep fog — reads as the room's atmosphere itself */}
      <motion.div
        className="absolute -inset-[60px] depth-fog"
        style={{ x: sx, y: sy }}
      />

      {/* Risk-reactive ambient tint — slow crossfade between tier hues */}
      <motion.div
        key={tier ?? 'none'}
        className="absolute inset-0"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1.8, ease: [0.16, 1, 0.3, 1] }}
        style={{
          background: `radial-gradient(70% 55% at 50% 55%, ${tierTint}, transparent 75%)`,
        }}
      />

      {/* Focus-mode darkening veil — the world recedes around the graph */}
      <motion.div
        className="absolute inset-0"
        initial={false}
        animate={{ opacity: focusModeOn ? 1 : 0 }}
        transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
        style={{
          background:
            'radial-gradient(ellipse 95% 75% at center, transparent 35%, rgba(0,0,0,0.55) 100%)',
        }}
      />

      {/* Scene flash — bumps on every focus toggle, washes the world */}
      <AnimatePresence>
        {focusTransitionId > 0 && (
          <motion.div
            key={`focus-flash-${focusTransitionId}`}
            initial={{ opacity: 0.18, scale: 1 }}
            animate={{ opacity: 0, scale: 1.04 }}
            transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0"
            style={{
              background:
                'radial-gradient(60% 45% at 50% 50%, rgba(168,85,247,0.22), transparent 75%)',
            }}
          />
        )}
      </AnimatePresence>

      {/* Route-change wash — a felt scene shift without a hard cut */}
      <AnimatePresence>
        {routeChangeId > 0 && (
          <motion.div
            key={`route-${routeChangeId}`}
            initial={{ opacity: 0.10 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0"
            style={{
              background:
                'linear-gradient(180deg, rgba(7,9,14,0.45) 0%, rgba(7,9,14,0) 60%)',
            }}
          />
        )}
      </AnimatePresence>

      {/* Narration micro-flash — softer, ice-toned, reactive to query landings */}
      <AnimatePresence>
        {narrationFlashId > 0 && (
          <motion.div
            key={`narr-${narrationFlashId}`}
            initial={{ opacity: 0.12 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 1.2, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0"
            style={{
              background:
                'radial-gradient(50% 40% at 50% 50%, rgba(34,211,238,0.18), transparent 75%)',
            }}
          />
        )}
      </AnimatePresence>

      {/* Ring-detected flash — rose breath sweeps in from edges */}
      <AnimatePresence>
        {ringFlashId > 0 && (
          <motion.div
            key={`ring-${ringFlashId}`}
            initial={{ opacity: 0.16 }}
            animate={{ opacity: 0 }}
            transition={{ duration: 1.4, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0"
            style={{
              background:
                'radial-gradient(ellipse 100% 80% at 50% 50%, transparent 50%, rgba(244,63,94,0.22) 100%)',
            }}
          />
        )}
      </AnimatePresence>

      {/* Hidden-path flash — violet, slower bloom from center */}
      <AnimatePresence>
        {pathFlashId > 0 && (
          <motion.div
            key={`path-${pathFlashId}`}
            initial={{ opacity: 0.14, scale: 0.95 }}
            animate={{ opacity: 0, scale: 1.04 }}
            transition={{ duration: 1.6, ease: [0.16, 1, 0.3, 1] }}
            className="absolute inset-0"
            style={{
              background:
                'radial-gradient(55% 45% at 50% 50%, rgba(168,85,247,0.20), transparent 80%)',
            }}
          />
        )}
      </AnimatePresence>

      {/* Final vignette — pulls the eye toward center always */}
      <div
        className="absolute inset-0 worldspace-vignette"
        style={{
          background:
            'radial-gradient(ellipse 85% 70% at center, transparent 40%, rgba(0,0,0,0.45) 100%)',
        }}
      />
    </div>
  );
}

function routeMood(pathname: string): 'graph' | 'analytical' | 'reading' | 'theater' {
  if (pathname === '/autopilot') return 'theater';
  if (
    pathname === '/investigate' ||
    pathname.startsWith('/rings') ||
    pathname.startsWith('/replay') ||
    pathname.startsWith('/entity')
  ) {
    return 'graph';
  }
  if (
    pathname.startsWith('/benchmark') ||
    pathname.startsWith('/simulate') ||
    pathname.startsWith('/sources')
  ) {
    return 'analytical';
  }
  return 'reading';
}
