import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useIntelStore } from '@/store/intel-store';
import { cn, formatTime } from '@/lib/utils';
import type { StreamEvent, StreamEventKind } from '@/types/intel';

const kindGlyph: Record<StreamEventKind, string> = {
  'session.start': '▶',
  'topology.expanded': '◇',
  'entity.discovered': '●',
  'edge.traversed': '─',
  'ring.detected': '◎',
  'hidden.relationship': '◌',
  'path.discovered': '⇢',
  'suspicion.escalated': '▲',
  'evidence.collected': '✶',
  'signal.surfaced': '⊹',
  'report.section': '☷',
  'session.complete': '■',
};

const kindTone: Record<StreamEventKind, string> = {
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

export function TimelineFeed() {
  const { events, streamingPhase, active } = useIntelStore();
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current && streamingPhase === 'streaming') {
      scrollRef.current.scrollTo({
        left: scrollRef.current.scrollWidth,
        behavior: 'smooth',
      });
    }
  }, [events.length, streamingPhase]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 h-8 flex items-center gap-3 border-b border-[var(--color-line-soft)]">
        <span className="heading-tactical">Investigation timeline</span>
        <span className="font-mono text-[10px] text-[var(--color-text-muted)]">
          {events.length} events · {active.label}
        </span>
        <div className="ml-auto flex items-center gap-2">
          {Object.entries(
            events.reduce<Record<string, number>>((acc, e) => {
              acc[e.kind] = (acc[e.kind] ?? 0) + 1;
              return acc;
            }, {})
          )
            .slice(0, 5)
            .map(([k, v]) => (
              <span
                key={k}
                className={cn(
                  'chip text-[9px]',
                  kindTone[k as StreamEventKind]
                )}
              >
                {kindGlyph[k as StreamEventKind]} {k.split('.')[1]} · {v}
              </span>
            ))}
        </div>
      </div>
      <div
        ref={scrollRef}
        className="flex-1 min-h-0 flex items-stretch overflow-x-auto scroll-tactical relative"
      >
        {events.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="flex items-stretch gap-3 px-3 py-2 h-full">
            <AnimatePresence initial={false}>
              {events.map((e, i) => (
                <TimelineCard key={e.id} event={e} index={i} />
              ))}
            </AnimatePresence>
            {streamingPhase === 'streaming' && <Cursor />}
          </div>
        )}
        <div className="absolute inset-y-0 left-0 w-12 pointer-events-none bg-gradient-to-r from-[var(--color-graphite-900)] to-transparent" />
        <div className="absolute inset-y-0 right-0 w-12 pointer-events-none bg-gradient-to-l from-[var(--color-graphite-900)] to-transparent" />
      </div>
    </div>
  );
}

function TimelineCard({ event, index }: { event: StreamEvent; index: number }) {
  void index;
  const selectEntity = useIntelStore((s) => s.selectEntity);
  return (
    <motion.button
      layout
      initial={{ opacity: 0, y: 8, filter: 'blur(3px)' }}
      animate={{ opacity: 1, y: 0, filter: 'blur(0)' }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
      onClick={() => {
        if (event.refs && event.refs[0]) selectEntity(event.refs[0]);
      }}
      className="panel-soft min-w-[180px] max-w-[220px] px-2.5 py-2 text-left flex flex-col gap-1 shrink-0 hover:border-[rgba(34,211,238,0.3)] transition-colors"
    >
      <div className="flex items-center gap-2">
        <span className={cn('text-[12px]', kindTone[event.kind])}>{kindGlyph[event.kind]}</span>
        <span className="font-mono text-[9px] uppercase tracking-wider text-[var(--color-text-muted)]">
          {event.kind.replace('.', ' / ')}
        </span>
        <span className="ml-auto font-mono text-[9px] text-[var(--color-text-faint)]">
          {String(event.seq).padStart(3, '0')}
        </span>
      </div>
      <div className="text-[11px] text-[var(--color-text-primary)] leading-snug line-clamp-2">
        {event.title}
      </div>
      <div className="font-mono text-[9px] text-[var(--color-text-muted)] mt-auto">
        {formatTime(event.at)}
      </div>
    </motion.button>
  );
}

function Cursor() {
  return (
    <motion.div
      animate={{ opacity: [0.4, 1, 0.4] }}
      transition={{ repeat: Infinity, duration: 1.4 }}
      className="self-stretch flex items-center shrink-0"
    >
      <div className="w-px h-full bg-[var(--color-ice-400)] shadow-[0_0_8px_var(--color-ice-400)]" />
      <span className="ml-1 font-mono text-[9px] uppercase tracking-wider text-[var(--color-ice-400)]">
        live
      </span>
    </motion.div>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex items-center justify-center text-[12px] text-[var(--color-text-muted)] font-mono">
      <span className="opacity-70">▷ awaiting LAUNCH — events stream here in real time</span>
    </div>
  );
}
