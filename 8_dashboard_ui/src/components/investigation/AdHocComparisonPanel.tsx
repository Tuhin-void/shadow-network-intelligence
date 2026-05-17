import { useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  Coins,
  Cpu,
  GitBranch,
  Info,
  Loader2,
  Play,
  Scale,
  Timer,
} from 'lucide-react';
import { api, type BackendBenchmarkRunResult, type BackendPipelineAggregate } from '@/lib/api-client';
import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';

/**
 * AdHocComparisonPanel — runs the analyst's CURRENT investigation query
 * through all three pipelines (PureLLM / VectorRAG / GraphRAG) on demand
 * and surfaces the operational comparison.
 *
 * Hard contracts:
 *   • Same backend code path as the batch benchmark — every number is
 *     directly comparable. No synthesized metrics.
 *   • No ground truth: scoring is OFF by default. The toggle exists so a
 *     reviewer can ask for partial signal (judge + semantic against the
 *     question text itself), but the UI honestly labels it.
 *   • Triggered ONLY by the analyst clicking "run comparison" — never
 *     auto-fires, never re-runs the live investigation behind their back.
 */
type Phase = 'idle' | 'running' | 'ready' | 'error' | 'busy';

export function AdHocComparisonPanel() {
  // The "current question" is whatever the analyst most recently submitted
  // as a custom investigation. We do NOT re-derive it from the live event
  // stream — that would couple this panel to graph-side state.
  const recent = useIntelStore((s) => s.customQueryHistory[0] ?? '');

  const [question, setQuestion] = useState<string>(recent);
  const [withScoring, setWithScoring] = useState<boolean>(false);
  const [phase, setPhase] = useState<Phase>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BackendBenchmarkRunResult | null>(null);

  // Sync question with the latest analyst query whenever the panel opens
  // and the user hasn't manually overridden the field.
  const handleSync = () => setQuestion(recent);

  const run = async () => {
    const q = (question || recent || '').trim();
    if (!q) return;
    setPhase('running');
    setError(null);
    setResult(null);
    try {
      const res = await api.runAdHocBenchmark({ question: q, with_scoring: withScoring });
      setResult(res);
      setPhase('ready');
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      // 409 = another benchmark run is in progress
      if (msg.includes('409') || msg.toLowerCase().includes('in progress')) {
        setPhase('busy');
      } else {
        setPhase('error');
      }
      setError(msg);
    }
  };

  return (
    <section className="surface overflow-hidden">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Scale className="w-3 h-3 text-[var(--color-text-muted)]" />
        <span className="heading-tactical">3-pipeline comparison · this query</span>
        <span className="chip text-[8.5px] inline-flex items-center gap-1 border-[rgba(34,211,238,0.32)] text-[var(--color-ice-400)]">
          <Cpu className="w-2.5 h-2.5" />
          real pipelines
        </span>
        <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          POST /benchmark/ad-hoc
        </span>
      </div>

      {/* Controls — analyst query (pre-filled from the last live investigation) */}
      <div className="px-3 py-2 border-b border-[var(--color-line-soft)] space-y-2">
        <div className="flex items-center gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={recent ? 'edit or run as-is' : 'run a custom investigation first to seed this'}
            disabled={phase === 'running'}
            className={cn(
              'flex-1 panel-soft px-2 h-7 bg-transparent border-0 outline-none',
              'text-[12px] text-[var(--color-text-bright)]',
              'placeholder:text-[var(--color-text-muted)] placeholder:tracking-wide',
              'disabled:opacity-50',
            )}
          />
          {recent && question !== recent && (
            <button
              onClick={handleSync}
              title="sync with latest live investigation"
              className="h-7 px-2 inline-flex items-center font-mono text-[9px] tracking-[0.22em] uppercase rounded-sm border border-[var(--color-line)] text-[var(--color-text-muted)] hover:text-[var(--color-ice-300)] hover:bg-[rgba(34,211,238,0.05)]"
            >
              sync
            </button>
          )}
          <button
            onClick={run}
            disabled={!question.trim() || phase === 'running'}
            className={cn(
              'h-7 px-3 inline-flex items-center gap-1.5 font-mono text-[10px] tracking-[0.26em] uppercase rounded-sm',
              question.trim() && phase !== 'running'
                ? 'border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-300)] hover:bg-[rgba(34,211,238,0.12)]'
                : 'border border-[var(--color-line)] text-[var(--color-text-muted)] cursor-not-allowed',
            )}
          >
            {phase === 'running' ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <Play className="w-3 h-3" />
            )}
            run comparison
          </button>
        </div>

        <label className={cn(
          'flex items-center gap-1.5 cursor-pointer select-none',
          phase === 'running' && 'opacity-40 cursor-not-allowed',
        )}>
          <input
            type="checkbox"
            disabled={phase === 'running'}
            checked={withScoring}
            onChange={(e) => setWithScoring(e.target.checked)}
            className="accent-[var(--color-ice-400)]"
          />
          <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-secondary)]">
            score (partial · no ground truth)
          </span>
          <span className="font-mono text-[8.5px] text-[var(--color-text-muted)] italic">
            judge + semantic only
          </span>
        </label>
      </div>

      {/* Status / error */}
      {phase === 'busy' && (
        <div className="px-3 py-2 border-b border-[var(--color-line-soft)] flex items-center gap-2 bg-[rgba(245,158,11,0.04)]">
          <Info className="w-3.5 h-3.5 text-[var(--color-amber-400)]" />
          <span className="font-mono text-[10.5px] text-[var(--color-amber-300)]">
            benchmark service is busy with another run · try again in a moment
          </span>
        </div>
      )}
      {phase === 'error' && error && (
        <div className="px-3 py-2 border-b border-[var(--color-line-soft)] flex items-start gap-2 bg-[rgba(244,63,94,0.04)]">
          <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-rose-400)] mt-0.5" />
          <span className="font-mono text-[10.5px] text-[var(--color-rose-300)] break-all">
            {error.slice(0, 320)}
          </span>
        </div>
      )}

      {/* Pre-run hint when idle and we have a recent question seeded */}
      {phase === 'idle' && !result && (
        <div className="px-3 py-3 font-mono text-[10.5px] leading-relaxed text-[var(--color-text-muted)]">
          {recent
            ? <>question seeded from the latest live investigation. Click <span className="text-[var(--color-ice-300)]">run comparison</span> to execute it through all three pipelines.</>
            : <>run a custom investigation first — the query will seed here, then you can compare across all three pipelines.</>
          }
        </div>
      )}

      {/* Result aggregates */}
      {phase === 'ready' && result && (
        <Aggregates result={result} />
      )}
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function Aggregates({ result }: { result: BackendBenchmarkRunResult }) {
  const q = result.quantitative;
  const byKey: Record<string, BackendPipelineAggregate> = Object.fromEntries(
    q.pipelines.map((p) => [p.approach, p]),
  );
  const order: Array<'pure_llm' | 'vector_rag' | 'graph_rag'> = ['pure_llm', 'vector_rag', 'graph_rag'];
  const scoringEnabled = !!q.scoring?.enabled;
  return (
    <div className="px-3 py-3 space-y-2.5">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="w-3 h-3 text-[var(--color-emerald-400)]" />
        <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-emerald-400)]">
          comparison ready
        </span>
        <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {q.queries_run} q · {scoringEnabled ? 'scored' : 'no scoring'}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-2">
        {order.map((k) => {
          const p = byKey[k];
          if (!p || !p.queries) {
            return (
              <div key={k} className="panel-soft p-2 font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                no data · {k}
              </div>
            );
          }
          return <PipelineCard key={k} p={p} />;
        })}
      </div>

      {/* The why-graph-wins explainer — drawn from the raw aggregate, not boilerplate */}
      <ComparisonInsight pipelines={q.pipelines as BackendPipelineAggregate[]} />
    </div>
  );
}

