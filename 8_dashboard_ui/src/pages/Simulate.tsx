import { useNavigate } from 'react-router-dom';
import { useIntelStore } from '@/store/intel-store';
import { PageHeader } from '@/components/layout/PageHeader';
import {
  Beaker,
  CircleDot,
  Eye,
  GitBranch,
  Network,
  Play,
  ShieldAlert,
  Sparkles,
  Spline,
  Swords,
  Target,
} from 'lucide-react';
import { cn, toneClass } from '@/lib/utils';
import type { PresetSnapshot } from '@/types/intel';
import { motion } from 'framer-motion';

/**
 * Simulation Lab — the synthetic environment, reframed.
 *
 * These 8 presets are no longer "demo data" — they're adversarial scenarios
 * that exercise specific fraud topologies. Used for:
 *   • benchmarking GraphRAG vs Vector vs LLM
 *   • topology stress testing
 *   • analyst training
 *   • investigation rehearsal
 */
export function Simulate() {
  const navigate = useNavigate();
  const { presets, selectPreset } = useIntelStore();

  const fixtures: Array<{
    id: string;
    label: string;
    purpose: 'benchmark' | 'training' | 'stress' | 'rehearsal';
  }> = [
    { id: 'shell_cascade', label: 'UBO Concealment',          purpose: 'benchmark' },
    { id: 'card_ring',     label: 'Bust-out Coordination',    purpose: 'training' },
    { id: 'sanctions_evasion', label: 'OFAC Proxy Layering',  purpose: 'benchmark' },
    { id: 'crypto_mixer',  label: 'Mixer Recombination',      purpose: 'stress' },
    { id: 'mule_network',  label: 'Mule Rotation',            purpose: 'rehearsal' },
    { id: 'procurement_fraud', label: 'Bid-rigging Collusion',purpose: 'training' },
    { id: 'insider_leak',  label: 'Tipper–Tippee Chain',      purpose: 'rehearsal' },
    { id: 'dark_adtech',   label: 'Ad-fraud Cluster',         purpose: 'stress' },
  ];

  const launch = (presetId: string) => {
    selectPreset(presetId);
    navigate('/autopilot');
  };
  const benchmark = (presetId: string) => {
    selectPreset(presetId);
    navigate('/benchmark');
  };

  return (
    <div className="fill overflow-y-auto scroll-tactical">
      <div className="absolute top-[56px] inset-x-0 z-10">
        <PageHeader
          icon={Beaker}
          eyebrow="simulation lab"
          title="Adversarial scenarios"
          meta={`${presets.length} fixtures · benchmark + training`}
        />
      </div>

      <div className="px-6 pt-[100px] pb-10 mx-auto" style={{ maxWidth: 1480 }}>
        {/* Intro strip */}
        <div className="surface px-4 py-3 mb-4 flex items-start gap-3">
          <Beaker className="w-4 h-4 text-[var(--color-violet-400)] mt-0.5 shrink-0" />
          <div className="flex-1">
            <h2 className="text-[14px] font-medium text-[var(--color-text-bright)]">
              Run investigations against curated fraud topologies
            </h2>
            <p className="text-[12px] text-[var(--color-text-secondary)] mt-1 leading-relaxed">
              Eight calibrated scenarios cover the dominant fraud structures — UBO concealment, ring coordination, sanctions evasion, mixer obfuscation, mule rotation, bid-rigging, insider tipping, and ad-fraud clusters. Use them to benchmark GraphRAG vs Vector RAG vs Pure LLM, train new analysts, or stress-test mapping changes before pointing the platform at production data.
            </p>
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              <span className="chip chip-ice text-[9px]">
                <Target className="w-2.5 h-2.5" />
                100% structural recall · GraphRAG verified
              </span>
              <span className="chip chip-violet text-[9px]">
                <ShieldAlert className="w-2.5 h-2.5" />
                no PII · synthetic
              </span>
              <span className="chip chip-amber text-[9px]">
                <Sparkles className="w-2.5 h-2.5" />
                deterministic · repeatable
              </span>
            </div>
          </div>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-2 gap-3">
          {presets.map((p, i) => {
            const fixture = fixtures.find((f) => f.id === p.id);
            return (
              <motion.div
                key={p.id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.32, delay: i * 0.04 }}
              >
                <FixtureCard
                  preset={p}
                  purpose={fixture?.purpose ?? 'benchmark'}
                  reframedLabel={fixture?.label}
                  onLaunch={() => launch(p.id)}
                  onBenchmark={() => benchmark(p.id)}
                  onInvestigate={() => {
                    selectPreset(p.id);
                    navigate('/investigate');
                  }}
                />
              </motion.div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

const PURPOSE_META: Record<
  'benchmark' | 'training' | 'stress' | 'rehearsal',
  { label: string; color: string; icon: typeof Beaker }
> = {
  benchmark: {
    label: 'benchmark fixture',
    color: 'var(--color-ice-400)',
    icon: Swords,
  },
  training: {
    label: 'analyst training',
    color: 'var(--color-amber-400)',
    icon: Eye,
  },
  stress: {
    label: 'topology stress',
    color: 'var(--color-violet-400)',
    icon: Network,
  },
  rehearsal: {
    label: 'investigation rehearsal',
    color: 'var(--color-emerald-400)',
    icon: Target,
  },
};

function FixtureCard({
  preset,
  purpose,
  reframedLabel,
  onLaunch,
  onBenchmark,
  onInvestigate,
}: {
  preset: PresetSnapshot;
  purpose: 'benchmark' | 'training' | 'stress' | 'rehearsal';
  reframedLabel?: string;
  onLaunch: () => void;
  onBenchmark: () => void;
  onInvestigate: () => void;
}) {
  const meta = PURPOSE_META[purpose];
  const tone = toneClass(preset.tone);
  const PurposeIcon = meta.icon;
  return (
    <div className="surface overflow-hidden">
      <div className="px-4 py-3 border-b border-[var(--color-line-soft)] flex items-start gap-3">
        <div
          className="w-9 h-9 rounded-sm border inline-flex items-center justify-center shrink-0"
          style={{
            borderColor: meta.color,
            color: meta.color,
            background: `${meta.color}10`,
          }}
        >
          <PurposeIcon className="w-4 h-4" strokeWidth={1.4} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className="font-mono text-[9.5px] tracking-[0.32em] uppercase"
              style={{ color: meta.color }}
            >
              {meta.label}
            </span>
            <span className={cn('chip text-[9px]', tone.text, tone.border)}>
              {preset.id}
            </span>
          </div>
          <h3 className="text-[14px] font-medium text-[var(--color-text-bright)]">
            {reframedLabel ?? preset.label}
          </h3>
          <p className="text-[11.5px] text-[var(--color-text-secondary)] mt-1 leading-relaxed line-clamp-2">
            {preset.description}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-px bg-[var(--color-line-soft)]">
        <Metric
          icon={ShieldAlert}
          label="entities"
          value={preset.graph.entities.length}
          tone="ice"
        />
        <Metric
          icon={GitBranch}
          label="edges"
          value={preset.graph.edges.length}
          tone="amber"
        />
        <Metric
          icon={CircleDot}
          label="rings"
          value={preset.rings.length}
          tone="rose"
        />
        <Metric
          icon={Spline}
          label="hidden"
          value={preset.hidden.length}
          tone="violet"
        />
      </div>

      <div className="px-4 py-2.5 flex items-center gap-2">
        <button
          onClick={onLaunch}
          className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
        >
          <Play className="w-3 h-3" />
          autopilot
        </button>
        <button
          onClick={onInvestigate}
          className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(168,85,247,0.4)] bg-[rgba(168,85,247,0.06)] text-[var(--color-violet-300)] hover:bg-[rgba(168,85,247,0.1)]"
        >
          <Target className="w-3 h-3" />
          investigate
        </button>
        <button
          onClick={onBenchmark}
          className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-secondary)] hover:text-[var(--color-amber-400)] hover:border-[rgba(245,158,11,0.4)] ml-auto"
        >
          <Swords className="w-3 h-3" />
          benchmark
        </button>
      </div>
    </div>
  );
}

function Metric({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Beaker;
  label: string;
  value: number;
  tone: 'ice' | 'amber' | 'rose' | 'violet';
}) {
  const color = {
    ice: 'var(--color-ice-400)',
    amber: 'var(--color-amber-400)',
    rose: 'var(--color-rose-400)',
    violet: 'var(--color-violet-400)',
  }[tone];
  return (
    <div className="bg-[var(--color-graphite-900)] px-3 py-2">
      <div className="flex items-center gap-1.5">
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[9px] tracking-[0.22em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
      </div>
      <div className="font-mono text-[14px] font-light mt-0.5" style={{ color }}>
        {value}
      </div>
    </div>
  );
}
