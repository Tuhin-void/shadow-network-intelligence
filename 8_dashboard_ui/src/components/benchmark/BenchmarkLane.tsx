import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { cn } from '@/lib/utils';
import {
  AlertOctagon,
  Brain,
  Check,
  ChevronRight,
  Clock,
  Cpu,
  ExternalLink,
  Eye,
  Gauge,
  GitBranch,
  Hand,
  Layers,
  Network,
  ShieldAlert,
  Spline,
  X,
  Zap,
} from 'lucide-react';
import type { BenchmarkMethod, MethodResult, PresetSnapshot } from '@/types/intel';
import { useIntelStore } from '@/store/intel-store';
import { forensicMetricsFor, parseTraceStep } from '@/lib/benchmark-metrics';
import { runQuery, queriesForPreset } from '@/lib/queries';

const methodMeta: Record<
  BenchmarkMethod,
  {
    label: string;
    sub: string;
    icon: typeof Brain;
    accent: string;
    border: string;
    bg: string;
    soft: string;
  }
> = {
  pure_llm: {
    label: 'Pure LLM',
    sub: 'no retrieval',
    icon: Brain,
    accent: 'text-[var(--color-rose-400)]',
    border: 'border-[rgba(244,63,94,0.32)]',
    bg: 'bg-[rgba(244,63,94,0.04)]',
    soft: 'bg-[rgba(244,63,94,0.08)]',
  },
  vector_rag: {
    label: 'Vector RAG',
    sub: 'chunk retrieval',
    icon: Layers,
    accent: 'text-[var(--color-amber-400)]',
    border: 'border-[rgba(245,158,11,0.3)]',
    bg: 'bg-[rgba(245,158,11,0.04)]',
    soft: 'bg-[rgba(245,158,11,0.08)]',
  },
  graph_rag: {
    label: 'Graph RAG',
    sub: 'topology-aware',
    icon: Network,
    accent: 'text-[var(--color-ice-300)]',
    border: 'border-[rgba(34,211,238,0.4)]',
    bg: 'bg-[rgba(34,211,238,0.05)]',
    soft: 'bg-[rgba(34,211,238,0.12)]',
  },
};

interface BenchmarkLaneProps {
  method: BenchmarkMethod;
  result: MethodResult;
  groundTruth: string;
  /** Showdown phase (0 standby → 4 verdict). Drives reveal choreography. */
  phase?: 0 | 1 | 2 | 3 | 4;
}

