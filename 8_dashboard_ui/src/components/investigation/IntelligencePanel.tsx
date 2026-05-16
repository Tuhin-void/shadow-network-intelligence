import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ChevronDown, Sparkles } from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { cn, entityGlyph, tierColor } from '@/lib/utils';
import { RiskBadge } from '@/components/shared/RiskBadge';
import type {
  HiddenRelationship,
  IntelReport,
  Ring,
  StructuralSignal,
  TraversalPath,
} from '@/types/intel';

/* -------------------------------------------------------------------------- */
/* Sections                                                                   */
/* -------------------------------------------------------------------------- */

const SECTIONS: Array<{
  key: keyof IntelReport;
  label: string;
  glyph: string;
}> = [
  { key: 'suspects', label: 'Suspects', glyph: '01' },
  { key: 'hiddenRelationships', label: 'Hidden relationships', glyph: '02' },
  { key: 'rings', label: 'Ring connections', glyph: '03' },
  { key: 'ownershipFlow', label: 'Ownership flow', glyph: '04' },
  { key: 'transactionFlows', label: 'Transaction flows', glyph: '05' },
  { key: 'sharedInfrastructure', label: 'Shared infrastructure', glyph: '06' },
  { key: 'traversalPaths', label: 'Traversal paths', glyph: '07' },
  { key: 'structuralSignals', label: 'Structural signals', glyph: '08' },
  { key: 'evidence', label: 'Evidence chain', glyph: '09' },
];

