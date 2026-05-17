import { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  Cpu,
  GitBranch,
  Loader2,
  Play,
  Radio,
  Sparkles,
  Square,
  Target,
  Zap,
} from 'lucide-react';
import { api } from '@/lib/api-client';
import type {
  BackendBenchmarkRunResult,
  BackendBenchmarkServiceStatus,
  BackendBenchmarkStreamEvent,
  BackendPipelineAggregate,
} from '@/lib/api-client';
import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';

/**
 * LiveBenchmarkConsole — operational console for triggering real,
 * in-process benchmark runs through the orchestrator API.
 *
 * Hard contracts:
 *   • Every metric shown originates in a backend event or the persisted
 *     run JSON. No client-side synthesis.
 *   • The "Investigate" action on each completed row hands the same
 *     question off to `runCustomDeepStream` so the analyst sees the
 *     real GraphRAG investigation that would answer it.
 *   • If the backend reports run.busy, we surface that — never silently
 *     queue a second run.
 */
type Phase = 'idle' | 'starting' | 'running' | 'complete' | 'error' | 'busy';

type CompletedRow = {
  approach: string;
  queryId: string;
  question: string;
  index: number;
  total: number;
  result: Record<string, any>;
  evaluation: Record<string, any> | null;
};

type PerApproach = {
  completed: number;
  failed: number;
  totalTokens: number;
  totalRetrievalMs: number;
};

