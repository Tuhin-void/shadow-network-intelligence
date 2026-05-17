import { useEffect, useState } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { api } from '@/lib/api-client';
import {
  transformBenchmarkBundle,
  type RealBenchmarkBundle,
} from '@/lib/adapters/benchmark';
import { StructuralVerdict } from './StructuralVerdict';
import { QuantitativeComparison } from './QuantitativeComparison';
import { KeyMetricsBoard } from './KeyMetricsBoard';
import { TopologyComparisonChamber } from './TopologyComparisonChamber';
import { EvidenceTable } from './EvidenceTable';
import { MethodologyCard } from './MethodologyCard';
import { LiveBenchmarkConsole } from './LiveBenchmarkConsole';
import { StructuralVerdictExplainerLoader } from './StructuralVerdictExplainerLoader';
import { cn } from '@/lib/utils';

/**
 * RealBenchmarkPanel — the assembled benchmark evidence chamber.
 *
 *   1. StructuralVerdict           the dominant hero (real numbers)
 *   2. TopologyComparisonChamber   schematic side-by-side of the 3 pipelines
 *   3. EvidenceTable               inspectable per-query evidence (real)
 *   4. MethodologyCard             provenance + reproducibility commands
 *
 * All real-numeric content originates in scripts/adversarial_results.json
 * and is read via /api/v1/benchmark/summary. Nothing is computed in the
 * browser. The topology comparison panels are explicitly labeled
 * "schematic · conceptual" so they cannot be mistaken for live graph output.
 */
export function RealBenchmarkPanel() {
  const [bundle, setBundle] = useState<RealBenchmarkBundle | null>(null);
  const [phase, setPhase] = useState<'idle' | 'loading' | 'ready' | 'error'>('loading');
  const [error, setError] = useState<string | null>(null);
  // Incremented after a live benchmark run completes — propagated to
  // QuantitativeComparison so it re-fetches the latest run aggregates.
  const [quantReloadToken, setQuantReloadToken] = useState(0);

  const reload = async () => {
    setPhase('loading');
    setError(null);
    try {
      const raw = await api.getBenchmarkSummary();
      setBundle(transformBenchmarkBundle(raw));
      setPhase('ready');
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setPhase('error');
    }
  };

  useEffect(() => {
    reload();
  }, []);

  if (phase === 'loading' && !bundle) {
    return (
      <div className="surface p-3 flex items-center gap-3">
        <RefreshCw className="w-3 h-3 text-[var(--color-ice-400)] animate-spin" />
        <span className="font-mono text-[10.5px] uppercase tracking-[0.22em] text-[var(--color-text-muted)]">
          reading benchmark artifacts …
        </span>
      </div>
    );
  }

  if (phase === 'error' || !bundle) {
    return (
      <div className="surface p-3">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-rose-400)]" />
          <span className="label-tactical text-[var(--color-rose-400)]">
            benchmark backend unreachable
          </span>
          <button
            onClick={reload}
            className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)]"
          >
            retry
          </button>
        </div>
        {error && (
          <div className="font-mono text-[10px] text-[var(--color-rose-300)] mb-2 break-all">
            {error.slice(0, 240)}
          </div>
        )}
        <div className="panel-soft p-2">
          <div className="font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] mb-1">
            generate the artifact locally
          </div>
          <code className="font-mono text-[10.5px] text-[var(--color-ice-300)]">
            python3 scripts/adversarial_benchmark.py --profile small
          </code>
        </div>
      </div>
    );
  }

  // From this point bundle is guaranteed non-null.
  const adv = bundle.adversarial;

  if (!adv) {
    return (
      <div className="surface p-3">
        <div className="flex items-center gap-2 mb-2">
          <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-amber-400)]" />
          <span className="label-tactical text-[var(--color-amber-400)]">
            no adversarial benchmark artifact yet
          </span>
        </div>
        <div className="text-[11.5px] text-[var(--color-text-secondary)] mb-2 leading-relaxed">
          The orchestrator is reachable but no benchmark JSON has been
          produced. Run the deterministic suite to generate it:
        </div>
        <div className="panel-soft p-2">
          <code className="font-mono text-[10.5px] text-[var(--color-ice-300)]">
            {bundle.scriptsToRegenerate?.adversarial ??
              'python3 scripts/adversarial_benchmark.py --profile small'}
          </code>
        </div>
        <button
          onClick={reload}
          className="mt-2 h-7 px-2.5 inline-flex items-center gap-1.5 text-[10px] font-mono tracking-[0.26em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] text-[var(--color-ice-400)]"
        >
          <RefreshCw className="w-3 h-3" />
          retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 max-w-[1280px] mx-auto">
      {/* Quiet operational status — one subtle line, then the verdict.
          No badge spam, no LIVE shouting. */}
      <div className="flex items-center gap-2.5 px-1">
        <span className="w-1.5 h-1.5 rounded-full bg-[var(--color-emerald-400)] anim-drift" />
        <span className="font-mono text-[9.5px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          TigerGraph connected · artifact-backed · deterministic execution
        </span>
        <button
          onClick={reload}
          className={cn(
            'ml-auto h-6 px-2 inline-flex items-center gap-1.5 rounded-sm',
            'font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]',
            'hover:bg-[rgba(34,211,238,0.05)] hover:text-[var(--color-ice-400)]',
          )}
          title="Reload benchmark artifacts"
        >
          <RefreshCw className={cn('w-3 h-3', phase === 'loading' && 'animate-spin')} />
          reload
        </button>
      </div>

      <LiveBenchmarkConsole onRunComplete={() => setQuantReloadToken((t) => t + 1)} />
      <StructuralVerdict data={adv} />
      <QuantitativeComparison reloadToken={quantReloadToken} />
      <StructuralVerdictExplainerLoader reloadToken={quantReloadToken} />
      <TopologyComparisonChamber />
      <KeyMetricsBoard bundle={bundle} />
      <EvidenceTable data={adv} />
      <MethodologyCard bundle={bundle} />
    </div>
  );
}