export function BenchmarkLane({
  method,
  result,
  groundTruth,
  phase = 4,
}: BenchmarkLaneProps) {
  const navigate = useNavigate();
  const { active, applyQuery } = useIntelStore();
  const m = methodMeta[method];
  const Icon = m.icon;
  const totalRel = result.relationshipsFound + result.relationshipsMissed;
  const recall = totalRel ? result.relationshipsFound / totalRel : 0;
  const fx = forensicMetricsFor(method, result);

  const isWinner = method === 'graph_rag';
  const dimOthers = phase >= 3 && !isWinner;
  const winnerLift = phase >= 3 && isWinner;
  const showLane = phase >= 1;
  const showMetrics = phase >= 2;
  const showRevealBlocks = phase >= 3;

  const [forensicsOpen, setForensicsOpen] = useState(false);
  const [blindSpotOpen, setBlindSpotOpen] = useState<string | null>(null);

  // Apply a trace step to the live graph — only meaningful for graph_rag,
  // but Vector / LLM steps still flash a focus hint.
  const runTrace = (step: string) => {
    const action = parseTraceStep(step);
    const presetQueries = queriesForPreset(active);
    let transform = null;
    switch (action.kind) {
      case 'path':
      case 'reverse':
        transform = runQuery(active, presetQueries.find((q) => q.kind === 'shortest_path')!);
        break;
      case 'ring':
        transform = runQuery(
          active,
          presetQueries.find((q) => q.kind === 'isolate_ring')!
        );
        break;
      case 'cluster':
      case 'fingerprint':
      case 'address': {
        const sharedQ = presetQueries.find((q) => q.kind === 'find_shared_infra');
        transform = sharedQ ? runQuery(active, sharedQ) : null;
        break;
      }
      default:
        transform = null;
    }
    if (transform) applyQuery({ ...transform, narrationLine: `trace · ${step}` });
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, filter: 'blur(8px)' }}
      animate={{
        opacity: showLane ? (dimOthers ? 0.45 : 1) : 0,
        y: 0,
        filter: 'blur(0px)',
        scale: winnerLift ? 1.02 : 1,
      }}
      transition={{ duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        'surface relative min-h-0 overflow-hidden h-full',
        m.border,
        winnerLift && 'glow-ice'
      )}
      style={{
        display: 'grid',
        gridTemplateRows: 'auto auto minmax(0, 1fr)',
      }}
    >
      {/* Header */}
      <div className={cn('px-3 py-2.5 border-b border-[var(--color-line-soft)]', m.bg)}>
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center justify-center w-7 h-7 rounded-sm border',
              m.border,
              m.soft,
              m.accent
            )}
          >
            <Icon className="w-3.5 h-3.5" />
          </span>
          <div className="flex flex-col leading-tight">
            <span className={cn('text-[12px] font-semibold tracking-wide', m.accent)}>
              {m.label}
            </span>
            <span className="font-mono text-[9px] uppercase tracking-[0.22em] text-[var(--color-text-muted)]">
              {m.sub}
            </span>
          </div>
          <div className="ml-auto flex items-center gap-1.5">
            <AnimatePresence>
              {showMetrics && (
                <>
                  <motion.span
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4 }}
                    className="chip text-[9px]"
                  >
                    <Clock className="w-2.5 h-2.5" />
                    {(result.latencyMs / 1000).toFixed(2)}s
                  </motion.span>
                  <motion.span
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: 0.1 }}
                    className="chip text-[9px]"
                  >
                    <Cpu className="w-2.5 h-2.5" />
                    {result.tokens}
                  </motion.span>
                  <motion.span
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.4, delay: 0.15 }}
                    className="chip text-[9px]"
                    title="estimated cost"
                  >
                    $ {fx.cost.toFixed(3)}
                  </motion.span>
                </>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Metrics row */}
      <div className="grid grid-cols-4 gap-px bg-[var(--color-line-soft)]">
        <Metric
          label="Confidence"
          value={`${Math.round(result.confidence * 100)}%`}
          tone={m.accent}
          visible={showMetrics}
          delay={0}
        />
        <Metric
          label="Hops"
          value={result.hops}
          tone={m.accent}
          visible={showMetrics}
          delay={0.1}
        />
        <Metric
          label="Recall"
          value={`${Math.round(recall * 100)}%`}
          tone={m.accent}
          visible={showMetrics}
          delay={0.2}
        />
        <Metric
          label="Rings"
          value={result.ringsDetected}
          tone={m.accent}
          visible={showMetrics}
          delay={0.3}
        />
      </div>

      {/* Body */}
      <div className="min-h-0 overflow-y-auto scroll-tactical">
        {/* Answer — click to drill into investigation */}
        <AnimatePresence>
          {showMetrics && (
            <Block
              label="Answer"
              action={
                isWinner ? (
                  <button
                    onClick={() => navigate('/investigate')}
                    className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-ice-400)] hover:underline flex items-center gap-1"
                    title="open in manual workspace"
                  >
                    <Hand className="w-2.5 h-2.5" />
                    investigate
                  </button>
                ) : null
              }
            >
              <motion.p
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="text-[12px] text-[var(--color-text-primary)] leading-relaxed"
              >
                {result.answer}
              </motion.p>
            </Block>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {showRevealBlocks && (
            <>
              {/* Forensic metrics — collapsible */}
              <Block
                label="Forensic metrics"
                action={
                  <button
                    onClick={() => setForensicsOpen((v) => !v)}
                    className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-ice-400)] flex items-center gap-1"
                  >
                    {forensicsOpen ? 'collapse' : 'expand'}
                    <ChevronRight
                      className={cn('w-2.5 h-2.5 transition-transform', forensicsOpen && 'rotate-90')}
                    />
                  </button>
                }
              >
                <AnimatePresence initial={false}>
                  {forensicsOpen ? (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.24 }}
                      className="overflow-hidden"
                    >
                      <div className="grid grid-cols-2 gap-1.5 mt-1">
                        <ForensicCell
                          icon={GitBranch}
                          label="edges traversed"
                          value={fx.edgesTraversed.toLocaleString()}
                          tone={m.accent}
                        />
                        <ForensicCell
                          icon={Eye}
                          label="topology coverage"
                          value={`${Math.round(fx.topologyCoverage * 100)}%`}
                          tone={m.accent}
                        />
                        <ForensicCell
                          icon={ShieldAlert}
                          label="hallucination risk"
                          value={`${Math.round(fx.hallucinationRisk * 100)}%`}
                          tone={
                            fx.hallucinationRisk > 0.3
                              ? 'text-[var(--color-rose-400)]'
                              : 'text-[var(--color-emerald-400)]'
                          }
                        />
                        <ForensicCell
                          icon={AlertOctagon}
                          label="blind spot severity"
                          value={`${Math.round(fx.blindSpotSeverity * 100)}%`}
                          tone={
                            fx.blindSpotSeverity > 0.4
                              ? 'text-[var(--color-rose-400)]'
                              : 'text-[var(--color-emerald-400)]'
                          }
                        />
                        <ForensicCell
                          icon={Spline}
                          label="evidence completeness"
                          value={`${Math.round(fx.evidenceCompleteness * 100)}%`}
                          tone={m.accent}
                        />
                        <ForensicCell
                          icon={Zap}
                          label="confidence propagation"
                          value={`${Math.round(fx.confidencePropagation * 100)}%`}
                          tone={m.accent}
                        />
                      </div>
                    </motion.div>
                  ) : (
                    <CompactForensics fx={fx} m={m} />
                  )}
                </AnimatePresence>
              </Block>

              {/* Retrieval / reasoning trace — click each to drive the graph */}
              <Block label="Retrieval / reasoning trace">
                <ol className="space-y-1.5">
                  {result.trace.map((t, i) => {
                    const action = parseTraceStep(t);
                    const interactable =
                      action.kind === 'path' ||
                      action.kind === 'ring' ||
                      action.kind === 'reverse' ||
                      action.kind === 'cluster' ||
                      action.kind === 'fingerprint' ||
                      action.kind === 'address';
                    return (
                      <motion.li
                        key={t}
                        initial={{ opacity: 0, x: -6 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.35, delay: i * 0.06 }}
                        className="flex items-start gap-2 text-[11px]"
                      >
                        <span
                          className={cn(
                            'inline-flex items-center justify-center w-4 h-4 rounded-sm border font-mono text-[9px] shrink-0',
                            m.border,
                            m.accent
                          )}
                        >
                          {i + 1}
                        </span>
                        {interactable ? (
                          <button
                            onClick={() => runTrace(t)}
                            className="font-mono text-[11px] text-left flex-1 group"
                            title="apply this step to the live graph"
                          >
                            <span className="text-[var(--color-text-secondary)] group-hover:text-[var(--color-ice-400)] leading-relaxed">
                              {t}
                            </span>
                            <span className="ml-2 inline-flex items-center font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] group-hover:text-[var(--color-ice-400)]">
                              ▸ {action.sub}
                            </span>
                          </button>
                        ) : (
                          <span className="font-mono text-[11px] text-[var(--color-text-secondary)] leading-relaxed">
                            {t}
                            <span className="ml-2 font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-faint)]">
                              · {action.sub}
                            </span>
                          </span>
                        )}
                      </motion.li>
                    );
                  })}
                </ol>
              </Block>

              {/* Blind spots — each click highlights what's missing */}
              {result.blindSpots.length > 0 ? (
                <Block label="Blind spots" warning>
                  <ul className="space-y-1">
                    {result.blindSpots.map((b) => {
                      const open = blindSpotOpen === b;
                      return (
                        <motion.li
                          key={b}
                          initial={{ opacity: 0, x: -4 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          <button
                            onClick={() => setBlindSpotOpen(open ? null : b)}
                            className="w-full flex items-start gap-2 text-[11px] text-left group"
                            title="explain what was missed"
                          >
                            <X className="w-3 h-3 text-[var(--color-rose-400)] mt-0.5 shrink-0" />
                            <span className="text-[var(--color-text-secondary)] group-hover:text-[var(--color-rose-300)] flex-1">
                              {b}
                            </span>
                            <ChevronRight
                              className={cn(
                                'w-3 h-3 text-[var(--color-text-muted)] mt-0.5 transition-transform shrink-0',
                                open && 'rotate-90'
                              )}
                            />
                          </button>
                          <AnimatePresence>
                            {open && (
                              <motion.div
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.22 }}
                                className="overflow-hidden mt-1"
                              >
                                <BlindSpotDetail
                                  spot={b}
                                  preset={active}
                                  onShowWhatGraphFound={() => {
                                    const presetQueries = queriesForPreset(active);
                                    // Apply the strongest "shows what graph found" query
                                    const q =
                                      presetQueries.find((q) => q.kind === 'show_hidden_to') ??
                                      presetQueries.find((q) => q.kind === 'shortest_path');
                                    if (q) {
                                      applyQuery({
                                        ...runQuery(active, q),
                                        narrationLine: `graph found · what ${m.label} missed`,
                                      });
                                      navigate('/investigate');
                                    }
                                  }}
                                />
                              </motion.div>
                            )}
                          </AnimatePresence>
                        </motion.li>
                      );
                    })}
                  </ul>
                </Block>
              ) : (
                <Block label="Blind spots">
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.4 }}
                    className="flex items-center gap-2 text-[11px] text-[var(--color-emerald-400)]"
                  >
                    <Check className="w-3 h-3" />
                    <span>No structural gaps — answer matches ground truth.</span>
                  </motion.div>
                </Block>
              )}

              <Block label="Structural recall">
                <div className="flex items-center gap-2 text-[11px]">
                  <Gauge className="w-3 h-3 text-[var(--color-text-muted)]" />
                  <span className="font-mono text-[var(--color-text-secondary)]">
                    found {result.relationshipsFound}
                  </span>
                  <span className="text-[var(--color-text-muted)]">·</span>
                  <span className="font-mono text-[var(--color-rose-400)]">
                    missed {result.relationshipsMissed}
                  </span>
                  <span className="text-[var(--color-text-muted)]">·</span>
                  <span className="font-mono text-[var(--color-violet-400)]">
                    hidden {result.hiddenLinksFound}
                  </span>
                </div>
                <div className="h-1 mt-2 rounded-full bg-[var(--color-graphite-800)] overflow-hidden flex">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${recall * 100}%` }}
                    transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1] }}
                    className="h-full bg-[var(--color-emerald-500)]"
                  />
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(1 - recall) * 100}%` }}
                    transition={{ duration: 0.9, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
                    className="h-full bg-[var(--color-rose-500)] opacity-70"
                  />
                </div>
              </Block>

              {method === 'graph_rag' && (
                <Block
                  label="Ground truth alignment"
                  action={
                    <button
                      onClick={() => navigate('/reports')}
                      className="font-mono text-[9px] tracking-[0.18em] uppercase text-[var(--color-text-muted)] hover:text-[var(--color-emerald-400)] flex items-center gap-1"
                    >
                      <ExternalLink className="w-2.5 h-2.5" />
                      open dossier
                    </button>
                  }
                >
                  <motion.p
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ duration: 0.6, delay: 0.5 }}
                    className="text-[11px] text-[var(--color-text-secondary)] italic leading-relaxed"
                  >
                    {groundTruth}
                  </motion.p>
                </Block>
              )}
            </>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

