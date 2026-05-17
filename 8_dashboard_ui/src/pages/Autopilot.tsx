import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowLeft,
  CircleDot,
  Eye,
  GitBranch,
  Hand,
  Pause,
  Play,
  ShieldAlert,
  Spline,
  Sparkles,
  Zap,
} from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { cn, entityGlyph, formatTime, tierColor } from '@/lib/utils';
import type { StreamEvent, StreamEventKind } from '@/types/intel';
import { Synthesis } from '@/components/autopilot/Synthesis';

const NARR_VERB: Record<StreamEventKind, string> = {
  'session.start': 'igniting',
  'topology.expanded': 'expanding',
  'entity.discovered': 'surfacing',
  'edge.traversed': 'traversing',
  'ring.detected': 'ring locked',
  'hidden.relationship': 'hidden tie',
  'path.discovered': 'path opened',
  'suspicion.escalated': 'suspicion rising',
  'evidence.collected': 'evidence pinned',
  'signal.surfaced': 'signal',
  'report.section': 'briefing',
  'session.complete': 'synthesis',
};

const NARR_TONE: Record<StreamEventKind, string> = {
  'session.start': 'text-[var(--color-text-secondary)]',
  'topology.expanded': 'text-[var(--color-ice-400)]',
  'entity.discovered': 'text-[var(--color-ice-400)]',
  'edge.traversed': 'text-[var(--color-text-secondary)]',
  'ring.detected': 'text-[var(--color-rose-400)]',
  'hidden.relationship': 'text-[var(--color-violet-400)]',
  'path.discovered': 'text-[var(--color-amber-400)]',
  'suspicion.escalated': 'text-[var(--color-rose-400)]',
  'evidence.collected': 'text-[var(--color-emerald-400)]',
  'signal.surfaced': 'text-[var(--color-ice-400)]',
  'report.section': 'text-[var(--color-text-secondary)]',
  'session.complete': 'text-[var(--color-emerald-400)]',
};

