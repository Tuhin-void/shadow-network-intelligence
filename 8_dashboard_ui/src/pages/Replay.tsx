import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useIntelStore } from '@/store/intel-store';
import { cn, formatTime } from '@/lib/utils';
import { SyntheticScenarioRibbon } from '@/components/shared/SyntheticScenarioRibbon';
import {
  ChevronLeft,
  ChevronRight,
  Clock,
  GalleryVerticalEnd,
  Pause,
  Play,
  RotateCcw,
} from 'lucide-react';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { GraphLegend } from '@/components/graph/GraphHud';
import { TacticalRail } from '@/components/layout/TacticalRail';
import { WorkspaceTabs } from '@/components/layout/WorkspaceTabs';
import type { Session, StreamEvent, StreamEventKind } from '@/types/intel';
import { motion } from 'framer-motion';

const KIND_TONE: Record<StreamEventKind, string> = {
  'session.start': 'var(--color-text-secondary)',
  'topology.expanded': 'var(--color-ice-400)',
  'entity.discovered': 'var(--color-ice-400)',
  'edge.traversed': 'var(--color-text-secondary)',
  'ring.detected': 'var(--color-rose-400)',
  'hidden.relationship': 'var(--color-violet-400)',
  'path.discovered': 'var(--color-amber-400)',
  'suspicion.escalated': 'var(--color-rose-400)',
  'evidence.collected': 'var(--color-emerald-400)',
  'signal.surfaced': 'var(--color-ice-400)',
  'report.section': 'var(--color-text-secondary)',
  'session.complete': 'var(--color-emerald-400)',
};

/**
 * Replay — reconstructs an investigation step-by-step from a saved Session,
 * OR from the active preset's canonical stream if no session is selected.
 */
