import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useIntelStore } from '@/store/intel-store';
import { cn, entityGlyph, tierColor, toneClass } from '@/lib/utils';
import {
  Activity,
  AlertOctagon,
  ArrowRight,
  BookOpen,
  CircleDot,
  Clock,
  Eye,
  GitBranch,
  Hand,
  Network,
  ShieldAlert,
  Spline,
  Swords,
} from 'lucide-react';
import type { PresetSnapshot, RiskTier } from '@/types/intel';
import { motion } from 'framer-motion';
import { LiveLaunchpad } from '@/components/investigation/LiveLaunchpad';

/**
 * Home / Command Center.
 *
 * Operational front door. Surfaces only investigation-relevant state —
 * no fake telemetry, no equal-priority widget grid.
 *
 *  • Top strip: case counts, total entities under coverage, ring count,
 *    hidden-tie count, critical-tier suspects (across all cases).
 *  • Body row 1: active case banner + quick actions (autopilot / investigate / benchmark)
 *  • Body row 2: investigation queue (every preset is a "case") + critical suspects rail
 */
export function Home() {
  const navigate = useNavigate();
  const { presets, sessions, selectPreset, active } = useIntelStore();

  const stats = useMemo(() => computeStats(presets), [presets]);
  const criticalSuspects = useMemo(() => topSuspects(presets, 8), [presets]);

  return (
    <div className="fill overflow-y-auto scroll-tactical">
      <div className="px-6 pt-16 pb-10 mx-auto" style={{ maxWidth: 1480 }}>
        {/* Header */}
        <div className="flex items-end justify-between mb-5">
          <div>
            <div className="font-mono text-[10px] tracking-[0.4em] uppercase text-[var(--color-text-muted)]">
              command center
            </div>
            <h1 className="text-[26px] font-light tracking-tight text-[var(--color-text-bright)] mt-1">
              Operational overview
            </h1>
          </div>
          <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            <Clock className="w-3 h-3" />
            <span>{new Date().toISOString().slice(0, 19).replace('T', ' ')}</span>
            <span className="text-[var(--color-text-ghost)]">·</span>
            <span className="text-[var(--color-emerald-400)]">analyst.0xA1</span>
          </div>
        </div>

        {/* Thesis pip — judges arriving from the README land here. One
         *  tap to the methodology page so they can verify the framing
         *  before exploring the operational surface. */}
        <button
          onClick={() => navigate('/methodology')}
          className="w-full mb-4 flex items-center gap-4 px-4 py-3 rounded-sm surface text-left hover:bg-[rgba(34,211,238,0.025)] group transition-colors"
        >
          <span
            className="inline-flex items-center justify-center w-8 h-8 rounded-sm shrink-0"
            style={{
              background: 'rgba(34,211,238,0.10)',
              color: 'var(--color-ice-400)',
            }}
          >
            <BookOpen className="w-4 h-4" strokeWidth={1.5} />
          </span>
          <div className="flex-1 min-w-0">
            <div className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
              thesis · methodology · architecture
            </div>
            <div className="text-[13px] text-[var(--color-text-bright)] font-light mt-0.5">
              <span className="text-[var(--color-ice-300)]">Topology is information.</span>{' '}
              See why GraphRAG on TigerGraph beats Vector RAG and LLM-only on
              multi-hop reasoning — measured against annotated ground truth.
            </div>
          </div>
          <ArrowRight className="w-4 h-4 text-[var(--color-text-muted)] group-hover:text-[var(--color-ice-400)] group-hover:translate-x-0.5 transition-all shrink-0" />
        </button>

        {/* Stat strip */}
        <div className="grid grid-cols-5 gap-2 mb-5">
          <Stat
            label="cases"
            value={stats.cases}
            sub={`${stats.activeCase} loaded`}
            icon={Network}
            tone="ice"
          />
          <Stat
            label="entities"
            value={stats.entities}
            sub="under coverage"
            icon={ShieldAlert}
            tone="ice"
          />
          <Stat
            label="rings"
            value={stats.rings}
            sub={`${stats.criticalRings} critical`}
            icon={CircleDot}
            tone="rose"
          />
          <Stat
            label="hidden ties"
            value={stats.hidden}
            sub="surfaced via topology"
            icon={Spline}
            tone="violet"
          />
          <Stat
            label="paths"
            value={stats.paths}
            sub="traversal evidence"
            icon={GitBranch}
            tone="amber"
          />
        </div>

        {/* Active case banner */}
        <ActiveCaseBanner
          preset={active}
          onAutopilot={() => navigate('/autopilot')}
          onInvestigate={() => navigate('/investigate')}
          onBenchmark={() => navigate('/benchmark')}
        />

        {/* Live orchestrator launchpad — silently hidden when backend offline */}
        <LiveLaunchpad />

        {/* Two columns: investigation queue + critical suspects */}
        <div className="grid grid-cols-[minmax(0,1fr)_360px] gap-3 mt-5">
          <section className="surface overflow-hidden">
            <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
              <Activity className="w-3 h-3 text-[var(--color-ice-400)]" />
              <span className="heading-tactical">Investigation queue</span>
              <span className="chip ml-auto">{presets.length}</span>
            </div>
            <div className="divide-y divide-[var(--color-line-soft)]">
              {presets.map((p, i) => {
                const isActive = p.id === active.id;
                const session = sessions.find((s) => s.presetId === p.id);
                return (
                  <button
                    key={p.id}
                    onClick={() => {
                      selectPreset(p.id);
                      navigate('/investigate');
                    }}
                    className={cn(
                      'w-full text-left px-3 py-2.5 flex items-center gap-3 transition-colors',
                      'hover:bg-[rgba(34,211,238,0.04)]',
                      isActive && 'bg-[rgba(34,211,238,0.05)]'
                    )}
                  >
                    <span className="font-mono text-[9.5px] text-[var(--color-text-faint)] w-5">
                      {String(i + 1).padStart(2, '0')}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={cn(
                            'text-[12.5px] font-medium truncate',
                            isActive
                              ? 'text-[var(--color-text-bright)]'
                              : 'text-[var(--color-text-primary)]'
                          )}
                        >
                          {p.label}
                        </span>
                        {isActive && (
                          <span className="chip chip-ice text-[8.5px]">active</span>
                        )}
                        {session && (
                          <span className="chip chip-emerald text-[8.5px]">archived</span>
                        )}
                      </div>
                      <div className="font-mono text-[9.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] mt-0.5 truncate">
                        {p.tags.join(' · ')} · {p.graph.entities.length} entities · {p.rings.length} ring{p.rings.length === 1 ? '' : 's'}
                      </div>
                    </div>
                    <CaseToneChip preset={p} />
                    <RiskGlyph risk={topRisk(p)} />
                  </button>
                );
              })}
            </div>
          </section>

          <section className="surface overflow-hidden">
            <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
              <AlertOctagon className="w-3 h-3 text-[var(--color-rose-400)]" />
              <span className="heading-tactical">Critical suspects</span>
              <span className="chip chip-rose ml-auto">{criticalSuspects.length}</span>
            </div>
            <div className="divide-y divide-[var(--color-line-soft)]">
              {criticalSuspects.map((c) => (
                <button
                  key={`${c.presetId}_${c.entityId}`}
                  onClick={() => {
                    selectPreset(c.presetId);
                    navigate(`/entity/${c.entityId}`);
                  }}
                  className="w-full text-left px-3 py-2.5 flex items-center gap-3 hover:bg-[rgba(244,63,94,0.04)]"
                >
                  <span
                    className="inline-flex items-center justify-center w-6 h-6 rounded-sm border text-[10.5px] shrink-0"
                    style={{
                      borderColor: tierColor(c.tier),
                      color: tierColor(c.tier),
                      background: `${tierColor(c.tier)}10`,
                    }}
                  >
                    {entityGlyph(c.kind)}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11.5px] text-[var(--color-text-bright)] truncate">
                      {c.label}
                    </div>
                    <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] truncate">
                      {c.kind.replace('_', ' ')} · in {c.presetLabel}
                    </div>
                  </div>
                  <span
                    className="font-mono text-[10.5px]"
                    style={{ color: tierColor(c.tier) }}
                  >
                    {c.risk}
                  </span>
                </button>
              ))}
            </div>
          </section>
        </div>

        {/* Recent sessions / footer */}
        {sessions.length > 0 && (
          <section className="surface overflow-hidden mt-5">
            <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
              <Clock className="w-3 h-3 text-[var(--color-text-muted)]" />
              <span className="heading-tactical">Recent investigations</span>
              <span className="chip ml-auto">{sessions.length}</span>
            </div>
            <div className="grid grid-cols-3 divide-x divide-[var(--color-line-soft)]">
              {sessions.slice(0, 3).map((s) => (
                <button
                  key={s.id}
                  onClick={() => navigate('/sessions')}
                  className="px-3 py-2.5 text-left hover:bg-[rgba(148,163,184,0.04)]"
                >
                  <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                    {s.id} · {s.events.length} events
                  </div>
                  <div className="text-[12px] text-[var(--color-text-bright)] mt-0.5 truncate">
                    {s.title}
                  </div>
                  <div className="font-mono text-[9px] text-[var(--color-text-muted)] mt-0.5">
                    {s.analyst} · {s.status}
                  </div>
                </button>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function Stat({
  label,
  value,
  sub,
  icon: Icon,
  tone,
}: {
  label: string;
  value: number;
  sub: string;
  icon: typeof Activity;
  tone: 'ice' | 'rose' | 'violet' | 'amber';
}) {
  const color =
    tone === 'ice'
      ? 'var(--color-ice-400)'
      : tone === 'rose'
      ? 'var(--color-rose-400)'
      : tone === 'violet'
      ? 'var(--color-violet-400)'
      : 'var(--color-amber-400)';
  return (
    <div className="surface px-3 py-2.5">
      <div className="flex items-center gap-1.5">
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[9.5px] tracking-[0.22em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
      </div>
      <div className="font-mono text-[22px] font-light leading-none mt-1.5" style={{ color }}>
        {value}
      </div>
      <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] mt-1">
        {sub}
      </div>
    </div>
  );
}

function ActiveCaseBanner({
  preset,
  onAutopilot,
  onInvestigate,
  onBenchmark,
}: {
  preset: PresetSnapshot;
  onAutopilot: () => void;
  onInvestigate: () => void;
  onBenchmark: () => void;
}) {
  const tone = toneClass(preset.tone);
  return (
    <motion.section
      layoutId="active-case"
      className="surface relative overflow-hidden"
    >
      <div className="fill tactical-grid-fine opacity-30 pointer-events-none" />
      <div className="relative px-5 py-4 flex items-start gap-5">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
              active investigation
            </span>
            <span className={cn('chip text-[9px]', tone.text, tone.border)}>
              {preset.label}
            </span>
            <span className="chip text-[9px]">{preset.id}</span>
          </div>
          <h2 className="text-[18px] font-light tracking-tight text-[var(--color-text-bright)] leading-snug">
            {preset.report.narrative.headline}
          </h2>
          <p className="text-[12px] text-[var(--color-text-secondary)] mt-1.5 leading-relaxed max-w-[820px]">
            {preset.report.narrative.body}
          </p>
          <div className="flex flex-wrap gap-1 mt-2.5">
            {preset.report.narrative.highlights.map((h) => (
              <span key={h} className="chip chip-ice text-[9px]">
                {h}
              </span>
            ))}
          </div>
        </div>
        <div className="flex flex-col gap-2 shrink-0 w-[180px]">
          <button
            onClick={onInvestigate}
            className="h-9 px-3 inline-flex items-center justify-center gap-2 text-[11px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(168,85,247,0.4)] bg-[rgba(168,85,247,0.06)] text-[var(--color-violet-300)] hover:bg-[rgba(168,85,247,0.1)]"
          >
            <Hand className="w-3 h-3" />
            investigate
          </button>
          <button
            onClick={onAutopilot}
            className="h-9 px-3 inline-flex items-center justify-center gap-2 text-[11px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
          >
            <Eye className="w-3 h-3" />
            autopilot
          </button>
          <button
            onClick={onBenchmark}
            className="h-9 px-3 inline-flex items-center justify-center gap-2 text-[11px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:border-[rgba(245,158,11,0.35)] hover:text-[var(--color-amber-400)]"
          >
            <Swords className="w-3 h-3" />
            benchmark
          </button>
        </div>
      </div>
    </motion.section>
  );
}

function CaseToneChip({ preset }: { preset: PresetSnapshot }) {
  const tone = toneClass(preset.tone);
  return (
    <span className={cn('chip text-[8.5px]', tone.text, tone.border)}>
      {preset.tone}
    </span>
  );
}

function RiskGlyph({ risk }: { risk: number }) {
  const color =
    risk >= 80
      ? 'var(--color-rose-400)'
      : risk >= 60
      ? 'var(--color-amber-400)'
      : risk >= 35
      ? 'var(--color-ice-400)'
      : 'var(--color-emerald-400)';
  return (
    <div
      className="font-mono text-[12px] font-light w-8 text-right"
      style={{ color }}
    >
      {risk}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Derivations                                                                */
/* -------------------------------------------------------------------------- */

function computeStats(presets: PresetSnapshot[]) {
  let entities = 0;
  let rings = 0;
  let criticalRings = 0;
  let hidden = 0;
  let paths = 0;
  presets.forEach((p) => {
    entities += p.graph.entities.length;
    rings += p.rings.length;
    criticalRings += p.rings.filter((r) => r.risk === 'critical').length;
    hidden += p.hidden.length;
    paths += p.paths.length;
  });
  return {
    cases: presets.length,
    activeCase: 1,
    entities,
    rings,
    criticalRings,
    hidden,
    paths,
  };
}

function topSuspects(presets: PresetSnapshot[], n: number) {
  const all: Array<{
    presetId: string;
    presetLabel: string;
    entityId: string;
    label: string;
    kind: PresetSnapshot['graph']['entities'][number]['kind'];
    risk: number;
    tier: RiskTier;
  }> = [];
  presets.forEach((p) => {
    p.graph.entities.forEach((e) => {
      if (e.risk >= 70) {
        all.push({
          presetId: p.id,
          presetLabel: p.label,
          entityId: e.id,
          label: e.label,
          kind: e.kind,
          risk: e.risk,
          tier: e.tier,
        });
      }
    });
  });
  return all.sort((a, b) => b.risk - a.risk).slice(0, n);
}

function topRisk(preset: PresetSnapshot): number {
  return Math.max(...preset.graph.entities.map((e) => e.risk), 0);
}
