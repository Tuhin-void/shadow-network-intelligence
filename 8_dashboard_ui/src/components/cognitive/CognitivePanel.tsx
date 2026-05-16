import { useState } from 'react';
import { motion } from 'framer-motion';
import {
  AlertTriangle,
  Brain,
  CheckCircle2,
  ChevronDown,
  Cpu,
  Eye,
  Layers,
  Network,
  ScrollText,
  Zap,
} from 'lucide-react';
import { useIntelStore } from '@/store/intel-store';
import { cn } from '@/lib/utils';
import type {
  CognitiveAgent,
  CognitiveClaim,
  CognitiveReport,
} from '@/lib/adapters/cognitive';

/**
 * CognitivePanel — operational intelligence surface for the deep
 * investigation pipeline (agent swarm + reasoning engine).
 *
 * Sections, all sourced from REAL graph-grounded backend data:
 *   1. Headline + structural confidence
 *   2. Five-agent strip (cards with confidence + summary + metrics)
 *   3. Key claims with confidence + basis tags
 *   4. Contradictions (if any)
 *   5. Per-suspect explanations
 *
 * The panel renders nothing when there is no cognitive report yet.
 */
export function CognitivePanel() {
  const report = useIntelStore((s) => s.cognitiveReport);
  const phase = useIntelStore((s) => s.cognitivePhase);
  const error = useIntelStore((s) => s.cognitiveError);
  const clear = useIntelStore((s) => s.clearCognitiveReport);

  if (phase === 'running') {
    return (
      <div className="surface p-3 flex items-center gap-3">
        <Cpu className="w-3.5 h-3.5 text-[var(--color-ice-400)] anim-drift" />
        <span className="font-mono text-[10.5px] tracking-[0.22em] uppercase text-[var(--color-ice-400)]">
          cognitive layer · synthesizing
        </span>
      </div>
    );
  }
  if (phase === 'error') {
    return (
      <div className="surface p-3">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-3.5 h-3.5 text-[var(--color-rose-400)]" />
          <span className="font-mono text-[10.5px] tracking-[0.22em] uppercase text-[var(--color-rose-400)]">
            cognitive run failed
          </span>
          <button
            onClick={clear}
            className="ml-auto font-mono text-[9.5px] text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)] uppercase tracking-[0.22em]"
          >
            dismiss
          </button>
        </div>
        {error && (
          <div className="font-mono text-[10px] text-[var(--color-rose-300)] mt-2 break-all">
            {error.slice(0, 280)}
          </div>
        )}
      </div>
    );
  }
  if (!report) return null;

  return (
    <div className="flex flex-col gap-3">
      <Headline report={report} />
      <AgentStrip agents={report.agents} />
      <ClaimsList claims={report.claims} />
      {report.contradictions.length > 0 && (
        <Contradictions list={report.contradictions} />
      )}
      <ExplanationsList explanations={report.explanations} />
    </div>
  );
}

/* -------------------------------------------------------------------------- */

function Headline({ report }: { report: CognitiveReport }) {
  const conf = report.overallConfidence;
  const color =
    conf >= 0.7
      ? 'var(--color-emerald-400)'
      : conf >= 0.4
      ? 'var(--color-ice-400)'
      : 'var(--color-amber-400)';
  return (
    <section className="surface px-3 py-3">
      <div className="flex items-center gap-2 mb-2">
        <Brain className="w-3.5 h-3.5" style={{ color }} />
        <span
          className="font-mono text-[9.5px] tracking-[0.32em] uppercase"
          style={{ color }}
        >
          cognitive synthesis
        </span>
        {report.cacheHit && (
          <span className="chip chip-emerald text-[8.5px] ml-1 inline-flex items-center gap-1">
            <Zap className="w-2.5 h-2.5" /> cache hit
          </span>
        )}
        <span className="ml-auto font-mono text-[9.5px] text-[var(--color-text-muted)] uppercase tracking-[0.22em]">
          {report.elapsedMs.toFixed(0)}ms
        </span>
      </div>
      <div className="text-[13px] leading-snug text-[var(--color-text-bright)] font-light">
        {report.headline}
      </div>
      <div className="text-[11px] text-[var(--color-text-secondary)] mt-1.5 leading-relaxed">
        {report.body}
      </div>

      <div className="flex items-center gap-3 mt-3">
        <ConfidenceBar value={conf} color={color} />
        <span
          className="font-mono text-[20px] font-light leading-none"
          style={{ color }}
        >
          {(conf * 100).toFixed(0)}
          <span className="text-[12px] opacity-60">%</span>
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5 mt-3">
        <Stat label="suspects" value={report.counts.suspects} />
        <Stat label="agents" value={report.counts.agents} />
        <Stat label="claims" value={report.counts.claims} />
        <Stat label="structural edges" value={report.counts.structuralEdges} />
        <Stat label="contradictions" value={report.counts.contradictions} />
      </div>
    </section>
  );
}