export function Autopilot() {
  const navigate = useNavigate();
  const {
    active,
    events,
    streamingPhase,
    progress,
    speed,
    startStream,
    stopStream,
    resetStream,
    setSpeed,
    setRunMode,
  } = useIntelStore();

  // Engage on mount — but only if not already mid-investigation, so navigating
  // away and back doesn't reset the analyst's run.
  useEffect(() => {
    setRunMode('auto');
    if (streamingPhase === 'idle' && events.length === 0) {
      const t = setTimeout(() => startStream(), 600);
      return () => clearTimeout(t);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const last = events[events.length - 1];
  const showSynthesis = streamingPhase === 'complete';
  const focusModeOn = useIntelStore((s) => s.focusModeOn);

  return (
    <div className="fill bg-[var(--color-void)] overflow-hidden text-[var(--color-text-primary)]">
      {/* GRAPH = the whole canvas. No central widgets blocking it. */}
      <GraphCanvas cinematic />

      {/* ─── TOP RAIL — fades in focus mode ───────────────────────── */}
      <div
        className="absolute top-0 left-0 right-0 h-12 flex items-center justify-between px-5 z-30 border-b border-[var(--color-line-soft)] bg-[rgba(7,9,14,0.65)] backdrop-blur-md transition-opacity duration-300"
        style={{ opacity: focusModeOn ? 0 : 1, pointerEvents: focusModeOn ? 'none' : 'auto' }}
      >
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate('/home')}
            className="flex items-center gap-2 font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)] transition-colors"
          >
            <ArrowLeft className="w-3 h-3" />
            mode
          </button>
          <span className="w-px h-4 bg-[var(--color-line)]" />
          <div className="flex items-center gap-2 px-2 h-7 rounded-sm border border-[rgba(34,211,238,0.32)] bg-[rgba(34,211,238,0.05)]">
            <span className="relative inline-flex w-1.5 h-1.5">
              <span className="absolute inset-0 rounded-full bg-[var(--color-ice-400)] anim-pulse-ring" />
              <span className="relative inline-flex w-1.5 h-1.5 rounded-full bg-[var(--color-ice-400)]" />
            </span>
            <Eye className="w-3 h-3 text-[var(--color-ice-400)]" />
            <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-ice-400)]">
              autopilot
            </span>
          </div>
          <span className="chip text-[8.5px] inline-flex items-center gap-1 border-[rgba(245,158,11,0.28)] text-[var(--color-amber-400)]">
            <span className="w-1 h-1 rounded-full bg-[var(--color-amber-400)]" />
            synthetic walkthrough
          </span>
        </div>

        {/* Centered headline so user always knows WHAT case + WHAT the conclusion is */}
        <div className="absolute left-1/2 -translate-x-1/2 max-w-[44%] truncate text-center">
          <div className="font-mono text-[9px] tracking-[0.4em] uppercase text-[var(--color-text-muted)]">
            investigation 0x{active.id.slice(0, 4).toUpperCase()} · {active.label}
          </div>
          <div className="text-[12.5px] text-[var(--color-text-bright)] font-medium leading-tight truncate">
            {active.report.narrative.headline}
          </div>
        </div>

        <div className="flex items-center gap-3">
          <SpeedSelector speed={speed} setSpeed={setSpeed} />
          {streamingPhase === 'streaming' ? (
            <button
              onClick={stopStream}
              className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.22em] uppercase rounded-sm border border-[rgba(244,63,94,0.4)] bg-[rgba(244,63,94,0.05)] text-[var(--color-rose-400)] hover:bg-[rgba(244,63,94,0.1)]"
            >
              <Pause className="w-3 h-3" />
              pause
            </button>
          ) : (
            <button
              onClick={() => {
                resetStream();
                setTimeout(() => startStream(), 80);
              }}
              className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.22em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.05)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
            >
              <Play className="w-3 h-3" />
              {streamingPhase === 'complete' ? 'replay' : 'launch'}
            </button>
          )}
        </div>
      </div>

      {/* Side rails + bottom bar fade away in graph focus mode. */}
      {!focusModeOn && (
        <>
          {/* ─── LEFT RAIL — KEY SUSPECTS EMERGING ──────────────────── */}
          <SuspectsRail />

          {/* ─── RIGHT RAIL — FINDINGS AS THEY SURFACE ──────────────── */}
          <FindingsRail />

          {/* ─── BOTTOM BAR — action + narration + progress in one row ─ */}
          <BottomBar
            event={last}
            progress={progress}
            phase={streamingPhase}
            onTakeManual={() => navigate('/investigate')}
          />
        </>
      )}

      {/* Synthesis climax */}
      <AnimatePresence>{showSynthesis && <Synthesis />}</AnimatePresence>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* LEFT RAIL — emerging suspects                                              */
/* -------------------------------------------------------------------------- */