export function LiveBenchmarkConsole({ onRunComplete }: { onRunComplete?: () => void }) {
  const navigate = useNavigate();
  const runCustomDeep = useIntelStore((s) => s.runCustomDeepStream);

  const [serviceStatus, setServiceStatus] = useState<BackendBenchmarkServiceStatus | null>(null);
  const [phase, setPhase] = useState<Phase>('idle');
  const [limit, setLimit] = useState<number>(3);
  const [withScoring, setWithScoring] = useState<boolean>(true);

  const [progress, setProgress] = useState<{
    runId: string | null;
    queriesPlanned: number;
    completed: number;
    failed: number;
    perApproach: Record<string, PerApproach>;
  }>({ runId: null, queriesPlanned: 0, completed: 0, failed: 0, perApproach: {} });

  const [rows, setRows] = useState<CompletedRow[]>([]);
  const [lastResult, setLastResult] = useState<BackendBenchmarkRunResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<boolean>(false);

  const abortRef = useRef<AbortController | null>(null);

  // Initial service status — cheap, gives us provider config + busy flag.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const s = await api.getBenchmarkServiceStatus();
        if (!cancelled) setServiceStatus(s);
      } catch {
        /* benchmark service is optional UX surface; silent on probe failure */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  // Cancel any in-flight stream when the component unmounts.
  useEffect(() => () => abortRef.current?.abort(), []);

  const cancel = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    if (phase === 'running' || phase === 'starting') setPhase('idle');
  };

  const start = async () => {
    cancel();
    setPhase('starting');
    setError(null);
    setRows([]);
    setLastResult(null);
    setProgress({ runId: null, queriesPlanned: 0, completed: 0, failed: 0, perApproach: {} });

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      for await (const ev of api.streamBenchmarkRun(
        { limit, with_scoring: withScoring },
        controller.signal,
      )) {
        handleEvent(ev);
      }
    } catch (e) {
      if ((e as any)?.name === 'AbortError') return;
      setError(e instanceof Error ? e.message : String(e));
      setPhase('error');
    } finally {
      abortRef.current = null;
    }
  };

  const handleEvent = (ev: BackendBenchmarkStreamEvent) => {
    const kind = String(ev.kind || '');

    if (kind === 'run.busy') {
      setPhase('busy');
      setError(String(ev.message ?? 'benchmark service is busy'));
      return;
    }
    if (kind === 'run.started') {
      setPhase('running');
      setProgress((prev) => ({
        ...prev,
        runId: (ev.run_id as string) ?? null,
        queriesPlanned: (ev.queries as number) ?? 0,
        completed: 0,
        failed: 0,
        perApproach: {},
      }));
      return;
    }
    if (kind === 'query.completed') {
      const approach = String(ev.approach ?? '');
      const result = (ev.result as Record<string, any>) || {};
      const row: CompletedRow = {
        approach,
        queryId: String(ev.query_id ?? ''),
        question: String(ev.question ?? ''),
        index: Number(ev.index ?? 0),
        total: Number(ev.total ?? 0),
        result,
        evaluation: (ev.evaluation as Record<string, any> | null) ?? null,
      };
      setRows((prev) => [...prev, row]);
      setProgress((prev) => {
        const pa: PerApproach = prev.perApproach[approach] ?? {
          completed: 0, failed: 0, totalTokens: 0, totalRetrievalMs: 0,
        };
        return {
          ...prev,
          completed: prev.completed + 1,
          perApproach: {
            ...prev.perApproach,
            [approach]: {
              completed: pa.completed + 1,
              failed: pa.failed,
              totalTokens: pa.totalTokens + Number(result.total_tokens || 0),
              totalRetrievalMs: pa.totalRetrievalMs + Number(result.retrieval_ms || 0),
            },
          },
        };
      });
      return;
    }
    if (kind === 'query.failed') {
      const approach = String(ev.approach ?? '');
      setProgress((prev) => {
        const pa: PerApproach = prev.perApproach[approach] ?? {
          completed: 0, failed: 0, totalTokens: 0, totalRetrievalMs: 0,
        };
        return {
          ...prev,
          failed: prev.failed + 1,
          perApproach: {
            ...prev.perApproach,
            [approach]: { ...pa, failed: pa.failed + 1 },
          },
        };
      });
      return;
    }
    if (kind === 'run.completed') {
      setPhase('complete');
      const runId = (ev.run_id as string) ?? progress.runId;
      if (runId) {
        // Pull the full run JSON so we have the persisted aggregates.
        api.getBenchmarkRun(runId).then((res) => {
          setLastResult(res);
          if (onRunComplete) onRunComplete();
        }).catch(() => {
          /* non-fatal — UI already showed per-event progress */
        });
      }
      return;
    }
    if (kind === 'run.error') {
      setPhase('error');
      setError(String(ev.error ?? 'unknown run error'));
    }
  };

  const investigate = async (q: string) => {
    if (!q.trim()) return;
    try {
      await runCustomDeep(q.trim());
      navigate('/investigate');
    } catch {
      navigate('/investigate');
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────

  const isRunning = phase === 'starting' || phase === 'running';
  const provider = serviceStatus?.providers ?? {};

  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Radio className={cn(
          'w-3 h-3',
          isRunning ? 'text-[var(--color-emerald-400)] anim-drift' : 'text-[var(--color-text-muted)]',
        )} />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          live benchmark execution
        </span>
        <span className="text-[var(--color-text-ghost)] mx-1">·</span>
        <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          in-process · same code path as CLI
        </span>
        {serviceStatus && (
          <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            graph {String(provider.graph_provider ?? '?')} · embed {String(provider.embedder_provider ?? '?')} · llm {String(provider.llm_provider ?? '?')}
          </span>
        )}
      </div>

      {/* Controls */}
      <div className="px-4 py-3 flex items-center gap-3 border-b border-[var(--color-line-soft)] flex-wrap">
        <div className="flex items-center gap-1.5">
          <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
            queries
          </span>
          <div className="flex items-center gap-0.5 panel-soft p-0.5">
            {[3, 5, 10].map((n) => (
              <button
                key={n}
                disabled={isRunning}
                onClick={() => setLimit(n)}
                className={cn(
                  'h-6 px-2 font-mono text-[10px] tracking-[0.22em] uppercase rounded-sm transition-colors',
                  limit === n
                    ? 'bg-[rgba(34,211,238,0.08)] text-[var(--color-ice-300)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text-primary)]',
                  isRunning && 'opacity-40 cursor-not-allowed',
                )}
              >
                {n}
              </button>
            ))}
          </div>
        </div>

        <label className={cn(
          'flex items-center gap-1.5 cursor-pointer select-none',
          isRunning && 'opacity-40 cursor-not-allowed',
        )}>
          <input
            type="checkbox"
            disabled={isRunning}
            checked={withScoring}
            onChange={(e) => setWithScoring(e.target.checked)}
            className="accent-[var(--color-ice-400)]"
          />
          <span className="font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-secondary)]">
            score (judge + entity + semantic)
          </span>
        </label>

        <div className="ml-auto flex items-center gap-2">
          {isRunning ? (
            <button
              onClick={cancel}
              className="h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(244,63,94,0.4)] bg-[rgba(244,63,94,0.05)] text-[var(--color-rose-400)] hover:bg-[rgba(244,63,94,0.1)]"
            >
              <Square className="w-3 h-3" />
              abort
            </button>
          ) : (
            <button
              onClick={start}
              className="h-7 px-3 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-300)] hover:bg-[rgba(34,211,238,0.12)]"
            >
              <Play className="w-3 h-3" />
              run now
            </button>
          )}
        </div>
      </div>

      {/* Progress strip — shown only when there's something to report */}
      {(isRunning || rows.length > 0 || phase === 'complete' || phase === 'busy' || phase === 'error') && (
        <div className="px-4 py-3 border-b border-[var(--color-line-soft)] bg-[rgba(7,9,14,0.4)]">
          <div className="flex items-center gap-3 flex-wrap">
            <PhaseChip phase={phase} />

            {progress.queriesPlanned > 0 && (
              <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
                <span className="text-[var(--color-text-bright)]">{progress.completed}</span>
                {' / '}
                {progress.queriesPlanned * 3} results
                {progress.failed > 0 && (
                  <span className="ml-2 text-[var(--color-rose-400)]">· {progress.failed} failed</span>
                )}
              </span>
            )}

            {progress.runId && (
              <span className="font-mono text-[9.5px] text-[var(--color-text-muted)] truncate max-w-[180px]" title={progress.runId}>
                {progress.runId}
              </span>
            )}

            {/* Per-approach pills (only shown once data starts flowing) */}
            <div className="ml-auto flex items-center gap-2">
              {(['pure_llm', 'vector_rag', 'graph_rag'] as const).map((a) => {
                const pa = progress.perApproach[a];
                if (!pa) return null;
                return <ApproachPill key={a} approach={a} stats={pa} />;
              })}
            </div>
          </div>

          {error && (
            <div className="mt-2 flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-rose-400)] mt-0.5" />
              <span className="font-mono text-[10px] text-[var(--color-rose-300)] break-all">
                {error.slice(0, 360)}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Aggregate result panel when complete */}
      {phase === 'complete' && lastResult && (
        <ResultAggregates result={lastResult} onInvestigate={investigate} />
      )}

      {/* Streaming row log — collapsible to keep the page calm */}
      {rows.length > 0 && (
        <div>
          <button
            onClick={() => setExpanded((v) => !v)}
            className="w-full px-4 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)] hover:bg-[rgba(34,211,238,0.025)] transition-colors"
          >
            <ChevronDown className={cn('w-3 h-3 text-[var(--color-text-muted)] transition-transform', expanded && 'rotate-180')} />
            <span className="font-mono text-[10px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              streamed results · {rows.length}
            </span>
            <span className="ml-auto font-mono text-[9.5px] text-[var(--color-text-muted)]">
              click row to investigate the question
            </span>
          </button>
          {expanded && <StreamedRowLog rows={rows} onInvestigate={investigate} />}
        </div>
      )}
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function PhaseChip({ phase }: { phase: Phase }) {
  const styles: Record<Phase, { label: string; color: string; bg: string; icon: typeof Activity }> = {
    idle:     { label: 'idle',     color: 'var(--color-text-muted)',  bg: 'rgba(148,163,184,0.08)', icon: Activity },
    starting: { label: 'starting', color: 'var(--color-ice-400)',     bg: 'rgba(34,211,238,0.08)',  icon: Loader2 },
    running:  { label: 'running',  color: 'var(--color-ice-300)',     bg: 'rgba(34,211,238,0.10)',  icon: Loader2 },
    complete: { label: 'complete', color: 'var(--color-emerald-400)', bg: 'rgba(16,185,129,0.08)',  icon: CheckCircle2 },
    error:    { label: 'error',    color: 'var(--color-rose-400)',    bg: 'rgba(244,63,94,0.08)',   icon: AlertTriangle },
    busy:     { label: 'busy',     color: 'var(--color-amber-400)',   bg: 'rgba(245,158,11,0.08)',  icon: Loader2 },
  };
  const s = styles[phase];
  const Icon = s.icon;
  const spinning = phase === 'running' || phase === 'starting' || phase === 'busy';
  return (
    <span
      className="inline-flex items-center gap-1.5 h-6 px-2 rounded-sm border font-mono text-[9.5px] tracking-[0.22em] uppercase"
      style={{ color: s.color, borderColor: `${s.color}55`, background: s.bg }}
    >
      <Icon className={cn('w-3 h-3', spinning && 'animate-spin')} />
      {s.label}
    </span>
  );
}

function ApproachPill({ approach, stats }: { approach: string; stats: PerApproach }) {
  const color =
    approach === 'graph_rag' ? 'var(--color-emerald-400)' :
    approach === 'vector_rag' ? 'var(--color-amber-400)' :
    'var(--color-rose-400)';
  return (
    <div
      className="inline-flex items-center gap-2 h-6 px-2 rounded-sm border"
      style={{ borderColor: `${color}55`, background: `${color}0d` }}
      title={`${approach}: ${stats.completed} completed (${stats.totalTokens} tokens, ${stats.totalRetrievalMs.toFixed(0)}ms retrieval)`}
    >
      <span className="font-mono text-[9px] tracking-[0.22em] uppercase" style={{ color }}>
        {approach.replace('_', '·')}
      </span>
      <span className="font-mono text-[10px]" style={{ color }}>
        {stats.completed}
      </span>
    </div>
  );
}

function StreamedRowLog({
  rows,
  onInvestigate,
}: {
  rows: CompletedRow[];
  onInvestigate: (q: string) => void;
}) {
  return (
    <table className="w-full font-mono text-[10.5px]">
      <thead className="text-[var(--color-text-muted)] uppercase tracking-[0.16em] text-[9px]">
        <tr className="border-b border-[var(--color-line-soft)]">
          <th className="text-left px-3 py-1.5">approach</th>
          <th className="text-left px-3 py-1.5">id</th>
          <th className="text-left px-3 py-1.5 max-w-[280px]">question</th>
          <th className="text-right px-3 py-1.5">tok</th>
          <th className="text-right px-3 py-1.5">ret ms</th>
          <th className="text-right px-3 py-1.5">srcs</th>
          <th className="text-right px-3 py-1.5">judge</th>
          <th className="text-right px-3 py-1.5">entF1</th>
          <th className="text-right px-3 py-1.5">sem</th>
          <th className="w-8 px-1"></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const color =
            r.approach === 'graph_rag' ? 'var(--color-emerald-400)' :
            r.approach === 'vector_rag' ? 'var(--color-amber-400)' :
            'var(--color-rose-400)';
          const judge = (r.evaluation?.judge_breakdown?.overall as number | undefined);
          const entF1 = (r.evaluation?.entity_match?.f1 as number | undefined);
          const sem = (r.evaluation?.semantic_score as number | undefined);
          return (
            <tr key={`${r.approach}-${r.queryId}-${i}`} className="border-b border-[var(--color-line-soft)] hover:bg-[rgba(34,211,238,0.025)]">
              <td className="px-3 py-1 font-mono text-[9.5px]" style={{ color }}>
                {r.approach.replace('_', '·')}
              </td>
              <td className="px-3 py-1 text-[var(--color-ice-400)]">{r.queryId}</td>
              <td className="px-3 py-1 text-[var(--color-text-secondary)] truncate max-w-[280px]" title={r.question}>
                {r.question}
              </td>
              <td className="px-3 py-1 text-right text-[var(--color-text-bright)]">
                {Number(r.result.total_tokens || 0).toLocaleString()}
              </td>
              <td className="px-3 py-1 text-right text-[var(--color-text-bright)]">
                {Math.round(Number(r.result.retrieval_ms || 0)).toLocaleString()}
              </td>
              <td className="px-3 py-1 text-right text-[var(--color-text-bright)]">
                {Array.isArray(r.result.sources) ? r.result.sources.length : 0}
              </td>
              <td className="px-3 py-1 text-right">
                {judge == null ? '—' : <span className="text-[var(--color-text-bright)]">{judge.toFixed(1)}</span>}
              </td>
              <td className="px-3 py-1 text-right">
                {entF1 == null ? '—' : <span style={{ color }}>{(entF1 * 100).toFixed(0)}</span>}
              </td>
              <td className="px-3 py-1 text-right">
                {sem == null ? '—' : <span className="text-[var(--color-text-bright)]">{sem.toFixed(2)}</span>}
              </td>
              <td className="px-1 py-1">
                <button
                  onClick={() => onInvestigate(r.question)}
                  title="Investigate this question in the workspace"
                  className="w-6 h-6 inline-flex items-center justify-center text-[var(--color-text-muted)] hover:text-[var(--color-ice-300)] transition-colors"
                >
                  <Target className="w-3 h-3" />
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/* -------------------------------------------------------------------------- */

function ResultAggregates({
  result,
  onInvestigate,
}: {
  result: BackendBenchmarkRunResult;
  onInvestigate: (q: string) => void;
}) {
  const q = result.quantitative;
  const order: Array<'pure_llm' | 'vector_rag' | 'graph_rag'> = ['pure_llm', 'vector_rag', 'graph_rag'];
  const byKey: Record<string, BackendPipelineAggregate> = Object.fromEntries(
    q.pipelines.map((p) => [p.approach, p]),
  );
  const scoringEnabled = !!q.scoring?.enabled;
  return (
    <div className="px-4 py-3 border-b border-[var(--color-line-soft)] bg-[rgba(7,9,14,0.4)]">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="w-3 h-3 text-[var(--color-emerald-400)]" />
        <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-emerald-400)]">
          run complete · aggregates
        </span>
        <span className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {q.queries_run} q · {scoringEnabled ? 'scored' : 'no scoring'}
          {q.scoring?.semantic_methods?.length ? ` · semantic ${q.scoring.semantic_methods.join('+')}` : ''}
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
          return <AggregateCard key={k} p={p} />;
        })}
      </div>

      {/* Investigate-this-run handoff — surface the queries we actually ran. */}
      {result.run.queries && result.run.queries.length > 0 && (
        <div className="mt-3 panel-soft p-2">
          <div className="flex items-center gap-2 mb-1.5">
            <GitBranch className="w-3 h-3 text-[var(--color-ice-400)]" />
            <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
              investigate any benchmarked query
            </span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {result.run.queries.slice(0, 8).map((q) => (
              <button
                key={q.id}
                onClick={() => onInvestigate(q.question)}
                title={q.question}
                className="inline-flex items-center gap-1 h-6 px-2 rounded-sm border border-[var(--color-line-soft)] hover:border-[rgba(34,211,238,0.4)] hover:bg-[rgba(34,211,238,0.05)] transition-colors"
              >
                <Zap className="w-2.5 h-2.5 text-[var(--color-ice-400)]" />
                <span className="font-mono text-[9.5px] text-[var(--color-text-secondary)] hover:text-[var(--color-text-bright)]">
                  {q.id}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function AggregateCard({ p }: { p: BackendPipelineAggregate }) {
  const color =
    p.approach === 'graph_rag' ? 'var(--color-emerald-400)' :
    p.approach === 'vector_rag' ? 'var(--color-amber-400)' :
    'var(--color-rose-400)';
  const has = (n: number | undefined): n is number => typeof n === 'number';
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

      <Line label="avg tokens" value={(p.avg_total_tokens ?? 0).toFixed(0)} color={color} />
      <Line label="avg retrieval" value={`${Math.round(p.avg_retrieval_ms ?? 0)} ms`} color={color} />
      <Line label="avg sources"  value={(p.avg_sources_retrieved ?? 0).toFixed(1)} color={color} />
      {has(p.avg_cost) && p.avg_cost > 0 && (
        <Line label="cost / query" value={`$${(p.avg_cost ?? 0).toFixed(6)}`} color={color} />
      )}

      {/* Scoring block — only shown when the run was scored */}
      {has(p.n_evaluated) && (p.n_evaluated ?? 0) > 0 && (
        <div className="mt-2 pt-2 border-t border-[var(--color-line-soft)] space-y-0.5">
          <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] mb-1">
            scoring · {p.n_evaluated} evaluated
          </div>
          {has(p.avg_judge_overall) && (
            <Line label="judge overall"      value={`${(p.avg_judge_overall ?? 0).toFixed(2)} / 5`} color={color} />
          )}
          {has(p.judge_pass_rate) && (
            <Line label="judge pass"         value={`${Math.round((p.judge_pass_rate ?? 0) * 100)}%`} color={color} />
          )}
          {has(p.hallucination_resistance_rate) && (
            <Line label="hallu resistance"   value={`${Math.round((p.hallucination_resistance_rate ?? 0) * 100)}%`} color={color} />
          )}
          {has(p.avg_entity_f1) && (
            <Line label="entity F1"          value={`${(p.avg_entity_f1 ?? 0).toFixed(3)}`} color={color} />
          )}
          {has(p.avg_semantic_score) && (
            <Line label="semantic"           value={`${(p.avg_semantic_score ?? 0).toFixed(3)}`} color={color} />
          )}
        </div>
      )}
    </div>
  );
}

function Line({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="flex items-baseline gap-2">
      <span className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)]">
        {label}
      </span>
      <span className="ml-auto font-mono text-[11px] font-light tracking-tight" style={{ color }}>
        {value}
      </span>
    </div>
  );
}