function ConfidenceBar({ value, color }: { value: number; color: string }) {
  return (
    <div className="flex-1 h-2 rounded-sm bg-[var(--color-graphite-800)] overflow-hidden">
      <motion.div
        initial={{ width: 0 }}
        animate={{ width: `${Math.round(value * 100)}%` }}
        transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
        className="h-full"
        style={{
          background:
            value >= 0.7
              ? `linear-gradient(to right, ${color}, var(--color-ice-400))`
              : color,
        }}
      />
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <span className="chip text-[9px] inline-flex items-center gap-1">
      <span className="font-mono text-[var(--color-text-muted)] uppercase tracking-[0.18em]">
        {label}
      </span>
      <span className="font-mono text-[var(--color-text-bright)]">{value}</span>
    </span>
  );
}

/* -------------------------------------------------------------------------- */

const AGENT_ICON = {
  retrieval_analyst: Eye,
  graph_topology_investigator: Network,
  sanctions_exposure_tracer: AlertTriangle,
  fraud_ring_analyst: Layers,
  synthesis_coordinator: Brain,
} as const;

function AgentStrip({ agents }: { agents: CognitiveAgent[] }) {
  if (agents.length === 0) return null;
  return (
    <section className="surface overflow-hidden">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <Cpu className="w-3 h-3 text-[var(--color-ice-400)]" />
        <span className="heading-tactical">Investigation agents</span>
        <span className="chip ml-auto">{agents.length}</span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 divide-x divide-y divide-[var(--color-line-soft)]">
        {agents.map((a) => (
          <AgentCard key={a.id} agent={a} />
        ))}
      </div>
    </section>
  );
}

