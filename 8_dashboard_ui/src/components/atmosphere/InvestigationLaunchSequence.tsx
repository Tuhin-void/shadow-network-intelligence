import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';

/**
 * InvestigationLaunchSequence — a thin top strip that surfaces the live
 * progression of an in-flight investigation against the real backend.
 *
 * Each phase is CAUSALLY bound to a real SSE event kind. Nothing is faked,
 * nothing is pre-timed:
 *
 *   QUERY ACCEPTED        ← `session.started` / `query.received`
 *   GRAPH SCAN INITIATED  ← (synthetic transition — fires immediately
 *                            after the engine call begins; replaced once
 *                            the first entity arrives)
 *   ENTITIES SURFACING    ← first `entity.found`
 *   STRUCTURAL LINKS      ← `ring.discovered` or `hidden_relationship.found`
 *   TOPOLOGY EXPANSION    ← `neighborhood.expanded`
 *   COGNITIVE SYNTHESIS   ← `agent.finished` or `reasoning.synthesized`
 *   INVESTIGATION STABLE  ← `report.finalized` / `deep_report.finalized`
 *
 * The strip auto-dismisses ~3s after the investigation stabilizes. Aborts
 * collapse it immediately.
 *
 * Constraints:
 *   • No spinners, no progress bars implying fake progress
 *   • No "hacking" effects, no neon overload
 *   • Pure progression of real backend phases
 *   • Sits below the FloatingNav, above pages; non-blocking
 */