export function Replay() {
  const params = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const { sessions, presets, active, selectPreset, applyQuery, resetStream } =
    useIntelStore();

  // Choose the session to replay — route param wins, then local pick, then first.
  const [sessionId, setSessionId] = useState<string | null>(
    params.id ?? sessions[0]?.id ?? null
  );
  // Sync to URL param so the TacticalRail navigating to /replay/:id updates us
  useEffect(() => {
    if (params.id && params.id !== sessionId) setSessionId(params.id);
  }, [params.id, sessionId]);
  const session: Session | null = useMemo(() => {
    if (!sessionId) return null;
    return sessions.find((s) => s.id === sessionId) ?? null;
  }, [sessionId, sessions]);

  // If session exists & is from a different preset, switch presets
  useEffect(() => {
    if (session && session.presetId !== active.id) {
      selectPreset(session.presetId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [session?.presetId]);

  // The events we're scrubbing through: from session if available, else from preset.stream
  const events: StreamEvent[] = session?.events ?? active.stream;
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);

  // Reset index when session changes
  useEffect(() => {
    setIndex(0);
    resetStream();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, active.id]);

  // Whenever the scrubber moves, re-apply the topology state up to index
  useEffect(() => {
    // For simplicity, project the state: collect all discovered/surfaced from events[0..index-1]
    const discovered = new Set<string>([active.seed]);
    const paths = new Set<string>();
    const rings = new Set<string>();
    let lastNarr: string | null = null;

    for (let i = 0; i < index; i += 1) {
      const e = events[i];
      const refs = e.refs ?? [];
      if (e.kind === 'entity.discovered' || e.kind === 'topology.expanded') {
        refs.forEach((id) => discovered.add(id));
      }
      if (e.kind === 'path.discovered') {
        refs.forEach((id) => paths.add(id));
        const p = active.paths.find((x) => x.id === refs[0]);
        if (p) p.nodes.forEach((n) => discovered.add(n));
      }
      if (e.kind === 'ring.detected') {
        refs.forEach((id) => rings.add(id));
        const r = active.rings.find((x) => x.id === refs[0]);
        if (r) r.members.forEach((m) => discovered.add(m));
      }
      if (e.kind === 'hidden.relationship') {
        const h = active.hidden.find((x) => x.id === refs[0]);
        if (h) {
          discovered.add(h.from);
          discovered.add(h.to);
          h.via.forEach((v) => discovered.add(v));
        }
      }
      lastNarr = `${e.kind} · ${e.title}`;
    }

    applyQuery({
      discoverEntities: Array.from(discovered),
      surfacePaths: Array.from(paths),
      surfaceRings: Array.from(rings),
      narrationLine: lastNarr,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [index, events, active.id]);

  // Auto-play
  useEffect(() => {
    if (!playing) return;
    if (index >= events.length) {
      setPlaying(false);
      return;
    }
    const t = setTimeout(() => setIndex((i) => Math.min(events.length, i + 1)), 480);
    return () => clearTimeout(t);
  }, [playing, index, events.length]);

  const current = events[Math.max(0, index - 1)];

  return (
    <div className="fill overflow-hidden">
      <SyntheticScenarioRibbon
        label="replay visualization"
        hint="scenario stream replay · not live retrieval"
      />
      {/* Workspace micro-tabs strip + slim contextual rail */}
      <WorkspaceTabs />
      <TacticalRail defaultTab="replay" />

      {/* Body */}
      <div
        className="absolute top-[96px] inset-x-0 bottom-0"
        style={{
          display: 'grid',
          gridTemplateColumns: '92px minmax(0, 1fr) 360px',
          gap: 6,
          padding: 6,
        }}
      >
        {/* LEFT gutter for the floating rail */}
        <div />

        {/* CENTER — graph */}
        <div className="relative surface overflow-hidden min-h-0">
          <div className="absolute top-0 left-0 right-0 h-7 flex items-center px-3 z-30 bg-[rgba(7,9,14,0.55)] backdrop-blur-sm border-b border-[var(--color-line-soft)]">
            <GalleryVerticalEnd className="w-3 h-3 text-[var(--color-ice-400)]" />
            <span className="heading-tactical ml-2">Topology · t = {index}</span>
            {current && (
              <span
                className="ml-3 font-mono text-[10px] tracking-[0.22em] uppercase"
                style={{ color: KIND_TONE[current.kind] }}
              >
                {current.kind}
              </span>
            )}
            <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              scrub the rail below
            </span>
          </div>
          <div className="absolute top-7 left-0 right-0 bottom-[80px]">
            <GraphCanvas />
            <GraphLegend />
          </div>

          {/* Scrubber rail */}
          <div className="absolute bottom-0 left-0 right-0 h-[80px] border-t border-[var(--color-line-soft)] bg-[rgba(7,9,14,0.7)] backdrop-blur-md px-3 py-2 flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setIndex((i) => Math.max(0, i - 1))}
                disabled={index === 0}
                className="h-7 w-7 inline-flex items-center justify-center rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:bg-[rgba(34,211,238,0.06)] hover:border-[rgba(34,211,238,0.32)] disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setPlaying((p) => !p)}
                className={cn(
                  'h-7 w-7 inline-flex items-center justify-center rounded-sm border',
                  playing
                    ? 'border-[rgba(244,63,94,0.4)] bg-[rgba(244,63,94,0.06)] text-[var(--color-rose-400)]'
                    : 'border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)]'
                )}
              >
                {playing ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              </button>
              <button
                onClick={() => setIndex((i) => Math.min(events.length, i + 1))}
                disabled={index >= events.length}
                className="h-7 w-7 inline-flex items-center justify-center rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:bg-[rgba(34,211,238,0.06)] hover:border-[rgba(34,211,238,0.32)] disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => {
                  setPlaying(false);
                  setIndex(0);
                }}
                className="h-7 w-7 inline-flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)] rounded-sm hover:bg-[rgba(148,163,184,0.06)]"
              >
                <RotateCcw className="w-3 h-3" />
              </button>

              <input
                type="range"
                min={0}
                max={events.length}
                value={index}
                onChange={(e) => setIndex(parseInt(e.target.value, 10))}
                className="flex-1 accent-[var(--color-ice-500)]"
              />
              <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] w-20 text-right">
                {index} / {events.length}
              </span>
            </div>

            {/* Step dots row */}
            <div className="flex items-center gap-[3px] h-3 overflow-hidden">
              {events.map((e, i) => (
                <button
                  key={e.id + i}
                  onClick={() => setIndex(i + 1)}
                  className="flex-1 h-2 rounded-sm transition-all"
                  style={{
                    background:
                      i < index
                        ? KIND_TONE[e.kind]
                        : 'rgba(148,163,184,0.10)',
                    opacity: i < index ? 0.8 : 1,
                  }}
                  title={`${e.kind} · ${e.title}`}
                />
              ))}
            </div>
          </div>
        </div>

        {/* RIGHT — event detail */}
        <div className="surface overflow-y-auto scroll-tactical min-h-0">
          <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
            <span className="heading-tactical">Current event</span>
          </div>
          {current ? (
            <motion.div
              key={current.id}
              initial={{ opacity: 0, y: 6, filter: 'blur(3px)' }}
              animate={{ opacity: 1, y: 0, filter: 'blur(0)' }}
              transition={{ duration: 0.28 }}
              className="p-4"
            >
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
                  seq {String(current.seq).padStart(3, '0')}
                </span>
                <span
                  className="font-mono text-[10px] tracking-[0.22em] uppercase"
                  style={{ color: KIND_TONE[current.kind] }}
                >
                  {current.kind}
                </span>
                <span className="ml-auto font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] flex items-center gap-1">
                  <Clock className="w-2.5 h-2.5" />
                  {formatTime(current.at)}
                </span>
              </div>
              <div className="text-[13px] text-[var(--color-text-bright)] leading-snug">
                {current.title}
              </div>
              {current.refs && current.refs.length > 0 && (
                <div className="mt-3">
                  <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
                    references
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {current.refs.map((r) => (
                      <span
                        key={r}
                        className="chip text-[9px]"
                        style={{
                          color: 'var(--color-ice-400)',
                          borderColor: 'rgba(34,211,238,0.32)',
                        }}
                      >
                        {r}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              {current.section && (
                <div className="mt-3">
                  <div className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
                    contributes to
                  </div>
                  <span className="chip chip-emerald text-[9px]">
                    {current.section}
                  </span>
                </div>
              )}
            </motion.div>
          ) : (
            <div className="p-4 font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              scrub the rail or press play
            </div>
          )}

          {/* Upcoming events */}
          <div className="border-t border-[var(--color-line-soft)]">
            <div className="px-3 h-7 flex items-center border-b border-[var(--color-line-soft)]">
              <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                upcoming · {Math.max(0, events.length - index)}
              </span>
            </div>
            <div className="px-2 py-1.5 space-y-0.5">
              {events.slice(index, index + 8).map((e, i) => (
                <button
                  key={e.id + i}
                  onClick={() => setIndex(index + i + 1)}
                  className="w-full text-left px-1.5 py-1 rounded-sm hover:bg-[rgba(148,163,184,0.04)] flex items-center gap-2"
                >
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: KIND_TONE[e.kind] }}
                  />
                  <span
                    className="font-mono text-[9.5px] tracking-[0.18em] uppercase shrink-0 w-24 truncate"
                    style={{ color: KIND_TONE[e.kind] }}
                  >
                    {e.kind.split('.')[1]}
                  </span>
                  <span className="text-[10.5px] text-[var(--color-text-secondary)] truncate">
                    {e.title}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