function PipelineCard({ p }: { p: BackendPipelineAggregate }) {
  const color =
    p.approach === 'graph_rag' ? 'var(--color-emerald-400)' :
    p.approach === 'vector_rag' ? 'var(--color-amber-400)' :
    'var(--color-rose-400)';
  return (
    <div className="panel-soft p-2.5">
      <div className="flex items-center gap-1.5 mb-1.5">
        <Cpu className="w-3 h-3" style={{ color }} />
        <span className="font-mono text-[10px] tracking-[0.26em] uppercase" style={{ color }}>
          {String(p.approach).replace('_', '·')}
        </span>
        <span className="ml-auto font-mono text-[9px] text-[var(--color-text-muted)]">
          {p.queries} q{p.errors ? ` · ${p.errors} err` : ''}
        </span>
      </div>
      <Line label="avg tokens"    value={`${(p.avg_total_tokens ?? 0).toFixed(0)}`} color={color} icon={Coins} />
      <Line label="avg retrieval" value={`${Math.round(p.avg_retrieval_ms ?? 0)} ms`} color={color} icon={Timer} />
      <Line label="avg sources"   value={`${(p.avg_sources_retrieved ?? 0).toFixed(1)}`} color={color} icon={GitBranch} />
      {(p.avg_cost ?? 0) > 0 && (
        <Line label="cost / query" value={`$${(p.avg_cost ?? 0).toFixed(6)}`} color={color} icon={Coins} />
      )}
      {(p.n_evaluated ?? 0) > 0 && (
        <div className="mt-2 pt-2 border-t border-[var(--color-line-soft)] space-y-0.5">
          <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
            partial scoring · no ground truth
          </div>
          {p.avg_judge_overall != null && (
            <Line label="judge overall" value={`${p.avg_judge_overall.toFixed(2)} / 5`} color={color} />
          )}
          {p.avg_semantic_score != null && (
            <Line label="semantic"      value={`${p.avg_semantic_score.toFixed(3)}`} color={color} />
          )}
        </div>
      )}
    </div>
  );
}

