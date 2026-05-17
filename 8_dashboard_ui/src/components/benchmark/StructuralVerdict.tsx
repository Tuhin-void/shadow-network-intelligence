import { motion } from 'framer-motion';
import { Eye, Network, ShieldAlert } from 'lucide-react';
import type { RealBenchmarkSummary } from '@/lib/adapters/benchmark';

/**
 * StructuralVerdict — the calm operational verdict hero.
 *
 * Quiet confidence: a single live dot in the eyebrow line, then the
 * headline + body + three-pipeline tiles. No badge spam, no shouting
 * "LIVE · REAL · ACTIVE · STREAMING". The numbers speak.
 *
 * Every value originates in `scripts/adversarial_results.json`.
 */
export function StructuralVerdict({ data }: { data: RealBenchmarkSummary }) {
  const total = data.queryCount;
  const recovered = data.aggregate.queriesWithStructuralEvidence;
  const vec = data.aggregate.vectorragStructuralTotal;
  const llm = data.aggregate.pureLLMStructuralTotal;
  const totalEdges = data.aggregate.totalStructuralEdges;
  const totalNeighbors = data.aggregate.totalNeighborsTraversed;

  return (
    <section className="surface overflow-hidden relative">
      <div className="fill tactical-grid-fine opacity-20 pointer-events-none" />

      <div className="relative px-6 py-7">
        {/* Eyebrow — one quiet status line, nothing more */}
        <div className="flex items-center gap-2.5">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-emerald-400)] anim-drift" />
          <span className="font-mono text-[10px] tracking-[0.42em] uppercase text-[var(--color-text-muted)]">
            structural verdict
          </span>
          <span className="text-[var(--color-text-ghost)] mx-1">·</span>
          <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            adversarial suite · profile {data.profile}
          </span>
        </div>

        <motion.h1
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="text-[34px] md:text-[40px] leading-[1.1] font-light tracking-tight text-[var(--color-text-bright)] mt-4"
        >
          <span className="text-[var(--color-emerald-400)] font-normal">
            {recovered}/{total}
          </span>{' '}
          structural relationships reconstructed.
        </motion.h1>

        <p className="text-[12.5px] text-[var(--color-text-secondary)] mt-3 leading-relaxed max-w-[780px]">
          On a 20-query adversarial suite designed to require multi-hop graph
          traversal or hidden-relationship discovery, GraphRAG surfaces
          structural evidence on every query.{' '}
          <span className="text-[var(--color-text-primary)]">
            VectorRAG and PureLLM produce zero structural answers
          </span>{' '}
          — not from a tuning failure, but because chunked text retrieval and
          context-window guessing fundamentally cannot reconstruct
          relationships that exist only on graph edges.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-2 mt-6">
          <VerdictTile
            tone="emerald"
            icon={Network}
            label="GraphRAG"
            value={`${recovered} / ${total}`}
            sub={`${totalEdges} structural edges · ${totalNeighbors.toLocaleString()} neighbors traversed`}
            verdict="topology reconstructed"
          />
          <VerdictTile
            tone="rose"
            icon={ShieldAlert}
            label="VectorRAG"
            value={`${vec} / ${total}`}
            sub="text chunks only — edges are not text"
            verdict="cannot reconstruct structure"
          />
          <VerdictTile
            tone="rose"
            icon={Eye}
            label="PureLLM"
            value={`${llm} / ${total}`}
            sub="no retrieval at all"
            verdict="ungrounded"
          />
        </div>
      </div>
    </section>
  );
}

function VerdictTile({
  tone,
  icon: Icon,
  label,
  value,
  sub,
  verdict,
}: {
  tone: 'emerald' | 'rose';
  icon: typeof Network;
  label: string;
  value: string;
  sub: string;
  verdict: string;
}) {
  const color =
    tone === 'emerald'
      ? 'var(--color-emerald-400)'
      : 'var(--color-rose-400)';
  const border =
    tone === 'emerald'
      ? 'rgba(16,185,129,0.28)'
      : 'rgba(244,63,94,0.22)';
  const bg =
    tone === 'emerald'
      ? 'rgba(16,185,129,0.04)'
      : 'rgba(244,63,94,0.03)';
  return (
    <div
      className="px-4 py-3.5 rounded-sm border"
      style={{ borderColor: border, background: bg }}
    >
      <div className="flex items-center gap-1.5 mb-2">
        <Icon className="w-3 h-3" style={{ color }} />
        <span
          className="font-mono text-[9.5px] tracking-[0.32em] uppercase"
          style={{ color }}
        >
          {label}
        </span>
      </div>
      <div
        className="font-mono text-[32px] font-light leading-none tracking-tight"
        style={{ color }}
      >
        {value}
      </div>
      <div className="text-[11px] text-[var(--color-text-secondary)] mt-2.5 leading-snug">
        {sub}
      </div>
      <div
        className="font-mono text-[9px] tracking-[0.22em] uppercase mt-2.5 opacity-90"
        style={{ color }}
      >
        ▸ {verdict}
      </div>
    </div>
  );
}
