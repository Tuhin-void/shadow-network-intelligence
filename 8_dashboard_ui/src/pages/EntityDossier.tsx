import { useEffect, useMemo } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useIntelStore, getEntityById } from '@/store/intel-store';
import { cn, entityGlyph, tierColor } from '@/lib/utils';
import {
  ArrowLeft,
  CircleDot,
  Crosshair,
  Eye,
  GitBranch,
  Hand,
  Layers,
  Network,
  ShieldAlert,
  Spline,
  Waves,
} from 'lucide-react';
import { RiskBadge } from '@/components/shared/RiskBadge';
import { GraphCanvas } from '@/components/graph/GraphCanvas';
import { GraphLegend } from '@/components/graph/GraphHud';

/**
 * EntityDossier — the entity profile page.
 *
 * Layout:
 *   • Header: identity card (glyph, name, kind, id, risk badge, flags)
 *   • Stat strip: degree, hidden ties, paths on, ring memberships, signals
 *   • Two-column body:
 *       Left  : neighborhood graph (the entity's local topology)
 *       Right : WHY reasoning panel (rings, hidden ties, paths, signals, shared infra, direct edges)
 *   • Actions: open in investigation workspace, open in autopilot, jump to ring
 */
export function EntityDossier() {
  const params = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { active, presets, selectPreset, selectEntity, setFocusMode, applyQuery } =
    useIntelStore();

  // Resolve entity across all presets — if it's not in the active preset, switch presets.
  useEffect(() => {
    if (!params.id) return;
    const localHit = active.graph.entities.find((e) => e.id === params.id);
    if (localHit) {
      selectEntity(params.id);
      return;
    }
    // search other presets
    for (const p of presets) {
      const hit = p.graph.entities.find((e) => e.id === params.id);
      if (hit) {
        selectPreset(p.id);
        selectEntity(params.id);
        return;
      }
    }
    // not found
  }, [params.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const entity = getEntityById(params.id);

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

  /** 2-hop neighborhood around the focused entity, with rings/hidden/paths it touches. */
  const neighborhood = useMemo<Set<string>>(() => {
    if (!entity) return new Set();
    const ids = new Set<string>([entity.id]);
    // 1-hop direct neighbors
    active.graph.edges.forEach((e) => {
      if (e.source === entity.id) ids.add(e.target);
      if (e.target === entity.id) ids.add(e.source);
    });
    // 2-hop expansion
    const hop1 = new Set(ids);
    active.graph.edges.forEach((e) => {
      if (hop1.has(e.source) || hop1.has(e.target)) {
        ids.add(e.source);
        ids.add(e.target);
      }
    });
    // Include ring members the entity is part of
    active.rings.forEach((r) => {
      if (r.members.includes(entity.id)) r.members.forEach((m) => ids.add(m));
    });
    // Include hidden tie via-chains
    active.hidden.forEach((h) => {
      if (h.from === entity.id || h.to === entity.id) {
        ids.add(h.from);
        ids.add(h.to);
        h.via.forEach((v) => ids.add(v));
      }
    });
    // Include paths the entity sits on
    active.paths.forEach((p) => {
      if (p.nodes.includes(entity.id)) p.nodes.forEach((n) => ids.add(n));
    });
    return ids;
  }, [entity, active]);

  if (!entity || !why) {
    return (
      <div className="fill flex flex-col items-center justify-center text-[var(--color-text-muted)]">
        <Network className="w-7 h-7 opacity-50 mb-3" />
        <div className="font-mono text-[10px] tracking-[0.32em] uppercase">
          entity not found
        </div>
        <button
          onClick={() => navigate('/entities')}
          className="mt-4 h-8 px-3 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:border-[rgba(34,211,238,0.4)] hover:text-[var(--color-ice-400)]"
        >
          <ArrowLeft className="w-3 h-3" />
          back to index
        </button>
      </div>
    );
  }

  const reasonCount =
    why.ringMembership.length +
    why.hiddenLinks.length +
    why.paths.length +
    why.signals.length +
    why.sharedInfra.length;

  // The graph canvas reads the active preset state — focus on this entity by
  // applying a quick query transform on mount so the topology is anchored on it.
  useEffect(() => {
    if (!entity) return;
    applyQuery({
      selectEntityId: entity.id,
      focusMode: 'overview',
      narrationLine: `Dossier open · ${entity.label}`,
    });
  }, [entity?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="fill overflow-y-auto scroll-tactical">
      <div className="px-6 pt-16 pb-10 mx-auto" style={{ maxWidth: 1480 }}>
        {/* Breadcrumb */}
        <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.28em] uppercase text-[var(--color-text-muted)] mb-4">
          <button
            onClick={() => navigate('/entities')}
            className="hover:text-[var(--color-ice-400)] flex items-center gap-1.5"
          >
            <ArrowLeft className="w-3 h-3" />
            entities
          </button>
          <span className="text-[var(--color-text-ghost)]">/</span>
          <span className="text-[var(--color-text-secondary)]">{active.label}</span>
          <span className="text-[var(--color-text-ghost)]">/</span>
          <span className="text-[var(--color-text-bright)]">{entity.id}</span>
        </div>

        {/* Identity header */}
        <div className="surface px-5 py-4 mb-3 relative overflow-hidden">
          <div className="fill tactical-grid-fine opacity-30 pointer-events-none" />
          <div className="relative flex items-start gap-4">
            <span
              className="inline-flex items-center justify-center w-12 h-12 rounded-sm border text-[20px] shrink-0"
              style={{
                borderColor: tierColor(entity.tier),
                color: tierColor(entity.tier),
                background: `${tierColor(entity.tier)}12`,
              }}
            >
              {entityGlyph(entity.kind)}
            </span>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
                  entity · {entity.kind.replace('_', ' ')} · {entity.id}
                </span>
              </div>
              <h1 className="text-[22px] font-light tracking-tight text-[var(--color-text-bright)]">
                {entity.label}
              </h1>
              {(entity.flags ?? []).length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {(entity.flags ?? []).map((f) => (
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
            <div className="flex flex-col items-end gap-2">
              <RiskBadge score={entity.risk} tier={entity.tier} size="md" />
              <button
                onClick={() => navigate('/investigate')}
                className="h-8 px-3 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(168,85,247,0.4)] bg-[rgba(168,85,247,0.06)] text-[var(--color-violet-300)] hover:bg-[rgba(168,85,247,0.1)]"
              >
                <Hand className="w-3 h-3" />
                open in workspace
              </button>
              <button
                onClick={() => navigate('/autopilot')}
                className="h-8 px-3 inline-flex items-center gap-2 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
              >
                <Eye className="w-3 h-3" />
                replay autopilot
              </button>
            </div>
          </div>
        </div>

        {/* Stat strip */}
        <div className="grid grid-cols-5 gap-2 mb-3">
          <Stat
            icon={Network}
            label="degree"
            value={why.directEdges.length}
            sub="direct edges"
            tone="ice"
          />
          <Stat
            icon={Spline}
            label="hidden"
            value={why.hiddenLinks.length}
            sub="topology ties"
            tone="violet"
          />
          <Stat
            icon={GitBranch}
            label="paths"
            value={why.paths.length}
            sub="on traversal"
            tone="amber"
          />
          <Stat
            icon={CircleDot}
            label="rings"
            value={why.ringMembership.length}
            sub="memberships"
            tone="rose"
          />
          <Stat
            icon={Waves}
            label="signals"
            value={why.signals.length}
            sub="structural"
            tone="ice"
          />
        </div>

        {/* WHY summary */}
        <div className="surface px-4 py-3 mb-3 border-l-2 border-[var(--color-rose-500)]">
          <div className="flex items-center gap-2 mb-1">
            <Crosshair className="w-3 h-3 text-[var(--color-rose-400)]" />
            <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-rose-400)]">
              why flagged
            </span>
            <span className="chip ml-auto text-[9px]">{reasonCount} reasons</span>
          </div>
          <p className="text-[13px] text-[var(--color-text-bright)] leading-snug">
            {summarizeWhy(entity.label, why)}
          </p>
        </div>

        {/* Two columns: neighborhood graph + reasoning */}
        <div
          className="grid gap-3 items-stretch"
          style={{ gridTemplateColumns: 'minmax(0, 1fr) 420px', minHeight: 520 }}
        >
          {/* Neighborhood graph */}
          <div className="surface relative overflow-hidden">
            <div className="absolute top-0 left-0 right-0 h-7 flex items-center px-3 z-30 bg-[rgba(7,9,14,0.55)] backdrop-blur-sm border-b border-[var(--color-line-soft)]">
              <Network className="w-3 h-3 text-[var(--color-ice-400)]" />
              <span className="heading-tactical ml-2">Local topology</span>
              <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                entity anchor · {entity.id}
              </span>
            </div>
            <div className="absolute top-7 left-0 right-0 bottom-0">
              <GraphCanvas neighborhood={neighborhood} />
              <GraphLegend />
            </div>
          </div>

          {/* Reasoning panel */}
          <div className="surface overflow-y-auto scroll-tactical">
            <div className="px-3 h-7 flex items-center border-b border-[var(--color-line-soft)] sticky top-0 z-10 bg-[rgba(7,9,14,0.92)] backdrop-blur-md">
              <span className="heading-tactical">Reasoning</span>
              <span className="ml-auto chip text-[9px]">{reasonCount}</span>
            </div>
            <div className="divide-y divide-[var(--color-line-soft)]">
              {why.ringMembership.length > 0 && (
                <Section
                  icon={CircleDot}
                  tone="rose"
                  label="Ring memberships"
                  count={why.ringMembership.length}
                  onFocus={() => setFocusMode('rings')}
                  focusLabel="ring mode"
                >
                  {why.ringMembership.map((r) => (
                    <div
                      key={r.id}
                      className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-rose-500)] mb-1"
                    >
                      <div className="text-[11.5px] text-[var(--color-text-primary)]">{r.name}</div>
                      <div className="mt-0.5 font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
                        cohesion {r.cohesion.toFixed(2)} · {r.signal.replace('_', ' ')} · {r.members.length} members
                      </div>
                    </div>
                  ))}
                </Section>
              )}
              {why.hiddenLinks.length > 0 && (
                <Section
                  icon={Spline}
                  tone="violet"
                  label="Hidden ties via topology"
                  count={why.hiddenLinks.length}
                  onFocus={() => setFocusMode('hidden')}
                  focusLabel="hidden mode"
                >
                  {why.hiddenLinks.map((h) => {
                    const other = h.from === entity.id ? h.to : h.from;
                    const ent = active.graph.entities.find((e) => e.id === other);
                    return (
                      <button
                        key={h.id}
                        onClick={() => navigate(`/entity/${other}`)}
                        className="w-full text-left rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-violet-500)] hover:bg-[rgba(168,85,247,0.06)] mb-1"
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
                      </button>
                    );
                  })}
                </Section>
              )}
              {why.paths.length > 0 && (
                <Section
                  icon={GitBranch}
                  tone="amber"
                  label="Paths it sits on"
                  count={why.paths.length}
                  onFocus={() => setFocusMode('paths')}
                  focusLabel="path mode"
                >
                  {why.paths.map((p) => (
                    <div
                      key={p.id}
                      className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-amber-500)] mb-1"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[11.5px] text-[var(--color-text-primary)]">
                          {p.label}
                        </span>
                        <span className="ml-auto font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
                          {p.hops} hops · {p.intent.replace('_', ' ')}
                        </span>
                      </div>
                      <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5">
                        {p.why}
                      </div>
                    </div>
                  ))}
                </Section>
              )}
              {why.signals.length > 0 && (
                <Section
                  icon={Waves}
                  tone="ice"
                  label="Signals naming this entity"
                  count={why.signals.length}
                >
                  {why.signals.map((s) => (
                    <div
                      key={s.id}
                      className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-ice-500)] mb-1"
                    >
                      <div className="flex items-center gap-2">
                        <span className="text-[11.5px] text-[var(--color-text-primary)]">{s.name}</span>
                        <span className="ml-auto font-mono text-[10px] text-[var(--color-ice-400)]">
                          {s.intensity.toFixed(2)}
                        </span>
                      </div>
                      <div className="text-[10.5px] text-[var(--color-text-secondary)] mt-0.5">
                        {s.description}
                      </div>
                    </div>
                  ))}
                </Section>
              )}
              {why.sharedInfra.length > 0 && (
                <Section
                  icon={Layers}
                  tone="emerald"
                  label="Shared infrastructure"
                  count={why.sharedInfra.length}
                >
                  {why.sharedInfra.map((h) => {
                    const other = h.from === entity.id ? h.to : h.from;
                    const ent = active.graph.entities.find((e) => e.id === other);
                    return (
                      <div
                        key={h.id}
                        className="rounded-sm bg-[rgba(255,255,255,0.012)] px-2 py-1.5 border-l-2 border-[var(--color-emerald-500)] mb-1"
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
                </Section>
              )}
              <Section
                icon={Network}
                tone="ice"
                label="Direct edges"
                count={why.directEdges.length}
              >
                {why.directEdges.slice(0, 14).map((e) => {
                  const otherId = e.source === entity.id ? e.target : e.source;
                  const other = active.graph.entities.find((x) => x.id === otherId);
                  return (
                    <button
                      key={e.id}
                      onClick={() => navigate(`/entity/${otherId}`)}
                      className="w-full flex items-center gap-2 px-1.5 h-6 text-[11px] hover:bg-[rgba(148,163,184,0.04)] rounded-sm"
                    >
                      <span className="font-mono text-[9px] tracking-[0.14em] uppercase text-[var(--color-text-muted)] w-24 truncate">
                        {e.kind.replace('_', ' ')}
                      </span>
                      <span className="text-[var(--color-text-primary)] truncate flex-1 text-left">
                        {other?.label ?? otherId}
                      </span>
                      <span className="font-mono text-[9px] text-[var(--color-text-muted)]">
                        {e.confidence.toFixed(2)}
                      </span>
                    </button>
                  );
                })}
              </Section>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function Stat({
  icon: Icon,
  label,
  value,
  sub,
  tone,
}: {
  icon: typeof Network;
  label: string;
  value: number;
  sub: string;
  tone: 'ice' | 'violet' | 'amber' | 'rose';
}) {
  const color = {
    ice: 'var(--color-ice-400)',
    violet: 'var(--color-violet-400)',
    amber: 'var(--color-amber-400)',
    rose: 'var(--color-rose-400)',
  }[tone];
  return (
    <div className="surface px-3 py-2">
      <div className="flex items-center gap-1.5">
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[9.5px] tracking-[0.22em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
      </div>
      <div className="font-mono text-[19px] font-light leading-none mt-1.5" style={{ color }}>
        {value}
      </div>
      <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] mt-1">
        {sub}
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
  onFocus,
  focusLabel,
}: {
  icon: typeof Network;
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
    <section className="px-3 py-2.5">
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
      `member of ${why.ringMembership.length} ring${why.ringMembership.length === 1 ? '' : 's'} (${why.ringMembership[0].name})`
    );
  }
  if (why.hiddenLinks.length > 0) {
    reasons.push(
      `${why.hiddenLinks.length} hidden tie${why.hiddenLinks.length === 1 ? '' : 's'} via topology`
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
      `${why.sharedInfra.length} shared-infrastructure tie${why.sharedInfra.length === 1 ? '' : 's'}`
    );
  }
  if (why.signals.length > 0) {
    reasons.push(
      `flagged by ${why.signals.length} structural signal${why.signals.length === 1 ? '' : 's'}`
    );
  }
  if (reasons.length === 0) {
    return `${label} has no structural reasons surfaced — likely a peripheral entity.`;
  }
  return `${label} is implicated because it is ${reasons.join('; ')}.`;
}