function Line({
  label, value, color, icon: Icon,
}: {
  label: string;
  value: string;
  color: string;
  icon?: typeof Coins;
}) {
  return (
    <div className="flex items-baseline gap-2">
      {Icon && <Icon className="w-2.5 h-2.5 shrink-0" style={{ color }} />}
      <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
        {label}
      </span>
      <span className="ml-auto font-mono text-[11px] font-light tracking-tight" style={{ color }}>
        {value}
      </span>
    </div>
  );
}

function ComparisonInsight({ pipelines }: { pipelines: BackendPipelineAggregate[] }) {
  // Pull the three pipelines and synthesize ONE line of operational insight
  // grounded entirely in the actual numbers we just measured.
  const g = pipelines.find((p) => p.approach === 'graph_rag');
  const v = pipelines.find((p) => p.approach === 'vector_rag');
  const l = pipelines.find((p) => p.approach === 'pure_llm');
  if (!g || !v || !l) return null;

  const gTok = g.avg_total_tokens ?? 0;
  const lTok = l.avg_total_tokens ?? 0;
  const gSrc = g.avg_sources_retrieved ?? 0;
  const vSrc = v.avg_sources_retrieved ?? 0;
  const gRet = g.avg_retrieval_ms ?? 0;

  return (
    <div className="panel-soft p-2 border-l-2 border-[rgba(16,185,129,0.4)]">
      <div className="flex items-center gap-1.5 mb-1">
        <Info className="w-3 h-3 text-[var(--color-emerald-400)]" />
        <span className="font-mono text-[9px] tracking-[0.32em] uppercase text-[var(--color-emerald-400)]">
          measured insight
        </span>
      </div>
      <ul className="text-[10.5px] text-[var(--color-text-secondary)] leading-relaxed list-none pl-0 space-y-0.5">
        <li>
          <span className="text-[var(--color-emerald-400)]">▸</span> GraphRAG paid <span className="font-mono text-[var(--color-text-bright)]">{Math.round(gRet).toLocaleString()}ms</span> of real retrieval to return <span className="font-mono text-[var(--color-text-bright)]">{gSrc.toFixed(1)}</span> structural sources.
        </li>
        <li>
          <span className="text-[var(--color-amber-400)]">▸</span> VectorRAG retrieved <span className="font-mono text-[var(--color-text-bright)]">{vSrc.toFixed(1)}</span> sources by similarity — no edge types, no topology continuity.
        </li>
        <li>
          <span className="text-[var(--color-rose-400)]">▸</span> PureLLM ran with no retrieval and burned <span className="font-mono text-[var(--color-text-bright)]">{lTok.toFixed(0)}</span> tokens vs GraphRAG's <span className="font-mono text-[var(--color-text-bright)]">{gTok.toFixed(0)}</span>.
        </li>
      </ul>
    </div>
  );
}