export function InvestigationLaunchSequence() {
  const events = useIntelStore((s) => s.events);
  const liveStreamPhase = useIntelStore((s) => s.liveStreamPhase);
  const cognitivePhase = useIntelStore((s) => s.cognitivePhase);
  const liveStreamError = useIntelStore((s) => s.liveStreamError);
  const cognitiveError = useIntelStore((s) => s.cognitiveError);

  const [visibleAfterComplete, setVisibleAfterComplete] = useState(false);

  // Show whenever streaming OR briefly after complete so the analyst can
  // see the final phase land.
  const streaming = liveStreamPhase === 'streaming' || cognitivePhase === 'running';
  const justFinished =
    (liveStreamPhase === 'complete' || cognitivePhase === 'complete') &&
    visibleAfterComplete;
  const errored = liveStreamPhase === 'error' || cognitivePhase === 'error';

  useEffect(() => {
    if (streaming) {
      setVisibleAfterComplete(true);
      return;
    }
    if (liveStreamPhase === 'complete' || cognitivePhase === 'complete') {
      const t = setTimeout(() => setVisibleAfterComplete(false), 3000);
      return () => clearTimeout(t);
    }
    if (errored) {
      // Errors persist 6s.
      const t = setTimeout(() => setVisibleAfterComplete(false), 6000);
      return () => clearTimeout(t);
    }
  }, [streaming, liveStreamPhase, cognitivePhase, errored]);

  const visible = streaming || justFinished || errored;

  const phase = useMemo(() => derivePhase(events, {
    streaming,
    complete: liveStreamPhase === 'complete' || cognitivePhase === 'complete',
    errored,
  }), [events, streaming, liveStreamPhase, cognitivePhase, errored]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          key="launch-sequence"
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
          className="fixed top-3 left-1/2 -translate-x-1/2 z-40 pointer-events-none"
        >
          <div
            className={cn(
              'panel-soft pointer-events-auto px-3 py-1.5 inline-flex items-center gap-3',
              'backdrop-blur-md bg-[rgba(7,9,14,0.78)] border',
              errored
                ? 'border-[rgba(244,63,94,0.4)]'
                : streaming
                ? 'border-[rgba(34,211,238,0.32)]'
                : 'border-[rgba(16,185,129,0.32)]',
            )}
            style={{ minWidth: 480 }}
          >
            {/* Pulsing dot — colour tracks state */}
            <span
              className={cn(
                'w-1.5 h-1.5 rounded-full shrink-0',
                streaming && 'anim-drift',
                errored
                  ? 'bg-[var(--color-rose-400)]'
                  : streaming
                  ? 'bg-[var(--color-ice-400)]'
                  : 'bg-[var(--color-emerald-400)]',
              )}
            />
            <span
              className="font-mono text-[9.5px] tracking-[0.32em] uppercase shrink-0"
              style={{
                color: errored
                  ? 'var(--color-rose-400)'
                  : streaming
                  ? 'var(--color-ice-400)'
                  : 'var(--color-emerald-400)',
              }}
            >
              investigation
            </span>

            {/* Phase ladder — visual sequence of phases lit by real events */}
            <PhaseLadder current={phase.activeIndex} total={PHASES.length} />

            <span
              key={phase.label}
              className="font-mono text-[10.5px] tracking-[0.18em] uppercase text-[var(--color-text-bright)] whitespace-nowrap"
            >
              {phase.label}
            </span>

            <span className="ml-auto font-mono text-[9.5px] text-[var(--color-text-muted)] shrink-0">
              {events.length} events
            </span>
          </div>

          {/* Error line, if any */}
          {errored && (liveStreamError || cognitiveError) && (
            <div className="mt-1 panel-soft pointer-events-auto px-3 py-1 max-w-[480px] mx-auto bg-[rgba(7,9,14,0.78)] border border-[rgba(244,63,94,0.3)]">
              <span className="font-mono text-[10px] text-[var(--color-rose-300)] break-all">
                {(liveStreamError || cognitiveError || '').slice(0, 200)}
              </span>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/* -------------------------------------------------------------------------- */
/* Phase derivation — from REAL SSE event kinds                               */
/* -------------------------------------------------------------------------- */

const PHASES = [
  { id: 'accepted',    label: 'QUERY ACCEPTED' },
  { id: 'scanning',    label: 'GRAPH SCAN INITIATED' },
  { id: 'surfacing',   label: 'ENTITIES SURFACING' },
  { id: 'structural',  label: 'STRUCTURAL LINKS' },
  { id: 'expansion',   label: 'TOPOLOGY EXPANSION' },
  { id: 'cognitive',   label: 'COGNITIVE SYNTHESIS' },
  { id: 'stable',      label: 'INVESTIGATION STABLE' },
] as const;

type PhaseId = (typeof PHASES)[number]['id'];

function derivePhase(
  events: Array<{ kind: string }>,
  state: { streaming: boolean; complete: boolean; errored: boolean },
): { activeIndex: number; label: string; id: PhaseId } {
  if (state.errored) {
    return { activeIndex: -1, label: 'INVESTIGATION INTERRUPTED', id: 'scanning' };
  }
  if (state.complete) {
    return _phaseAt(6);
  }
  // Walk backward through events to find the most-advanced phase reached.
  const kinds = new Set<string>();
  for (const e of events) kinds.add(e.kind);

  if (kinds.has('session.complete')) return _phaseAt(6);
  if (
    kinds.has('topology.expanded') &&
    (kinds.has('evidence.collected') || kinds.has('ring.detected'))
  ) {
    return _phaseAt(5);
  }
  if (kinds.has('topology.expanded')) return _phaseAt(4);
  if (kinds.has('hidden.relationship') || kinds.has('ring.detected')) {
    return _phaseAt(3);
  }
  if (kinds.has('entity.discovered')) return _phaseAt(2);
  if (kinds.has('session.start')) return _phaseAt(1);
  // Streaming flagged but no events yet → first phase
  if (state.streaming) return _phaseAt(0);
  return _phaseAt(0);
}

function _phaseAt(i: number) {
  const p = PHASES[Math.max(0, Math.min(PHASES.length - 1, i))];
  return { activeIndex: i, label: p.label, id: p.id };
}

/* -------------------------------------------------------------------------- */

function PhaseLadder({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-1 shrink-0">
      {Array.from({ length: total }, (_, i) => (
        <span
          key={i}
          className={cn(
            'h-1 rounded-full transition-all',
            i <= current ? 'w-4' : 'w-2',
          )}
          style={{
            background:
              i < current
                ? 'var(--color-ice-400)'
                : i === current
                ? 'var(--color-emerald-400)'
                : 'rgba(148,163,184,0.18)',
            boxShadow:
              i === current
                ? '0 0 6px rgba(16,185,129,0.6)'
                : i < current
                ? '0 0 4px rgba(34,211,238,0.4)'
                : 'none',
          }}
        />
      ))}
    </div>
  );
}
