import { useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntelStore } from '@/store/intel-store';
import { cn, entityGlyph, tierColor } from '@/lib/utils';
import {
  CircleDot,
  Eye,
  Hand,
  Layers,
  Network,
  Sparkles,
  Waves,
} from 'lucide-react';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { GraphLegend } from '@/components/graph/GraphHud';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { TacticalRail } from '@/components/layout/TacticalRail';
import { WorkspaceTabs } from '@/components/layout/WorkspaceTabs';
import type { PresetSnapshot, Ring } from '@/types/intel';

interface RingRow {
  presetId: string;
  presetLabel: string;
  ring: Ring;
}

export function Rings() {
  const navigate = useNavigate();
  const { presets, active, surfacedRings, applyQuery } = useIntelStore();

  const allRings: RingRow[] = useMemo(
    () =>
      presets.flatMap((p) =>
        p.rings.map((ring) => ({ presetId: p.id, presetLabel: p.label, ring }))
      ),
    [presets]
  );

  // Derive selection from store — the rail surfaces rings via applyQuery.
  const selectedRing: RingRow | null = useMemo(() => {
    const sId = Array.from(surfacedRings)[0];
    if (sId) {
      const row = allRings.find((r) => r.ring.id === sId);
      if (row) return row;
    }
    // Default to first ring of active preset
    return allRings.find((r) => r.presetId === active.id) ?? allRings[0] ?? null;
  }, [surfacedRings, allRings, active.id]);

  // Auto-surface the first ring of the active preset on mount so the detail
  // panel is never empty when the user lands here directly.
  useEffect(() => {
    if (surfacedRings.size === 0 && selectedRing) {
      applyQuery({
        focusMode: 'rings',
        surfaceRings: [selectedRing.ring.id],
        discoverEntities: selectedRing.ring.members,
        selectEntityId: selectedRing.ring.members[0],
        narrationLine: `Ring isolated · ${selectedRing.ring.name}`,
      });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="fill overflow-hidden">
      {/* Workspace micro-tabs strip + slim contextual rail */}
      <WorkspaceTabs />
      <TacticalRail defaultTab="rings" />

      {/* Body */}
      <div
        className="absolute top-[96px] inset-x-0 bottom-0"
        style={{
          display: 'grid',
          gridTemplateColumns: '92px minmax(0, 1fr) 380px',
          gap: 6,
          padding: 6,
        }}
      >
        {/* LEFT gutter for the floating rail */}
        <div />

        {/* CENTER — graph */}
        <div className="relative surface overflow-hidden min-h-0">
          <div className="absolute top-0 left-0 right-0 h-7 flex items-center px-3 z-30 bg-[rgba(7,9,14,0.55)] backdrop-blur-sm border-b border-[var(--color-line-soft)]">
            <CircleDot className="w-3 h-3 text-[var(--color-rose-400)]" />
            <span className="heading-tactical ml-2">Ring isolation</span>
            <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              focus mode · rings
            </span>
          </div>
          <div className="absolute top-7 left-0 right-0 bottom-0">
            <GraphCanvas />
            <GraphLegend />
          </div>
        </div>

        {/* RIGHT — ring detail */}
        <div className="surface overflow-y-auto scroll-tactical min-h-0">
          {selectedRing ? (
            <RingDetail
              row={selectedRing}
              preset={presets.find((p) => p.id === selectedRing.presetId)!}
              onEntity={(id) => navigate(`/entity/${id}`)}
              onOpenInWorkspace={() => navigate('/investigate')}
              onAutopilot={() => navigate('/autopilot')}
            />
          ) : (
            <div className="p-4 font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              select a ring to inspect
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function RingDetail({
  row,
  preset,
  onEntity,
  onOpenInWorkspace,
  onAutopilot,
}: {
  row: RingRow;
  preset: PresetSnapshot;
  onEntity: (id: string) => void;
  onOpenInWorkspace: () => void;
  onAutopilot: () => void;
}) {
  const { ring } = row;
  const memberEntities = ring.members
    .map((id) => preset.graph.entities.find((e) => e.id === id))
    .filter((e): e is NonNullable<typeof e> => Boolean(e));

  // Signals contributing to this ring (any signal that mentions a member)
  const contributingSignals = preset.report.structuralSignals.filter((s) =>
    s.contributors.some((c) => ring.members.includes(c))
  );

  // Hidden ties that fall inside the ring
  const innerHidden = preset.hidden.filter(
    (h) => ring.members.includes(h.from) && ring.members.includes(h.to)
  );

  return (
    <div>
      <div className="px-4 pt-4 pb-3 border-b border-[var(--color-line-soft)]">
        <div className="flex items-center gap-2 mb-1">
          <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
            ring · {row.ring.id}
          </span>
          <RiskBadge tier={ring.risk} size="xs" showScore={false} />
        </div>
        <h2 className="text-[16px] font-light tracking-tight text-[var(--color-text-bright)] leading-snug">
          {ring.name}
        </h2>
        <div className="flex flex-wrap items-center gap-1.5 mt-2">
          <span className="chip chip-rose text-[9px]">
            <CircleDot className="w-2.5 h-2.5" />
            {ring.signal.replace('_', ' ')}
          </span>
          <span className="chip text-[9px]">
            <Sparkles className="w-2.5 h-2.5" />
            cohesion {ring.cohesion.toFixed(2)}
          </span>
          <span className="chip text-[9px]">{ring.members.length} members</span>
        </div>
      </div>

      {/* WHY this ring exists */}
      <Section icon={Sparkles} tone="rose" label="Why this ring exists" count={contributingSignals.length + innerHidden.length}>
        <p className="text-[12px] text-[var(--color-text-primary)] leading-snug mb-2">
          The {ring.signal.replace('_', ' ')} signature collapsed {ring.members.length} nominally distinct entities into one operational cluster. Structural cohesion is {ring.cohesion.toFixed(2)}.
        </p>
        {contributingSignals.length > 0 && (
          <div className="space-y-1 mt-2">
            <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
              contributing signals
            </div>
            {contributingSignals.map((s) => (
              <div
                key={s.id}
                className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-ice-500)]"
              >
                <div className="flex items-center gap-2">
                  <Waves className="w-3 h-3 text-[var(--color-ice-400)]" />
                  <span className="text-[11.5px] text-[var(--color-text-primary)]">
                    {s.name}
                  </span>
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
        )}
        {innerHidden.length > 0 && (
          <div className="space-y-1 mt-3">
            <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
              hidden ties within ring
            </div>
            {innerHidden.map((h) => (
              <div
                key={h.id}
                className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-violet-500)]"
              >
                <div className="font-mono text-[10px] tracking-[0.14em] uppercase text-[var(--color-violet-400)]">
                  {h.from} → {h.to}
                </div>
                <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5">
                  {h.reason}
                </div>
              </div>
            ))}
          </div>
        )}
      </Section>

      {/* Ring members */}
      <Section icon={Network} tone="rose" label="Ring members" count={memberEntities.length}>
        <div className="space-y-1">
          {memberEntities.map((e) => (
            <button
              key={e.id}
              onClick={() => onEntity(e.id)}
              className="w-full text-left rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 flex items-center gap-2.5 hover:bg-[rgba(34,211,238,0.04)]"
            >
              <span
                className="inline-flex items-center justify-center w-6 h-6 rounded-sm border text-[11px] shrink-0"
                style={{
                  borderColor: tierColor(e.tier),
                  color: tierColor(e.tier),
                  background: `${tierColor(e.tier)}10`,
                }}
              >
                {entityGlyph(e.kind)}
              </span>
              <div className="flex-1 min-w-0">
                <div className="text-[11.5px] text-[var(--color-text-bright)] truncate">
                  {e.label}
                </div>
                <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                  {e.kind.replace('_', ' ')} · {e.id}
                </div>
              </div>
              <RiskBadge score={e.risk} tier={e.tier} size="xs" />
            </button>
          ))}
        </div>
      </Section>

      {/* Actions */}
      <div className="px-3 pb-4 pt-2 flex flex-col gap-2">
        <button
          onClick={onOpenInWorkspace}
          className="h-8 px-3 inline-flex items-center justify-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(168,85,247,0.4)] bg-[rgba(168,85,247,0.06)] text-[var(--color-violet-300)] hover:bg-[rgba(168,85,247,0.1)]"
        >
          <Hand className="w-3 h-3" />
          open in workstation
        </button>
        <button
          onClick={onAutopilot}
          className="h-8 px-3 inline-flex items-center justify-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
        >
          <Eye className="w-3 h-3" />
          replay in autopilot
        </button>
      </div>
    </div>
  );
}

function Section({
  icon: Icon,
  tone,
  label,
  count,
  children,
}: {
  icon: typeof Layers;
  tone: 'rose' | 'violet' | 'amber' | 'ice' | 'emerald';
  label: string;
  count: number;
  children: React.ReactNode;
}) {
  const color = {
    rose: 'var(--color-rose-400)',
    violet: 'var(--color-violet-400)',
    amber: 'var(--color-amber-400)',
    ice: 'var(--color-ice-400)',
    emerald: 'var(--color-emerald-400)',
  }[tone];
  return (
    <section className="px-3 py-2.5 border-b border-[var(--color-line-soft)] last:border-b-0">
      <div className="flex items-center gap-2 mb-2">
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[9.5px] tracking-[0.22em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
        <span className="chip text-[9px]">{count}</span>
      </div>
      {children}
    </section>
  );
}

