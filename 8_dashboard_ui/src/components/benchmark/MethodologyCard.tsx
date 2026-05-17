import { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import {
  BookOpenText,
  ChevronDown,
  Database,
  Fingerprint,
  Layers,
  RotateCcw,
  Shield,
  ShieldCheck,
} from 'lucide-react';
import type { RealBenchmarkBundle } from '@/lib/adapters/benchmark';
import { cn } from '@/lib/utils';

/**
 * MethodologyCard — calm trust surface with optional deep audit drawer.
 *
 *   • Default view: four high-signal trust pillars. No file paths, no
 *     command dumps, no developer-console exposure. Reads like a research
 *     platform's verification block.
 *   • Expandable "technical audit" drawer surfaces the underlying
 *     artifact references, regeneration commands, reliability verdict,
 *     and TigerGraph snapshot for reviewers who want to verify or
 *     reproduce — same depth as before, just opt-in.
 *
 * Credibility is preserved. The progressive disclosure pattern adds
 * polish without hiding any evidence.
 */
export function MethodologyCard({ bundle }: { bundle: RealBenchmarkBundle }) {
  const [open, setOpen] = useState(false);
  const tg = bundle.tigergraph;
  const rel = bundle.reliability;
  const adv = bundle.adversarial;

  return (
    <section className="surface overflow-hidden">
      <div className="px-4 h-9 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <BookOpenText className="w-3 h-3 text-[var(--color-text-muted)]" />
        <span className="font-mono text-[10px] tracking-[0.32em] uppercase text-[var(--color-text-muted)]">
          methodology · verification
        </span>
        <span className="ml-auto font-mono text-[9.5px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          deterministic · reproducible
        </span>
      </div>

      {/* Calm default summary */}
      <div className="px-5 py-4">
        <p className="text-[13px] text-[var(--color-text-bright)] font-light leading-snug">
          Benchmark validated against deterministic TigerGraph-backed
          evaluation artifacts.
        </p>
        <p className="text-[11.5px] text-[var(--color-text-secondary)] leading-relaxed mt-2 max-w-[820px]">
          20-query adversarial suite · reproducible execution · topology-aware
          evaluation · zero browser-generated metrics. Every value on this
          surface is a projection of a captured evaluation artifact — the
          interface performs presentation, never computation.
        </p>

        {/* Four trust pillars */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mt-4">
          <Pillar
            icon={Database}
            label="evaluation artifacts"
            value={adv ? `${adv.queryCount} queries` : '—'}
            sub="captured per benchmark execution"
          />
          <Pillar
            icon={ShieldCheck}
            label="topology snapshot"
            value={tg ? tg.status : '—'}
            sub={
              tg
                ? `${tg.vertexTotal.toLocaleString()} vertices · ${tg.edgeTotal.toLocaleString()} edges`
                : 'snapshot pending'
            }
          />
          <Pillar
            icon={RotateCcw}
            label="reproducibility"
            value={rel ? formatVerdict(rel.verdict) : '—'}
            sub={
              rel
                ? `${rel.queriesRun} × ${rel.trialsPerQuery} trials · ${rel.structuralDrift} drift`
                : 'reliability pending'
            }
          />
          <Pillar
            icon={Shield}
            label="ui rendering"
            value="projection only"
            sub="no metric is computed in the browser"
          />
        </div>

        {/* Progressive disclosure trigger */}
        <button
          onClick={() => setOpen((v) => !v)}
          className={cn(
            'mt-4 inline-flex items-center gap-1.5 h-7 px-2.5 rounded-sm',
            'font-mono text-[10px] tracking-[0.26em] uppercase',
            'border border-[var(--color-line-soft)] text-[var(--color-text-muted)]',
            'hover:bg-[rgba(34,211,238,0.04)] hover:text-[var(--color-ice-400)] hover:border-[rgba(34,211,238,0.32)]',
            open && 'bg-[rgba(34,211,238,0.04)] text-[var(--color-ice-400)] border-[rgba(34,211,238,0.32)]',
          )}
        >
          <Fingerprint className="w-3 h-3" />
          {open ? 'hide technical audit' : 'inspect benchmark provenance'}
          <ChevronDown
            className={cn(
              'w-3 h-3 transition-transform',
              open && 'rotate-180',
            )}
          />
        </button>
      </div>

      {/* Expandable technical audit drawer */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="audit"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden border-t border-[var(--color-line-soft)] bg-[rgba(7,9,14,0.32)]"
          >
            <div className="px-5 py-4 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-1">
              <AuditRow
                icon={Layers}
                label="evaluation artifact · adversarial suite"
                value="scripts/adversarial_results.json"
                mono
              />
              <AuditRow
                icon={RotateCcw}
                label="reproducibility artifact"
                value="scripts/benchmark_reliability.json"
                mono
              />
              <AuditRow
                icon={Database}
                label="topology snapshot"
                value="scripts/tigergraph_validation.json"
                mono
              />
              <AuditRow
                icon={Shield}
                label="evaluation philosophy"
                value="adversarial — queries explicitly require multi-hop traversal or hidden-relationship discovery"
              />

              <AuditRow
                icon={Fingerprint}
                label="regenerate adversarial benchmark"
                value="python3 scripts/adversarial_benchmark.py --profile small"
                mono
              />
              <AuditRow
                icon={Fingerprint}
                label="regenerate reliability verdict"
                value="python3 scripts/benchmark_reliability.py --limit 5"
                mono
              />
              <AuditRow
                icon={Fingerprint}
                label="regenerate topology snapshot"
                value="python3 scripts/tigergraph_validate.py"
                mono
              />

              {tg && (
                <AuditRow
                  icon={Database}
                  label="captured tigergraph state"
                  value={`${tg.status} · ${tg.vertexTotal.toLocaleString()} vertices · ${tg.edgeTotal.toLocaleString()} edges · ${tg.reverseEdgesObserved} reverse-edge types`}
                />
              )}
              {rel && (
                <AuditRow
                  icon={ShieldCheck}
                  label="reliability verdict"
                  value={`${rel.verdict} · ${rel.queriesRun} × ${rel.trialsPerQuery} trials · drift ${rel.structuralDrift} · empty ${rel.emptyAnswers}`}
                />
              )}
            </div>

            <div className="px-5 py-2 border-t border-[var(--color-line-soft)] font-mono text-[9.5px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] flex items-center gap-2">
              <span className="w-1 h-1 rounded-full bg-[var(--color-emerald-400)]" />
              every cell on this surface is a projection of a captured evaluation artifact.
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function Pillar({
  icon: Icon,
  label,
  value,
  sub,
}: {
  icon: typeof Database;
  label: string;
  value: string;
  sub: string;
}) {
  return (
    <div className="panel-soft px-3 py-2.5">
      <div className="flex items-center gap-1.5 mb-1">
        <Icon className="w-3 h-3 text-[var(--color-text-muted)]" />
        <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {label}
        </span>
      </div>
      <div className="text-[12.5px] text-[var(--color-text-bright)] font-light leading-snug">
        {value}
      </div>
      <div className="text-[10px] text-[var(--color-text-secondary)] mt-1 leading-snug">
        {sub}
      </div>
    </div>
  );
}

function AuditRow({
  icon: Icon,
  label,
  value,
  mono,
}: {
  icon: typeof Database;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-start gap-2 py-1.5 border-b border-[var(--color-line-soft)] last:border-b-0">
      <Icon className="w-3 h-3 mt-0.5 text-[var(--color-text-muted)] shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-text-muted)]">
          {label}
        </div>
        <div
          className={
            mono
              ? 'font-mono text-[11px] text-[var(--color-ice-300)] break-all leading-snug mt-0.5'
              : 'text-[11px] text-[var(--color-text-secondary)] leading-snug mt-0.5'
          }
        >
          {value}
        </div>
      </div>
    </div>
  );
}

function formatVerdict(v: string): string {
  switch (v.toUpperCase()) {
    case 'STABLE':
      return 'stable';
    case 'ACCEPTABLE':
      return 'verified';
    case 'DEGRADED':
      return 'degraded';
    case 'OFFLINE':
      return 'offline';
    default:
      return v.toLowerCase();
  }
}