/* -------------------------------------------------------------------------- */

function CompactForensics({
  fx,
  m,
}: {
  fx: ReturnType<typeof forensicMetricsFor>;
  m: (typeof methodMeta)[BenchmarkMethod];
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1 text-[10.5px] font-mono">
      <span className="text-[var(--color-text-muted)]">edges</span>
      <span className={m.accent}>{fx.edgesTraversed.toLocaleString()}</span>
      <span className="text-[var(--color-text-faint)]">·</span>
      <span className="text-[var(--color-text-muted)]">cov</span>
      <span className={m.accent}>{Math.round(fx.topologyCoverage * 100)}%</span>
      <span className="text-[var(--color-text-faint)]">·</span>
      <span className="text-[var(--color-text-muted)]">halluc</span>
      <span
        className={
          fx.hallucinationRisk > 0.3
            ? 'text-[var(--color-rose-400)]'
            : 'text-[var(--color-emerald-400)]'
        }
      >
        {Math.round(fx.hallucinationRisk * 100)}%
      </span>
    </div>
  );
}

function BlindSpotDetail({
  spot,
  preset,
  onShowWhatGraphFound,
}: {
  spot: string;
  preset: PresetSnapshot;
  onShowWhatGraphFound: () => void;
}) {
  // Try to surface what the GraphRAG topology actually contains that this
  // method missed. Mostly heuristic — but enough to drive analyst attention.
  const isOwnership = /ownership|cascade|chain|nominee/i.test(spot);
  const isDevice = /device|fingerprint/i.test(spot);
  const isReverse = /reverse|terminal|beneficiary|fund/i.test(spot);
  const isAddress = /address|jurisdiction|nicosia|vaduz/i.test(spot);

  let recoveredBy: string | null = null;
  if (isOwnership) {
    const path = preset.report.ownershipFlow[0];
    recoveredBy = path
      ? `GraphRAG recovered this via ${path.label} (${path.hops} hops)`
      : null;
  } else if (isReverse) {
    const rev = preset.paths.find((p) => p.intent === 'reverse_edge');
    recoveredBy = rev
      ? `GraphRAG used reverse traversal: ${rev.label} (${rev.hops} hops)`
      : null;
  } else if (isDevice) {
    const sig = preset.report.structuralSignals.find((s) => /device/i.test(s.name));
    recoveredBy = sig
      ? `Fingerprint signal '${sig.name}' (intensity ${sig.intensity.toFixed(2)})`
      : null;
  } else if (isAddress) {
    const sig = preset.report.structuralSignals.find((s) => /address/i.test(s.name));
    recoveredBy = sig
      ? `Address signal '${sig.name}' (intensity ${sig.intensity.toFixed(2)})`
      : null;
  }

  return (
    <div className="rounded-sm bg-[rgba(244,63,94,0.05)] border-l-2 border-[var(--color-rose-500)] px-2.5 py-2 ml-5">
      <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-[var(--color-rose-400)]">
        what was missed
      </div>
      <div className="text-[11px] text-[var(--color-text-primary)] mt-0.5 leading-snug">
        {spot}
      </div>
      {recoveredBy && (
        <div className="mt-2 text-[10.5px] text-[var(--color-emerald-400)] leading-snug">
          ✓ {recoveredBy}
        </div>
      )}
      <button
        onClick={onShowWhatGraphFound}
        className="mt-2 h-6 px-2 inline-flex items-center gap-1.5 text-[9.5px] font-mono tracking-[0.22em] uppercase rounded-sm border border-[rgba(34,211,238,0.4)] bg-[rgba(34,211,238,0.06)] text-[var(--color-ice-400)] hover:bg-[rgba(34,211,238,0.1)]"
      >
        <Eye className="w-2.5 h-2.5" />
        show on graph
      </button>
    </div>
  );
}

