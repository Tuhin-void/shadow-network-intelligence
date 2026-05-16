import { useIntelStore, getEntityById } from '@/store/intel-store';
import { cn, entityGlyph, tierColor } from '@/lib/utils';
import { RiskBadge } from '@/components/shared/RiskBadge';
import {
  AlertOctagon,
  Bookmark,
  CircleDot,
  GitBranch,
  Layers,
  NotebookPen,
  Pin,
  ShieldAlert,
  Spline,
  Waves,
} from 'lucide-react';
import { useMemo, useState } from 'react';

/**
 * EntityInspector — the WHY for a single entity.
 *
 * For the selected entity, surfaces every structural reason it appears
 * in the investigation:
 *   • ring memberships (closed-cycle / shared-infra cohesion)
 *   • hidden ties (topology-derived, with via-chain)
 *   • paths it sits on (ownership / evidence / reverse-edge)
 *   • structural signals that named it as a contributor
 *   • shared infrastructure links (devices / addresses / phones)
 *   • direct edges (kind + counterparty + confidence)
 *
 * Every claim is one-click pivotable back into the graph.
 */
export function EntityInspector() {
  const selectedEntityId = useIntelStore((s) => s.selectedEntityId);
  const active = useIntelStore((s) => s.active);
  const selectEntity = useIntelStore((s) => s.selectEntity);
  const setFocusMode = useIntelStore((s) => s.setFocusMode);
  const bookmarkedEntities = useIntelStore((s) => s.bookmarkedEntities);
  const toggleBookmark = useIntelStore((s) => s.toggleBookmark);
  const notes = useIntelStore((s) => s.notes);
  const setNote = useIntelStore((s) => s.setNote);
  const entity = getEntityById(selectedEntityId);
  const isBookmarked = entity ? bookmarkedEntities.has(entity.id) : false;
  const note = entity ? notes[entity.id] ?? '' : '';

  const why = useMemo(() => {
    if (!entity) return null;
    const directEdges = active.graph.edges.filter(
      (e) => e.source === entity.id || e.target === entity.id
    );
    const ringMembership = active.rings.filter((r) => r.members.includes(entity.id));
    const hiddenLinks = active.hidden.filter(
      (h) => h.from === entity.id || h.to === entity.id
    );
    const sharedInfra = active.report.sharedInfrastructure.filter(
      (h) => h.from === entity.id || h.to === entity.id || h.via.includes(entity.id)
    );
    const paths = active.paths.filter((p) => p.nodes.includes(entity.id));
    const signals = active.report.structuralSignals.filter((s) =>
      s.contributors.includes(entity.id)
    );
    return { directEdges, ringMembership, hiddenLinks, sharedInfra, paths, signals };
  }, [entity, active]);

  if (!entity || !why) {
    return (
      <div className="p-4 text-[12px] text-[var(--color-text-muted)]">
        <div className="label-tactical mb-2">Inspector</div>
        Select a node on the graph or a finding in the report to inspect its
        structural profile and reasoning.
      </div>
    );
  }

  const reasonCount =
    why.ringMembership.length +
    why.hiddenLinks.length +
    why.paths.length +
    why.signals.length +
    why.sharedInfra.length;

  return (
    <div className="text-[12px]">
      {/* Identity row */}
      <div className="px-3 pt-3 pb-2.5 flex items-start gap-3 border-b border-[var(--color-line-soft)]">
        <span
          className="inline-flex items-center justify-center w-9 h-9 rounded-sm border text-[14px] shrink-0"
          style={{
            borderColor: tierColor(entity.tier),
            color: tierColor(entity.tier),
            background: `${tierColor(entity.tier)}10`,
          }}
        >
          {entityGlyph(entity.kind)}
        </span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-[13px] text-[var(--color-text-bright)] truncate">
            {entity.label}
          </div>
          <div className="font-mono text-[9.5px] uppercase tracking-[0.18em] text-[var(--color-text-muted)] mt-0.5">
            {entity.kind.replace('_', ' ')} · {entity.id}
          </div>
          {entity.flags && entity.flags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {entity.flags.map((f) => (
                <span
                  key={f}
                  className="chip text-[9px]"
                  style={{
                    borderColor: 'rgba(244,63,94,0.4)',
                    color: 'var(--color-rose-400)',
                  }}
                >
                  <ShieldAlert className="w-2.5 h-2.5" /> {f}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex flex-col items-end gap-1.5 shrink-0">
          <RiskBadge score={entity.risk} tier={entity.tier} size="sm" />
          <button
            onClick={() => toggleBookmark(entity.id)}
            title={isBookmarked ? 'remove bookmark' : 'bookmark entity'}
            className={cn(
              'w-6 h-6 inline-flex items-center justify-center rounded-sm border',
              isBookmarked
                ? 'border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)]'
                : 'border-[var(--color-line)] text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)] hover:border-[rgba(34,211,238,0.32)]'
            )}
          >
            <Bookmark className="w-3 h-3" fill={isBookmarked ? 'currentColor' : 'none'} strokeWidth={1.5} />
          </button>
        </div>
      </div>

      {/* WHY summary line */}
      <div className="px-3 py-2 border-b border-[var(--color-line-soft)] bg-[rgba(244,63,94,0.04)]">
        <div className="flex items-center gap-2">
          <AlertOctagon className="w-3 h-3 text-[var(--color-rose-400)]" />
          <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-rose-400)]">
            why flagged
          </span>
          <span className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            {reasonCount} reason{reasonCount === 1 ? '' : 's'}
          </span>
        </div>
        <div className="mt-1 text-[11px] text-[var(--color-text-primary)] leading-snug">
          {summarizeWhy(entity.label, why)}
        </div>
      </div>

      {/* Analyst notes — persisted to localStorage */}
      <NoteEditor
        entityId={entity.id}
        value={note}
        onChange={(v) => setNote(entity.id, v)}
      />

      {/* Stat strip */}
      <div className="grid grid-cols-3 gap-px bg-[var(--color-line-soft)]">
        <Stat label="degree" value={why.directEdges.length} />
        <Stat
          label="hidden"
          value={why.hiddenLinks.length}
          accent="violet"
        />
        <Stat label="paths" value={why.paths.length} accent="amber" />
      </div>

      {/* Reason sections */}
      <div className="divide-y divide-[var(--color-line-soft)]">
        {/* Rings */}
        {why.ringMembership.length > 0 && (
          <ReasonSection
            icon={CircleDot}
            tone="rose"
            label="Ring memberships"
            count={why.ringMembership.length}
            onFocus={() => setFocusMode('rings')}
            focusLabel="ring mode"
          >
            <div className="space-y-1">
              {why.ringMembership.map((r) => (
                <div
                  key={r.id}
                  className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-rose-500)]"
                >
                  <div className="text-[11px] text-[var(--color-text-primary)]">{r.name}</div>
                  <div className="mt-0.5 font-mono text-[9.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
                    cohesion {r.cohesion.toFixed(2)} · {r.signal.replace('_', ' ')} · {r.members.length} members
                  </div>
                </div>
              ))}
            </div>
          </ReasonSection>
        )}

        {/* Hidden ties */}
        {why.hiddenLinks.length > 0 && (
          <ReasonSection
            icon={Spline}
            tone="violet"
            label="Hidden ties via topology"
            count={why.hiddenLinks.length}
            onFocus={() => setFocusMode('hidden')}
            focusLabel="hidden mode"
          >
            <div className="space-y-1">
              {why.hiddenLinks.map((h) => {
                const other = h.from === entity.id ? h.to : h.from;
                const ent = active.graph.entities.find((e) => e.id === other);
                return (
                  <button
                    key={h.id}
                    onClick={() => selectEntity(other)}
                    className="w-full text-left rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-violet-500)] hover:bg-[rgba(168,85,247,0.06)]"
                  >
                    <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.12em] uppercase">
                      <span className="text-[var(--color-text-muted)]">to</span>
                      <span className="text-[var(--color-violet-400)] truncate">
                        {ent?.label ?? other}
                      </span>
                      <span className="ml-auto text-[var(--color-text-muted)]">
                        conf {h.confidence.toFixed(2)}
                      </span>
                    </div>
                    <div className="text-[11px] text-[var(--color-text-secondary)] mt-0.5">
                      {h.reason}
                    </div>
                    <div className="font-mono text-[9px] tracking-[0.14em] uppercase text-[var(--color-text-muted)] mt-1 truncate">
                      via {h.via.join(' → ')}
                    </div>
                  </button>
                );
              })}
            </div>
          </ReasonSection>
        )}

        {/* Paths on which this entity sits */}
        {why.paths.length > 0 && (
          <ReasonSection
            icon={GitBranch}
            tone="amber"
            label="Paths it sits on"
            count={why.paths.length}
            onFocus={() => setFocusMode('paths')}
            focusLabel="path mode"
          >
            <div className="space-y-1">
              {why.paths.map((p) => (
                <div
                  key={p.id}
                  className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-amber-500)]"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-[var(--color-text-primary)]">
                      {p.label}
                    </span>
                    <span className="ml-auto font-mono text-[9.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
                      {p.hops} hops · {p.intent.replace('_', ' ')}
                    </span>
                  </div>
                  <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5">
                    {p.why}
                  </div>
                </div>
              ))}
            </div>
          </ReasonSection>
        )}

        {/* Structural signals */}
        {why.signals.length > 0 && (
          <ReasonSection
            icon={Waves}
            tone="ice"
            label="Signals naming this entity"
            count={why.signals.length}
          >
            <div className="space-y-1">
              {why.signals.map((s) => (
                <div
                  key={s.id}
                  className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-ice-500)]"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] text-[var(--color-text-primary)]">{s.name}</span>
                    <span className="ml-auto font-mono text-[10px] text-[var(--color-ice-400)]">
                      {s.intensity.toFixed(2)}
                    </span>
                  </div>
                  <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5">
                    {s.description}
                  </div>
                </div>
              ))}
            </div>
          </ReasonSection>
        )}

        {/* Shared infrastructure */}
        {why.sharedInfra.length > 0 && (
          <ReasonSection
            icon={Layers}
            tone="emerald"
            label="Shared infrastructure"
            count={why.sharedInfra.length}
          >
            <div className="space-y-1">
              {why.sharedInfra.map((h) => {
                const other = h.from === entity.id ? h.to : h.from;
                const ent = active.graph.entities.find((e) => e.id === other);
                return (
                  <div
                    key={h.id}
                    className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-emerald-500)]"
                  >
                    <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.12em] uppercase">
                      <span className="text-[var(--color-text-muted)]">shares</span>
                      <span className="text-[var(--color-emerald-400)] truncate">
                        {h.via.join(', ')}
                      </span>
                    </div>
                    <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5">
                      with {ent?.label ?? other}
                    </div>
                  </div>
                );
              })}
            </div>
          </ReasonSection>
        )}

        {/* Direct edges (the ground truth) */}
        <ReasonSection icon={Pin} tone="ice" label="Direct edges" count={why.directEdges.length}>
          <div className="space-y-0.5">
            {why.directEdges.slice(0, 8).map((e) => {
              const otherId = e.source === entity.id ? e.target : e.source;
              const other = active.graph.entities.find((x) => x.id === otherId);
              return (
                <button
                  key={e.id}
                  onClick={() => selectEntity(otherId)}
                  className="w-full flex items-center gap-2 px-1.5 h-6 text-[11px] hover:bg-[rgba(148,163,184,0.04)] rounded-sm"
                >
                  <span className="font-mono text-[9px] tracking-[0.14em] uppercase text-[var(--color-text-muted)] w-24 truncate">
                    {e.kind.replace('_', ' ')}
                  </span>
                  <span className="text-[var(--color-text-primary)] truncate flex-1">
                    {other?.label ?? otherId}
                  </span>
                  <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
                    {e.confidence.toFixed(2)}
                  </span>
                </button>
              );
            })}
            {why.directEdges.length > 8 && (
              <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] pl-1.5 mt-1">
                + {why.directEdges.length - 8} more
              </div>
            )}
          </div>
        </ReasonSection>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function NoteEditor({
  entityId,
  value,
  onChange,
}: {
  entityId: string;
  value: string;
  onChange: (v: string) => void;
}) {
  void entityId;
  const [expanded, setExpanded] = useState(Boolean(value));
  const hasNote = value.trim().length > 0;
  if (!expanded) {
    return (
      <button
        onClick={() => setExpanded(true)}
        className="w-full px-3 py-1.5 flex items-center gap-2 border-b border-[var(--color-line-soft)] hover:bg-[rgba(34,211,238,0.04)] text-left"
      >
        <NotebookPen className="w-3 h-3 text-[var(--color-text-muted)]" />
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {hasNote ? `note · ${value.split('\n')[0].slice(0, 38)}${value.length > 38 ? '…' : ''}` : 'add analyst note'}
        </span>
      </button>
    );
  }
  return (
    <div className="px-3 py-2 border-b border-[var(--color-line-soft)] bg-[rgba(255,255,255,0.012)]">
      <div className="flex items-center gap-2 mb-1.5">
        <NotebookPen className="w-3 h-3 text-[var(--color-ice-400)]" />
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          analyst note · persisted
        </span>
        <button
          onClick={() => setExpanded(false)}
          className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]"
        >
          collapse
        </button>
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        autoFocus={!hasNote}
        placeholder="why does this matter? what did you find?"
        rows={3}
        className="w-full bg-[rgba(7,9,14,0.55)] border border-[var(--color-line-soft)] rounded-sm px-2 py-1.5 text-[11.5px] text-[var(--color-text-primary)] placeholder:text-[var(--color-text-faint)] outline-none focus:border-[rgba(34,211,238,0.32)] resize-y leading-snug"
      />
      <div className="mt-1 font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-faint)]">
        {hasNote
          ? `saved · ${value.length} chars`
          : 'auto-saves as you type'}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: 'ice' | 'amber' | 'violet';
}) {
  const color =
    accent === 'violet'
      ? 'var(--color-violet-400)'
      : accent === 'amber'
      ? 'var(--color-amber-400)'
      : 'var(--color-ice-400)';
  return (
    <div className="bg-[var(--color-graphite-900)] px-2.5 py-1.5">
      <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
        {label}
      </div>
      <div className="font-mono text-[14px] font-light mt-0.5" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

function ReasonSection({
  icon: Icon,
  tone,
  label,
  count,
  children,
  onFocus,
  focusLabel,
}: {
  icon: typeof CircleDot;
  tone: 'rose' | 'violet' | 'amber' | 'ice' | 'emerald';
  label: string;
  count: number;
  children: React.ReactNode;
  onFocus?: () => void;
  focusLabel?: string;
}) {
  const color = {
    rose: 'var(--color-rose-400)',
    violet: 'var(--color-violet-400)',
    amber: 'var(--color-amber-400)',
    ice: 'var(--color-ice-400)',
    emerald: 'var(--color-emerald-400)',
  }[tone];
  return (
    <section className="px-3 py-2">
      <div className="flex items-center gap-2 mb-1.5">
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[9.5px] tracking-[0.22em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
        <span className="chip text-[9px]">{count}</span>
        {onFocus && (
          <button
            onClick={onFocus}
            className="ml-auto font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]"
          >
            ▸ {focusLabel}
          </button>
        )}
      </div>
      {children}
    </section>
  );
}

/* -------------------------------------------------------------------------- */
/* Plain-language WHY summarizer                                              */
/* -------------------------------------------------------------------------- */

function summarizeWhy(
  label: string,
  why: {
    directEdges: unknown[];
    ringMembership: { name: string }[];
    hiddenLinks: unknown[];
    sharedInfra: unknown[];
    paths: { intent: string }[];
    signals: unknown[];
  }
): string {
  const reasons: string[] = [];
  if (why.ringMembership.length > 0) {
    reasons.push(
      `member of ${why.ringMembership.length} ring${
        why.ringMembership.length === 1 ? '' : 's'
      } (${why.ringMembership[0].name})`
    );
  }
  if (why.hiddenLinks.length > 0) {
    reasons.push(
      `${why.hiddenLinks.length} hidden tie${
        why.hiddenLinks.length === 1 ? '' : 's'
      } via topology`
    );
  }
  if (why.paths.length > 0) {
    const ownership = why.paths.filter((p) => p.intent === 'shortest_path').length;
    const evidence = why.paths.filter((p) => p.intent === 'evidence_chain').length;
    const reverse = why.paths.filter((p) => p.intent === 'reverse_edge').length;
    const parts: string[] = [];
    if (ownership) parts.push(`${ownership} ownership chain`);
    if (evidence) parts.push(`${evidence} money flow`);
    if (reverse) parts.push(`${reverse} reverse-edge`);
    if (parts.length) reasons.push(`on ${parts.join(' + ')}`);
  }
  if (why.sharedInfra.length > 0) {
    reasons.push(
      `${why.sharedInfra.length} shared-infrastructure tie${
        why.sharedInfra.length === 1 ? '' : 's'
      }`
    );
  }
  if (why.signals.length > 0) {
    reasons.push(
      `flagged by ${why.signals.length} structural signal${
        why.signals.length === 1 ? '' : 's'
      }`
    );
  }
  if (reasons.length === 0) {
    return `${label} has no structural reasons surfaced — likely a peripheral entity.`;
  }
  return `${label} is implicated because it is ${reasons.join('; ')}.`;
}