function SuspectsRail() {
  const active = useIntelStore((s) => s.active);
  const discoveredEntities = useIntelStore((s) => s.discoveredEntities);
  const selectedEntityId = useIntelStore((s) => s.selectedEntityId);
  const selectEntity = useIntelStore((s) => s.selectEntity);

  // Surface the highest-risk people / shell companies / wallets that have emerged
  const emerging = active.graph.entities
    .filter(
      (e) =>
        discoveredEntities.has(e.id) &&
        ['person', 'shell_company', 'wallet', 'company'].includes(e.kind) &&
        e.risk >= 50
    )
    .sort((a, b) => b.risk - a.risk)
    .slice(0, 6);

  return (
    <div className="absolute top-16 left-3 z-20 w-[260px] pointer-events-none">
      <div className="pointer-events-auto surface-floating overflow-hidden">
        <div className="px-3 h-7 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
          <ShieldAlert className="w-3 h-3 text-[var(--color-rose-400)]" />
          <span className="heading-tactical">Emerging suspects</span>
          <span className="ml-auto font-mono text-[9px] tracking-[0.2em] uppercase text-[var(--color-text-muted)]">
            {emerging.length} surfaced
          </span>
        </div>
        <div className="p-1.5 space-y-1 max-h-[340px] overflow-y-auto scroll-tactical">
          {emerging.length === 0 ? (
            <div className="px-2 py-3 font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--color-text-muted)]">
              awaiting topology expansion…
            </div>
          ) : (
            emerging.map((e) => {
              const isSel = e.id === selectedEntityId;
              const flagsToShow = (e.flags ?? []).slice(0, 2);
              return (
                <motion.button
                  key={e.id}
                  layout
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
                  onClick={() => selectEntity(e.id)}
                  className={cn(
                    'w-full text-left rounded-sm px-2 py-1.5 flex items-center gap-2',
                    'border',
                    isSel
                      ? 'border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.05)]'
                      : 'border-transparent hover:bg-[rgba(148,163,184,0.04)]'
                  )}
                >
                  <span
                    className="inline-flex items-center justify-center w-6 h-6 rounded-sm border shrink-0 text-[11px]"
                    style={{
                      borderColor: tierColor(e.tier),
                      color: tierColor(e.tier),
                      background: `${tierColor(e.tier)}10`,
                    }}
                  >
                    {entityGlyph(e.kind)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[12px] text-[var(--color-text-bright)] truncate">
                      {e.label}
                    </div>
                    <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                      {e.kind.replace('_', ' ')}
                      {flagsToShow.length > 0 && (
                        <span className="text-[var(--color-rose-400)]">
                          {' · '}
                          {flagsToShow.join(' · ')}
                        </span>
                      )}
                    </div>
                  </div>
                  <span
                    className="font-mono text-[10.5px] font-medium"
                    style={{ color: tierColor(e.tier) }}
                  >
                    {e.risk}
                  </span>
                </motion.button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* RIGHT RAIL — findings as they surface, each with WHY                       */
/* -------------------------------------------------------------------------- */

interface Finding {
  id: string;
  kind: 'ring' | 'hidden' | 'path' | 'signal';
  title: string;
  why: string;
  detail?: string;
}

function FindingsRail() {
  const active = useIntelStore((s) => s.active);
  const surfacedRings = useIntelStore((s) => s.surfacedRings);
  const surfacedPaths = useIntelStore((s) => s.surfacedPaths);
  const events = useIntelStore((s) => s.events);
  const selectEntity = useIntelStore((s) => s.selectEntity);
  const setFocusMode = useIntelStore((s) => s.setFocusMode);

  const findings: Finding[] = [];
  active.rings.forEach((r) => {
    if (surfacedRings.has(r.id)) {
      findings.push({
        id: r.id,
        kind: 'ring',
        title: r.name,
        why: `cohesion ${r.cohesion.toFixed(2)} · ${r.signal.replace('_', ' ')} · ${r.members.length} members`,
        detail: r.members[0],
      });
    }
  });
  active.paths.forEach((p) => {
    if (surfacedPaths.has(p.id)) {
      findings.push({
        id: p.id,
        kind: 'path',
        title: p.label,
        why: `${p.hops} hops · ${p.intent.replace('_', ' ')}`,
        detail: p.nodes[0],
      });
    }
  });
  // Pull hidden ties from events (since the store doesn't track surfacedHidden as a set)
  events.forEach((e) => {
    if (e.kind === 'hidden.relationship' && e.refs && e.refs[0]) {
      const h = active.hidden.find((x) => x.id === e.refs![0]);
      if (h && !findings.some((f) => f.id === h.id)) {
        findings.push({
          id: h.id,
          kind: 'hidden',
          title: `${h.from} → ${h.to}`,
          why: h.reason,
          detail: h.from,
        });
      }
    }
    if (e.kind === 'signal.surfaced' && e.refs && e.refs[0]) {
      const s = active.report.structuralSignals.find((x) => x.id === e.refs![0]);
      if (s && !findings.some((f) => f.id === s.id)) {
        findings.push({
          id: s.id,
          kind: 'signal',
          title: s.name,
          why: s.description,
          detail: s.contributors[0],
        });
      }
    }
  });

  return (
    <div className="absolute top-16 right-3 z-20 w-[300px] pointer-events-none">
      <div className="pointer-events-auto surface-floating overflow-hidden">
        <div className="px-3 h-7 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
          <Sparkles className="w-3 h-3 text-[var(--color-ice-400)]" />
          <span className="heading-tactical">Findings</span>
          <span className="ml-auto font-mono text-[9px] tracking-[0.2em] uppercase text-[var(--color-text-muted)]">
            {findings.length} surfaced
          </span>
        </div>
        <div className="p-1.5 space-y-1 max-h-[460px] overflow-y-auto scroll-tactical">
          {findings.length === 0 ? (
            <div className="px-2 py-3 font-mono text-[10px] tracking-[0.2em] uppercase text-[var(--color-text-muted)]">
              no structural findings yet…
            </div>
          ) : (
            findings.map((f) => {
              const { icon: Icon, color, accent } = findingMeta(f.kind);
              return (
                <motion.button
                  key={f.id}
                  layout
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ duration: 0.32, ease: [0.16, 1, 0.3, 1] }}
                  onClick={() => {
                    if (f.detail) selectEntity(f.detail);
                    setFocusMode(
                      f.kind === 'ring'
                        ? 'rings'
                        : f.kind === 'hidden'
                        ? 'hidden'
                        : f.kind === 'path'
                        ? 'paths'
                        : 'overview'
                    );
                  }}
                  className={cn(
                    'w-full text-left rounded-sm px-2 py-1.5 border',
                    'border-transparent hover:bg-[rgba(148,163,184,0.04)]',
                    'border-l-2'
                  )}
                  style={{ borderLeftColor: color }}
                >
                  <div className="flex items-center gap-2">
                    <Icon className="w-3 h-3 shrink-0" style={{ color }} />
                    <span
                      className="font-mono text-[9px] tracking-[0.22em] uppercase"
                      style={{ color }}
                    >
                      {f.kind}
                    </span>
                    <span className="ml-auto font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
                      {accent}
                    </span>
                  </div>
                  <div className="text-[11.5px] text-[var(--color-text-primary)] mt-0.5 leading-snug">
                    {f.title}
                  </div>
                  <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5 leading-snug">
                    {f.why}
                  </div>
                </motion.button>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}

function findingMeta(kind: Finding['kind']) {
  switch (kind) {
    case 'ring':
      return { icon: CircleDot, color: 'var(--color-rose-400)', accent: 'closed-cycle' };
    case 'hidden':
      return { icon: Spline, color: 'var(--color-violet-400)', accent: 'topology-derived' };
    case 'path':
      return { icon: GitBranch, color: 'var(--color-amber-400)', accent: 'traversal' };
    case 'signal':
      return { icon: Sparkles, color: 'var(--color-ice-400)', accent: 'structural' };
  }
}

/* -------------------------------------------------------------------------- */
/* BOTTOM — single narration line + progress                                  */
/* -------------------------------------------------------------------------- */

function BottomBar({
  event,
  progress,
  phase,
  onTakeManual,
}: {
  event: StreamEvent | undefined;
  progress: number;
  phase: 'idle' | 'streaming' | 'complete';
  onTakeManual: () => void;
}) {
  return (
    <div className="absolute bottom-0 left-0 right-0 z-20 px-3 pb-3 pointer-events-none">
      <div className="surface-floating pointer-events-auto px-3 py-2 flex items-center gap-3">
        {/* LEFT — action button (fixed slot, never overlaps) */}
        <button
          onClick={onTakeManual}
          className="h-7 px-2.5 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.28em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:text-[var(--color-violet-400)] hover:border-[rgba(168,85,247,0.4)] transition-colors shrink-0"
          title="switch to manual workstation"
        >
          <Hand className="w-3 h-3" />
          <span className="hidden md:inline">take manual control</span>
          <span className="md:hidden">manual</span>
        </button>

        <span className="w-px h-5 bg-[var(--color-line)] shrink-0" aria-hidden />

        {/* CENTER — status dot + narration (truncates, never collides) */}
        <span className="relative inline-flex w-1.5 h-1.5 shrink-0">
          <span
            className={cn(
              'absolute inset-0 rounded-full anim-pulse-ring',
              phase === 'streaming' ? 'bg-[var(--color-ice-400)]' : 'bg-[var(--color-text-faint)]'
            )}
          />
          <span
            className={cn(
              'relative inline-flex w-1.5 h-1.5 rounded-full',
              phase === 'streaming'
                ? 'bg-[var(--color-ice-400)]'
                : phase === 'complete'
                ? 'bg-[var(--color-emerald-400)]'
                : 'bg-[var(--color-text-faint)]'
            )}
          />
        </span>

        <div className="flex-1 min-w-0">
          {event ? (
            <motion.div
              key={event.id}
              initial={{ opacity: 0, x: 6, filter: 'blur(3px)' }}
              animate={{ opacity: 1, x: 0, filter: 'blur(0)' }}
              transition={{ duration: 0.32 }}
              className="flex items-center gap-2.5 min-w-0"
            >
              <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] shrink-0 hidden md:inline">
                seq {String(event.seq).padStart(3, '0')}
              </span>
              <span
                className={cn(
                  'font-mono text-[10px] tracking-[0.26em] uppercase shrink-0 hidden md:inline',
                  NARR_TONE[event.kind]
                )}
              >
                {NARR_VERB[event.kind]}
              </span>
              <span className="text-[var(--color-text-faint)] shrink-0 hidden md:inline">·</span>
              <span className="text-[12px] text-[var(--color-text-bright)] truncate min-w-0">
                {event.title}
              </span>
              <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] shrink-0 hidden lg:inline">
                {formatTime(event.at)}
              </span>
            </motion.div>
          ) : (
            <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              standby · engaging autopilot
            </span>
          )}
        </div>

        <span className="w-px h-5 bg-[var(--color-line)] shrink-0" aria-hidden />

        {/* RIGHT — progress (fixed slot) */}
        <div className="flex items-center gap-2 shrink-0">
          <div className="w-[120px] sm:w-[160px] h-1 rounded-full bg-[var(--color-graphite-800)] overflow-hidden">
            <motion.div
              initial={false}
              animate={{ width: `${Math.round(progress * 100)}%` }}
              transition={{ duration: 0.4 }}
              className="h-full bg-gradient-to-r from-[var(--color-ice-500)] to-[var(--color-violet-500)]"
            />
          </div>
          <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] w-9 text-right">
            {Math.round(progress * 100)}%
          </span>
        </div>
      </div>
    </div>
  );
}

function SpeedSelector({
  speed,
  setSpeed,
}: {
  speed: 0.5 | 1 | 2 | 4;
  setSpeed: (s: 0.5 | 1 | 2 | 4) => void;
}) {
  const SPEEDS: Array<0.5 | 1 | 2 | 4> = [0.5, 1, 2, 4];
  return (
    <div className="flex items-center gap-0.5 px-1 h-7 rounded-sm border border-[var(--color-line-soft)] bg-[rgba(10,13,19,0.5)] backdrop-blur-md">
      <Zap className="w-3 h-3 text-[var(--color-text-muted)] mx-1" />
      {SPEEDS.map((s) => (
        <button
          key={s}
          onClick={() => setSpeed(s)}
          className={cn(
            'h-5 px-1.5 text-[9px] font-mono rounded-sm transition-colors',
            speed === s
              ? 'bg-[rgba(34,211,238,0.12)] text-[var(--color-ice-400)]'
              : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]'
          )}
        >
          {s}x
        </button>
      ))}
    </div>
  );
}