function ForensicCell({
  icon: Icon,
  label,
  value,
  tone,
}: {
  icon: typeof Brain;
  label: string;
  value: string;
  tone: string;
}) {
  return (
    <div className="rounded-sm bg-[rgba(255,255,255,0.012)] border border-[var(--color-line-soft)] px-2 py-1.5">
      <div className="flex items-center gap-1.5 font-mono text-[9px] tracking-[0.16em] uppercase text-[var(--color-text-muted)]">
        <Icon className={cn('w-2.5 h-2.5', tone)} />
        {label}
      </div>
      <div className={cn('font-mono text-[12px] mt-0.5', tone)}>{value}</div>
    </div>
  );
}

function Metric({
  label,
  value,
  tone,
  visible,
  delay,
}: {
  label: string;
  value: string | number;
  tone: string;
  visible: boolean;
  delay: number;
}) {
  return (
    <div className="bg-[var(--color-graphite-900)] px-2.5 py-2 relative overflow-hidden">
      <div className="label-tactical text-[9px]">{label}</div>
      <AnimatePresence>
        {visible ? (
          <motion.div
            key="v"
            initial={{ opacity: 0, y: 8, filter: 'blur(3px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0)' }}
            transition={{ duration: 0.45, delay, ease: [0.16, 1, 0.3, 1] }}
            className={cn('font-mono text-[14px] font-semibold mt-0.5', tone)}
          >
            {value}
          </motion.div>
        ) : (
          <div className="font-mono text-[14px] font-semibold mt-0.5 text-[var(--color-text-ghost)]">
            ··
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function Block({
  label,
  children,
  warning,
  action,
}: {
  label: string;
  children: React.ReactNode;
  warning?: boolean;
  action?: React.ReactNode;
}) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.35 }}
      className="px-3 py-2.5 border-b border-[var(--color-line-soft)] last:border-b-0"
    >
      <div className="flex items-center gap-2 mb-1.5">
        <div
          className={cn(
            'label-tactical flex-1',
            warning && 'text-[var(--color-rose-400)]'
          )}
        >
          {label}
        </div>
        {action}
      </div>
      {children}
    </motion.section>
  );
}