function AgentCard({ agent }: { agent: CognitiveAgent }) {
  const [open, setOpen] = useState(false);
  const Icon =
    AGENT_ICON[agent.id as keyof typeof AGENT_ICON] ?? Cpu;
  const conf = agent.confidence;
  const color =
    conf >= 0.7
      ? 'var(--color-emerald-400)'
      : conf >= 0.4
      ? 'var(--color-ice-400)'
      : 'var(--color-text-muted)';
  return (
    <button
      onClick={() => setOpen((v) => !v)}
      className={cn(
        'text-left px-3 py-2.5 transition-colors',
        'hover:bg-[rgba(34,211,238,0.04)]',
      )}
    >
      <div className="flex items-center gap-2 mb-1">
        <Icon className="w-3.5 h-3.5" style={{ color }} />
        <span className="text-[11.5px] font-medium text-[var(--color-text-bright)]">
          {agent.label}
        </span>
        <span
          className="ml-auto font-mono text-[10px] tracking-[0.18em] uppercase"
          style={{ color }}
        >
          {(conf * 100).toFixed(0)}%
        </span>
        <ChevronDown
          className={cn(
            'w-3 h-3 text-[var(--color-text-muted)] transition-transform',
            open && 'rotate-180',
          )}
        />
      </div>
      <div className="text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
        {agent.summary}
      </div>
      {open && (
        <div className="mt-2 panel-soft p-2 space-y-1">
          {agent.metrics.length === 0 ? (
            <div className="font-mono text-[9.5px] text-[var(--color-text-muted)] uppercase tracking-[0.22em]">
              no metrics
            </div>
          ) : (
            agent.metrics.map((m) => (
              <div key={m.key} className="flex items-baseline gap-2">
                <span className="font-mono text-[9.5px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] flex-1">
                  {m.key.replaceAll('_', ' ')}
                </span>
                <span className="font-mono text-[10.5px] text-[var(--color-text-bright)]">
                  {m.value}
                </span>
              </div>
            ))
          )}
          {agent.notes.length > 0 && (
            <div className="mt-1.5 pt-1.5 border-t border-[var(--color-line-soft)] space-y-0.5">
              {agent.notes.map((n, i) => (
                <div
                  key={i}
                  className="text-[10px] text-[var(--color-amber-400)] flex items-start gap-1"
                >
                  <AlertTriangle className="w-2.5 h-2.5 mt-0.5 shrink-0" />
                  <span>{n}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </button>
  );
}

/* -------------------------------------------------------------------------- */

const BASIS_COLOR: Record<CognitiveClaim['basis'], string> = {
  ring: 'var(--color-rose-400)',
  ownership: 'var(--color-amber-400)',
  flow: 'var(--color-ice-400)',
  infra: 'var(--color-violet-400)',
  other: 'var(--color-text-muted)',
};

function ClaimsList({ claims }: { claims: CognitiveClaim[] }) {
  if (claims.length === 0) {
    return (
      <section className="surface px-3 py-3">
        <div className="flex items-center gap-2 mb-1">
          <ScrollText className="w-3 h-3 text-[var(--color-text-muted)]" />
          <span className="heading-tactical">Key structural claims</span>
        </div>
        <div className="font-mono text-[10.5px] text-[var(--color-text-muted)] uppercase tracking-[0.18em]">
          no edges surfaced — degraded retrieval
        </div>
      </section>
    );
  }
  return (
    <section className="surface overflow-hidden">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <ScrollText className="w-3 h-3 text-[var(--color-ice-400)]" />
        <span className="heading-tactical">Key structural claims</span>
        <span className="chip ml-auto">{claims.length}</span>
      </div>
      <div className="divide-y divide-[var(--color-line-soft)]">
        {claims.slice(0, 14).map((c, i) => (
          <div
            key={i}
            className="px-3 py-2 flex items-start gap-2"
            style={{ borderLeft: `2px solid ${BASIS_COLOR[c.basis]}` }}
          >
            <span
              className="chip text-[8.5px] mt-0.5 uppercase tracking-[0.18em]"
              style={{
                color: BASIS_COLOR[c.basis],
                borderColor: BASIS_COLOR[c.basis] + '55',
              }}
            >
              {c.basis}
            </span>
            <div className="flex-1 min-w-0">
              <div className="text-[11.5px] text-[var(--color-text-primary)] leading-snug">
                {c.statement}
              </div>
              {c.refs.length > 0 && (
                <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)] mt-0.5 truncate">
                  refs: {c.refs.slice(0, 4).join(' · ')}
                </div>
              )}
            </div>
            <span
              className="font-mono text-[10px] mt-0.5 shrink-0"
              style={{ color: BASIS_COLOR[c.basis] }}
            >
              {(c.confidence * 100).toFixed(0)}%
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function Contradictions({
  list,
}: {
  list: CognitiveReport['contradictions'];
}) {
  return (
    <section className="surface overflow-hidden">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)] bg-[rgba(244,63,94,0.04)]">
        <AlertTriangle className="w-3 h-3 text-[var(--color-rose-400)]" />
        <span className="heading-tactical text-[var(--color-rose-400)]">
          Contradictions
        </span>
        <span className="chip chip-rose ml-auto">{list.length}</span>
      </div>
      <div className="divide-y divide-[var(--color-line-soft)]">
        {list.slice(0, 6).map((x, i) => (
          <div key={i} className="px-3 py-2">
            <div className="text-[11.5px] text-[var(--color-rose-300)] leading-snug">
              {x.reason}
            </div>
            <div className="font-mono text-[10px] text-[var(--color-text-muted)] mt-1 truncate">
              ▸ {x.claimA}
            </div>
            <div className="font-mono text-[10px] text-[var(--color-text-muted)] truncate">
              ▸ {x.claimB}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* -------------------------------------------------------------------------- */

function ExplanationsList({
  explanations,
}: {
  explanations: Record<string, string>;
}) {
  const entries = Object.entries(explanations);
  if (entries.length === 0) return null;
  return (
    <section className="surface overflow-hidden">
      <div className="px-3 h-8 flex items-center gap-2 border-b border-[var(--color-line-soft)]">
        <CheckCircle2 className="w-3 h-3 text-[var(--color-emerald-400)]" />
        <span className="heading-tactical">Why each entity surfaced</span>
        <span className="chip ml-auto">{entries.length}</span>
      </div>
      <div className="divide-y divide-[var(--color-line-soft)]">
        {entries.slice(0, 10).map(([vid, reason]) => (
          <div key={vid} className="px-3 py-2">
            <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-[var(--color-ice-400)]">
              {vid}
            </div>
            <div className="text-[11px] text-[var(--color-text-secondary)] mt-0.5 leading-relaxed">
              {reason}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
