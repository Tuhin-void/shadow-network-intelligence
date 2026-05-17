import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Coins,
  Database,
  Gavel,
  GitBranch,
  Info,
  Network,
  Scale,
  ShieldAlert,
  Sparkles,
  Target,
  Timer,
} from 'lucide-react';
import { api } from '@/lib/api-client';
import {
  transformQuantitativeBenchmark,
  type PipelineAggregate,
  type PipelineKey,
  type QuantitativeBenchmark,
} from '@/lib/adapters/benchmark';
import { cn } from '@/lib/utils';

/**
 * QuantitativeComparison — premium side-by-side 3-pipeline matrix.
 *
 * Reads /api/v1/benchmark/quantitative which projects the latest 3-pipeline
 * benchmark run JSON. Every value originates in:
 *   • 2_baseline_systems/outputs/benchmark_results/benchmark_RUN_*.json
 *   • scripts/adversarial_results.json (structural-recovery cross-reference)
 *
 * No metric is synthesized. The LLM-latency component is the mock-LLM
 * placeholder (transparently disclosed) — operational latency is presented
 * via `avgRetrievalMs` which is REAL.
 */
export function QuantitativeComparison({ reloadToken = 0 }: { reloadToken?: number } = {}) {
  const [data, setData] = useState<QuantitativeBenchmark | null>(null);
  const [phase, setPhase] = useState<'loading' | 'ready' | 'error'>('loading');
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setPhase('loading');
        const raw = await api.getQuantitativeBenchmark();
        if (cancelled) return;
        setData(transformQuantitativeBenchmark(raw));
        setPhase('ready');
      } catch (e) {
        if (cancelled) return;
        setErr(e instanceof Error ? e.message : String(e));
        setPhase('error');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadToken]);

  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Scale className="w-3 h-3 text-[var(--color-text-muted)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          quantitative comparison
        </span>
        <span className="text-[var(--color-text-ghost)] mx-1">·</span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          side-by-side · real measurements
        </span>
        {data && (
          <span className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            profile {data.profile} · run {data.runId.slice(-12)}
          </span>
        )}
      </div>

      {phase === 'loading' && (
        <div className="px-4 py-6 font-mono text-[10.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          loading quantitative artifacts …
        </div>
      )}

      {phase === 'error' && (
        <div className="px-4 py-3">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-amber-400)]" />
            <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-amber-400)]">
              quantitative artifact not present
            </span>
          </div>
          {err && (
            <div className="font-mono text-[10px] text-[var(--color-text-secondary)] mb-3 break-all leading-snug">
              {err.slice(0, 360)}
            </div>
          )}
          <div className="panel-soft p-2">
            <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] mb-1">
              generate locally
            </div>
            <code className="font-mono text-[10.5px] text-[var(--color-ice-300)] block break-all">
              python -m 2_baseline_systems benchmark --profile small --limit 5 \
                --approaches pure_llm vector_rag graph_rag \
                --embedder mock --llm mock \
                --vector-provider chroma --graph-provider tigergraph
            </code>
          </div>
        </div>
      )}

      {data && <Body data={data} />}
    </section>
  );
}

/* -------------------------------------------------------------------------- */

const PIPELINE_LABEL: Record<PipelineKey, string> = {
  pure_llm: 'PureLLM',
  vector_rag: 'VectorRAG',
  graph_rag: 'GraphRAG',
};

const PIPELINE_TONE: Record<PipelineKey, 'emerald' | 'rose' | 'amber'> = {
  graph_rag: 'emerald',
  vector_rag: 'amber',
  pure_llm: 'rose',
};

