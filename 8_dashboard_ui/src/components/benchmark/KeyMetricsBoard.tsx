import {
  Compass,
  GitFork,
  Layers,
  Network,
  RotateCcw,
  ScrollText,
  Timer,
} from 'lucide-react';
import type {
  RealBenchmarkBundle,
  RealBenchmarkSummary,
  RealReliability,
} from '@/lib/adapters/benchmark';

/**
 * KeyMetricsBoard — the high-signal metrics layer.
 *
 * Six metrics, each derived from the real adversarial JSON, each paired
 * with a one-line "what this measures" hint so a non-technical reviewer
 * can read the page without referencing methodology.
 *
 * No spreadsheet dump. No fabrication. Hints describe what the metric
 * captures structurally, not marketing claims.
 */
export function KeyMetricsBoard({ bundle }: { bundle: RealBenchmarkBundle }) {
  const adv = bundle.adversarial;
  const rel = bundle.reliability;
  if (!adv) return null;

  const cards = computeCards(adv, rel);

  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          key signals
        </span>
        <span className="text-[var(--color-text-ghost)] mx-1">·</span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          what each measure captures
        </span>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 divide-x divide-y divide-[var(--color-line-soft)]">
        {cards.map((c) => (
          <MetricCard key={c.id} card={c} />
        ))}
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */

interface Card {
  id: string;
  icon: typeof Network;
  label: string;
  value: string;
  ratio?: number | null;          // 0..1 — drives the fill bar
  unit?: string;
  hint: string;
  tone: 'emerald' | 'ice' | 'amber' | 'rose' | 'muted';
}

function computeCards(adv: RealBenchmarkSummary, rel: RealReliability | null): Card[] {
  const rec = adv.aggregate.queriesWithStructuralEvidence;
  const total = adv.queryCount;
  const recoveryRate = total > 0 ? rec / total : 0;

  // Hidden-ring reconstruction: count queries whose `ring_touch_sum > 0`
  const ringQueries = adv.rows.filter((r) => r.graphrag.ringTouch > 0).length;

  // Multi-hop success: queries whose neighbors traversed >= 100 (heuristic
  // for "actually walked the graph", not just touched one vertex). Pure
  // projection of the recorded neighbors count.
  const multiHopQueries = adv.rows.filter((r) => r.graphrag.neighbors >= 100).length;

  // Topology continuity: average distinct structural edge-types per query
  const distinctEdgeAvg =
    adv.rows.length > 0
      ? adv.rows.reduce((s, r) => s + (r.graphrag.edgeTypes?.length ?? 0), 0) /
        adv.rows.length
      : 0;

  // Latency: mean recorded ms
  const meanLatencyMs = adv.aggregate.avgLatencyMs || 0;

  // Reproducibility: from reliability artifact
  const reliabilityStable = rel
    ? rel.structuralDrift === 0 && rel.emptyAnswers === 0
    : false;

  return [
    {
      id: 'recovery',
      icon: Network,
      label: 'structural recovery',
      value: `${rec} / ${total}`,
      ratio: recoveryRate,
      hint:
        'How many queries returned at least one real graph edge as evidence — i.e. the answer was reconstructed from topology, not guessed.',
      tone: 'emerald',
    },
    {
      id: 'ring',
      icon: Layers,
      label: 'hidden ring reconstruction',
      value: `${ringQueries} / ${total}`,
      ratio: ringQueries / Math.max(1, total),
      hint:
        'Queries where GraphRAG surfaced ring-membership ties via reverse-edge traversal — the ring is the answer.',
      tone: 'emerald',
    },
    {
      id: 'multihop',
      icon: GitFork,
      label: 'multi-hop traversal',
      value: `${multiHopQueries} / ${total}`,
      ratio: multiHopQueries / Math.max(1, total),
      hint:
        'Queries that walked 100+ graph neighbors. Captures whether retrieval went beyond a single-hop lookup.',
      tone: 'ice',
    },
    {
      id: 'continuity',
      icon: Compass,
      label: 'topology continuity',
      value: distinctEdgeAvg.toFixed(1),
      unit: 'edge types / query',
      ratio: Math.min(1, distinctEdgeAvg / 4),
      hint:
        'Mean number of distinct structural edge types appearing in each answer — high values mean the topology stayed connected end-to-end.',
      tone: 'ice',
    },
    {
      id: 'latency',
      icon: Timer,
      label: 'mean traversal latency',
      value: formatLatency(meanLatencyMs),
      hint:
        'Real cold-cache traversal cost on the live TigerGraph instance. Warm cache returns sub-second.',
      tone: 'amber',
    },
    {
      id: 'reproducibility',
      icon: RotateCcw,
      label: 'reproducibility',
      value: rel
        ? reliabilityStable
          ? 'stable'
          : rel.verdict.toLowerCase()
        : '—',
      ratio: rel ? (reliabilityStable ? 1 : 0.5) : null,
      hint: rel
        ? `${rel.queriesRun} queries × ${rel.trialsPerQuery} trials · ${rel.structuralDrift} structural drift · ${rel.emptyAnswers} empty answers.`
        : 'Reliability artifact not generated yet (run scripts/benchmark_reliability.py).',
      tone: reliabilityStable ? 'emerald' : 'muted',
    },
  ];
}

function formatLatency(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

/* -------------------------------------------------------------------------- */

function MetricCard({ card }: { card: Card }) {
  const color = toneColor(card.tone);
  return (
    <div className="px-4 py-3.5">
      <div className="flex items-center gap-2">
        <card.icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[9.5px] tracking-[0.28em] uppercase"
          style={{ color }}
        >
          {card.label}
        </span>
      </div>
      <div className="flex items-baseline gap-2 mt-2.5">
        <span
          className="font-mono text-[22px] font-light leading-none tracking-tight"
          style={{ color }}
        >
          {card.value}
        </span>
        {card.unit && (
          <span className="font-mono text-[10px] text-[var(--color-text-muted)] tracking-tight">
            {card.unit}
          </span>
        )}
      </div>
      {card.ratio != null && (
        <div className="h-[3px] mt-3 rounded-full bg-[var(--color-graphite-800)] overflow-hidden">
          <div
            className="h-full rounded-full transition-all"
            style={{
              width: `${Math.round(Math.max(0, Math.min(1, card.ratio)) * 100)}%`,
              background: color,
              opacity: 0.85,
            }}
          />
        </div>
      )}
      <p className="text-[10.5px] text-[var(--color-text-secondary)] leading-snug mt-3">
        {card.hint}
      </p>
    </div>
  );
}

function toneColor(tone: Card['tone']): string {
  switch (tone) {
    case 'emerald':
      return 'var(--color-emerald-400)';
    case 'ice':
      return 'var(--color-ice-400)';
    case 'amber':
      return 'var(--color-amber-400)';
    case 'rose':
      return 'var(--color-rose-400)';
    case 'muted':
      return 'var(--color-text-secondary)';
  }
}