export function IntelligencePanel() {
  const { active, streamingPhase, progress } = useIntelStore();
  const report = active.report;

  // For "live" feel: reveal sections progressively when streaming.
  // Otherwise reveal all immediately.
  const reveal = streamingPhase === 'streaming'
    ? Math.max(1, Math.floor(progress * SECTIONS.length))
    : SECTIONS.length;

  return (
    <div className="flex flex-col h-full">
      <NarrativeBlock report={report} />
      <div className="px-3 h-7 flex items-center border-b border-[var(--color-line-soft)] sticky top-0 z-10 bg-[var(--color-graphite-900)]">
        <span className="heading-tactical">Report · 9 sections</span>
        <span className="ml-auto font-mono text-[10px] text-[var(--color-text-muted)]">
          {Math.min(reveal, SECTIONS.length)} / 9
        </span>
      </div>
      <div className="flex-1 overflow-y-auto scroll-tactical">
        {SECTIONS.map((s, i) => (
          <Section
            key={s.key}
            index={i + 1}
            glyph={s.glyph}
            label={s.label}
            disabled={i >= reveal}
            sectionKey={s.key}
            report={report}
          />
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Narrative                                                                  */
/* -------------------------------------------------------------------------- */

function NarrativeBlock({ report }: { report: IntelReport }) {
  return (
    <div className="px-3 py-3 border-b border-[var(--color-line-soft)] bg-[var(--color-graphite-900)]">
      <div className="flex items-center gap-2 mb-1.5">
        <Sparkles className="w-3 h-3 text-[var(--color-ice-400)]" />
        <span className="label-tactical">Narrative</span>
      </div>
      <p className="text-[13px] leading-snug font-medium text-[var(--color-text-bright)]">
        {report.narrative.headline}
      </p>
      <p className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed mt-1.5">
        {report.narrative.body}
      </p>
      <div className="flex flex-wrap gap-1 mt-2">
        {report.narrative.highlights.map((h) => (
          <span key={h} className="chip text-[9px] border-[rgba(34,211,238,0.3)] text-[var(--color-ice-400)]">
            {h}
          </span>
        ))}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Section dispatch                                                            */
/* -------------------------------------------------------------------------- */

function Section({
  index,
  glyph,
  label,
  disabled,
  sectionKey,
  report,
}: {
  index: number;
  glyph: string;
  label: string;
  disabled: boolean;
  sectionKey: keyof IntelReport;
  report: IntelReport;
}) {
  const [open, setOpen] = useState(true);
  void index;
  const data = report[sectionKey] as unknown;
  const count = Array.isArray(data) ? data.length : 0;

  return (
    <motion.div
      initial={false}
      animate={{ opacity: disabled ? 0.32 : 1 }}
      className="border-b border-[var(--color-line-soft)]"
    >
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 h-9 hover:bg-[rgba(148,163,184,0.03)] transition-colors"
        disabled={disabled}
      >
        <span className="font-mono text-[9px] text-[var(--color-text-muted)]">{glyph}</span>
        <span className="heading-tactical text-left">{label}</span>
        {count > 0 && (
          <span className="chip text-[9px] ml-1">{count}</span>
        )}
        {disabled && (
          <span className="ml-auto font-mono text-[9px] text-[var(--color-text-faint)] uppercase tracking-wider">
            queued
          </span>
        )}
        {!disabled && (
          <ChevronDown
            className={cn(
              'ml-auto w-3 h-3 text-[var(--color-text-muted)] transition-transform',
              open && 'rotate-180'
            )}
          />
        )}
      </button>
      <AnimatePresence initial={false}>
        {open && !disabled && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3">{renderSection(sectionKey, report)}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function renderSection(key: keyof IntelReport, report: IntelReport) {
  switch (key) {
    case 'suspects':
      return <SuspectList items={report.suspects} />;
    case 'hiddenRelationships':
      return <HiddenList items={report.hiddenRelationships} />;
    case 'rings':
      return <RingList items={report.rings} />;
    case 'ownershipFlow':
      return <PathList items={report.ownershipFlow} tone="amber" />;
    case 'transactionFlows':
      return <PathList items={report.transactionFlows} tone="ice" />;
    case 'sharedInfrastructure':
      return <HiddenList items={report.sharedInfrastructure} compact />;
    case 'traversalPaths':
      return <PathList items={report.traversalPaths} tone="ice" />;
    case 'structuralSignals':
      return <SignalList items={report.structuralSignals} />;
    case 'evidence':
      return <EvidenceList />;
  }
  return null;
}

/* -------------------------------------------------------------------------- */
/* Renderers                                                                  */
/* -------------------------------------------------------------------------- */

function SuspectList({ items }: { items: IntelReport['suspects'] }) {
  const selectEntity = useIntelStore((s) => s.selectEntity);
  return (
    <div className="space-y-1">
      {items.map((e) => (
        <button
          key={e.id}
          onClick={() => selectEntity(e.id)}
          className="w-full text-left panel-soft px-2.5 py-2 flex items-center gap-2.5 hover:bg-[rgba(34,211,238,0.04)] transition-colors"
        >
          <span
            className="inline-flex items-center justify-center w-7 h-7 rounded-sm border text-[12px]"
            style={{
              borderColor: tierColor(e.tier),
              color: tierColor(e.tier),
              background: `${tierColor(e.tier)}12`,
            }}
          >
            {entityGlyph(e.kind)}
          </span>
          <div className="flex-1 min-w-0">
            <div className="text-[12px] font-medium text-[var(--color-text-bright)] truncate">
              {e.label}
            </div>
            <div className="font-mono text-[9px] uppercase tracking-wider text-[var(--color-text-muted)]">
              {e.kind.replace('_', ' ')} · {e.id}
            </div>
          </div>
          <RiskBadge score={e.risk} tier={e.tier} size="xs" />
        </button>
      ))}
    </div>
  );
}

function HiddenList({
  items,
  compact,
}: {
  items: HiddenRelationship[];
  compact?: boolean;
}) {
  const active = useIntelStore((s) => s.active);
  const selectEntity = useIntelStore((s) => s.selectEntity);
  return (
    <div className="space-y-1.5">
      {items.map((h) => {
        const from = active.graph.entities.find((e) => e.id === h.from);
        const to = active.graph.entities.find((e) => e.id === h.to);
        return (
          <div key={h.id} className="panel-soft p-2 border-l-2 border-[var(--color-violet-500)]">
            <div className="flex items-center gap-2">
              <button
                onClick={() => selectEntity(h.from)}
                className="font-mono text-[10px] text-[var(--color-violet-400)] hover:text-[var(--color-violet-300)] truncate"
              >
                {from?.label ?? h.from}
              </button>
              <span className="text-[var(--color-text-muted)] font-mono text-[10px]">→</span>
              <button
                onClick={() => selectEntity(h.to)}
                className="font-mono text-[10px] text-[var(--color-violet-400)] hover:text-[var(--color-violet-300)] truncate"
              >
                {to?.label ?? h.to}
              </button>
              <span className="ml-auto font-mono text-[10px] text-[var(--color-text-muted)]">
                {h.confidence.toFixed(2)}
              </span>
            </div>
            <div className="text-[11px] text-[var(--color-text-secondary)] mt-1">{h.reason}</div>
            {!compact && (
              <div className="font-mono text-[9px] text-[var(--color-text-muted)] mt-1 uppercase tracking-wider truncate">
                via {h.via.join(' → ')}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

function RingList({ items }: { items: Ring[] }) {
  const setFocusMode = useIntelStore((s) => s.setFocusMode);
  return (
    <div className="space-y-1.5">
      {items.map((r) => (
        <div key={r.id} className="panel-soft p-2 border-l-2 border-[var(--color-rose-500)]">
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-medium text-[var(--color-text-bright)] truncate">
              {r.name}
            </span>
            <RiskBadge tier={r.risk} size="xs" />
            <span className="ml-auto font-mono text-[10px] text-[var(--color-text-muted)]">
              cohesion {r.cohesion.toFixed(2)}
            </span>
          </div>
          <div className="font-mono text-[10px] text-[var(--color-text-muted)] mt-1 uppercase tracking-wider">
            signal · {r.signal.replace('_', ' ')}
          </div>
          <div className="flex flex-wrap gap-1 mt-1.5">
            {r.members.slice(0, 6).map((m) => (
              <span key={m} className="chip text-[9px]">
                {m}
              </span>
            ))}
            {r.members.length > 6 && (
              <span className="chip text-[9px]">+{r.members.length - 6}</span>
            )}
          </div>
          <button
            onClick={() => setFocusMode('rings')}
            className="mt-1.5 font-mono text-[10px] text-[var(--color-ice-400)] hover:underline"
          >
            ▸ focus ring on graph
          </button>
        </div>
      ))}
    </div>
  );
}

function PathList({
  items,
  tone,
}: {
  items: TraversalPath[];
  tone: 'ice' | 'amber';
}) {
  const active = useIntelStore((s) => s.active);
  const setFocusMode = useIntelStore((s) => s.setFocusMode);
  const color =
    tone === 'amber' ? 'var(--color-amber-500)' : 'var(--color-ice-500)';
  return (
    <div className="space-y-1.5">
      {items.map((p) => (
        <div
          key={p.id}
          className="panel-soft p-2"
          style={{ borderLeft: `2px solid ${color}` }}
        >
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-medium text-[var(--color-text-bright)] truncate">
              {p.label}
            </span>
            <span className="ml-auto chip text-[9px]">{p.hops} hops</span>
            <span className="chip text-[9px]">{p.intent.replace('_', ' ')}</span>
          </div>
          <div className="text-[11px] text-[var(--color-text-secondary)] mt-1">{p.why}</div>
          <div className="flex items-center gap-1 mt-1.5 flex-wrap">
            {p.nodes.map((id, i) => {
              const e = active.graph.entities.find((x) => x.id === id);
              return (
                <span key={id} className="flex items-center gap-1">
                  <span
                    className="font-mono text-[10px] px-1.5 py-0.5 rounded-sm border"
                    style={{
                      borderColor: 'var(--color-line)',
                      color: 'var(--color-text-primary)',
                    }}
                  >
                    {e?.label ?? id}
                  </span>
                  {i < p.nodes.length - 1 && (
                    <span className="text-[var(--color-text-muted)] font-mono text-[10px]">→</span>
                  )}
                </span>
              );
            })}
          </div>
          <button
            onClick={() => setFocusMode('paths')}
            className="mt-1.5 font-mono text-[10px] hover:underline"
            style={{ color }}
          >
            ▸ animate traversal on graph
          </button>
        </div>
      ))}
    </div>
  );
}

function SignalList({ items }: { items: StructuralSignal[] }) {
  return (
    <div className="space-y-1.5">
      {items.map((s) => (
        <div key={s.id} className="panel-soft p-2">
          <div className="flex items-center gap-2">
            <span className="text-[12px] font-medium text-[var(--color-text-bright)] truncate">
              {s.name}
            </span>
            <span className="ml-auto font-mono text-[10px] text-[var(--color-ice-400)]">
              {s.intensity.toFixed(2)}
            </span>
          </div>
          <div className="text-[11px] text-[var(--color-text-secondary)] mt-1">{s.description}</div>
          <div className="h-1 rounded-full bg-[var(--color-graphite-800)] overflow-hidden mt-2">
            <div
              className="h-full bg-gradient-to-r from-[var(--color-ice-500)] to-[var(--color-violet-500)]"
              style={{ width: `${Math.round(s.intensity * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function EvidenceList() {
  const active = useIntelStore((s) => s.active);
  return (
    <div className="relative pl-6">
      <span className="absolute left-2 top-1 bottom-1 w-px bg-[var(--color-line)]" />
      <div className="space-y-2">
        {active.report.evidence.map((ev) => (
          <div key={ev.id} className="relative">
            <span
              className="absolute -left-[18px] top-1 w-2 h-2 rounded-full"
              style={{ background: 'var(--color-ice-400)' }}
            />
            <div className="font-mono text-[10px] uppercase tracking-wider text-[var(--color-text-muted)]">
              basis · {ev.basis}
            </div>
            <div className="text-[12px] text-[var(--color-text-primary)]">{ev.claim}</div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
                refs {ev.refs.slice(0, 2).join(', ')}
                {ev.refs.length > 2 ? '…' : ''}
              </span>
              <span className="ml-auto font-mono text-[9px] text-[var(--color-ice-400)]">
                conf {ev.confidence.toFixed(2)}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