function Body({ data }: { data: QuantitativeBenchmark }) {
  // Order pipelines as PureLLM → VectorRAG → GraphRAG so the eye walks left-to-right
  // from "no retrieval" to "structural retrieval".
  const order: PipelineKey[] = ['pure_llm', 'vector_rag', 'graph_rag'];
  const byKey: Record<string, PipelineAggregate> = Object.fromEntries(
    data.pipelines.map((p) => [p.approach, p]),
  );

  const struct = data.structural;
  const totalQ = struct?.queries ?? 0;

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-3 divide-x divide-y divide-[var(--color-line-soft)]">
        {order.map((k) => {
          const p = byKey[k];
          if (!p) {
            return <NoData key={k} approach={k} />;
          }
          const structuralRecovery =
            struct
              ? k === 'graph_rag'
                ? struct.graphRag
                : k === 'vector_rag'
                ? struct.vectorRag
                : struct.pureLLM
              : null;
          return (
            <PipelineCard
              key={k}
              approach={k}
              data={p}
              structuralRecovery={structuralRecovery}
              structuralTotal={totalQ}
            />
          );
        })}
      </div>

      {/* Why GraphRAG wins quantitatively — short structural reasoning footer */}
      <div className="border-t border-[var(--color-line-soft)] px-4 py-3 bg-[rgba(7,9,14,0.4)]">
        <div className="flex items-center gap-2 mb-2">
          <Info className="w-3 h-3 text-[var(--color-emerald-400)]" />
          <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-emerald-400)]">
            why graphRAG measures lower context cost
          </span>
        </div>
        <ul className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed space-y-1 list-none pl-0">
          <li>
            <span className="text-[var(--color-emerald-400)]">▸</span> Typed-edge
            traversal returns the structural answer directly — a compact
            edge-set instead of a chunk-set.
          </li>
          <li>
            <span className="text-[var(--color-emerald-400)]">▸</span> Topology-aware
            reranking constrains the context to entities that actually
            participate in the answer, not similar text.
          </li>
          <li>
            <span className="text-[var(--color-emerald-400)]">▸</span> The cost
            of multi-hop traversal lives in retrieval latency (visible above),
            but the LLM call is dramatically smaller — fewer irrelevant
            chunks, cleaner reasoning surface.
          </li>
        </ul>
      </div>

      {/* Honest disclosure — what's real, what's mock */}
      <div className="border-t border-[var(--color-line-soft)] px-4 py-2 font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] flex items-center gap-2 flex-wrap">
        <span className="w-1 h-1 rounded-full bg-[var(--color-amber-400)]" />
        <span className="text-[var(--color-amber-400)]">disclosure:</span>
        <span>LLM call latency = mock 50ms placeholder · retrieval ms is real · token counts are real · sources real</span>
      </div>
    </>
  );
}

/* -------------------------------------------------------------------------- */

function NoData({ approach }: { approach: PipelineKey }) {
  return (
    <div className="px-4 py-4 font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
      no data · {PIPELINE_LABEL[approach]}
    </div>
  );
}

function PipelineCard({
  approach,
  data,
  structuralRecovery,
  structuralTotal,
}: {
  approach: PipelineKey;
  data: PipelineAggregate;
  structuralRecovery: number | null;
  structuralTotal: number;
}) {
  const tone = PIPELINE_TONE[approach];
  const color = toneColor(tone);
  const border = toneBorder(tone);

  return (
    <div className="px-4 py-4 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{ background: color }}
        />
        <span
          className="font-mono text-[10.5px] tracking-[0.32em] uppercase"
          style={{ color }}
        >
          {PIPELINE_LABEL[approach]}
        </span>
        <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {data.queries} q
        </span>
      </div>

      {/* Structural recovery — the headline number */}
      {structuralRecovery != null && (
        <div className="panel-soft p-2.5 rounded-sm" style={{ borderLeft: `2px solid ${border}` }}>
          <div className="flex items-center gap-1.5">
            <Network className="w-3 h-3" style={{ color }} />
            <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              structural recovery
            </span>
            <span className="ml-auto font-mono text-[10px] text-[var(--color-text-muted)]">
              adversarial suite
            </span>
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span
              className="font-mono text-[24px] font-light leading-none tracking-tight"
              style={{ color }}
            >
              {structuralRecovery} / {structuralTotal}
            </span>
            {structuralRecovery > 0 ? (
              <CheckCircle2 className="w-3 h-3" style={{ color }} />
            ) : (
              <ShieldAlert className="w-3 h-3" style={{ color }} />
            )}
          </div>
          <p className="text-[10px] text-[var(--color-text-secondary)] mt-1.5 leading-snug">
            queries whose answer required real graph edges as evidence
          </p>
        </div>
      )}

      <MetricRow
        icon={Coins}
        color={color}
        label="avg tokens"
        value={data.avgTotalTokens.toFixed(0)}
        sub={`prompt ${data.avgPromptTokens.toFixed(0)} + completion ${data.avgCompletionTokens.toFixed(0)}`}
        hint="context size sent to the LLM per query"
      />

      <MetricRow
        icon={Timer}
        color={color}
        label="avg retrieval"
        value={formatMs(data.avgRetrievalMs)}
        sub="real cost · LLM call excluded"
        hint="actual retrieval cost measured end-to-end"
      />

      <MetricRow
        icon={GitBranch}
        color={color}
        label="avg sources"
        value={data.avgSourcesRetrieved.toFixed(1)}
        sub={
          approach === 'graph_rag'
            ? 'focused structural answer'
            : approach === 'vector_rag'
            ? 'chunk-based retrieval'
            : 'no retrieval'
        }
        hint="items returned per query"
      />

      {/* Token-reduction bar — informational, comparing to heaviest pipeline */}
      {data.avgTotalTokens > 0 && (
        <div>
          <div className="flex items-center justify-between mb-1">
            <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              token reduction vs heaviest
            </span>
            <span className="font-mono text-[11px]" style={{ color }}>
              {Math.round(data.tokenReductionVsHeaviest * 100)}%
            </span>
          </div>
          <div className="h-[3px] rounded-full bg-[var(--color-graphite-800)] overflow-hidden">
            <div
              className="h-full rounded-full"
              style={{
                width: `${Math.round(Math.max(0, Math.min(1, data.tokenReductionVsHeaviest)) * 100)}%`,
                background: color,
                opacity: 0.85,
              }}
            />
          </div>
        </div>
      )}

      {/* Real cost when the run had a priced model. */}
      {data.avgCost > 0 && (
        <MetricRow
          icon={Coins}
          color={color}
          label="cost / query"
          value={`$${data.avgCost.toFixed(6)}`}
          sub={`total $${data.totalCost.toFixed(4)} · TokenTracker pricing`}
          hint="real $ estimate using the TokenTracker pricing table"
        />
      )}

      {/* Scoring block — only when the run included evaluations. */}
      {data.scoring && (
        <div className="pt-2 mt-1 border-t border-[var(--color-line-soft)] space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Gavel className="w-3 h-3" style={{ color }} />
            <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              scored · {data.scoring.nEvaluated} q
            </span>
          </div>
          <ScoreRow
            label="judge overall"
            value={`${data.scoring.judgeOverall.toFixed(2)} / 5`}
            color={color}
            hint="avg LLM-judge overall score across all evaluated queries"
          />
          <ScoreRow
            label="judge pass"
            value={`${Math.round(data.scoring.judgePassRate * 100)}%`}
            color={color}
            hint="fraction of queries where the judge scored overall ≥ 4/5"
          />
          <ScoreRow
            label="hallu resist"
            value={`${Math.round(data.scoring.hallucinationResistanceRate * 100)}%`}
            color={color}
            hint="fraction of queries where the judge scored hallucination ≥ 4/5"
          />
          <ScoreRow
            label="entity F1"
            value={data.scoring.entityF1.toFixed(3)}
            color={color}
            hint="regex-extracted entity IDs vs ground-truth entity set"
          />
          <ScoreRow
            label="entity recall"
            value={data.scoring.entityRecall.toFixed(3)}
            color={color}
            hint="how many ground-truth entities the answer surfaces"
          />
          <ScoreRow
            label="semantic"
            value={data.scoring.semanticScore.toFixed(3)}
            color={color}
            hint="cosine / BERTScore similarity between answer and ground-truth reference"
          />
          {Object.entries(data.scoring.failureCounts).length > 0 && (
            <div className="flex flex-wrap gap-1 pt-1">
              {Object.entries(data.scoring.failureCounts).map(([k, v]) => (
                <span
                  key={k}
                  className="chip text-[8.5px] border-[rgba(244,63,94,0.32)] text-[var(--color-rose-300)]"
                  title={`${v} queries flagged: ${k.replace(/_/g, ' ')}`}
                >
                  {k.replace(/_/g, '·')} {v}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ScoreRow({
  label,
  value,
  color,
  hint,
}: {
  label: string;
  value: string;
  color: string;
  hint: string;
}) {
  return (
    <div className="flex items-baseline gap-2" title={hint}>
      <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
        {label}
      </span>
      <span className="ml-auto font-mono text-[11px] font-light tracking-tight" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function MetricRow({
  icon: Icon,
  color,
  label,
  value,
  sub,
  hint,
}: {
  icon: typeof Database;
  color: string;
  label: string;
  value: string;
  sub: string;
  hint: string;
}) {
  return (
    <div className="flex items-start gap-2.5 group" title={hint}>
      <Icon className="w-3 h-3 mt-0.5 shrink-0" style={{ color }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            {label}
          </span>
          <span className="ml-auto font-mono text-[13px] font-light tracking-tight" style={{ color }}>
            {value}
          </span>
        </div>
        <div className="font-mono text-[9px] text-[var(--color-text-muted)] mt-0.5">
          {sub}
        </div>
      </div>
    </div>
  );
}

function formatMs(ms: number): string {
  if (ms < 1) return `0 ms`;
  if (ms < 1000) return `${ms.toFixed(0)} ms`;
  return `${(ms / 1000).toFixed(2)} s`;
}

function toneColor(tone: 'emerald' | 'rose' | 'amber'): string {
  switch (tone) {
    case 'emerald':
      return 'var(--color-emerald-400)';
    case 'rose':
      return 'var(--color-rose-400)';
    case 'amber':
      return 'var(--color-amber-400)';
  }
}

function toneBorder(tone: 'emerald' | 'rose' | 'amber'): string {
  switch (tone) {
    case 'emerald':
      return 'rgba(16,185,129,0.35)';
    case 'rose':
      return 'rgba(244,63,94,0.32)';
    case 'amber':
      return 'rgba(245,158,11,0.32)';
  }
}

export default QuantitativeComparison;
